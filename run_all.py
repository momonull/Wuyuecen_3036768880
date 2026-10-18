"""
run_all.py — 一键复现入口（根目录薄封装）

按模板要求在 code/run_all.py 保存主体逻辑；本文件仅作便捷入口，
在项目根目录执行 `python run_all.py` 时转发到 code/run_all.py，二者行为完全一致。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    entry = ROOT / "code" / "run_all.py"
    sys.exit(subprocess.run([sys.executable, str(entry)], cwd=str(ROOT)).returncode)


if __name__ == "__main__":
    main()
