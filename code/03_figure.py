"""
03_figure.py — Phase 2: 复现 Figure 1（起始工资分布直方图）

Card & Krueger (1994) "Minimum Wages and Employment" 复现项目。

读入 data/processed/ck94_clean.csv，生成 2×2 面板直方图（行 = 州，列 = 调查期）：
  行：New Jersey / Pennsylvania
  列：February 1992 (Wave 1) / November 1992 (Wave 2)
每个面板为起始工资（WAGE_ST / WAGE_ST2）的分布，并标出 $4.25 与 $5.05 两条参考线。

预期（与原文 Figure 1 一致）：
  * NJ Wave2 分布整体右移、在 $5.05 处大量堆积（最低工资上调后起始工资被「钉」到新底线）。
  * PA 两期分布几乎重合（对照州最低工资不变）。
输出 outputs/figures/figure1.png（300 dpi）。

口径：y 轴用「门店占比(fraction)」而非计数，使四面板在样本量不同时可直接比较；
      这是「分布」的标准表示。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # 无头环境，直接写文件
import matplotlib.pyplot as plt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "processed" / "ck94_clean.csv"
FIG_DIR = ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT = FIG_DIR / "figure1.png"

# 参考线
MIN_WAGE_OLD = 4.25
MIN_WAGE_NEW = 5.05


def main():
    df = pd.read_csv(CLEAN)
    nj = df[df.STATE == 1]
    pa = df[df.STATE == 0]

    panels = [
        ("New Jersey", "February 1992", nj.WAGE_ST),
        ("New Jersey", "November 1992", nj.WAGE_ST2),
        ("Pennsylvania", "February 1992", pa.WAGE_ST),
        ("Pennsylvania", "November 1992", pa.WAGE_ST2),
    ]

    # 统一分箱：$4.00–$6.50，箱宽 $0.10（起始工资以 $0.05 为步长，箱宽取 0.10 覆盖）
    bins = np.arange(4.00, 6.50, 0.10)

    fig, axes = plt.subplots(2, 2, figsize=(9, 6.5), sharex=True, sharey=True)
    axes = axes.ravel()

    for ax, (state, wave, wage) in zip(axes, panels):
        w = wage.dropna()
        # 门店占比（fraction）直方图
        ax.hist(w, bins=bins, weights=np.ones(len(w)) / len(w),
                edgecolor="black", linewidth=0.5, color="#4c72b0", alpha=0.85)
        ax.axvline(MIN_WAGE_OLD, color="crimson", linestyle="--", linewidth=1.2,
                   label="$4.25$")
        ax.axvline(MIN_WAGE_NEW, color="darkgreen", linestyle="--", linewidth=1.2,
                   label="$5.05$")
        ax.set_title(f"{state} — {wave}", fontsize=10)
        ax.grid(axis="y", alpha=0.25)
        ax.set_ylim(0, 1.0)

    for ax in axes[2:]:
        ax.set_xlabel("Starting wage ($/hour)")
    for ax in [axes[0], axes[2]]:
        ax.set_ylabel("Fraction of stores")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", frameon=False, fontsize=9)

    fig.suptitle("Figure 1 — Distribution of Starting Wage Rates", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
