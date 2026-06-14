# 产出文件索引

## 全部产出汇总

| 批次 | 文件名 | 路径 | 条数 |
|------|--------|------|------|
| v14原始版 | `v14_batch_1780071590.txt` | v14_batch/ | 50,000 |
| v15审美版 | `v15_batch_002-010.txt` | v15_batch/ | 55,488 |
| 百万批v1 | `million_batch_001-003_178008916x.txt` | million_batch/ | 146,183 |
| 百万批v2 | `million_batch_001-006_178009023x.txt` | million_batch/ | 278,646 |
| 百万续产 | `million_batch_035-044_178012018x.txt` | million_batch/ | 93,149 |
| **总计** | | | **~517,978条** |

## 文件格式说明

- 每条为to_chi原始完整段落，200-1500字
- 含完整场景/人物/服装/光线描述
- 无碎片、无逻辑错误、无性别断裂
- 审美版额外过滤了艺术/时尚/潮流关键词

## 目录结构

```
/mnt/d/Hermes/1000000提示词/大生产/
├── v14_batch/       ← 基础过滤版（50,000条）
├── v15_batch/       ← 审美过滤版（55,488条）
├── million_batch/   ← 百万批量版（517,978条）
└── 代码/            ← 各版本生产脚本
    ├── batch_produce_v10.py
    ├── batch_produce_v14.py
    ├── batch_produce_v15.py
    ├── batch_produce_million.py
    ├── batch_produce_million_v2.py
    └── batch_produce_final.py
```

## 原始语料

- 来源：`/mnt/d/ComfyUI/提示词/to_chi/`（261个文件，520,008条）
- 基础过滤后可用：~239,986条（去除了比喻词/多人词/非人物/过短过长）
- 审美过滤后可用：~203,144条（含200+审美关键词）
