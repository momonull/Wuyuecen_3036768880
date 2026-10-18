# data/processed/ — 处理后的数据

本目录存放由 `code/01_clean.py` 从 `data/raw/public.csv` 生成的清洗后数据：

| 文件 | 说明 |
| --- | --- |
| `ck94_clean.csv` | 清洗 + 构造全部派生变量后的门店级数据（回归直接输入） |
| `variable_construction.md` | 变量构建日志（FTE、全职占比、GAP、关店处理等口径的完整说明） |

## 为什么 `ck94_clean.csv` 不入库

`ck94_clean.csv` 由受限原始数据派生，仍含门店级微观信息，已由 `.gitignore` 排除（`data/processed/*.csv`）。运行 `python run_all.py` 会自动重新生成该文件，无需手动提交。

> 变量口径与「为何这样定义」详见 `variable_construction.md`；与原文目标值的逐项对照见 `outputs/replication_targets.md`。
