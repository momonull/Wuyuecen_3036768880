"""
01_clean.py — Phase 1: 数据清洗与变量构建

Card & Krueger (1994) "Minimum Wages and Employment" 复现项目。

读入 data/raw/public.csv（原始数据，不改动），构造全部派生变量，
输出 data/processed/ck94_clean.csv。

口径依据：PROJECT_PLAN.md §3.2 与 output/replication_targets.md（PDF 第 776 页逐格核对）。

构造变量（映射见 data/processed/variable_construction.md）：
  fte               全职当量就业 = EMPFT + NMGRS + 0.5*EMPPT
  fte2              Wave2 全职当量就业 = EMPFT2 + NMGRS2 + 0.5*EMPPT2
  pct_ft            全职占比(%) = EMPFT / fte * 100       （⚠️ 分母是 fte，非员工总数）
  pct_ft2           Wave2 全职占比(%) = EMPFT2 / fte2 * 100
  full_meal_price   全餐价格 = PSODA + PFRY + PENTREE
  full_meal_price2  Wave2 全餐价格 = PSODA2 + PFRY2 + PENTREE2
  emp_chg           店内就业变化 = fte2 - fte
  wage_chg          起始工资变化 = WAGE_ST2 - WAGE_ST
  gap               初始工资缺口（Table 4）：PA=0；NJ 且 WAGE_ST>=5.05 时=0；
                    其余 NJ 为 (5.05 - WAGE_ST)/WAGE_ST；NJ 缺 WAGE_ST 时为缺失
  closure           关店状态（分类）：answered / permanent / temporary / refused
  bal_emp           就业平衡样本标记：fte 与 fte2 均非缺失

关店处理（原文 Table 2 注，STATUS2 见 DATA_DICTIONARY）：
  永久关闭 STATUS2==3（6 家）  Wave2 就业 = 0 —— 原始数据 EMPFT2/EMPPT2/NMGRS2 已为 0，无需改动
  临时关闭 STATUS2∈{2,4,5}（4 家）  Wave2 就业 = 缺失 —— 原始数据即为 NaN
  拒访     STATUS2==0（1 家）  Wave2 全部缺失
"""

import sys

import numpy as np
import pandas as pd
from pathlib import Path

# Windows 控制台默认可能用 GBK 编码，强制 stdout 用 UTF-8，避免中文摘要乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "public.csv"
OUT_DIR = ROOT / "data" / "processed"
OUT = OUT_DIR / "ck94_clean.csv"


def build_variables(df):
    out = df.copy()

    # ---- 就业（全职当量）----
    out["fte"] = out["EMPFT"] + out["NMGRS"] + 0.5 * out["EMPPT"]
    out["fte2"] = out["EMPFT2"] + out["NMGRS2"] + 0.5 * out["EMPPT2"]

    # ---- 全职占比（分母为全职当量 fte，不是员工总数）----
    out["pct_ft"] = out["EMPFT"] / out["fte"] * 100
    out["pct_ft2"] = out["EMPFT2"] / out["fte2"] * 100

    # ---- 全餐价格 ----
    out["full_meal_price"] = out["PSODA"] + out["PFRY"] + out["PENTREE"]
    out["full_meal_price2"] = out["PSODA2"] + out["PFRY2"] + out["PENTREE2"]

    # ---- 变化量 ----
    out["emp_chg"] = out["fte2"] - out["fte"]
    out["wage_chg"] = out["WAGE_ST2"] - out["WAGE_ST"]

    # ---- 关店状态 ----
    closure = pd.Series("answered", index=out.index)
    closure[out.STATUS2 == 3] = "permanent"
    closure[out.STATUS2.isin([2, 4, 5])] = "temporary"
    closure[out.STATUS2 == 0] = "refused"
    out["closure"] = closure

    # ---- 就业平衡样本标记（Table 3 row 4 用）----
    out["bal_emp"] = out["fte"].notna() & out["fte2"].notna()

    # ---- GAP（Table 4 的初始工资缺口）----
    gap = pd.Series(np.nan, index=out.index)
    gap[out.STATE == 0] = 0.0                       # PA 店
    nj = out.STATE == 1
    gap[nj & (out.WAGE_ST >= 5.05)] = 0.0           # NJ 起始工资已 >= 新最低工资
    low = nj & (out.WAGE_ST < 5.05)
    gap[low] = (5.05 - out.WAGE_ST[low]) / out.WAGE_ST[low]
    out["gap"] = gap

    return out


def summarize(df):
    """生成核验摘要文本，与 output/replication_targets.md 的原文目标值比对。"""
    L = []
    a = L.append
    a("")
    a("=== 门店类型分布 (%)  [目标: BK 41.1/44.3, KFC 20.5/15.2, Roy 24.8/21.5, Wendy 13.6/19.0, 直营 34.1/35.4] ===")
    for st, name in [(1, "NJ"), (0, "PA")]:
        s = df[df.STATE == st]
        row = {c: float(round(100 * (s.CHAIN == c).mean(), 1)) for c in [1, 2, 3, 4]}
        row["直营"] = float(round(100 * (s.CO_OWNED == 1).mean(), 1))
        a(f"  {name}: {row}")

    a("")
    a("=== 关键均值 (NJ / PA)  [目标值见括号] ===")
    for st, name in [(1, "NJ"), (0, "PA")]:
        s = df[df.STATE == st]
        a(f"  {name}:")
        a(f"    Wave1 FTE       {s.fte.mean():.2f}   (20.4 / 23.3)")
        a(f"    Wave1 起始工资   {s.WAGE_ST.mean():.2f}   (4.61 / 4.63)")
        a(f"    Wave1 全职占比%  {s.pct_ft.mean():.1f}   (32.8 / 35.0)")
        a(f"    Wave1 全餐价格   {s.full_meal_price.mean():.2f}   (3.35 / 3.04)")
        a(f"    Wave2 FTE       {s.fte2.mean():.2f}   (21.0 / 21.2)")
        a(f"    Wave2 起始工资   {s.WAGE_ST2.mean():.2f}   (5.08 / 4.62)")
        a(f"    Wave2 全职占比%  {s.pct_ft2.mean():.1f}   (35.9 / 30.4)")
        a(f"    Wave2 全餐价格   {s.full_meal_price2.mean():.2f}   (3.41 / 3.03)")

    a("")
    a("=== 关店/样本计数 ===")
    a(f"  closure 分布: {df.closure.value_counts().to_dict()}")
    a(f"  bal_emp (就业平衡): {df.bal_emp.sum()} / {len(df)}")
    a(f"  NJ={ (df.STATE==1).sum() }, PA={ (df.STATE==0).sum() }")
    return "\n".join(L)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW)
    clean = build_variables(df)
    clean.to_csv(OUT, index=False)
    print(f"wrote {OUT}  ({clean.shape[0]} rows x {clean.shape[1]} cols)")
    text = summarize(clean)
    print(text)

    # 落盘核验快照，作为可查询日志（不必重跑即可查看）
    snapshot = ROOT / "output" / "clean_verification.txt"
    snapshot.write_text(f"# 01_clean.py 核验快照（自动生成，勿手改）\n\n{text}\n", encoding="utf-8")
    print(f"\nwrote verification snapshot: {snapshot}")


if __name__ == "__main__":
    main()
