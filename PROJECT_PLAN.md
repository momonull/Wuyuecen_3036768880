# Card & Krueger (1994) 复现与扩展 — 项目执行计划

> 目标论文：Card, D., & Krueger, A. B. (1994). *Minimum Wages and Employment: A Case Study of the Fast-Food Industry in New Jersey and Pennsylvania.* American Economic Review, 84(4), 772–793.
>
> 任务：复现 **Table 2–4 与 Figure 1**（Table 1 因数据受限不要求）；完成**一个独立扩展**；交付**可复现工作流 + 实证报告 + AI 使用披露**，最终以 GitHub 仓库提交。
>
> 工具偏好：**Python（主）+ Stata（交叉验证）**。

---

## 0. 你要交付什么（六大交付物）

| # | 交付物 | 占分 | 一句话要求 |
|---|---|---|---|
| 1 | 实证报告 (empirical report) | 含在 5%+5% | 完整说明问题、数据、设计、复现、扩展、结论 |
| 2 | 复现包 (reproducibility package) | 20% | 原始数据/访问说明 + 处理数据 + 完整代码 + README |
| 3 | 可复现工作流 (skill/workflow) | 20% | 一个命令从输入数据生成所有表图，无需手动改数据/代码 |
| 4 | GitHub 仓库 + 提交历史 | 20% | 可 clone，有清晰的阶段性 commit，不是一次性上传 |
| 5 | 独立扩展 (independent extension) | 20% | 回答一个清晰的经济学问题 |
| 6 | AI 使用披露 | 5% | 说明 AI 用在哪、如何核查、纠正/拒绝了哪些错误 |

**评分权重对照**：理解论文与设计 5% · 数据与变量构建 25% · 核心复现与验证 25% · 独立扩展 20% · 可复现与工作流 20% · 报告与 AI 披露 5%。

---

## 1. 总体路线图

| 阶段 | 内容 | 大致占比 | 里程碑产出 |
|---|---|---|---|
| **Phase 0** | 读懂论文 + 搭环境 + 建 git | — | 目标数值清单、目录结构、首次 commit |
| **Phase 1** | 数据与变量构建 | 25% | `processed.csv` + 变量构建日志 |
| **Phase 2** | 核心复现（Table 2/3/4 + Fig 1） | 25% | 四张图表 + 与原文对照表 |
| **Phase 3** | 独立扩展 | 20% | 扩展分析 + 稳健性 + 解释 |
| **Phase 4** | 可复现工作流 + README | 20% | 一键复现脚本/工作流 |
| **Phase 5** | 报告 + AI 披露 | 10% | `report/` 终稿 |
| **Phase 6** | GitHub 提交与终检 | — | 仓库 URL |

---

## 2. Phase 0 — 读懂论文，搭好地基

### 2.1 把论文读透（这是复现的"标准答案"）

先精读 PDF，**手工摘出 Table 2–4 和 Figure 1 的目标数值**，做成一张"复现对照表"（后面 Phase 2 每一步都拿它比对）。至少记下：

- **Table 2（描述性统计）**：NJ 与 PA 两州，Wave 1 / Wave 2 各列，变量包括起始工资、FTE 就业、全职/兼职/经理人数、全餐价格（汽水+薯条+主菜）、营业小时等，以及各自的均值（和标准误）。
- **Table 3（核心 DID）**：就业人数"之前/之后/变化"，分 PA / NJ / 差异(NJ−PA) 三列，另按 NJ 初始工资分组（=$4.25 / $4.26–$4.99 / ≥$5.00）作列；行含"全样本变化""平衡样本变化"。**核心目标值：DID ≈ +2.76 FTE（t=2.03）**。
- **Table 4（简约式回归）**：因变量为两期 FTE 变化，关键系数 **NJ dummy ≈ 2.33 (SE 1.19)**、**GAP ≈ 15.65 (SE 6.08)**（样本 357 家）。
- **Figure 1（工资分布）**：NJ/PA × Wave1/Wave2 四张起始工资直方图，标出 $4.25 与 $5.05 两条参考线。

### 2.2 明确研究设计（报告第 3 节的骨架）

- **处理组**：新泽西州 NJ（1992/4/1 最低工资 $4.25 → $5.05）。
- **对照组**：宾州东部 PA（保持 $4.25）。
- **前**：Wave 1（1992 年 2–3 月）；**后**：Wave 2（1992 年 11–12 月）。
- **识别**：2×2 DID。关键假设：若无最低工资上调，NJ 与 PA 就业变化趋势相同（平行趋势，用东部 PA 作近似控制）。

### 2.3 建目录结构 + 初始化 git

```
personal project/
├── data/
│   ├── raw/            # public.csv（原始，不改动）
│   └── processed/      # 处理后的数据
├── code/
│   ├── 01_clean.py     # 数据清洗与变量构建
│   ├── 02_tables.py    # 复现 Table 2/3/4
│   ├── 03_figure.py    # 复现 Figure 1
│   ├── 04_extension.py # 独立扩展
│   └── run_all.py      # 一键复现入口
│   └── (可选) 02_tables.do  # Stata 交叉验证
├── output/
│   ├── tables/
│   └── figures/
├── report/
│   └── report.md / report.pdf
├── README.md
├── PROJECT_PLAN.md
└── AI_USE_DISCLOSURE.md
```

- 立即 `git init`，创建 `.gitignore`（忽略 `__pycache__/`、`.ipynb_checkpoints/`、输出缓存等）。
- **从现在起每完成一个里程碑就 commit 一次**（这是评分点，务必保留清晰历史）。

### 2.4 语言分工（Python 主 + Stata 交叉验证）

| 环节 | 推荐工具 | 理由 |
|---|---|---|
| 数据清洗、变量构建 | Python (pandas) | 透明、可 version-control、适合放 GitHub |
| 复现表/图、回归 | Python (statsmodels / linearmodels) | 免费可复现，评分者能直接跑 |
| **交叉验证** | Stata `.do` | 用 `diff` / `reghdfe` 独立算一遍 DID，作为"验证"环节的加分项 |
| 报告 | Markdown → PDF | 公式、图表易维护 |

> 建议：**以 Python 为主力**（因为 GitHub 可复现性是最重的一项），同时提供一份 Stata `.do` 复现核心 DID 表作为验证，呼应你"Python 和 Stata 都偏好"。

---

## 3. Phase 1 — 数据与变量构建（25%）

### 3.1 数据概况（已核实）

- `public.csv`：**410 行 × 46 列**，快餐店门店级调查数据。
- 州：NJ 331 家、PA 79 家。
- 品牌：Burger King 171 / KFC 80 / Roy Rogers 99 / Wendy's 60。
- 所有权：加盟 269 / 直营 141。
- Wave 2 状态：399 家成功回访，另有 6 家永久/翻新/修路/火灾关店等。

### 3.2 核心变量定义（写进代码注释与变量构建日志）

| 变量 | 定义（务必精确） |
|---|---|
| `fte` | **FTE 就业 = `EMPFT` + `NMGRS` + 0.5 × `EMPPT`**（全职工 + 经理 + 0.5×兼职工） |
| `fte2` | `EMPFT2` + `NMGRS2` + 0.5 × `EMPPT2` |
| `wage_st` / `wage_st2` | 起始时薪（美元/小时） |
| `full_meal_price` | `PSODA` + `PFRY` + `PENTREE`（全餐价格，Wave2 同理） |
| `state` | 1 = NJ（处理），0 = PA（控制） |
| `emp_chg` | `fte2 − fte`（店内就业变化，注意与"列均值之差"的区别，见 4.3） |
| `wage_chg` | `wage_st2 − wage_st` |

### 3.3 缺失值与样本筛选（每个决策都要记录理由）

- 关键列缺失情况（已核实）：`WAGE_ST` 缺 20、`WAGE_ST2` 缺 21、价格列各缺 17–28、`STATUS2` 几乎完整。
- **平衡样本** = `STATUS2 == 1` 且 Wave1/Wave2 关键变量都非缺失（约 NJ 304 + PA 74）。
- 处理策略（示例，写进日志）：
  - 复现 Table 3 时**分别报告**"全样本"与"平衡样本"（原文也这样做）。
  - 工资/价格缺失 → 各表 listwise 删除，**在表格注脚说明有效样本量**。
  - 任何删补决策都要在"变量构建日志"里记录：删了多少、为什么、对结果影响多大。

### 3.4 产出物

1. `code/01_clean.py`：从 `data/raw/public.csv` → 生成 `data/processed/ck94_clean.csv`（含所有构造变量）。
2. `data/processed/` 下附一份 `variable_construction.md`（或代码内长注释），逐条写清变量定义与清洗选择。

---

## 4. Phase 2 — 核心复现与验证（25%）

> 每一步都拿 Phase 0 摘出的"原文目标数值"比对，差异写进报告第 4 节"差异与解释"。

### 4.1 Table 2（描述性统计）

- 用 `groupby(['STATE'])` 分别算 Wave1/Wave2 各变量均值（可附标准误/样本量）。
- 表结构：行 = 变量，列 = NJ_w1 / NJ_w2 / PA_w1 / PA_w2（或 NJ/PA 两栏各含前后）。
- **验证**：NJ 起始工资应从 ~$4.61 升至 ~$5.08，PA 基本不变（~$4.63 → ~$4.62）。

### 4.2 Table 3（核心 DID 表）

- 主结构：三行 `PA` / `NJ` / `差异 (NJ − PA)`，行内分 `之前` / `之后` / `变化`（FTE 就业）。
- 附加列：NJ 店按 Wave-1 起始工资分组（=$4.25 / $4.26–$4.99 / ≥$5.00，N=101/140/73）及其对比列。
- 五行为：①之前 FTE ②之后 FTE ③变化(列均值差) ④变化(平衡样本) ⑤变化(临时关闭店=0)。
- **目标值**：DID ≈ **+2.76**（t=2.03）；NJ 高工资店(≥$5.00)变化 ≈ −2.16，与 PA(−2.28) 几乎相同（这是对 PA 对照组有效性的规范检验）。
- 标准误：`se = sqrt(var_NJ/n_NJ + var_PA/n_PA)`（两样本均值差）。

### 4.3 ⚠️ 关键实现细节（最容易出错的地方）

- 原文 Table 3 的"变化"列是 **`Wave2 均值 − Wave1 均值`（列均值之差）**，**不是** `店内变化 emp_chg 的均值`。
  - 实测：NJ 列均值之差 = 21.03 − 20.44 = **+0.59**；而 `emp_chg.mean()` = +0.47。两者因非平衡/缺失样本而不同。
  - 报告时二者都算，并在注脚注明口径，与原文对齐。

### 4.4 Table 4（就业变化的简约式回归）

- 因变量 = 两期 FTE 变化（`fte2 − fte`），样本 = 357 家（两期就业与工资均有效）。
- 5 列模型：`(i)` NJ dummy → `(ii)` +品牌/所有权控制 → `(iii)` GAP → `(iv)` GAP+控制 → `(v)` GAP+控制+地区虚拟变量。
- **目标系数**：NJ dummy ≈ **2.33** (SE 1.19)；GAP ≈ **15.65** (SE 6.08)。
- **GAP 构造**：PA 店 = 0；NJ 起始工资 ≥ $5.05 的店 = 0；其余 NJ 店 `GAP = (5.05 − W0)/W0`。
- 复现后与 Table 3 的 DID 对照（Table 4 列(i) 与 Table 3 row4 口径对应，样本不同导致略有差异，见原文注）。

### 4.5 Figure 1（工资分布直方图）

- 4 面板：`NJ_w1 / NJ_w2 / PA_w1 / PA_w2` 的 `WAGE_ST` 直方图。
- 加 `$4.25` 和 `$5.05` 两条垂直参考线。
- 预期：NJ 的 Wave2 分布整体右移、在 $5.05 处堆积（大量店被"钉"到新最低工资），PA 两期几乎重合。

### 4.6 验证与差异解释（报告第 4、6 节的素材）

- 若数值与原文有小差异，从以下角度解释（原文允许不逐字一致）：数据覆盖、样本期、变量构造（尤其 FTE 经理/兼职权重）、缺失值处理、标准误口径。

### 4.7 （可选加分）Stata 交叉验证

- 写 `02_tables.do`，用 `diff fte, t(STATE) p(1)`（若装了 `diff`）或 `reg fte i.STATE##i.POST, cluster(...)` 独立复现 DID，结果与 Python 对比一致后，在报告里写一句"Python 与 Stata 结果一致"。

---

## 5. Phase 3 — 独立扩展（20%，拉开差距的关键）

### 5.1 可选方向（选 1 个，讲清经济问题即可，不必堆代码）

| 方向 | 经济问题 | 优点 |
|---|---|---|
| **A. 所有权异质性（推荐）** | 直营店 vs 加盟店对最低工资的就业反应是否不同？（直营店利润缓冲/管理弹性不同） | 有理论动机、数据现成（`CO_OWNED`）、方法干净 |
| B. 品牌异质性 | 不同连锁品牌（BK/KFC/Roy/Wendy's）反应是否不同？ | 政策含义直接 |
| C. 价格传导 | 最低工资是否转嫁到快餐价格（全餐价格变动）？ | 与就业形成互补视角 |
| D. 用工结构替代 | 是否用兼职替代全职？（FT vs PT 分解） | 深入劳动力需求弹性 |

### 5.2 推荐扩展 A 的完整设计（照这个结构写报告第 5 节）

1. **问题与动机**：加盟商与直营店在定价权、成本结构、雇佣决策上有差异，最低工资冲击可能异质性传导。
2. **假设**：直营店（`CO_OWNED=1`）就业弹性更小/更可能不裁员。
3. **方法**：三重差分或分样本 DID —— 在 2×2 基础上加入 `CO_OWNED` 交互项：
   `Δemp = α + β·STATE + γ·CO_OWNED + δ·(STATE×CO_OWNED) + ε`，关注 δ。
4. **验证/稳健性**：加控制变量（初始规模、品牌固定效应）；换用平衡样本；报告异方差稳健/聚类标准误。
5. **解释**：把 δ 的经济含义与规模讲清楚（哪怕不显著，解释清楚也是好的扩展）。

> 无论选哪个方向，评分看的是：**问题清晰度 → 设计合适性 → 实现与验证质量 → 结果洞察**，不是代码量。

---

## 6. Phase 4 — 可复现工作流（20%）

### 6.1 一键复现入口

- `code/run_all.py`：按顺序调用 `01_clean → 02_tables → 03_figure → 04_extension`，从 `data/raw/` 的输入文件**全自动**生成 `output/` 下所有表图，**无需手动改数据或代码**（这是硬性要求）。
- 若用 Stata，提供 `run_all.do` 等价入口。

### 6.2 做成"可复用 skill / workflow"

任选其一（满足"a reusable skill or workflow"即可）：

1. **Makefile / shell 脚本**：`make all` 一键跑全流程，`make clean` 清空输出。
2. **Claude Code skill**：在 `.claude/skills/` 下写一个 `ck94-replicate` skill，封装"读输入 → 生成表图"的调用方式。
3. 明确在 README 里写：输入数据放进哪个文件夹后，跑哪条命令即可复现。

### 6.3 README（必含内容）

- 项目简介与复现目标（复现 Table 2–4 + Fig 1）。
- **输入文件夹结构**（数据放哪、文件名不能改）。
- 环境要求（Python 版本 + `requirements.txt`；Stata 版本，若用）。
- 一键复现命令 + 每一步生成什么。
- 受限数据说明（本数据为课程内使用，不公开上传；若将来处理受限数据，写访问说明）。
- AI 使用披露链接。

---

## 7. Phase 5 — 报告与 AI 披露（10%）

### 7.1 实证报告结构（对照项目要求的 7 个必含小节）

1. Research question & motivation（研究问题 + 动机）
2. Data sources, sample construction, variable definitions（数据、样本、变量）
3. Empirical design（实证设计，DID）
4. Core replication results & comparison with original（复现结果 + 与原文对比）
5. Independent extension（独立扩展）
6. Validation, limitations, conclusion（验证、局限、结论）
7. AI-use disclosure（AI 披露，单列或并入）

### 7.2 AI 使用披露（5%，别漏）

逐条记录：AI 用在哪（代码生成/调试/写作/图表）、**如何核查**（跑通/与原文比对/人工审）、**纠正或拒绝了哪些 AI 错误**（举 1–2 个真实例子，例如"AI 最初把 FTE 公式写错成全职+兼职，我改为全职+经理+0.5×兼职"）。诚实、具体最加分。

---

## 8. Phase 6 — GitHub 提交与终检

- 确认 `.gitignore` 排除原始受限数据（若要求不外传，只放 `data/` 访问说明与结构说明，不上传 `public.csv`，见 README 第 1 条注记）。
- 检查 commit 历史是否分阶段（至少：init → 数据清洗 → 复现 → 扩展 → 报告）。
- 把仓库设为可访问，提交 URL。
- 终检清单：
  - [ ] 干净环境下 clone 后，`python run_all.py` 能跑通并生成全部表图
  - [ ] 报告 7 个必含小节齐全
  - [ ] AI 披露独立成节且具体
  - [ ] README 完整、命令可执行
  - [ ] 目标数值对照表已归档

---

## 9. 关键技术要点备忘

```python
# FTE 就业（原文口径）
df['fte']  = df['EMPFT']  + df['NMGRS']  + 0.5 * df['EMPPT']
df['fte2'] = df['EMPFT2'] + df['NMGRS2'] + 0.5 * df['EMPPT2']

# Table 3 的 DID：用"列均值之差"口径
nj = df[df.STATE == 1]; pa = df[df.STATE == 0]
did = (nj.fte2.mean() - nj.fte.mean()) - (pa.fte2.mean() - pa.fte.mean())  # ≈ 2.75

# 标准误（两样本均值差）
import numpy as np
se = np.sqrt(nj.emp_chg.var()/len(nj) + pa.emp_chg.var()/len(pa))
```

```stata
* Stata 交叉验证（等价 DID）
gen fte  = EMPFT  + NMGRS  + 0.5*EMPPT
gen fte2 = EMPFT2 + NMGRS2 + 0.5*EMPPT2
gen chg  = fte2 - fte
* 或 diff 命令： diff chg, t(STATE) p(0)  // 结果应 ≈ 2.75
```

---

## 10. 建议时间线（个人项目，按需调整）

| 里程碑 | 建议完成 |
|---|---|
| Phase 0（读论文 + git + 目录） | 第 1 天 |
| Phase 1（清洗 + 变量构建） | 第 2–3 天 |
| Phase 2（复现 4 张图表 + 对照） | 第 4–6 天 |
| Phase 3（扩展 + 稳健性） | 第 7–9 天 |
| Phase 4（工作流 + README） | 第 10–11 天 |
| Phase 5（报告 + AI 披露） | 第 12–13 天 |
| Phase 6（提交 + 终检） | 第 14 天 |
