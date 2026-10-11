# Card & Krueger (1994) 复现与扩展 — 可复现工作流

复现 Card, D., & Krueger, A. B. (1994). *Minimum Wages and Employment: A Case Study of the
Fast-Food Industry in New Jersey and Pennsylvania.* American Economic Review, 84(4), 772–793
的 **Table 2–4 与 Figure 1**，并完成一个**独立扩展**（所有权异质性：直营 vs 加盟）。

| 目标 | 状态 |
|---|---|
| Table 2 描述性统计（NJ/PA × Wave1/Wave2） | ✅ 复现一致 |
| Table 3 核心 DID（FTE 就业，DID ≈ +2.76） | ✅ 复现一致（+2.754, t=2.05） |
| Table 4 简约式回归（NJ dummy ≈ 2.33、GAP ≈ 15.65） | ✅ 复现一致 |
| Figure 1 起始工资分布（2×2 面板） | ✅ 复现一致 |
| 独立扩展（DDD：直营 vs 加盟） | ✅ 完成（δ = −1.10，不显著） |

---

## 1. 输入数据（受限，不入库）

原始门店级调查数据 `public.csv`（410 行 × 46 列）为**课程内受限数据，未上传到本仓库**。
获取方式：从课程提供的 `01_DID.zip` 解压得到 `public.csv`，放入：

```
data/raw/public.csv
```

> 文件名与位置**不能改**，否则一键复现会失败。`.gitignore` 已排除该文件及 `*.zip`、`01_DID/`。

## 2. 环境要求

- Python 3.9+（开发环境 3.13；numpy 2.3 / pandas 2.3 / statsmodels 0.15 / matplotlib 3.11 / python-docx 1.2 已实测）。
- 依赖安装：

```bash
pip install -r requirements.txt
```

（可选）Stata 交叉验证脚本 `code/02_tables.do`（见 §6），Python 为主、Stata 仅作验证。

## 3. 一键复现命令

在项目根目录：

```bash
python run_all.py
```

该命令从 `data/raw/public.csv` 出发，依次运行 `01_clean → 02_tables → 03_figure → 04_extension → 05_report`，
**全自动**生成以下产物（无需手动改数据或代码）：

| 步骤 | 脚本 | 产出 |
|---|---|---|
| 数据清洗 | `code/01_clean.py` | `data/processed/ck94_clean.csv`、`output/clean_verification.txt` |
| 复现表 | `code/02_tables.py` | `output/tables/table2.md` `table3.md` `table4.md` `replication_check.md` |
| 复现图 | `code/03_figure.py` | `output/figures/figure1.png` |
| 独立扩展 | `code/04_extension.py` | `output/tables/extension.md`、`output/figures/extension_ddd.png` |
| 实证报告 | `code/05_report.py` | `report/report.md`、`report/report_en.docx`、`report/report_bilingual.docx` |

清空输出（若需要干净重跑）：删除 `data/processed/*.csv` 与 `output/tables|figures` 下产物即可；
`run_all.py` 会重新生成。

## 4. 目录结构

```
personal project/
├── data/
│   ├── raw/            # 放 public.csv（受限，不入库）
│   └── processed/      # 01_clean.py 生成的 ck94_clean.csv + 变量构建日志
├── code/
│   ├── 01_clean.py     # 数据清洗与变量构建
│   ├── 02_tables.py    # 复现 Table 2/3/4
│   ├── 03_figure.py    # 复现 Figure 1
│   ├── 04_extension.py # 独立扩展（DDD 所有权异质性）
│   ├── 05_report.py    # 生成实证报告（md + 英文 Word + 中英对照 Word）
│   └── 02_tables.do    # （可选）Stata 交叉验证核心 DID
├── output/
│   ├── tables/         # 复现表 + 扩展表（markdown）
│   └── figures/        # figure1.png + extension_ddd.png
├── report/             # 实证报告：report.md / report_en.docx / report_bilingual.docx
├── run_all.py          # 一键复现入口（含报告）
├── requirements.txt
├── PROJECT_PLAN.md     # 执行计划
├── AI_USE_DISCLOSURE.md# AI 使用披露
├── DATA_DICTIONARY.md  # 原始数据字典
└── README.md
```

## 5. 关键口径（写代码/复核前必读）

- **FTE 就业** = `EMPFT + NMGRS + 0.5 × EMPPT`（全职含经理 + 0.5×兼职）。
- **全职占比 (%)** = `EMPFT / FTE × 100`（分母是 FTE，**不是**员工总数）。
- **全餐价格** = `PSODA + PFRY + PENTREE`。
- **Table 3「变化」** = 列均值之差（Wave2 均值 − Wave1 均值），**不是**店内变化 `emp_chg` 的均值。
- **永久关闭店**（`STATUS2==3`，6 家）Wave2 就业 = 0；**临时关闭店**（`STATUS2∈{2,4,5}`，4 家）Wave2 就业 = 缺失。
- **Table 4 样本 = 357** = 两期就业 + Wave1 工资有效，且（Wave2 工资有效 或 永久关闭）。
- **GAP** = `(5.05 − W0)/W0`；PA 或 NJ 起始工资 ≥ 5.05 时取 0。
- 完整口径见 `data/processed/variable_construction.md` 与 `output/replication_targets.md`。

## 6. Stata 交叉验证（可选加分）

`code/02_tables.do` 用 `reg` 独立复现核心 DID（`chg = fte2 − fte` 对 `STATE` 回归，结果 ≈ +2.75），
与 Python 对照一致后，报告第 6 节注明「Python 与 Stata 结果一致」。

## 7. AI 使用披露

AI（Claude Code）在本项目中的用途、核查方式与纠错记录见 [AI_USE_DISCLOSURE.md](AI_USE_DISCLOSURE.md)。

## 8. 数据访问说明（原课程下载信息）

本仓库数据来自课程数据包，各 ZIP 对应项目如下；本复现项目仅需 `01_DID.zip`（解压得 `public.csv`）：

| 项目 | 所需数据包 |
|---|---|
| Card and Krueger: minimum wage / DID | 01 |
| Fama and French: three-factor | 02 和 04 |
| Shleifer / Greenwood and Sammon: index effect | 03 和 04 |
| Jegadeesh and Titman: momentum | 02 和 03 |

列定义见 `DATA_DICTIONARY.md`。原始 CSV 内容未改动；请在课程允许的数据访问条款内使用，勿将受限原始数据上传至公开仓库。
