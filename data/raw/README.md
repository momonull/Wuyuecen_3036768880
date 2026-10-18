# data/raw/ — 原始输入数据

本目录存放复现所需的**原始门店级调查数据** `public.csv`（410 行 × 46 列，Card & Krueger (1994) 最低工资 DID 调查数据）。

## 获取方式（课程受限数据，不入库）

1. 从课程提供的 `01_DID.zip` 解压得到 `public.csv`。
2. 将 `public.csv` 放入本目录：

```
data/raw/public.csv
```

> 文件名与位置**不能改**，否则 `python run_all.py` 会因找不到原始数据而中止。

## 为什么没有直接上传

`public.csv` 为课程内受限数据，已由 `.gitignore` 排除（`public.csv`、`*.zip`、`01_DID/`），不随仓库上传。列定义见仓库根目录 `DATA_DICTIONARY.md`，处理口径见 `data/processed/variable_construction.md`。
