# context_packer — 对话层上下文打包器

## 位置
`~/.hermes/scripts/context_packer.py`

## 原理
每次对话前调用，根据任务类型打包最小必要上下文。
**本地执行的不传给AI模型**：齿轮cron、ability_activator、task_monitor、pipeline调度、采集清洗等全部本地直接跑。
**只传给AI模型的**：核心身份 + 8条规则摘要 + 当前任务规则 + 工具列表 + 中断任务信息。

## 用法
```bash
# 通用任务（默认）
python3 ~/.hermes/scripts/context_packer.py general

# 修复任务（加载DeepSeek/PushPlus等修复规则）
python3 ~/.hermes/scripts/context_packer.py fix

# 推送任务（加载推送规则）
python3 ~/.hermes/scripts/context_packer.py push

# 开发任务
python3 ~/.hermes/scripts/context_packer.py develop

# 审核任务
python3 ~/.hermes/scripts/context_packer.py review

# 研究任务
python3 ~/.hermes/scripts/context_packer.py research
```

## 输出
写入 `reports/context_pack.json`，包含：
- `content`: 压缩后的上下文文本（~3000 tokens）
- `packed_tokens`: 压缩后token数
- `compression_ratio`: 压缩率

## cron配置（已部署）
```cron
* * * * * cd ~/.hermes && python3 scripts/context_packer.py general
```
每1分钟刷新，0.018秒/次，对性能零影响。

## 测试结果（2026-05-27）
- 6种任务类型全部通过：fix/push/develop/review/research/general
- 全链路压力测试17项全部通过
- 平均压缩率86.1%（21,312 → 2,999 tokens）
- 单次执行0.018秒
- 不修改crontab、不碰数据库、不干扰齿轮系统

## 关键代码
```python
# context_packer.py 核心逻辑
TASK_RULES = {
    "fix": """
## 修复任务规则
- 先排查根因（查日志/数据库/cron状态）
- AI评分中断时检查DeepSeek key和model名
- 推送失败检查PushPlus字数限制+URL转义
- 修复完必须跑一次真实测试
- 测试后审核+完善+再测试
""",
    "push": """
## 推送任务规则
- TARGET_COUNT=25（避免PushPlus 2万字限制）
- URL中的&必须转义为&amp;
- 推送失败自动重试2次
- 等级分5级(3/5/6/7/8/9)
""",
    # ... 其他类型
}
```
