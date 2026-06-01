# FitnessRecord — 训记训练数据存档

每次读取的训练计划和写回的训练记录都会保存在 `training_data/` 目录下。

## 目录结构
```
FitnessRecord/
├── training_data/     # 训记 API 返回的 JSON 数据
│   ├── read_YYYY-MM-DD.json    # 读取的训练计划
│   └── write_YYYY-MM-DD.json   # 写回的变更记录（含请求+响应）
├── scripts/            # 读写脚本
│   ├── read_train.py
│   └── write_train.py
├── .gitignore
└── README.md
```

## 使用方式
```bash
# 读取今日训练
python scripts/read_train.py 2026-06-01

# 写回训练数据
python scripts/write_train.py 2026-06-02
```
