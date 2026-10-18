"""
run_all.py — 一键复现入口（可复用工作流）

从原始输入 data/raw/public.csv 出发，按顺序调用全部脚本，自动生成所有表图与实证报告，
无需手动改数据或代码（硬性要求，见 PROJECT_PLAN §6.1）。

顺序与产出：
  01_clean.py     → data/processed/ck94_clean.csv + outputs/clean_verification.txt
  02_tables.py    → outputs/tables/{table2,table3,table4,replication_check}.md
  03_figure.py    → outputs/figures/figure1.png
  04_extension.py → outputs/tables/extension.md + outputs/figures/extension_ddd.png
  05_report.py    → report/report.md + report_en.docx + report_bilingual.docx

用法（在项目根目录）：
  python run_all.py            # 根目录薄封装，转发到本脚本
  python code/run_all.py       # 直接运行本脚本

前置条件：
  1. Python 3.x + requirements.txt 中的依赖（numpy / pandas / statsmodels / matplotlib / python-docx）。
  2. 受限数据 public.csv 已放入 data/raw/（获取方式见 README；该文件不入库）。
"""

import subprocess
import sys
from pathlib import Path

# Windows 控制台默认可能用 GBK 编码，强制 stdout 用 UTF-8，避免中文摘要乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 本文件位于 code/ 子目录，项目根目录是上一级
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ["01_clean.py", "02_tables.py", "03_figure.py", "04_extension.py", "05_report.py"]


def main():
    raw = ROOT / "data" / "raw" / "public.csv"
    if not raw.exists():
        print(f"[ERROR] 未找到原始数据 {raw}")
        print("        请先把受限数据 public.csv 放入 data/raw/（从 01_DID.zip 解压，获取方式见 README）。")
        sys.exit(1)

    for s in SCRIPTS:
        script = ROOT / "code" / s
        print(f"\n{'=' * 60}\n=== 运行 {s} ===\n{'=' * 60}")
        result = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
        if result.returncode != 0:
            print(f"\n[FAIL] {s} 退出码 {result.returncode}，流程中止。")
            sys.exit(result.returncode)

    print("\n" + "=" * 60)
    print("全部完成。表图见 outputs/tables/ 与 outputs/figures/，报告见 report/。")
    print("=" * 60)


if __name__ == "__main__":
    main()
