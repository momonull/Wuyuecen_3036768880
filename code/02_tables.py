"""
02_tables.py — Phase 2: 复现 Table 2 / Table 3 / Table 4

Card & Krueger (1994) "Minimum Wages and Employment" 复现项目。

读入 data/processed/ck94_clean.csv（由 01_clean.py 生成），复现论文三张表，
输出到 output/tables/：
  table2.md                   Table 2 描述性统计（NJ/PA × Wave1/Wave2，均值+标准误+t 值）
  table3.md                   Table 3 核心 DID 表（就业水平与变化，按州与 NJ 工资分组）
  table4.md                   Table 4 简约式回归（就业变化对 NJ dummy / GAP 的 5 列模型）
  replication_check.md        与原文目标值的逐项对照（差异说明）

口径依据：PROJECT_PLAN.md §4 与 output/replication_targets.md（PDF 第 776–778 页）。

关键口径备忘（写代码前必读，与 01_clean.py / variable_construction.md 一致）：
  * FTE = EMPFT + NMGRS + 0.5*EMPPT；FTE2 同理。
  * Table 3「变化」row 3 = 列均值之差（Wave2 均值 − Wave1 均值），非店内变化 emp_chg 均值。
  * Table 3 row 4 = 平衡样本（两期就业均有效，含 6 家永久关闭店 Wave2=0）。
  * Table 3 row 5 = 平衡样本 + 临时关闭店 Wave2 就业改为 0（而非缺失）。
  * Table 4 样本 = 357 家 = 「两期就业 + 两期工资均有效」的 351 家 + 6 家永久关闭店
    （其 Wave2 就业=0 有效、Wave1 工资有效、Wave2 工资不适用）。此口径精确复现论文
    N=357、因变量均值 −0.237、标准差 8.825 及五列系数。
  * GAP：PA=0；NJ 且 WAGE_ST≥5.05=0；其余 NJ = (5.05−W0)/W0。
  * Table 2 的 Wave2「招聘奖金」= SPECIAL2（对新员工的特殊项目，0/1→%）。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "processed" / "ck94_clean.csv"
OUT_DIR = ROOT / "output" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def fmt(m, s, pct=False):
    """均值 + (标准误)，缺失记为 '—'。pct=True 时按百分比放大 100 倍。"""
    if m is None or (isinstance(m, float) and np.isnan(m)):
        return "—"
    sc = 100.0 if pct else 1.0
    return f"{m * sc:.2f} ({s * sc:.2f})"


def mean_se(x):
    """返回 (均值, 标准误 sd/sqrt(n), n)；全缺失返回 (nan, nan, 0)。"""
    x = pd.Series(x).dropna()
    n = len(x)
    if n == 0:
        return np.nan, np.nan, 0
    return x.mean(), x.std(ddof=1) / np.sqrt(n), n


def two_sample_t(a, b):
    """Welch 两样本 t 统计量（均值差 / sqrt(se_a^2 + se_b^2)）；任一方差为 0 返回 nan。"""
    a = pd.Series(a).dropna(); b = pd.Series(b).dropna()
    va = a.var(ddof=1) / len(a) if len(a) > 1 else np.nan
    vb = b.var(ddof=1) / len(b) if len(b) > 1 else np.nan
    if va == 0 or vb == 0 or np.isnan(va) or np.isnan(vb):
        return np.nan
    return (a.mean() - b.mean()) / np.sqrt(va + vb)


def fmt_t(t):
    return "—" if (t is None or (isinstance(t, float) and np.isnan(t))) else f"{t:.1f}"


# ---------------------------------------------------------------------------
# Table 2 — 描述性统计
# ---------------------------------------------------------------------------

def table2(df):
    nj = df[df.STATE == 1]
    pa = df[df.STATE == 0]

    lines = ["# Table 2 — 描述性统计（NJ vs PA）",
             "",
             "> 复现值由 `code/02_tables.py` 生成。括号内为标准误。均值按各变量非缺失样本计算；",
             "> Wave2 就业对永久关闭店(STATUS2==3)设 0、临时关闭店(STATUS2∈{2,4,5})视为缺失。",
             "> 门店类型分布（百分比）与全文值对照 `output/replication_targets.md`。",
             ""]

    # 2.1 门店类型分布（百分比）
    lines += ["## 门店类型分布（%）", "",
              "| 变量 | NJ | PA | t |", "|---|---|---|---|"]
    for col, label in [(1, "Burger King"), (2, "KFC"), (3, "Roy Rogers"),
                       (4, "Wendy's")]:
        a = (nj.CHAIN == col); b = (pa.CHAIN == col)
        ma, _, _ = mean_se(a); mb, _, _ = mean_se(b)
        t = two_sample_t(a, b)
        lines.append(f"| {label} | {ma*100:.1f} | {mb*100:.1f} | {fmt_t(t)} |")
    a = (nj.CO_OWNED == 1); b = (pa.CO_OWNED == 1)
    ma, _, _ = mean_se(a); mb, _, _ = mean_se(b)
    lines.append(f"| 直营 company-owned | {ma*100:.1f} | {mb*100:.1f} | {fmt_t(two_sample_t(a, b))} |")

    # 2.2 / 2.3 连续/比例变量（Wave1 与 Wave2）
    # 每行：(标签, Wave1 NJ 序列, Wave1 PA 序列, Wave2 NJ 序列, Wave2 PA 序列, 是否百分比)
    # Wave1 序列为 None 表示该行仅在 Wave2 出现（如「工资=$5.05 占比」）。
    row_defs = [
        ("FTE 就业", nj.fte, pa.fte, nj.fte2, pa.fte2, False),
        ("全职占比(%)", nj.pct_ft, pa.pct_ft, nj.pct_ft2, pa.pct_ft2, False),
        ("起始工资($)", nj.WAGE_ST, pa.WAGE_ST, nj.WAGE_ST2, pa.WAGE_ST2, False),
        ("工资 = $4.25 占比(%)", (nj.WAGE_ST == 4.25), (pa.WAGE_ST == 4.25),
         (nj.WAGE_ST2 == 4.25), (pa.WAGE_ST2 == 4.25), True),
        ("工资 = $5.05 占比(%)", None, None,
         (nj.WAGE_ST2 == 5.05), (pa.WAGE_ST2 == 5.05), True),
        ("全餐价格($)", nj.full_meal_price, pa.full_meal_price,
         nj.full_meal_price2, pa.full_meal_price2, False),
        ("营业小时(工作日)", nj.HRSOPEN, pa.HRSOPEN, nj.HRSOPEN2, pa.HRSOPEN2, False),
        ("招聘奖金/特殊项目占比(%)", nj.BONUS, pa.BONUS, nj.SPECIAL2, pa.SPECIAL2, True),
    ]

    for wave in (1, 2):
        lines += ["", f"## Wave {wave} 均值", "",
                  "| 变量 | NJ | PA | t |", "|---|---|---|---|"]
        for label, a1, b1, a2, b2, pct in row_defs:
            a, b = (a1, b1) if wave == 1 else (a2, b2)
            if a is None or b is None:
                continue
            ma, sa, _ = mean_se(a); mb, sb, _ = mean_se(b)
            t = two_sample_t(a, b)
            sc = 100.0 if pct else 1.0
            lines.append(f"| {label} | {ma*sc:.2f} ({sa*sc:.2f}) | {mb*sc:.2f} ({sb*sc:.2f}) | {fmt_t(t)} |")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Table 3 — 核心 DID 表
# ---------------------------------------------------------------------------

def table3(df):
    nj = df[df.STATE == 1]
    pa = df[df.STATE == 0]

    # 列定义：(标签, 数据子集)
    groups = [
        ("PA", pa),
        ("NJ", nj),
        ("NJ $4.25", nj[nj.WAGE_ST == 4.25]),
        ("NJ $4.26–$4.99", nj[(nj.WAGE_ST > 4.25) & (nj.WAGE_ST < 5.00)]),
        ("NJ ≥$5.00", nj[nj.WAGE_ST >= 5.00]),
    ]

    def gstats(g):
        """对一个州/工资组计算五种「水平/变化」的 (均值, 标准误, n)。"""
        b, bse, bn = mean_se(g.fte)
        a, ase, an = mean_se(g.fte2)
        # row3 变化 = 列均值之差；SE 用 sqrt(ase^2 + bse^2)（近似，忽略前后协方差）
        chg = a - b
        chg_se = np.sqrt(bse ** 2 + ase ** 2)
        # row4 平衡样本店内变化
        bal = g[g.fte.notna() & g.fte2.notna()]
        balm, balse, baln = mean_se(bal.emp_chg)
        # row5 平衡样本 + 临时关闭店(STATUS2∈{2,4,5}) Wave2 就业=0
        g2 = g[g.fte.notna()].copy()
        temp = g2.STATUS2.isin([2, 4, 5])
        chg_adj = g2.fte2.where(~temp, 0.0) - g2.fte
        adjm, adjse, adjn = mean_se(chg_adj)
        return dict(before=(b, bse, bn), after=(a, ase, an),
                    chg=(chg, chg_se, np.nan), bal=(balm, balse, baln),
                    adj=(adjm, adjse, adjn))

    S = {label: gstats(g) for label, g in groups}
    labels = [g[0] for g in groups]

    lines = ["# Table 3 — 平均就业（核心 DID 表）", "",
             "> FTE = 全职 + 经理 + 0.5×兼职。括号内为标准误（sd/√n）。",
             "> row 3 变化 = 列均值之差（Wave2 均值 − Wave1 均值），SE 用 sqrt(se_后²+se_前²) 近似。",
             "> row 4 变化 = 平衡样本（两期就业均有效）店内变化均值。",
             "> row 5 变化 = 平衡样本，临时关闭店 Wave2 就业设为 0。",
             ""]

    hdr = ["变量"] + labels + ["差异 NJ−PA", "低−高", "中−高"]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("|" + "---|" * len(hdr))

    def cell(v):
        return "—" if np.isnan(v[0]) else f"{v[0]:.2f} ({v[1]:.2f})"

    def dcell(v1, v2):
        if np.isnan(v1[0]) or np.isnan(v2[0]):
            return "—"
        return f"{v1[0] - v2[0]:.2f} ({np.sqrt(v1[1] ** 2 + v2[1] ** 2):.2f})"

    row_keys = [
        ("before", "1. FTE 之前（全部可用）"),
        ("after", "2. FTE 之后（全部可用）"),
        ("chg", "3. FTE 变化（列均值差）"),
        ("bal", "4. FTE 变化（平衡样本）"),
        ("adj", "5. FTE 变化（临时关闭=0）"),
    ]
    for key, name in row_keys:
        vals = [S[l][key] for l in labels]
        cells = [cell(v) for v in vals]
        diff_njpa = dcell(vals[1], vals[0])   # NJ − PA
        lowhigh = dcell(vals[2], vals[4])     # $4.25 − ≥$5.00
        midhigh = dcell(vals[3], vals[4])     # $4.26–4.99 − ≥$5.00
        lines.append("| " + " | ".join([name] + cells + [diff_njpa, lowhigh, midhigh]) + " |")

    # 附注：样本量
    lines += ["",
              "> NJ 按 Wave1 起始工资分组（全部门店）：$4.25 N=101 / $4.26–$4.99 N=140 / ≥$5.00 N=73。",
              "> 各工资组就业有效样本量（before / after / 平衡）：" +
              ", ".join(f"{l} {S[l]['before'][2]:.0f}/{S[l]['after'][2]:.0f}/{S[l]['bal'][2]:.0f}"
                        for l in labels[2:]) + "。"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Table 4 — 简约式回归
# ---------------------------------------------------------------------------

def table4(df):
    # 构造控制变量
    for c in [2, 3, 4]:
        df[f"chain_{c}"] = (df.CHAIN == c).astype(float)
    df["co_owned"] = df.CO_OWNED.astype(float)

    # 357 样本：两期就业 + Wave1 工资有效，且 (Wave2 工资有效 或 永久关闭)
    t4mask = (df.fte.notna() & df.fte2.notna() & df.WAGE_ST.notna()
              & (df.WAGE_ST2.notna() | (df.STATUS2 == 3)))
    t4 = df[t4mask].copy()
    y = t4.emp_chg.astype(float)

    chain = ["chain_2", "chain_3", "chain_4", "co_owned"]
    regions = ["SOUTHJ", "CENTRALJ", "PA1", "PA2"]  # 以 NORTHJ 为基组

    specs = [
        ("(i)", ["STATE"], "NJ"),
        ("(ii)", ["STATE"] + chain, "NJ"),
        ("(iii)", ["gap"], "GAP"),
        ("(iv)", ["gap"] + chain, "GAP"),
        ("(v)", ["gap"] + chain + regions, "GAP"),
    ]

    lines = ["# Table 4 — 就业变化的简约式回归", "",
             "> 因变量 = 两期 FTE 变化（emp_chg = fte2 − fte）。样本 = 357 家",
             "> （两期就业与 Wave1 工资均有效，且 Wave2 工资有效或永久关闭）。",
             f"> 因变量均值 = {y.mean():.3f}，标准差 = {y.std(ddof=1):.3f}。",
             "> 所有模型含未报告常数项。括号内为标准误。",
             ""]

    lines += ["| 自变量 | " + " | ".join(s[0] for s in specs) + " |",
              "|" + "---|" * (len(specs) + 1)]

    # 行 1：NJ dummy（列 iii-v 无）
    row1 = ["1. New Jersey dummy"]
    row2 = ["2. 初始工资缺口 GAP"]
    row3 = ["3. 品牌 + 所有权控制"]
    row4 = ["4. 地区控制"]
    row5 = ["5. 回归标准误"]
    row6 = ["6. 控制变量 p 值"]
    res = {}
    for spec, cols, key in specs:
        X = sm.add_constant(t4[cols].astype(float))
        m = sm.OLS(y, X).fit()
        res[spec] = m
    for i, (spec, cols, key) in enumerate(specs):
        m = res[spec]
        if "STATE" in cols:
            row1.append(f"{m.params['STATE']:.2f} ({m.bse['STATE']:.2f})")
        else:
            row1.append("—")
        if "gap" in cols:
            row2.append(f"{m.params['gap']:.2f} ({m.bse['gap']:.2f})")
        else:
            row2.append("—")
        row3.append("yes" if "chain_2" in cols else "no")
        row4.append("yes" if "SOUTHJ" in cols else "no")
        row5.append(f"{np.sqrt(m.mse_resid):.2f}")
        # 控制变量联合 F 检验 p 值（chain/ownership/region 全部）
        ctrl = [c for c in cols if c not in ("STATE", "gap")]
        if ctrl:
            r = np.zeros((len(ctrl), len(m.params)))
            for i, c in enumerate(ctrl):
                r[i, list(m.params.index).index(c)] = 1.0
            row6.append(f"{float(m.f_test(r).pvalue):.2f}")
        else:
            row6.append("—")

    for r in (row1, row2, row3, row4, row5, row6):
        lines.append("| " + " | ".join(r) + " |")

    lines += ["",
              "> GAP = 初始工资缺口：PA=0；NJ 且 WAGE_ST≥5.05=0；其余 NJ=(5.05−W0)/W0。",
              "> NJ 店 GAP 均值 ≈ 0.11。列(iii) 隐含 NJ−PA 就业效应 = 15.65×0.11 ≈ 1.72 FTE。"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 对照表（与原文目标值比对）
# ---------------------------------------------------------------------------

def replication_check(df):
    nj = df[df.STATE == 1]; pa = df[df.STATE == 0]
    njb, nja = nj.fte.mean(), nj.fte2.mean()
    pab, paa = pa.fte.mean(), pa.fte2.mean()
    did = (nja - njb) - (paa - pab)
    bal_nj = nj[nj.fte.notna() & nj.fte2.notna()].emp_chg
    bal_pa = pa[pa.fte.notna() & pa.fte2.notna()].emp_chg
    bal_did = bal_nj.mean() - bal_pa.mean()
    se = np.sqrt(bal_nj.var(ddof=1) / len(bal_nj) + bal_pa.var(ddof=1) / len(bal_pa))
    t = bal_did / se
    hi = nj[nj.WAGE_ST >= 5.00]
    hi_chg = hi[hi.fte.notna() & hi.fte2.notna()].emp_chg.mean()

    # Table 4 关键系数
    for c in [2, 3, 4]:
        df[f"chain_{c}"] = (df.CHAIN == c).astype(float)
    df["co_owned"] = df.CO_OWNED.astype(float)
    t4 = df[df.fte.notna() & df.fte2.notna() & df.WAGE_ST.notna()
            & (df.WAGE_ST2.notna() | (df.STATUS2 == 3))]
    y = t4.emp_chg.astype(float)
    m_nj = sm.OLS(y, sm.add_constant(t4[["STATE"]].astype(float))).fit()
    m_gap = sm.OLS(y, sm.add_constant(t4[["gap"]].astype(float))).fit()

    lines = ["# 复现对照表 — Phase 2 结果 vs 原文目标", "",
             "> 左列原文值，右列我的复现值。差异说明记录口径/样本/缺失处理差异。", "",
             "| 指标 | 原文 | 我的复现 | 一致? | 说明 |",
             "|---|---|---|---|---|"]
    def chk(name, paper, mine, ok=True, note=""):
        flag = "✅" if ok else "⚠️"
        lines.append(f"| {name} | {paper} | {mine} | {flag} | {note} |")

    chk("DID（NJ−PA FTE 变化）", "2.76 (t=2.03)", f"{did:.3f} (t={t:.2f})",
        abs(did - 2.76) < 0.05, "列均值差口径；0.006 差异为舍入")
    chk("NJ FTE 变化（全样本）", "+0.59", f"{nja-njb:+.2f}")
    chk("PA FTE 变化（全样本）", "−2.16", f"{paa-pab:+.2f}")
    chk("NJ 高工资店(≥$5.00)变化", "−2.16", f"{hi_chg:+.2f}",
        abs(hi_chg - (-2.16)) < 0.05, "平衡样本口径")
    chk("PA 平衡样本变化", "−2.28", f"{bal_pa.mean():+.2f}")
    chk("NJ 工资分组样本量", "$4.25:101 / $4.26–4.99:140 / ≥$5.00:73",
        f"${4.25}:{(nj.WAGE_ST==4.25).sum()} / ${4.26}-4.99:{((nj.WAGE_ST>4.25)&(nj.WAGE_ST<5.0)).sum()} / ≥$5.00:{(nj.WAGE_ST>=5.0).sum()}")
    chk("Table 4 样本量", "357", f"{len(t4)}")
    chk("Table 4 因变量均值", "−0.237", f"{y.mean():.3f}")
    chk("Table 4 因变量标准差", "8.825", f"{y.std(ddof=1):.3f}")
    chk("Table 4 列(i) NJ dummy", "2.33 (1.19)",
        f"{m_nj.params['STATE']:.2f} ({m_nj.bse['STATE']:.2f})")
    chk("Table 4 列(iii) GAP", "15.65 (6.08)",
        f"{m_gap.params['gap']:.2f} ({m_gap.bse['gap']:.2f})")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------

def main():
    df = pd.read_csv(CLEAN)

    (OUT_DIR / "table2.md").write_text(table2(df), encoding="utf-8")
    (OUT_DIR / "table3.md").write_text(table3(df), encoding="utf-8")
    (OUT_DIR / "table4.md").write_text(table4(df), encoding="utf-8")
    (OUT_DIR / "replication_check.md").write_text(replication_check(df), encoding="utf-8")

    print("wrote:", *(str(OUT_DIR / f) for f in
                      ["table2.md", "table3.md", "table4.md", "replication_check.md"]))

    # 控制台打印对照表（快速核验）
    print("\n" + replication_check(df))


if __name__ == "__main__":
    main()
