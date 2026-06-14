# surgical_context_slicer — 手术刀式上下文切分

## 位置
`~/.hermes/scripts/surgical_context_slicer.py`

## 原理
从SOUL.md的压缩版(context_pack.json)中，根据当前任务类型精准提取相关规则和工具。
不相关的章节完全切掉，不保留。

## 如何判断任务类型
```python
def classify_task(task_id, detail, next_action):
    text = f"{task_id} {detail} {next_action}".lower()
    if any(kw in text for kw in ['push', '推送']): return "push"
    if any(kw in text for kw in ['fix', '修复', 'bug']): return "fix"
    if any(kw in text for kw in ['develop', '开发']): return "develop"
    if any(kw in text for kw in ['review', '审核']): return "review"
    if any(kw in text for kw in ['research', '研究']): return "research"
    return "general"
```

## 输出
写入 `reports/surgical_context.json`。

## 各任务类型分配

| 类型 | 必须规则 | 工具数 | 典型Token |
|------|---------|:-----:|:--------:|
| fix | 规则1-7全部 | 7个 | 1,105 |
| push | 规则1,5,7 | 5个 | 758 |
| develop | 规则1,2,5,6,7 | 6个 | 843 |
| review | 规则1,3,4,5,7 | 4个 | 758 |
| research | 规则1,5,8 | 4个 | 667 |
| general | 规则1-7全部 | 9个 | 947 |
| collect | 规则5,8 | 3个 | 587 |
| score | 规则5 | 2个 | 654 |

## 测试结果
- 8种任务类型全部通过：规则完整、工具完整、任务进度完整
- 平均token: 790 tokens（vs 原始21,312）
- 平均压缩率: 96.3%
