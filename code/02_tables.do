* ============================================================================
* 02_tables.do — Stata 交叉验证核心 DID（Card & Krueger 1994）
*
* 用途：独立复现 Python（02_tables.py）的核心 DID 结果，作交叉验证。
* 注意：本文件从 data/raw/public.csv 直接读入并自行构造变量，
*       不依赖 Python 生成的 ck94_clean.csv，保证「独立」验证。
*
* 运行：在项目根目录执行  do code/02_tables.do
* 预期（与 Python 一致，见 output/tables/replication_check.md）：
*   (1) 核心 DID 系数 ≈ +2.75  (t ≈ 2.05)   —— 平衡样本 chg 对 STATE 回归
*   (2) 扩展 DDD 系数  ≈ -1.10  (t ≈ -0.45) —— chg 对 STATE CO_OWNED STATE*CO_OWNED
*
* 注：本仓库开发环境无 Stata，本脚本为交叉验证用草稿，未在本机执行；
*     若运行结果与 Python 不一致，以 data/processed 的 Python 复现为准并报告差异。
* ============================================================================

version 16
clear all
set more off

* --- 读入原始数据（受限文件，位于 data/raw/public.csv，不入库） ---
import delimited "data/raw/public.csv", clear

* --- 构造变量（口径见 PROJECT_PLAN §9 / variable_construction.md） ---
* FTE 就业 = 全职 + 经理 + 0.5 * 兼职
gen  fte  = EMPFT  + NMGRS  + 0.5*EMPPT
gen  fte2 = EMPFT2 + NMGRS2 + 0.5*EMPPT2
gen  chg  = fte2 - fte

* 永久关闭店（STATUS2==3）Wave2 就业=0：原始数据已填 0，无需改；
* 临时关闭店（STATUS2∈{2,4,5}）Wave2 就业=缺失：原始数据为缺失，无需改。
* 故「平衡样本」= fte 与 fte2 均非缺失。

* --- (1) 核心 DID：就业变化对 NJ dummy 回归 ---
di _n "=== 核心 DID（平衡样本，chg 对 STATE）==="
reg chg STATE if fte != . & fte2 != .
* 等价两样本均值差（若已装 diff 命令，取消注释）：
*   diff chg if fte != . & fte2 != ., t(STATE)

* --- (2) 扩展 DDD：所有权异质性 ---
di _n "=== 扩展 DDD（chg 对 STATE CO_OWNED STATE*CO_OWNED）==="
gen owned = CO_OWNED
gen sxo   = STATE * CO_OWNED
reg chg STATE owned sxo if fte != . & fte2 != .

exit
