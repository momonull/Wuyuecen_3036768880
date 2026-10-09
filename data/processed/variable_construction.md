# 变量构建日志 — Card & Krueger (1994) 复现

> 由 `code/01_clean.py` 生成。输入 `data/raw/public.csv`（410 行 × 46 列，未改动），输出 `data/processed/ck94_clean.csv`（410 行 × 57 列）。
> 口径依据 `PROJECT_PLAN.md` §3.2 与 `output/replication_targets.md`（PDF 第 776 页逐格核对）。

## 一、构造变量一览

| 新变量 | 定义（精确口径） | 原始列 |
|---|---|---|
| `fte` | 全职当量就业 = `EMPFT + NMGRS + 0.5 × EMPPT`（全职工 + 经理 + 0.5×兼职工） | EMPFT/EMPPT/NMGRS |
| `fte2` | Wave2 全职当量就业 = `EMPFT2 + NMGRS2 + 0.5 × EMPPT2` | EMPFT2/EMPPT2/NMGRS2 |
| `pct_ft` | 全职占比(%) = `EMPFT / fte × 100` | — |
| `pct_ft2` | Wave2 全职占比(%) = `EMPFT2 / fte2 × 100` | — |
| `full_meal_price` | 全餐价格($) = `PSODA + PFRY + PENTREE` | PSODA/PFRY/PENTREE |
| `full_meal_price2` | Wave2 全餐价格($) = `PSODA2 + PFRY2 + PENTREE2` | PSODA2/PFRY2/PENTREE2 |
| `emp_chg` | 店内就业变化 = `fte2 − fte` | — |
| `wage_chg` | 起始工资变化 = `WAGE_ST2 − WAGE_ST` | — |
| `gap` | 初始工资缺口（Table 4）：PA=0；NJ 且 `WAGE_ST≥5.05`=0；其余 NJ = `(5.05−WAGE_ST)/WAGE_ST`；NJ 缺 WAGE_ST 时为缺失 | — |
| `closure` | 关店状态（分类）：`answered`/`permanent`/`temporary`/`refused` | STATUS2 |
| `bal_emp` | 就业平衡标记 = `fte` 与 `fte2` 均非缺失 | — |

未改动的原始列全部保留（`SHEET`、`CHAIN`、`CO_OWNED`、`STATE`、`WAGE_ST`、`HRSOPEN`、`BONUS`、各 `*2` 列等），保证可追溯。

## 二、关键口径说明（写代码前必读）

### 2.1 全职占比 `pct_ft` 的分母是「全职当量 fte」，不是员工总数
- `pct_ft = EMPFT / fte`，其中 `fte = EMPFT + NMGRS + 0.5×EMPPT`。
- ⚠️ 若误用「全职工（含经理）/ 员工总数」= `(EMPFT+NMGRS)/(EMPFT+NMGRS+EMPPT)`，会得到 NJ≈37.7，与论文 **32.8** 不符。
- 已用数据验证：`EMPFT/fte` 得 NJ=32.8、PA=35.0（Wave1），与论文精确一致。

### 2.2 关店处理（原文 Table 2 注）
- `STATUS2` 编码（DATA_DICTIONARY）：0=拒访，1=应答，2=翻新关闭，3=永久关闭，4=修路关闭，5=火灾关闭。
- **永久关闭 `STATUS2==3`（6 家）**：Wave2 就业 = 0。原始数据 `EMPFT2/EMPPT2/NMGRS2` 已填 0，`fte2` 自然为 0，无需额外改动（脚本保留显式语义并记录）。
- **临时关闭 `STATUS2∈{2,4,5}`（4 家）**：Wave2 就业 = 缺失。原始数据即为 NaN，`fte2` 自然为缺失。
- **拒访 `STATUS2==0`（1 家）**：Wave2 全部缺失。

### 2.3 缺失值处理策略
- **不做任何插补**。各变量在缺失处为 NaN，分析时按表 listwise 删除，并在表格注脚注明有效样本量（原文也如此）。
- 缺失规模（已核实）：`WAGE_ST` 缺 20、`WAGE_ST2` 缺 21、`EMPFT` 缺 6、`EMPFT2` 缺 12、价格列各缺 8–28。
- 例：`fte` 仅在 `EMPFT/EMPPT/NMGRS` 三者均非缺失时才有效（任一缺失则 NaN）。

## 三、样本筛选口径（供 Phase 2 使用）

| 概念 | 定义 | 计数 |
|---|---|---|
| 全样本 | 410 家（NJ 331 / PA 79） | 410 |
| 就业有效（Wave1） | `fte` 非缺失 | 398（NJ 321 / PA 77） |
| 就业有效（Wave2） | `fte2` 非缺失 | 396（NJ 319 / PA 77） |
| `bal_emp`（两期就业均有效） | `fte.notna() & fte2.notna()` | 384（NJ 309 / PA 75） |

> ⚠️ **平衡样本口径的细微差别（Table 3 row 4 需在 Phase 2 定案）**：
> - `bal_emp` = 384，**包含 6 家永久关闭店**（其 Wave2 就业=0 是"有效值"而非缺失）。
> - 若再要求 `STATUS2==1`（排除永久关闭店），得 378（NJ 304 / PA 74，即 PROJECT_PLAN §3.3 的"约 378"）。
> - 论文 Table 3 row 4 "balanced subsample" 定义为"两期均报告有效就业数据的门店"。永久关闭店 Wave2=0 是否算"有效"，需在 Phase 2 用论文精确数值（DID≈+2.76, t=2.03）反推定案。

## 四、核验结果（对照 output/replication_targets.md 原文目标值）

运行 `python code/01_clean.py` 的摘要输出与原文目标**全部精确一致**：

| 变量 | NJ | PA | 目标(NJ/PA) |
|---|---|---|---|
| Wave1 FTE | 20.44 | 23.33 | 20.4 / 23.3 |
| Wave1 起始工资 | 4.61 | 4.63 | 4.61 / 4.63 |
| Wave1 全职占比% | 32.8 | 35.0 | 32.8 / 35.0 |
| Wave1 全餐价格 | 3.35 | 3.04 | 3.35 / 3.04 |
| Wave2 FTE | 21.03 | 21.17 | 21.0 / 21.2 |
| Wave2 起始工资 | 5.08 | 4.62 | 5.08 / 4.62 |
| Wave2 全职占比% | 35.9 | 30.4 | 35.9 / 30.4 |
| Wave2 全餐价格 | 3.41 | 3.03 | 3.41 / 3.03 |

门店类型分布、关店计数也与原文一致（BK 41.1/44.3、KFC 20.5/15.2、Roy 24.8/21.5、Wendy 13.6/19.0、直营 34.1/35.4；永久 6 / 临时 4 / 拒访 1）。
