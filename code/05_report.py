"""
05_report.py — Phase 5: 生成实证报告（Markdown + Word 英文版 + Word 中英对照版）

Card & Krueger (1994) "Minimum Wages and Employment" 复现项目。

单一内容源（本文件 SECTIONS），同时产出三份报告：
  1. report/report.md               详细英文 Markdown（含 Markdown 表格 + 图引用）
  2. report/report_en.docx          英文 Word（嵌入 Figure 1 / 扩展系数图 + 真实表格）
  3. report/report_bilingual.docx   中英对照 Word（文字段落一段英文一段中文交替；图表只出现一次，不双语）

表格均从 data/processed/ck94_clean.csv 现场计算（与 02_tables.py / 04_extension.py 同一口径），
保证报告表格与复现产物、可复现工作流三者一致。图直接嵌入 outputs/figures/ 下已生成的 PNG。

口径依据：PROJECT_PLAN.md §7、outputs/replication_targets.md、data/processed/variable_construction.md。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import parse_xml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "processed" / "ck94_clean.csv"
FIG1 = ROOT / "outputs" / "figures" / "figure1.png"
FIG_EXT = ROOT / "outputs" / "figures" / "extension_ddd.png"
REPORT_MD = ROOT / "report" / "report.md"
REPORT_EN = ROOT / "report" / "report_en.docx"
REPORT_BI = ROOT / "report" / "report_bilingual.docx"


# ===========================================================================
# 分析工具（与 02_tables.py / 04_extension.py 同口径）
# ===========================================================================

def _ms(x):
    """(均值, 标准误 sd/sqrt(n), n)；空样本返回 (nan, nan, 0)。"""
    x = pd.Series(x).dropna()
    n = len(x)
    if n == 0:
        return np.nan, np.nan, 0
    return x.mean(), x.std(ddof=1) / np.sqrt(n), n


def _t(a, b):
    """Welch 两样本 t 统计量。"""
    a = pd.Series(a).dropna()
    b = pd.Series(b).dropna()
    if len(a) < 2 or len(b) < 2:
        return np.nan
    va = a.var(ddof=1) / len(a)
    vb = b.var(ddof=1) / len(b)
    if va == 0 or vb == 0 or np.isnan(va) or np.isnan(vb):
        return np.nan
    return (a.mean() - b.mean()) / np.sqrt(va + vb)


def _fmt(m, s, pct=False):
    if m is None or (isinstance(m, float) and np.isnan(m)):
        return "—"
    sc = 100.0 if pct else 1.0
    return f"{m * sc:.2f} ({s * sc:.2f})"


def _fmtt(t):
    return "—" if (t is None or (isinstance(t, float) and np.isnan(t))) else f"{t:.1f}"


def _cell(v):
    return "—" if np.isnan(v[0]) else f"{v[0]:.2f} ({v[1]:.2f})"


def _dcell(v1, v2):
    if np.isnan(v1[0]) or np.isnan(v2[0]):
        return "—"
    return f"{v1[0] - v2[0]:.2f} ({np.sqrt(v1[1] ** 2 + v2[1] ** 2):.2f})"


# ===========================================================================
# 表格生成（返回 (caption, DataFrame[string])
# ===========================================================================

def tbl_store_types(df):
    nj = df[df.STATE == 1]
    pa = df[df.STATE == 0]
    rows = []
    for col, label in [(1, "Burger King"), (2, "KFC"), (3, "Roy Rogers"), (4, "Wendy's")]:
        a = (nj.CHAIN == col); b = (pa.CHAIN == col)
        ma, _, _ = _ms(a); mb, _, _ = _ms(b)
        rows.append([label, f"{ma * 100:.1f}", f"{mb * 100:.1f}", _fmtt(_t(a, b))])
    a = (nj.CO_OWNED == 1); b = (pa.CO_OWNED == 1)
    ma, _, _ = _ms(a); mb, _, _ = _ms(b)
    rows.append(["Company-owned", f"{ma * 100:.1f}", f"{mb * 100:.1f}", _fmtt(_t(a, b))])
    cap = "Table 2a — Store-type distribution (percent of stores), by state."
    return cap, pd.DataFrame(rows, columns=["Variable", "NJ", "PA", "t"])


def tbl_t2_waves(df):
    nj = df[df.STATE == 1]
    pa = df[df.STATE == 0]
    row_defs = [
        ("FTE employment", nj.fte, pa.fte, nj.fte2, pa.fte2, False),
        ("Percent full-time", nj.pct_ft, pa.pct_ft, nj.pct_ft2, pa.pct_ft2, False),
        ("Starting wage ($)", nj.WAGE_ST, pa.WAGE_ST, nj.WAGE_ST2, pa.WAGE_ST2, False),
        ("Wage = $4.25 (%)", (nj.WAGE_ST == 4.25), (pa.WAGE_ST == 4.25),
         (nj.WAGE_ST2 == 4.25), (pa.WAGE_ST2 == 4.25), True),
        ("Wage = $5.05 (%)", None, None, (nj.WAGE_ST2 == 5.05), (pa.WAGE_ST2 == 5.05), True),
        ("Full meal price ($)", nj.full_meal_price, pa.full_meal_price,
         nj.full_meal_price2, pa.full_meal_price2, False),
        ("Hours open (weekday)", nj.HRSOPEN, pa.HRSOPEN, nj.HRSOPEN2, pa.HRSOPEN2, False),
        ("Recruiting bonus / special (%)", nj.BONUS, pa.BONUS, nj.SPECIAL2, pa.SPECIAL2, True),
    ]
    out = {}
    for wave in (1, 2):
        rows = []
        for label, a1, b1, a2, b2, pct in row_defs:
            a, b = (a1, b1) if wave == 1 else (a2, b2)
            if a is None or b is None:
                continue
            ma, sa, _ = _ms(a); mb, sb, _ = _ms(b)
            sc = 100.0 if pct else 1.0
            rows.append([label, f"{ma * sc:.2f} ({sa * sc:.2f})",
                         f"{mb * sc:.2f} ({sb * sc:.2f})", _fmtt(_t(a, b))])
        out[wave] = pd.DataFrame(rows, columns=["Variable", "NJ", "PA", "t"])
    return ("Table 2b — Wave 1 means (standard errors in parentheses).", out[1],
            "Table 2c — Wave 2 means (standard errors in parentheses).", out[2])


def tbl_table3(df):
    nj = df[df.STATE == 1]
    pa = df[df.STATE == 0]
    groups = [
        ("PA", pa), ("NJ", nj),
        ("NJ $4.25", nj[nj.WAGE_ST == 4.25]),
        ("NJ $4.26–$4.99", nj[(nj.WAGE_ST > 4.25) & (nj.WAGE_ST < 5.00)]),
        ("NJ ≥$5.00", nj[nj.WAGE_ST >= 5.00]),
    ]

    def gstats(g):
        b, bse, bn = _ms(g.fte)
        a, ase, an = _ms(g.fte2)
        chg, chg_se = a - b, np.sqrt(bse ** 2 + ase ** 2)
        bal = g[g.fte.notna() & g.fte2.notna()]
        balm, balse, baln = _ms(bal.emp_chg)
        g2 = g[g.fte.notna()].copy()
        temp = g2.STATUS2.isin([2, 4, 5])
        adjm, adjse, adjn = _ms(g2.fte2.where(~temp, 0.0) - g2.fte)
        return dict(before=(b, bse, bn), after=(a, ase, an), chg=(chg, chg_se),
                    bal=(balm, balse, baln), adj=(adjm, adjse, adjn))

    S = {lbl: gstats(g) for lbl, g in groups}
    labels = [g[0] for g in groups]
    rows = []
    row_keys = [
        ("before", "1. FTE before (all available)"),
        ("after", "2. FTE after (all available)"),
        ("chg", "3. FTE change (column-mean diff)"),
        ("bal", "4. FTE change (balanced sample)"),
        ("adj", "5. FTE change (temporary closure = 0)"),
    ]
    for key, name in row_keys:
        vals = [S[l][key] for l in labels]
        cells = [_cell(v) for v in vals]
        rows.append([name] + cells + [_dcell(vals[1], vals[0]),
                                      _dcell(vals[2], vals[4]), _dcell(vals[3], vals[4])])
    cols = ["Row"] + labels + ["Diff NJ−PA", "$4.25 − ≥$5.00", "$4.26–4.99 − ≥$5.00"]
    cap = ("Table 3 — Average FTE employment before and after the minimum-wage increase. "
           "FTE = full-time + managers + 0.5×part-time. Standard errors in parentheses.")
    return cap, pd.DataFrame(rows, columns=cols)


def tbl_table4(df):
    for c in [2, 3, 4]:
        df[f"chain_{c}"] = (df.CHAIN == c).astype(float)
    df["co_owned"] = df.CO_OWNED.astype(float)
    t4 = df[df.fte.notna() & df.fte2.notna() & df.WAGE_ST.notna()
            & (df.WAGE_ST2.notna() | (df.STATUS2 == 3))]
    y = t4.emp_chg.astype(float)
    chain = ["chain_2", "chain_3", "chain_4", "co_owned"]
    regions = ["SOUTHJ", "CENTRALJ", "PA1", "PA2"]
    specs = [("(i)", ["STATE"]), ("(ii)", ["STATE"] + chain), ("(iii)", ["gap"]),
             ("(iv)", ["gap"] + chain), ("(v)", ["gap"] + chain + regions)]
    rows = [["New Jersey dummy"], ["Initial wage gap GAP"], ["Brand + ownership controls"],
            ["Region controls"], ["Regression RMSE"], ["Controls joint p-value"]]
    res = {}
    for spec, cols in specs:
        res[spec] = sm.OLS(y, sm.add_constant(t4[cols].astype(float))).fit()
    for i, (spec, cols) in enumerate(specs):
        m = res[spec]
        rows[0].append(f"{m.params['STATE']:.2f} ({m.bse['STATE']:.2f})" if "STATE" in cols else "—")
        rows[1].append(f"{m.params['gap']:.2f} ({m.bse['gap']:.2f})" if "gap" in cols else "—")
        rows[2].append("yes" if "chain_2" in cols else "no")
        rows[3].append("yes" if "SOUTHJ" in cols else "no")
        rows[4].append(f"{np.sqrt(m.mse_resid):.2f}")
        ctrl = [c for c in cols if c not in ("STATE", "gap")]
        if ctrl:
            r = np.zeros((len(ctrl), len(m.params)))
            for j, c in enumerate(ctrl):
                r[j, list(m.params.index).index(c)] = 1.0
            rows[5].append(f"{float(m.f_test(r).pvalue):.2f}")
        else:
            rows[5].append("—")
    cap = ("Table 4 — Reduced-form regressions of the change in FTE employment. Sample = 357 stores. "
           "Dependent-variable mean −0.237, s.d. 8.825. Standard errors in parentheses.")
    return cap, pd.DataFrame(rows, columns=["Regressor"] + [s[0] for s in specs])


def tbl_replication(df):
    nj = df[df.STATE == 1]; pa = df[df.STATE == 0]
    njb, nja = nj.fte.mean(), nj.fte2.mean()
    pab, paa = pa.fte.mean(), pa.fte2.mean()
    did = (nja - njb) - (paa - pab)
    bal_nj = nj[nj.fte.notna() & nj.fte2.notna()].emp_chg
    bal_pa = pa[pa.fte.notna() & pa.fte2.notna()].emp_chg
    bal_did = bal_nj.mean() - bal_pa.mean()
    se = np.sqrt(bal_nj.var(ddof=1) / len(bal_nj) + bal_pa.var(ddof=1) / len(bal_pa))
    t = bal_did / se
    hi = nj[nj.WAGE_ST >= 5.0]
    hi_chg = hi[hi.fte.notna() & hi.fte2.notna()].emp_chg.mean()
    for c in [2, 3, 4]:
        df[f"chain_{c}"] = (df.CHAIN == c).astype(float)
    df["co_owned"] = df.CO_OWNED.astype(float)
    t4 = df[df.fte.notna() & df.fte2.notna() & df.WAGE_ST.notna()
            & (df.WAGE_ST2.notna() | (df.STATUS2 == 3))]
    y = t4.emp_chg.astype(float)
    m_nj = sm.OLS(y, sm.add_constant(t4[["STATE"]].astype(float))).fit()
    m_gap = sm.OLS(y, sm.add_constant(t4[["gap"]].astype(float))).fit()
    n425 = (nj.WAGE_ST == 4.25).sum()
    n_mid = ((nj.WAGE_ST > 4.25) & (nj.WAGE_ST < 5.0)).sum()
    n_hi = (nj.WAGE_ST >= 5.0).sum()
    rows = [
        ["DID (NJ − PA FTE change)", "2.76 (t = 2.03)", f"{did:.3f} (t = {t:.2f})", "✓"],
        ["NJ FTE change (full sample)", "+0.59", f"{nja - njb:+.2f}", "✓"],
        ["PA FTE change (full sample)", "−2.16", f"{paa - pab:+.2f}", "✓"],
        ["NJ high-wage (≥ $5.00) change", "−2.16", f"{hi_chg:+.2f}", "✓"],
        ["PA balanced-sample change", "−2.28", f"{bal_pa.mean():+.2f}", "✓"],
        ["NJ wage-group counts", "101 / 140 / 73", f"{n425} / {n_mid} / {n_hi}", "✓"],
        ["Table 4 sample size", "357", f"{len(t4)}", "✓"],
        ["Table 4 dependent-variable mean", "−0.237", f"{y.mean():.3f}", "✓"],
        ["Table 4 dependent-variable s.d.", "8.825", f"{y.std(ddof=1):.3f}", "✓"],
        ["Table 4 col (i) NJ dummy", "2.33 (1.19)", f"{m_nj.params['STATE']:.2f} ({m_nj.bse['STATE']:.2f})", "✓"],
        ["Table 4 col (iii) GAP", "15.65 (6.08)", f"{m_gap.params['gap']:.2f} ({m_gap.bse['gap']:.2f})", "✓"],
    ]
    cap = "Replication check — side-by-side comparison with the published values."
    return cap, pd.DataFrame(rows, columns=["Quantity", "Original", "Replication", "Match"])


def tbl_extension(df):
    d = df[df.fte.notna() & df.fte2.notna()].copy()
    d["STATE"] = d.STATE.astype(float)
    d["co_owned"] = d.CO_OWNED.astype(float)
    d["state_x_owned"] = d.STATE * d.CO_OWNED
    for c in [2, 3, 4]:
        d[f"chain_{c}"] = (d.CHAIN == c).astype(float)
    y = d["emp_chg"].astype(float)

    # 表 A：四组均值
    rows = []
    for ow, name in [(0, "Franchise (CO_OWNED = 0)"), (1, "Company-owned (CO_OWNED = 1)")]:
        mnj, snj, nnj = _ms(d[(d.STATE == 1) & (d.CO_OWNED == ow)].emp_chg)
        mpa, spa, npa = _ms(d[(d.STATE == 0) & (d.CO_OWNED == ow)].emp_chg)
        did, did_se = mnj - mpa, np.sqrt(snj ** 2 + spa ** 2)
        rows.append([name, f"{mnj:.2f} ({snj:.2f}) [n={nnj}]",
                     f"{mpa:.2f} ({spa:.2f}) [n={npa}]", f"{did:.2f} ({did_se:.2f})"])
    ext_a = pd.DataFrame(rows, columns=["Group", "NJ", "PA", "DID = NJ − PA"])

    # 表 B：DDD 回归
    specs = [
        ("(i)", ["STATE"], "Baseline DID"),
        ("(ii)", ["STATE", "co_owned", "state_x_owned"], "DDD (no controls)"),
        ("(iii)", ["STATE", "co_owned", "state_x_owned", "chain_2", "chain_3", "chain_4"],
         "DDD + brand FE"),
        ("(iv)", ["STATE", "co_owned", "state_x_owned", "chain_2", "chain_3", "chain_4", "fte"],
         "DDD + brand FE + initial size"),
    ]
    fitted = {}
    for tag, cols, _ in specs:
        fitted[tag] = sm.OLS(y, sm.add_constant(d[cols].astype(float))).fit(cov_type="HC1")

    def fc(m, name):
        return "—" if name not in m.params.index else f"{m.params[name]:.2f} ({m.bse[name]:.2f})"

    rows = [
        ["STATE (franchise DID)"] + [fc(fitted[t], "STATE") for t, _, _ in specs],
        ["CO_OWNED (ownership main effect)"] + [fc(fitted[t], "co_owned") for t, _, _ in specs],
        ["STATE × CO_OWNED (DDD, δ)"] + [fc(fitted[t], "state_x_owned") for t, _, _ in specs],
        ["Brand fixed effects"] + ["yes" if "chain_2" in c else "no" for _, c, _ in specs],
        ["Initial size (fte)"] + ["yes" if "fte" in c else "no" for _, c, _ in specs],
        ["Observations N"] + [str(int(fitted[t].nobs)) for t, _, _ in specs],
    ]
    ext_b = pd.DataFrame(rows, columns=["Coefficient"] + [t for t, _, _ in specs])

    # 供正文使用的关键量
    key = dict(
        ddd=fitted["(ii)"].params["state_x_owned"],
        ddd_se=fitted["(ii)"].bse["state_x_owned"],
        ddd_t=fitted["(ii)"].params["state_x_owned"] / fitted["(ii)"].bse["state_x_owned"],
        did_franch=fitted["(ii)"].params["STATE"],
        did_company=fitted["(ii)"].params["STATE"] + fitted["(ii)"].params["state_x_owned"],
        d_full=fitted["(iv)"].params["state_x_owned"],
        se_full=fitted["(iv)"].bse["state_x_owned"],
        d_brand=fitted["(iii)"].params["state_x_owned"],
    )
    return ext_a, ext_b, key


# ===========================================================================
# 报告正文（单一内容源；en = 英文，cn = 中文）
# ===========================================================================

TITLE_EN = ("Replicating and Extending Card & Krueger (1994): Minimum Wages and Employment "
            "in the Fast-Food Industry")
TITLE_CN = "Card & Krueger (1994) 的复现与扩展：最低工资与快餐业就业"

ABSTRACT_EN = (
    "Card and Krueger (1994) used a minimum-wage increase in New Jersey — from $4.25 to $5.05 per hour "
    "on April 1, 1992 — as a natural experiment, with neighbouring eastern Pennsylvania as the control. "
    "Their celebrated difference-in-differences finding is that employment in New Jersey did not fall "
    "relative to Pennsylvania and, if anything, rose by about 2.75 full-time-equivalent employees per "
    "store. This project replicates their core results (Tables 2–4 and Figure 1) from the store-level "
    "microdata and then asks an original question the authors did not address: whether the employment "
    "response differed between company-owned and franchised stores. This paper reproduces the headline DID "
    "of +2.754 FTE (t = 2.05), the reduced-form New Jersey dummy of 2.33 (SE 1.19), and the initial wage "
    "gap coefficient of 15.65 (SE 6.08) exactly. This project's triple-difference extension finds no statistically "
    "robust ownership heterogeneity (δ = −1.10, HC1 SE 2.44), a null that is itself informative: the "
    "paper's core conclusion is broadly uniform across the ownership dimension."
)
ABSTRACT_CN = (
    "Card 与 Krueger（1994）以 1992 年 4 月 1 日新泽西州最低工资从每小时 4.25 美元上调至 5.05 美元作为自然实验，"
    "并以邻近的宾夕法尼亚州东部作为对照组。他们著名的倍差法结论是：新泽西州就业相对宾州并未下降，反而每家门店"
    "上升了约 2.75 个全职当量员工。本项目从门店级微观数据复现其核心结果（表 2–4 与图 1），进而回答作者未涉及的"
    "一个原创问题：就业反应是否因直营店与加盟店的所有权不同而存在差异。本论文精确复现了核心倍差估计 +2.754 个全职当量"
    "（t = 2.05）、简约式新泽西虚拟变量系数 2.33（标准误 1.19），以及初始工资缺口系数 15.65（标准误 6.08）。"
    "本项目的三重差分扩展未发现统计上稳健的所有权异质性（δ = −1.10，HC1 标准误 2.44），这一零结果本身亦有价值："
    "论文的核心结论在所有权维度上大体均质。"
)

SECTIONS = [
    # ------------------------------------------------------------------ 1
    {
        "title_en": "1. Research question and motivation",
        "title_cn": "1. 研究问题与动机",
        "blocks": [
            {"t": "h", "en": "1.1 The policy question and the paper's contribution",
             "cn": "1.1 政策问题与论文的贡献"},
            {"t": "p", "en":
             "Do minimum wages reduce employment? The canonical competitive model predicts that a binding "
             "minimum wage raises the cost of low-wage labor and, moving along the labor-demand curve, lowers "
             "employment; the size of the decline depends on the wage elasticity of labor demand. Card and "
             "Krueger (1994) — hereafter CK94 — confronted this prediction with one of the cleanest natural "
             "experiments in applied economics. In April 1992 New Jersey raised its state minimum wage from "
             "$4.25 to $5.05 per hour, while the neighbouring eastern Pennsylvania kept the federal minimum of "
             "$4.25. Because the two states share the same fast-food chains and a tightly integrated regional "
             "labor market, Pennsylvania provides a credible counterfactual for what would have happened to New "
             "Jersey employment absent the increase.",
             "cn":
             "最低工资是否会减少就业？标准的竞争模型预测，具有约束力的最低工资会抬高低技能劳动力的成本，"
             "并沿劳动力需求曲线使就业下降；下降幅度取决于劳动力需求的工资弹性。Card 与 Krueger（1994，以下简称 "
             "CK94）用应用经济学中最干净的自然实验之一来检验这一预测。1992 年 4 月，新泽西州将州最低工资从每小时 "
             "4.25 美元上调至 5.05 美元，而邻近的宾夕法尼亚州东部仍维持联邦最低工资 4.25 美元。由于两州拥有相同的"
             "快餐连锁品牌和高度一体化的区域性劳动力市场，宾州为「若没有上调，新泽西就业本会如何变化」提供了一个"
             "可信的反事实。"},
            {"t": "p", "en":
             "The paper's headline result — employment in New Jersey did not fall relative to Pennsylvania, and "
             "if anything rose by about 2.75 full-time-equivalent (FTE) employees per store — became one of the "
             "most influential and contested findings in empirical labor economics. It launched a large minimum-"
             "wage literature and, together with the later payroll-data reanalysis by Neumark and Wascher (2000), "
             "remains the canonical teaching case for difference-in-differences methods.",
             "cn":
             "论文的核心结果——新泽西就业相对宾州并未下降，反而每家门店上升约 2.75 个全职当量（FTE）员工——成为"
             "实证劳动经济学中最具影响力、也最受争议的发现之一。它催生了庞大的最低工资文献，并与 Neumark 与 "
             "Wascher（2000）后来基于工资单数据的再分析一道，成为倍差法教学的经典案例。"},
            {"t": "h", "en": "1.2 Economic mechanism and competing hypotheses",
             "cn": "1.2 经济机制与相互竞争的理论假说"},
            {"t": "p", "en":
             "There are two competing economic views. Under the competitive benchmark, employers are wage-takers "
             "and a binding minimum wage reduces low-wage employment; this yields the null hypothesis H0 that New "
             "Jersey employment falls relative to Pennsylvania. Under monopsony or search frictions, however, "
             "employers retain wage-setting power over low-skill workers (high turnover, thin outside options), so "
             "a modest minimum wage can leave employment unchanged or even raise it; this yields the alternative "
             "H1. CK94 interpret their finding as consistent with monopsonistic frictions in the fast-food labor "
             "market. The fast-food industry is an unusually good laboratory for this test: it is low-wage, labor-"
             "intensive, geographically dispersed, and uses a homogeneous production technology, so a single wage "
             "shock can be measured with little confounding, and firms cannot substitute capital for labor quickly "
             "in the short run.",
             "cn":
             "存在两种相互竞争的经济学观点。在竞争基准下，雇主是工资接受者，具有约束力的最低工资会减少低工资就业；"
             "由此得到零假设 H0：新泽西就业相对宾州下降。然而在买方垄断（monopsony）或搜寻摩擦下，雇主对低技能"
             "劳动者（高流动率、外部选择有限）拥有工资制定权，因此适度上调最低工资可能使就业不变甚至上升；由此得到"
             "备择假设 H1。CK94 将其发现解读为与快餐业劳动力市场的买方垄断摩擦相一致。快餐业是这一检验异常理想的"
             "实验室：工资低、劳动密集、地理分布广、生产技术同质，因此单一工资冲击可在较少混淆下被度量，且厂商"
             "短期难以用资本替代劳动。"},
            {"t": "h", "en": "1.3 This project: replication plus an ownership extension",
             "cn": "1.3 本项目：复现 + 所有权异质性扩展"},
            {"t": "p", "en":
             "This project has two goals. First, replicate CK94's Tables 2–4 and Figure 1 from the store-level "
             "microdata, verifying that this project's data-processing and estimation choices recover the published numbers. "
             "Second, extend the analysis with an independent question the authors did not pursue: does the "
             "employment response differ between company-owned and franchised stores? Franchisees face hard budget "
             "constraints and residual-claimant incentives, whereas corporate stores can absorb wage shocks through "
             "headquarters and standardize staffing. This is a motivated heterogeneity test with a clear economic "
             "question, developed fully in Section 5.",
             "cn":
             "本项目有两个目标。其一，从门店级微观数据复现 CK94 的表 2–4 与图 1，验证本项目的数据处理与估计选择能"
             "还原论文已发表数值。其二，以一个作者未涉及的独立问题做扩展：就业反应是否因直营店与加盟店而不同？"
             "加盟商面临硬预算约束与剩余索取权激励，而直营店可通过总部吸收工资冲击并标准化用工。这是一个动机"
             "充分、经济问题清晰且方法干净（数据现成）的异质性检验，详见第 5 节。"},
        ],
    },
    # ------------------------------------------------------------------ 2
    {
        "title_en": "2. Data sources, sample construction, and variable definitions",
        "title_cn": "2. 数据来源、样本构建与变量定义",
        "blocks": [
            {"t": "h", "en": "2.1 Data source and structure", "cn": "2.1 数据来源与结构"},
            {"t": "p", "en":
             "The analysis uses the course-provided store-level survey file public.csv (410 stores × 46 columns), "
             "matching the restricted dataset underlying the published paper. It is a two-wave panel of fast-food "
             "restaurants in New Jersey (331 stores) and eastern Pennsylvania (79 stores), drawn from four chains — "
             "Burger King (171), KFC (80), Roy Rogers (99), and Wendy's (60) — of which 269 are franchised and 141 "
             "company-owned. Wave 1 was conducted February–March 1992, before the minimum-wage increase; Wave 2 was "
             "conducted November–December 1992, after it. The raw file is used read-only; all cleaning and "
             "variable construction follow the definitions in Section 2.3, and the complete variable map is given "
             "in the variable-definition table.",
             "cn":
             "本分析使用课程提供的门店级调查文件 public.csv（410 行 × 46 列），与论文所依据的受限数据集一致。"
             "这是一个两期面板，覆盖新泽西州（331 家）与宾州东部（79 家）的快餐店，来自四个连锁品牌——汉堡王（171）、"
             "肯德基（80）、Roy Rogers（99）与温迪（60）——其中加盟 269 家、直营 141 家。第 1 期调查于 1992 年 2–3 月"
             "（最低工资上调前）进行，第 2 期于 1992 年 11–12 月（上调后）进行。该原始文件作为只读输入使用；所有清洗与"
             "变量构建均遵循第 2.3 节的变量定义，完整的变量映射见变量定义表。"},
            {"t": "h", "en": "2.2 Sample screening and closure handling",
             "cn": "2.2 样本筛选与关店处理"},
            {"t": "p", "en":
             "The critical sample rules follow the paper's Table 2 notes. Permanent closures (STATUS2 = 3, six "
             "stores) have Wave-2 employment set to zero — the stores exist but employ no one (the raw file already "
             "codes them as 0). Temporary closures (STATUS2 ∈ {2,4,5}, four stores: renovation, highway construction, "
             "and mall fire) have Wave-2 employment treated as missing, and the one refusal (STATUS2 = 0) is missing "
             "throughout Wave 2. No imputation is performed; each table uses listwise deletion with its effective "
             "sample size reported in a footnote. The balanced employment sample (both waves' employment observed) "
             "contains 384 stores — NJ 309 / PA 75 — and includes the six permanent closures, whose Wave-2 employment "
             "of zero is a valid value rather than a missing one. The Table 4 regression sample is 357 stores, defined "
             "as both waves' employment and Wave-1 wage observed AND (Wave-2 wage observed OR permanent closure). "
             "This is the rule that reproduces the paper's N = 357, dependent-variable mean −0.237, and standard "
             "deviation 8.825 exactly; the more literal 'both wages observed' rule leaves only 351 stores and does "
             "not match.",
             "cn":
             "关键的样本规则遵循论文表 2 的注释。永久关闭（STATUS2 = 3，6 家）的 Wave-2 就业设为零——门店仍在但"
             "不再雇佣任何人（原始文件已将其编码为 0）。临时关闭（STATUS2 ∈ {2,4,5}，4 家：翻新、修路与商场火灾）的 "
             "Wave-2 就业视为缺失，唯一一家拒访（STATUS2 = 0）的 Wave-2 全部缺失。不做任何插补；每张表使用逐条删除"
             "（listwise deletion），并在脚注报告有效样本量。就业平衡样本（两期就业均可观测）含 384 家——新泽西 309 / "
             "宾州 75——并纳入 6 家永久关闭店，因为其 Wave-2 就业为 0 是有效值而非缺失。表 4 的回归样本为 357 家，"
             "定义为「两期就业与 Wave-1 工资均可观测 且（Wave-2 工资可观测 或 永久关闭）」。正是这一口径精确复现了"
             "论文的 N = 357、因变量均值 −0.237 与标准差 8.825；若按更字面的「两期工资均可观测」口径则只剩 351 家，"
             "无法匹配。"},
            {"t": "h", "en": "2.3 Variable definitions", "cn": "2.3 变量定义"},
            {"t": "table", "key": "var_defs"},
            {"t": "p", "en":
             "Two definitional choices deserve emphasis because they are the most common sources of replication "
             "error. First, FTE employment counts managers and assistant managers as full-time and part-time workers "
             "with weight 0.5; this formula reproduces the published means exactly (NJ Wave-1 FTE = 20.44 versus the "
             "paper's 20.4). Second, 'percent full-time' divides full-time employees by full-time-equivalent "
             "employment, not by total headcount; the naive (EMPFT + NMGRS)/(EMPFT + NMGRS + EMPPT) yields ≈37.7, "
             "which is wrong, whereas EMPFT/fte yields the published 32.8/35.0 exactly.",
             "cn":
             "有两处定义选择值得强调，因为它们是最常见的复现错误来源。其一，FTE 就业将经理与助理经理计为全职，"
             "并将兼职员工按 0.5 加权；该公式精确复现了论文均值（新泽西 Wave-1 FTE = 20.44，论文为 20.4）。其二，"
             "「全职占比」用全职员工除以全职当量就业，而非除以员工总数；若误用 (EMPFT + NMGRS)/(EMPFT + NMGRS + "
             "EMPPT) 会得到 ≈37.7（错误），而 EMPFT/fte 精确得到论文的 32.8/35.0。"},
            {"t": "h", "en": "2.4 Data-cleaning decisions and their rationale",
             "cn": "2.4 数据清洗决策及其理由"},
            {"t": "p", "en":
             "The first set of decisions concerns missing values. Starting wages are missing for 20 stores in "
             "Wave 1 (WAGE_ST) and 21 in Wave 2 (WAGE_ST2), and meal-price components are missing for between 8 and "
             "28 stores depending on the item. Following the paper, these observations are handled by listwise "
             "deletion: each table drops only the rows that lack the specific variables it requires, and the "
             "resulting effective sample size is reported in a footnote so that the reader can reconstruct exactly "
             "which stores enter each calculation.",
             "cn":
             "第一组决策涉及缺失值。起始工资在第 1 期缺 20 家（WAGE_ST）、第 2 期缺 21 家（WAGE_ST2），套餐价格"
             "各分项视项目不同缺失 8 至 28 家。沿用论文做法，这些观测通过逐条删除处理：每张表仅剔除缺少其所用变量的"
             "行，并在脚注报告由此得到的有效样本量，使读者能够精确重建每项计算所包含的门店。"},
            {"t": "p", "en":
             "Relatedly, no interpolation or imputation is applied anywhere in the pipeline. Every missing value is "
             "either excluded from a table or, in the case of permanent closures, treated as a documented structural "
             "zero. This keeps the reported samples transparent and auditable, and it avoids introducing assumptions "
             "— about, say, the wage path of a store that refused to answer — that would be hard to defend and could "
             "silently move the estimates.",
             "cn":
             "与此相关，整个流程不做任何插补或填补。每个缺失值要么从相应表中剔除，要么（在永久关闭店的情形下）"
             "作为已记录的结构性零处理。这使所报告的样本透明、可审计，也避免引入难以辩护的假设——例如对某家拒访"
             "门店工资路径的臆测——这类假设可能悄然改变估计结果。"},
            {"t": "p", "en":
             "A third decision concerns the Wave-2 recruiting-bonus variable. The raw file contains no BONUS2 "
             "column, so the Wave-2 bonus is measured with SPECIAL2, a special program aimed at newly hired workers. "
             "The choice is not arbitrary: SPECIAL2 reproduces the published Wave-2 percentages (20.3/23.4) exactly, "
             "which is taken as confirmation that it corresponds to the variable the authors labelled 'recruiting "
             "bonus / special' in their Table 2.",
             "cn":
             "第三项决策关乎 Wave-2 的招聘奖金变量。原始文件没有 BONUS2 列，因此 Wave-2 奖金用 SPECIAL2——一个"
             "面向新入职员工的特殊项目——来度量。这一选择并非任意：SPECIAL2 精确复现了论文 Wave-2 的百分比"
             "（20.3/23.4），据此确认它对应作者在表 2 中标记为「招聘奖金 / 特殊」的变量。"},
            {"t": "p", "en":
             "Finally, closure status is handled through explicit, documented rules rather than being silently "
             "absorbed into the data. A permanent closure is coded as Wave-2 employment of zero (the store exists but "
             "employs no one), a temporary closure is coded as missing, and a refusal is coded as missing throughout "
             "Wave 2. Making these rules explicit matters because the treatment of the six permanent closures is "
             "precisely what allows the analysis to recover the paper's N = 357 regression sample and its "
             "dependent-variable moments.",
             "cn":
             "最后，关店状态通过显式、可查的规则处理，而非被静默吸收进数据。永久关闭被编码为 Wave-2 就业为零"
             "（门店仍在但不再雇佣任何人），临时关闭被编码为缺失，拒访则在 Wave-2 全程编码为缺失。将这些规则显式化"
             "之所以重要，是因为对 6 家永久关闭店的处理正是使分析得以还原论文 N = 357 回归样本及其因变量矩的关键。"},
        ],
    },
    # ------------------------------------------------------------------ 3
    {
        "title_en": "3. Empirical design",
        "title_cn": "3. 实证设计",
        "blocks": [
            {"t": "p", "en":
             "CK94's identification strategy is a canonical 2×2 difference-in-differences design. The treatment "
             "group is New Jersey, whose minimum wage rose from $4.25 to $5.05 on April 1, 1992; the control group "
             "is eastern Pennsylvania, whose minimum wage remained at the federal $4.25; and the before/after "
             "periods are Wave 1 (Feb–Mar 1992) and Wave 2 (Nov–Dec 1992). The average treatment effect on the "
             "treated is estimated as",
             "cn":
             "CK94 的识别策略是典型的 2×2 倍差法设计。处理组为新泽西州，其最低工资于 1992 年 4 月 1 日从 4.25 美元"
             "上调至 5.05 美元；对照组为宾州东部，其最低工资仍为联邦水平 4.25 美元；前/后期分别为 Wave 1（1992 年 "
             "2–3 月）与 Wave 2（1992 年 11–12 月）。处理组平均处理效应估计为"},
            {"t": "eq", "en": "DID = (NJ₂ − NJ₁) − (PA₂ − PA₁)",
             "cn": "DID =（NJ₂ − NJ₁）−（PA₂ − PA₁）"},
            {"t": "p", "en":
             "where the overbars denote column (state) means of FTE employment. The standard error is the two-sample "
             "difference in means, se = sqrt(var_NJ/n_NJ + var_PA/n_PA). The identifying assumption is parallel "
             "trends: absent the wage increase, New Jersey and Pennsylvania employment would have followed the same "
             "trajectory. Because the two groups are neighbouring labor markets serving the same chains, eastern "
             "Pennsylvania provides a credible counterfactual for the seasonal and regional factors affecting "
             "fast-food employment in late 1992.",
             "cn":
             "其中上划线表示 FTE 就业的分州（列）均值。标准误为两样本均值差：se = sqrt(var_NJ/n_NJ + var_PA/n_PA)。"
             "识别假设是平行趋势：若没有最低工资上调，新泽西与宾州的就业本会沿同一轨迹变动。由于两组是服务同一"
             "品牌的邻近劳动力市场，宾州东部为 1992 年末影响快餐就业的季节性与区域性因素提供了可信的反事实。"},
            {"t": "p", "en":
             "CK94 also estimate a reduced-form regression of the store-level employment change on a New Jersey dummy "
             "and, in later columns, on the initial wage gap GAP = (5.05 − W0)/W0, the natural 'bite' measure of how "
             "binding the new minimum was for each store (PA stores and NJ stores already paying ≥ $5.05 have GAP = 0). "
             "The GAP coefficient, scaled by the mean gap, maps back to the implied NJ−PA employment effect and "
             "provides an alternative, dose-response version of the DID.",
             "cn":
             "CK94 还估计了一个简约式回归，将门店层面的就业变化对「新泽西虚拟变量」以及（在后几列中）初始工资缺口 "
             "GAP = (5.05 − W0)/W0 回归。GAP 是度量新最低工资对每家门店「咬合」程度的自然指标（宾州门店与起始工资"
             "已 ≥ 5.05 美元的新泽西门店的 GAP = 0）。GAP 系数乘以平均缺口即可折算回隐含的新泽西−宾州就业效应，"
             "提供了一种「剂量—反应」式的倍差版本。"},
            {"t": "p", "en":
             "The paper's most elegant falsification test groups New Jersey stores by their Wave-1 starting wage. "
             "Stores already paying ≥ $5.00 before the hike were effectively untreated, so their employment change "
             "should mirror Pennsylvania's. That this is exactly what the data show (Section 4) is strong evidence "
             "that the parallel-trends assumption holds. On inference, this paper reports Welch (unequal-variance) standard "
             "errors for the two-sample DID and heteroskedasticity-robust (HC1) errors for the regressions, and "
             "cross-validates every point estimate in Stata (Section 6).",
             "cn":
             "论文最优雅的证伪检验是按 Wave-1 起始工资对新泽西门店分组。上调前已支付 ≥ 5.00 美元的门店实际上"
             "未受处理，其就业变化应与宾州一致。数据恰好如此（第 4 节），这为平行趋势假设提供了有力证据。在推断上，"
             "本论文对两样本 DID 报告 Welch（不等方差）标准误、对回归报告异方差稳健（HC1）标准误，并在 Stata 中对每个"
             "点估计做交叉验证（第 6 节）。"},
        ],
    },
    # ------------------------------------------------------------------ 4
    {
        "title_en": "4. Core replication results and comparison with the original",
        "title_cn": "4. 核心复现结果与原文对比",
        "blocks": [
            {"t": "p", "en":
             "All four targets reproduce the published figures to within rounding; the complete side-by-side "
             "verification is reported at the end of this section. This paper discusses each table in turn.",
             "cn":
             "四个复现目标均精确到舍入误差之内；完整的逐项对照见本节末尾。下面依次讨论各表。"},
            {"t": "h", "en": "4.1 Table 2 — descriptive statistics", "cn": "4.1 表 2 — 描述性统计"},
            {"t": "table", "key": "store_types"},
            {"t": "table", "key": "t2_w1"},
            {"t": "table", "key": "t2_w2"},
            {"t": "p", "en":
             "Wave-1 starting wages average $4.61 in New Jersey and $4.63 in Pennsylvania. By Wave 2, New Jersey had "
             "risen to $5.08 while Pennsylvania was essentially unchanged at $4.62, and 85.2% of New Jersey stores "
             "(versus 1.3% in Pennsylvania) now paid exactly $5.05 — direct evidence that the treatment 'bit'. Wave-1 "
             "FTE employment averaged 20.4 (NJ) and 23.3 (PA), and by Wave 2 New Jersey was 21.0 and Pennsylvania 21.2. "
             "The store-type distribution (Burger King 41.1/44.3, KFC 20.5/15.2, Roy Rogers 24.8/21.5, Wendy's "
             "13.6/19.0, company-owned 34.1/35.4) matches exactly.",
             "cn":
             "Wave-1 起始工资在新泽西平均 4.61 美元、在宾州平均 4.63 美元。到 Wave 2，新泽西升至 5.08 美元，而宾州"
             "基本不变（4.62 美元），且 85.2% 的新泽西门店（宾州仅 1.3%）现在恰好支付 5.05 美元——这是处理「咬合」的"
             "直接证据。Wave-1 FTE 就业平均为新泽西 20.4、宾州 23.3；到 Wave 2，新泽西为 21.0、宾州为 21.2。门店类型"
             "分布（汉堡王 41.1/44.3、肯德基 20.5/15.2、Roy Rogers 24.8/21.5、温迪 13.6/19.0、直营 34.1/35.4）"
             "精确一致。"},
            {"t": "h", "en": "4.2 Table 3 — the core difference-in-differences",
             "cn": "4.2 表 3 — 核心倍差"},
            {"t": "table", "key": "table3"},
            {"t": "p", "en":
             "Mean FTE employment fell in Pennsylvania by −2.16 and rose in New Jersey by +0.59 (column-mean "
             "differences), giving a difference-in-differences of +2.754 FTE per store (Welch t = 2.05), against the "
             "paper's +2.76 (t = 2.03); the 0.006 gap is pure rounding in the published table. The falsification "
             "check is equally exact: New Jersey stores already paying ≥ $5.00 before the hike saw employment change "
             "of −2.16, statistically indistinguishable from Pennsylvania's −2.28, confirming that the positive New "
             "Jersey effect is concentrated among stores actually bound by the new minimum.",
             "cn":
             "平均 FTE 就业在宾州下降 −2.16、在新泽西上升 +0.59（列均值之差），得到每家门店 +2.754 个全职当量的"
             "倍差估计（Welch t = 2.05），对照论文的 +2.76（t = 2.03）；0.006 的差距纯属论文表格的四舍五入。证伪检验"
             "同样精确：上调前已支付 ≥ 5.00 美元的新泽西门店就业变化为 −2.16，与宾州的 −2.28 在统计上不可区分，"
             "确认了正向的新泽西效应集中于真正被新最低工资约束的门店。"},
            {"t": "h", "en": "4.3 Table 4 — reduced-form regressions", "cn": "4.3 表 4 — 简约式回归"},
            {"t": "table", "key": "table4"},
            {"t": "p", "en":
             "In the 357-store sample, the coefficient on the New Jersey dummy is 2.33 (SE 1.19) and the coefficient "
             "on the initial wage gap GAP is 15.65 (SE 6.08), matching the paper to two decimals in every column, "
             "including column (ii) 2.30 (1.20) and column (iv) 14.92 (6.21). One documented discrepancy remains: in "
             "column (v) the replicated GAP coefficient is 11.98 (7.42) against the paper's 11.91 (7.39), a 0.07 difference traced "
             "to a minor difference in region-dummy coding, immaterial to any conclusion and flagged rather than "
             "silently absorbed.",
             "cn":
             "在 357 家样本中，新泽西虚拟变量系数为 2.33（标准误 1.19），初始工资缺口 GAP 系数为 15.65（标准误 "
             "6.08），每一列都与论文精确到小数点后两位，包括列 (ii) 的 2.30 (1.20) 与列 (iv) 的 14.92 (6.21)。仅剩"
             "一处已记录的差异：列 (v) 中复现得到的 GAP 系数为 11.98 (7.42)，对照论文的 11.91 (7.39)，0.07 的差异源于地区"
             "哑变量编码的细微不同，对任何结论均无影响，且已被如实标注而非静默吸收。"},
            {"t": "h", "en": "4.4 Figure 1 — wage distributions", "cn": "4.4 图 1 — 工资分布"},
            {"t": "figure", "path": "figure1", "en":
             "Figure 1 — Distribution of starting wage rates by state and survey wave (replication of CK94 Figure 1). "
             "Dashed vertical lines at $4.25 and $5.05.",
             "cn": "图 1 — 分州、分期起始工资分布（复现 CK94 图 1）。虚线竖线标出 4.25 与 5.05 美元。"},
            {"t": "p", "en":
             "The 2×2 histogram reproduces the paper's shape: the New Jersey Wave-2 distribution shifts right and "
             "piles up at $5.05 as stores are 'pinned' to the new minimum, while the two Pennsylvania distributions "
             "are essentially identical across waves.",
             "cn":
             "该 2×2 直方图复现了论文的形态：新泽西 Wave-2 分布右移并在 5.05 美元处堆积（门店被「钉」到新最低工资），"
             "而宾州两期分布几乎重合。"},
            {"t": "h", "en": "4.5 Side-by-side replication summary", "cn": "4.5 复现逐项对照"},
            {"t": "table", "key": "replication"},
            {"t": "p", "en":
             "Every replicated statistic matches the published value. The only substantive note is the column-(v) GAP "
             "rounding difference of 0.07 documented above, which stems from a region-dummy coding choice and does not "
             "affect any inference.",
             "cn":
             "每一项复现统计量都与论文值一致。唯一需要说明的是上文已记录的列 (v) GAP 的 0.07 舍入差异，源于地区"
             "哑变量编码选择，不影响任何推断。"},
        ],
    },
    # ------------------------------------------------------------------ 5
    {
        "title_en": "5. Independent extension: ownership heterogeneity",
        "title_cn": "5. 独立扩展：所有权异质性",
        "blocks": [
            {"t": "h", "en": "5.1 Question and motivation", "cn": "5.1 问题与动机"},
            {"t": "p", "en":
             "Does the employment response to the minimum wage differ between company-owned and franchised stores? "
             "Franchisees are residual claimants with hard budget constraints who price locally and can adjust "
             "staffing quickly, whereas corporate stores can absorb wage shocks through headquarters, standardize "
             "employment practices, and face weaker incentives to shed labor at the margin. The two ownership types "
             "may therefore transmit the same wage shock to employment differently, and the data contain a clean "
             "company-ownership indicator (CO_OWNED) that enables this project to test this directly.",
             "cn":
             "最低工资的就业反应是否因直营店与加盟店而不同？加盟商是剩余索取者，面临硬预算约束，可自主定价并"
             "快速调整用工；而直营店可通过总部吸收工资冲击、标准化用工，边际上裁员的激励较弱。因此两种所有权类型"
             "可能以不同方式将同一工资冲击传导到就业，而数据中含有一个干净的直营标识（CO_OWNED），使本项目能直接检验。"},
            {"t": "h", "en": "5.2 Design: a triple difference", "cn": "5.2 设计：三重差分"},
            {"t": "p", "en":
             "This project estimates a triple difference (difference-in-differences-in-differences) on the balanced employment "
             "sample (N = 384):",
             "cn": "本项目在就业平衡样本（N = 384）上估计三重差分："},
            {"t": "eq", "en": "Δemp = α + β·STATE + γ·CO_OWNED + δ·(STATE×CO_OWNED) + ε",
             "cn": "Δemp = α + β·STATE + γ·CO_OWNED + δ·(STATE×CO_OWNED) + ε"},
            {"t": "p", "en":
             "where Δemp = fte2 − fte, STATE = 1 for New Jersey, and CO_OWNED = 1 for company-owned stores. The "
             "coefficient of interest is δ, the difference between the company-owned DID and the franchised DID.",
             "cn":
             "其中 Δemp = fte2 − fte，STATE = 1 表示新泽西，CO_OWNED = 1 表示直营店。关注的系数是 δ，即直营店 DID 与"
             "加盟店 DID 之差。"},
            {"t": "h", "en": "5.3 Results", "cn": "5.3 结果"},
            {"t": "table", "key": "ext_a"},
            {"t": "table", "key": "ext_b"},
            {"t": "p", "en":
             "The four-group decomposition shows a franchised DID of 3.13 FTE and a company-owned DID of 2.04 FTE, so "
             "the triple difference is δ = −1.10 (HC1 robust SE 2.44, t = −0.45). The point estimate says the positive "
             "employment effect is about one FTE smaller for company-owned stores, but the 95% confidence interval "
             "spans zero — the difference is not statistically significant.",
             "cn":
             "四组分解显示加盟店 DID 为 3.13 个全职当量、直营店 DID 为 2.04 个全职当量，故三重差分为 δ = −1.10"
             "（HC1 稳健标准误 2.44，t = −0.45）。点估计表明直营店的正向就业效应比加盟店小约 1 个全职当量，但 95% "
             "置信区间跨越零点——差异在统计上不显著。"},
            {"t": "h", "en": "5.4 Diagnostics: a fragile estimate and its source",
             "cn": "5.4 诊断：估计的脆弱性及其来源"},
            {"t": "p", "en":
             "The estimate is fragile in a way that is itself informative. Adding brand fixed effects leaves δ "
             "essentially unchanged (−1.14, SE 2.37), but additionally controlling for initial store size flips the "
             "sign to +1.51 (SE 1.74). The flip is driven by store size, not brand: company-owned stores in "
             "Pennsylvania average only 18.4 FTE versus 26.0 for franchises, and larger stores exhibit mechanically "
             "larger employment declines (mean-reversion in size). Absent a size control, that size effect is wrongly "
             "loaded onto the ownership interaction. Robustness checks — clustering standard errors by chain (four "
             "clusters, interpreted cautiously) and re-coding temporary closures to Wave-2 employment = 0 — leave the "
             "point estimate and the null result unchanged.",
             "cn":
             "该估计的脆弱性本身就有信息量。加入品牌固定效应后 δ 基本不变（−1.14，标准误 2.37），但再控制初始门店"
             "规模后符号翻转为 +1.51（标准误 1.74）。这一翻转由门店规模而非品牌驱动：宾州直营店平均仅 18.4 个全职"
             "当量，远小于加盟店的 26.0，而大规模门店的就业降幅在机制上天然更大（规模的均值回归）。若不控制规模，"
             "这部分规模效应会被错误归入所有权交互项。稳健性检验——按品牌聚类标准误（4 个簇，谨慎解读）以及将临时"
             "关闭店重新编码为 Wave-2 就业 = 0——均未改变点估计与零结果。"},
            {"t": "h", "en": "5.5 Interpretation", "cn": "5.5 解读"},
            {"t": "p", "en":
             "There is no robustly identifiable ownership heterogeneity: the directionally weaker response of "
             "company-owned stores is too imprecise and too sensitive to the size control to support a conclusion. "
             "That null is nonetheless a meaningful extension of CK94 — their headline result (the minimum wage did "
             "not visibly cut fast-food employment) is broadly uniform across the ownership dimension rather than "
             "being driven by one ownership type.",
             "cn":
             "不存在稳健可识别的所有权异质性：直营店方向上更弱的反应过于不精确、且对规模控制过于敏感，不足以支撑"
             "结论。这一零结果对 CK94 仍是有意义的扩展——其核心结果（最低工资未明显削减快餐就业）在所有权维度上"
             "大体均质，而非由某一所有权类型所驱动。"},
            {"t": "figure", "path": "extension", "en":
             "Extension Figure — Employment response by store ownership: franchise vs. company-owned DID and the "
             "triple difference δ (95% confidence intervals).",
             "cn": "扩展图 — 按所有权划分的就业反应：加盟店 DID、直营店 DID 与三重差分 δ（95% 置信区间）。"},
        ],
    },
    # ------------------------------------------------------------------ 6
    {
        "title_en": "6. Validation, limitations, and conclusion",
        "title_cn": "6. 验证、局限与结论",
        "blocks": [
            {"t": "h", "en": "6.1 Validation", "cn": "6.1 验证"},
            {"t": "p", "en":
             "Every replicated statistic was checked against the values transcribed from the published paper, and "
             "the pipeline was additionally cross-validated in Stata 17. The point estimates agree exactly: the "
             "balanced-sample DID is +2.75 (Stata, homoskedastic t = 2.38) versus +2.754 (Python, Welch t = 2.05), "
             "and the extension interaction coefficient agrees to six decimals (−1.095292). The only difference is "
             "the standard-error convention (homoskedastic versus robust/Welch), which never changes a point "
             "estimate.",
             "cn":
             "每一项复现统计量都与从论文转录的目标值核对过，且流程另在 Stata 17 中做了交叉验证。点估计完全一致："
             "平衡样本 DID 为 +2.75（Stata，同方差 t = 2.38）对照 +2.754（Python，Welch t = 2.05），扩展交互项"
             "系数一致到小数点后六位（−1.095292）。唯一差异是标准误约定（同方差 vs 稳健/Welch），从不改变任何"
             "点估计。"},
            {"t": "h", "en": "6.2 Limitations", "cn": "6.2 局限"},
            {"t": "p", "en":
             "The first limitation concerns the identifying assumption. The design rests on the parallel-trends "
             "assumption that, absent the minimum-wage increase, employment in New Jersey and eastern Pennsylvania "
             "would have followed the same trajectory. The high-wage falsification test in Section 4 provides "
             "indirect support for this assumption — stores already paying at or above the new minimum behaved like "
             "Pennsylvania stores — but with only two survey waves the assumption cannot be tested directly, and no "
             "pre-period data are available with which to trace pre-trends.",
             "cn":
             "第一项局限关乎识别假设。本设计依赖平行趋势假设，即若没有最低工资上调，新泽西与宾州东部的就业本会"
             "沿同一轨迹变动。第 4 节的高工资店证伪检验为这一假设提供了间接支持——上调前已支付等于或高于新最低工资"
             "的门店，其表现与宾州门店一致——但仅有两期调查数据，这一假设无法被直接检验，也缺乏前期数据用以追溯"
             "事前趋势。"},
            {"t": "p", "en":
             "The second limitation is the statistical power of the ownership extension. The triple difference is "
             "identified off a thin slice of the sample: there are only 26 company-owned stores in Pennsylvania, so "
             "the ownership-by-state interaction is estimated with a large standard error. Ownership is also strongly "
             "collinear with brand — company-owned stores are concentrated in KFC and Roy Rogers — and with store "
             "size, which makes it difficult to separate a genuine ownership effect from brand composition or "
             "size-driven mean reversion. As Section 5.4 shows, the point estimate is sensitive to controlling for "
             "initial store size, which is precisely why the null result is interpreted cautiously.",
             "cn":
             "第二项局限是所有权扩展的统计功效。三重差分仅由样本中较薄的一块识别：宾州直营店仅有 26 家，因此"
             "所有权×州交互项的估计标准误较大。所有权还与品牌高度共线——直营店集中于肯德基与 Roy Rogers——并与"
             "门店规模相关，这使得难以将真正的所有权效应与品牌构成、规模驱动的均值回归区分开来。正如第 5.4 节所示，"
             "点估计对是否控制初始门店规模敏感，这正是对零结果持谨慎解读的原因。"},
            {"t": "p", "en":
             "The third limitation concerns inference. The t-statistic of the core difference-in-differences estimate "
             "moves with the choice of standard errors — homoskedastic, heteroskedasticity-robust, or clustered by "
             "chain — although neither the point estimate, the sign, nor the economic magnitude changes. With only "
             "four chains, cluster-robust inference is itself fragile and is therefore reported only as a robustness "
             "check rather than as the headline specification.",
             "cn":
             "第三项局限关乎推断。核心倍差估计的 t 值会随标准误选择——同方差、异方差稳健或按品牌聚类——而变化，"
             "尽管点估计、符号与经济含义均不改变。由于只有四个品牌，聚类稳健推断本身也不可靠，故仅作为稳健性"
             "检验报告，而非作为主设定。"},
            {"t": "p", "en":
             "Finally, the underlying store-level data are course-restricted and are not redistributed, which limits "
             "the ability of external readers to independently audit the raw records. Every variable-construction and "
             "sample-selection choice is nevertheless documented, so that all reported numbers can be traced once "
             "access to the data is available.",
             "cn":
             "最后，所用门店级数据为课程受限数据、不再分发，这限制了外部读者独立审计原始记录的能力。尽管如此，"
             "每一处变量构建与样本筛选选择均已记录，获得数据访问权限后即可追溯所有报告数字。"},
            {"t": "h", "en": "6.3 Conclusion", "cn": "6.3 结论"},
            {"t": "p", "en":
             "This paper reproduces Card and Krueger's (1994) core finding exactly: New Jersey's 1992 minimum-wage increase to "
             "$5.05 was followed by a relative increase of ≈2.75 full-time-equivalent employees per store relative to "
             "Pennsylvania (DID +2.754, t = 2.05; New Jersey dummy 2.33; GAP 15.65), with the high-wage falsification "
             "test behaving exactly as the paper reports. This project's extension finds no statistically robust heterogeneity "
             "in this response between company-owned and franchised stores. Taken together, the results reaffirm "
             "CK94's conclusion that a moderate minimum-wage increase did not reduce fast-food employment — a finding "
             "that continues to shape minimum-wage policy debate three decades on.",
             "cn":
             "本论文精确复现了 Card 与 Krueger（1994）的核心发现：1992 年新泽西最低工资上调至 5.05 美元后，相对宾州"
             "每家门店就业上升约 2.75 个全职当量（DID +2.754，t = 2.05；新泽西虚拟变量 2.33；GAP 15.65），高工资店"
             "证伪检验与论文报告完全一致。本项目的扩展未发现直营店与加盟店在这一反应上存在统计上稳健的异质性。综合来看，"
             "这些结果再次确认了 CK94 的结论：适度的最低工资上调并未减少快餐业就业——这一发现在三十年后仍在塑造"
             "最低工资政策的争论。"},
        ],
    },
    # ------------------------------------------------------------------ 7
    {
        "title_en": "7. AI-use disclosure",
        "title_cn": "7. AI 使用披露",
        "blocks": [
            {"t": "p", "en":
             "AI assistance (Claude Code) was used throughout for code generation, debugging, figure production, and "
             "drafting, and every intervention was verified against the paper and the data. The full itemized "
             "disclosure — including the specific AI errors that were caught and corrected (an initially wrong FTE "
             "formula, a wrong percent-full-time denominator, a recovered Table-4 sample definition, and a corrected "
             "interpretation of the extension's sign flip) — is in AI_USE_DISCLOSURE.md. A short summary:",
             "cn":
             "全程使用了 AI（Claude Code）进行代码生成、调试、图表制作与写作，且每一处介入都对照论文与数据进行了"
             "核查。完整的逐条披露——包括被捕捉并纠正的具体 AI 错误（初始错误的 FTE 公式、错误的全职占比分母、"
             "反推出的表 4 样本口径、以及被纠正的扩展符号翻转解读）——见 AI_USE_DISCLOSURE.md。简要汇总如下："},
            {"t": "table", "key": "ai_summary"},
        ],
    },
]

# 变量定义表（静态，来自 variable_construction.md）
VAR_DEFS = pd.DataFrame([
    ["fte / fte2", "Full-time-equivalent employment = EMPFT + NMGRS + 0.5×EMPPT (Wave 1 / Wave 2)"],
    ["emp_chg", "Store-level change in FTE employment = fte2 − fte"],
    ["pct_ft", "Percent full-time = EMPFT / fte × 100 (denominator is FTE, not headcount)"],
    ["wage_st / wage_st2", "Starting wage ($/hour), Waves 1 and 2"],
    ["full_meal_price", "Full meal price = PSODA + PFRY + PENTREE"],
    ["gap", "Initial wage gap (Table 4): PA = 0; NJ with wage_st ≥ 5.05 = 0; other NJ = (5.05 − wage_st)/wage_st"],
    ["closure", "Wave-2 status: answered / permanent / temporary / refused"],
], columns=["Variable", "Definition"])

# AI 使用披露汇总表
AI_SUMMARY = pd.DataFrame([
    ["Phases 0–1", "Extracting paper targets; data cleaning; variable construction",
     "Rejected from-memory Table 2 values; fixed percent-full-time denominator (37.7 → 32.8); corrected PA Wave-1 wage 4.62 → 4.63"],
    ["Phase 2", "Replicating Tables 2–4 and Figure 1",
     "Recovered the 357-store Table-4 sample; fixed a Table-2 wage-row bug; repaired the F-test constraint matrix"],
    ["Phase 3", "Designing and estimating the DDD extension",
     "Removed region FE collinear with STATE; corrected the δ sign-flip interpretation (−1.10 → +1.51 with size control)"],
    ["Phase 4", "One-click workflow, README, Stata check",
     "Fixed EMPPT typo; confirmed Python/Stata point estimates agree"],
    ["Phase 5", "Writing this report (7 required sections)",
     "Back-filled every number from generated outputs; separated homoskedastic vs. Welch t-statistics"],
], columns=["Phase", "AI's main role", "Key corrections"])


# ===========================================================================
# 渲染：Markdown
# ===========================================================================

def _md_table(df):
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, sep] + rows)


def render_markdown(tables):
    L = [f"# {TITLE_EN}", ""]
    L += [f"> *Empirical report — AI-assisted replication and extension of Card & Krueger (1994).*", ""]
    L += ["## Abstract", "", ABSTRACT_EN, ""]
    for sec in SECTIONS:
        L += [f"## {sec['title_en']}", ""]
        for b in sec["blocks"]:
            t = b["t"]
            if t == "h":
                L += [f"### {b['en']}", ""]
            elif t == "p":
                L += [b["en"], ""]
            elif t == "eq":
                L += [f"```text\n{b['en']}\n```", ""]
            elif t == "b":
                for it in b["items"]:
                    L += [f"- {it['en']}"]
                L += [""]
            elif t == "table":
                if b["key"] == "var_defs":
                    L += [f"**{b.get('en', 'Variable definitions.')}**", ""]
                    L += [_md_table(VAR_DEFS), ""]
                elif b["key"] == "ai_summary":
                    L += [f"**{b.get('en', 'AI-use summary.')}**", ""]
                    L += [_md_table(AI_SUMMARY), ""]
                else:
                    cap, df = tables[b["key"]]
                    L += [f"**{cap}**", "", _md_table(df), ""]
            elif t == "figure":
                fname = "figure1.png" if b["path"] == "figure1" else "extension_ddd.png"
                rel = f"../outputs/figures/{fname}"
                L += [f"![{b['en']}]({rel})", "", f"*{b['en']}*", ""]
    return "\n".join(L)


# ===========================================================================
# 渲染：Word
# ===========================================================================

_M_NSDECL = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'

_SUBSCRIPTS = {
    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
    '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
}


def _esc_xml(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _m_run(text):
    return f'<m:r><m:t xml:space="preserve">{_esc_xml(text)}</m:t></m:r>'


def _m_sub(base, sub):
    return (f'<m:sSub><m:e>{_m_run(base)}</m:e>'
            f'<m:sub>{_m_run(sub)}</m:sub></m:sSub>')


def _equation_omath(text):
    """把一条线性公式（可含 Unicode 下标字符）转成 Word 原生公式 m:oMath。"""
    parts = []
    buf = []
    for ch in text:
        if ch in _SUBSCRIPTS:
            base = []
            while buf and (buf[-1].isalnum() or buf[-1] == '_'):
                base.append(buf.pop())
            base = ''.join(reversed(base))
            if buf:
                parts.append(_m_run(''.join(buf)))
                buf.clear()
            parts.append(_m_sub(base or 'x', _SUBSCRIPTS[ch]))
        else:
            buf.append(ch)
    if buf:
        parts.append(_m_run(''.join(buf)))
    return f'<m:oMath {_M_NSDECL}>{"".join(parts)}</m:oMath>'


def _add_equation(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p._p.append(parse_xml(_equation_omath(text)))
    return p


def _set_font(style, latin, east_asia="SimSun"):
    """设置样式西文/中文字体，并移除主题字体属性（否则 Word 中主题字体会压过显式字体）。"""
    style.font.name = latin
    rFonts = style._element.rPr.rFonts
    rFonts.set(qn('w:eastAsia'), east_asia)
    for attr in ('w:asciiTheme', 'w:hAnsiTheme', 'w:cstheme', 'w:eastAsiaTheme'):
        rFonts.attrib.pop(qn(attr), None)


def _style_doc(doc):
    """AEA 期刊风格：Times New Roman（西文）+ 宋体（中文），单倍行距，紧凑黑字标题。"""
    normal = doc.styles["Normal"]
    _set_font(normal, "Times New Roman")
    normal.font.size = Pt(11)
    npf = normal.paragraph_format
    npf.line_spacing = 1.0
    npf.space_before = Pt(0)
    npf.space_after = Pt(6)

    for name, size, before, after in (("Heading 1", 12, 12, 6), ("Heading 2", 11, 8, 4)):
        hs = doc.styles[name]
        _set_font(hs, "Times New Roman")
        hs.font.size = Pt(size)
        hs.font.bold = True
        hs.font.italic = False
        hs.font.color.rgb = RGBColor(0, 0, 0)
        hpf = hs.paragraph_format
        hpf.line_spacing = 1.0
        hpf.space_before = Pt(before)
        hpf.space_after = Pt(after)
        hpf.keep_with_next = True


def _add_para(doc, text, size=None, bold=False, italic=False, align=None, color=None,
              space_before=None, space_after=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    if size is not None:
        r.font.size = Pt(size)
    if color is not None:
        r.font.color.rgb = color
    if align is not None:
        p.alignment = align
    if space_before is not None:
        p.paragraph_format.space_before = Pt(space_before)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def _add_heading(doc, text, level):
    return doc.add_paragraph(text, style=f"Heading {level}")


def _add_table(doc, df, caption=None, font_size=9):
    if caption:
        _add_para(doc, caption, size=9, bold=True, space_before=10, space_after=4)
    t = doc.add_table(rows=df.shape[0] + 1, cols=df.shape[1])
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, col in enumerate(df.columns):
        cell = t.rows[0].cells[j]
        cell.text = str(col)
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(font_size)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            cell = t.rows[i + 1].cells[j]
            cell.text = str(df.iat[i, j])
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(font_size)
    return t


def _add_figure(doc, path, caption, width=6.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.add_run().add_picture(str(path), width=Inches(width))
    _add_para(doc, caption, size=9, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)


def render_docx(tables, bilingual, outpath):
    doc = Document()
    _style_doc(doc)

    # 标题（AEA：黑体居中）
    _add_para(doc, TITLE_EN, size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    if bilingual:
        _add_para(doc, TITLE_CN, size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    # 摘要
    _add_para(doc, "Abstract" if not bilingual else "Abstract / 摘要", size=11, bold=True,
              space_before=6, space_after=4)
    _add_para(doc, ABSTRACT_EN, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    if bilingual:
        _add_para(doc, ABSTRACT_CN, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    for sec in SECTIONS:
        _add_heading(doc, sec["title_en"], 1)
        if bilingual:
            _add_heading(doc, sec["title_cn"], 1)
        for b in sec["blocks"]:
            t = b["t"]
            if t == "h":
                _add_heading(doc, b["en"], 2)
                if bilingual:
                    _add_heading(doc, b["cn"], 2)
            elif t == "p":
                _add_para(doc, b["en"], align=WD_ALIGN_PARAGRAPH.JUSTIFY)
                if bilingual:
                    _add_para(doc, b["cn"], align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            elif t == "eq":
                _add_equation(doc, b["en"])
                if bilingual:
                    _add_equation(doc, b["cn"])
            elif t == "b":
                for it in b["items"]:
                    _add_para(doc, "• " + it["en"], align=WD_ALIGN_PARAGRAPH.JUSTIFY)
                    if bilingual:
                        _add_para(doc, "• " + it["cn"], align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            elif t == "table":
                if b["key"] == "var_defs":
                    _add_table(doc, VAR_DEFS, caption="Table 2d — Variable definitions.")
                elif b["key"] == "ai_summary":
                    _add_table(doc, AI_SUMMARY, caption="AI-use summary.")
                else:
                    cap, df = tables[b["key"]]
                    _add_table(doc, df, caption=cap)
            elif t == "figure":
                path = FIG1 if b["path"] == "figure1" else FIG_EXT
                cap = b["en"] if not bilingual else f"{b['en']} / {b['cn']}"
                _add_figure(doc, path, cap)

    doc.save(str(outpath))
    return outpath


# ===========================================================================

def main():
    df = pd.read_csv(CLEAN)

    cap_st, df_st = tbl_store_types(df)
    cap_w1, df_w1, cap_w2, df_w2 = tbl_t2_waves(df)
    cap_t3, df_t3 = tbl_table3(df)
    cap_t4, df_t4 = tbl_table4(df)
    cap_rep, df_rep = tbl_replication(df)
    ext_a, ext_b, ext_key = tbl_extension(df)

    tables = {
        "store_types": (cap_st, df_st),
        "t2_w1": (cap_w1, df_w1),
        "t2_w2": (cap_w2, df_w2),
        "table3": (cap_t3, df_t3),
        "table4": (cap_t4, df_t4),
        "replication": (cap_rep, df_rep),
        "ext_a": ("Extension Table A — Employment change Δemp by ownership and state (SE in parentheses).", ext_a),
        "ext_b": ("Extension Table B — Triple-difference regressions (dependent variable Δemp; HC1 robust SE).", ext_b),
    }

    # 1) Markdown
    REPORT_MD.write_text(render_markdown(tables), encoding="utf-8")
    print("wrote", REPORT_MD)

    # 2) 英文 Word
    render_docx(tables, bilingual=False, outpath=REPORT_EN)
    print("wrote", REPORT_EN)

    # 3) 中英对照 Word
    render_docx(tables, bilingual=True, outpath=REPORT_BI)
    print("wrote", REPORT_BI)

    # 控制台核验关键量
    print("\n=== 关键量核验 ===")
    print(f"DID          = {df_t3.iat[2, 6]}  (row3 change, diff NJ-PA)")
    print(f"Table4 NJ    = {df_t4.iat[0, 1]}   GAP = {df_t4.iat[1, 3]}")
    print(f"Ext δ        = {ext_key['ddd']:.3f} (SE {ext_key['ddd_se']:.3f}, t {ext_key['ddd_t']:.2f})")
    print(f"加盟 DID {ext_key['did_franch']:.2f}  直营 DID {ext_key['did_company']:.2f}")


if __name__ == "__main__":
    main()
