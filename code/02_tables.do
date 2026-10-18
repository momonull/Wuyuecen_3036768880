* ============================================================================
* 02_tables.do — Stata 交叉验证核心 DID（Card & Krueger 1994）
*
* 用途：独立复现 Python（02_tables.py）的核心 DID 结果，作交叉验证。
* 数据：从 data/raw/public.csv 读入，并在本脚本内完成与 Python 01_clean.py
*       一致的清洗 / 变量构建，保证两套软件输入口径完全相同。
*
* 运行：在项目根目录执行  do code/02_tables.do
* 预期（与 Python 一致，见 outputs/tables/replication_check.md）：
*   (1) 核心 DID 系数 ≈ +2.75  (t ≈ 2.05)   —— 平衡样本 emp_chg 对 STATE 回归
*   (2) 扩展 DDD 系数  ≈ -1.10  (t ≈ -0.45) —— emp_chg 对 STATE CO_OWNED STATE*CO_OWNED
*
* 变量名：raw 表头为大写（SHEET/CHAIN/.../EMPFT...）；Stata 变量名大小写不敏感，
*         此处用 case(lower) 统一转为小写，与 Python 端派生变量（fte/fte2/emp_chg）一致。
* 注：本脚本为可选交叉验证参考，未纳入 run_all.py 自动流程。
*     已在 Stata 17 上运行并与 Python 逐位一致（结果见 outputs/tables/stata_check.log）：
*       核心 DID 系数 2.75（= Python +2.754）；DDD 的 sxo = -1.095292（6 位小数一致）。
*     仅 SE 口径不同（Stata 同方差 vs Python Welch/HC1），点估计完全一致。
*     若重跑后结果与 Python 不一致，以 data/processed 的 Python 复现为准并报告差异。
* ============================================================================

clear all
set more off

* --- 打开日志（文本格式，输出到 outputs/tables/stata_check.log） ---
capture log close
log using "D:\小蓝的文件\HKU\Econ6067\personal project\output\tables\stata_check.log", replace text

* --- 读入原始数据（受限文件，不入库；case(lower) 统一小写变量名） ---
import delimited "D:\小蓝的文件\HKU\Econ6067\personal project\data\raw\public.csv", clear case(lower)

* ============================================================================
* 清洗与变量构建（与 Python 01_clean.py 口径一致，见 variable_construction.md）
* ============================================================================

* --- 关店处理 ---
* 永久关闭 STATUS2==3（6 家）：Wave2 就业 = 0（原始数据已填 0，此处显式重写以防万一）
* 临时关闭 STATUS2∈{2,4,5}（4 家）：Wave2 就业 = 缺失（原始数据已为缺失，显式置空）
replace empft2 = 0 if status2 == 3
replace emppt2  = 0 if status2 == 3
replace nmgrs2 = 0 if status2 == 3
foreach v of varlist empft2 emppt2 nmgrs2 {
    replace `v' = . if inlist(status2, 2, 4, 5)
}

* --- FTE 就业 = 全职 + 经理 + 0.5*兼职 ---
gen fte     = empft  + nmgrs  + 0.5*emppt
gen fte2    = empft2 + nmgrs2 + 0.5*emppt2
gen emp_chg = fte2 - fte

* --- 平衡样本标记 = 两期就业均非缺失 ---
gen bal_emp = !missing(fte) & !missing(fte2)

* ============================================================================
* (1) 核心 DID：就业变化对 NJ dummy 回归
* ============================================================================
di _n "=== 核心 DID（平衡样本，emp_chg 对 STATE）==="
reg emp_chg state if bal_emp == 1
* 等价两样本均值差（若已装 diff 命令，取消注释）：
*   diff emp_chg if bal_emp == 1, t(state)

* ============================================================================
* (2) 扩展 DDD：所有权异质性
* ============================================================================
di _n "=== 扩展 DDD（emp_chg 对 STATE CO_OWNED STATE*CO_OWNED）==="
gen sxo = state * co_owned
reg emp_chg state co_owned sxo if bal_emp == 1

* --- 关闭日志 ---
log close

exit
