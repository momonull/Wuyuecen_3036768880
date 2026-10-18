---
name: ck94-replication
description: Replicate Card & Krueger (1994) "Minimum Wages and Employment" Table 2/3/4 and Figure 1, plus a triple-difference (DDD) ownership-heterogeneity extension. Use whenever reproducing or extending the fast-food minimum-wage DID results from the AER 84(4) paper.
---

# Card & Krueger (1994) 复现与扩展技能

本技能封装「从原始门店级数据 `public.csv` 复现 CK94 的 Table 2–4 与 Figure 1，并做独立 DDD 扩展」的全部可复用口径与步骤。技能入口脚本见 `code/`，一键跑通见 `run_all.py`。

## 输入

- `data/raw/public.csv`：410 行 × 46 列门店级调查数据（课程受限数据，从 `01_DID.zip` 解压，**不入库**）。
- 原文目标值归档于 `outputs/replication_targets.md`（PDF 第 776 页逐格核对，经数据交叉验证）。

## 关键口径（写代码/复核前必读，错了会全错）

| 变量 | 定义 |
| --- | --- |
| 全职当量就业 FTE | `EMPFT + NMGRS + 0.5 * EMPPT`（全职含经理 + 0.5×兼职） |
| Wave2 FTE | `EMPFT2 + NMGRS2 + 0.5 * EMPPT2` |
| 全职占比 (%) | `EMPFT / FTE * 100` —— 分母是 **FTE**，**不是**员工总数（否则得 37.7 而非论文 32.8） |
| 全餐价格 | `PSODA + PFRY + PENTREE` |
| GAP（Table 4 关键自变量） | `(5.05 − WAGE_ST) / WAGE_ST`；PA 或 NJ 起始工资 ≥ 5.05 时取 0 |
| 店内就业变化 | `fte2 − fte`（Table 3 用**列均值之差**，不是店内变化均值） |

## 关店处理（原文 Table 2 注）

- 永久关闭 `STATUS2 == 3`（6 家）→ Wave2 就业 = 0（原始数据已填 0）。
- 临时关闭 `STATUS2 ∈ {2,4,5}`（4 家）→ Wave2 就业 = 缺失。
- 拒访 `STATUS2 == 0`（1 家）→ Wave2 全部缺失。
- 不插补，脚本显式记录规则即可。

## 样本口径（每张表不同，务必用对）

- **Table 2**：全样本描述统计，分 NJ/PA × Wave1/Wave2。
- **Table 3（DID）**：列均值之差 `DID = (NJ Wave2 − NJ Wave1) − (PA Wave2 − PA Wave1)` ≈ +2.754（t≈2.05，Welch 两样本 SE）。
- **Table 4（简约式，N=357）**：**不是**字面「两期就业 + 两期工资均有效」（那只得 351）。正确口径 = 「两期就业 + Wave1 工资有效」∩「Wave2 工资有效 **或** 永久关闭」= 351 完整店 + 6 永久关闭店 = **357**。用错口径因变量均值会从 −0.237 掉到 −0.03，GAP 系数从 15.65 漂到 17.05。
- **扩展 DDD（平衡样本 384）**：两期就业均有效（含 6 家永久关闭店）。

## 复现步骤

1. `python run_all.py`（或逐条跑 `code/01_clean.py` → `02_tables.py` → `03_figure.py` → `04_extension.py` → `05_report.py`）。
2. 每步产物对照 `outputs/replication_targets.md` 目标值逐项核对。

## 复现中的 6 处口径出入（已定案，别回退）

1. 全职占比分母用 **FTE**，非员工总数（见上表）。
2. Table 4 样本 = **357**（含 6 家永久关闭店），非 351。
3. Wave2「招聘奖金」对应 **`SPECIAL2`**，数据无 `BONUS2` 列。
4. Table 4 列(v) GAP = 11.98 vs 论文 11.91（差 0.07，源于地区哑变量编码微差，接受并注明）。
5. PA Wave1 起始工资 = **4.63**（非 4.62）。
6. 平衡样本 = **384**（含永久关闭店），非「约 378」。

## 独立扩展（方案 A：所有权异质性 DDD）

- 回归：`Δemp = α + β·STATE + γ·CO_OWNED + δ·(STATE × CO_OWNED) + ε`，关注 δ。
- 四组均值手算分解：加盟 DID = 3.13、直营 DID = 2.04、DDD δ = −1.10（HC1 SE 2.44，t≈−0.45，不显著）。
- **坑**：`STATE` 与地区哑变量（SOUTHJ/CENTRALJ/PA1/PA2）在两州设定下**完全共线**，DDD 回归里不要同时放，否则 `SingularMatrixWarning`。
- δ 对是否控制初始规模 `fte` 敏感（加品牌 FE 后 δ≈−1.14，再加 `fte` 反转为 +1.51），结论应诚实报告「无稳健可识别的所有权异质性」。

## 交叉验证（可选加分）

- Stata `code/02_tables.do`：`reg` 复现核心 DID（`chg = fte2 − fte` 对 `STATE`，点估计 2.75）与 DDD（`sxo` 系数 −1.095292，与 Python 精确到 6 位小数一致）。
- 注意：Stata 默认同方差 SE（DID t≈2.38），Python 用 Welch/HC1 稳健 SE（t≈2.05），**点估计一致、SE 约定不同**，报告须分开注明。
