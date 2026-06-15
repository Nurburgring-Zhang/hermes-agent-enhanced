# Loop Engineering — 六层架构框架

> 基于 Addy Osmani (Google Cloud AI Director) 和 Boris Cherny (Claude Code lead) 提出的范式

## 核心理念

Loop Engineering 将 AI Agent 的使用从"一轮一轮对话"升级为"设计能自己运转的闭环系统"。

```
人的位置: 从执行者 → 调度者
提示词:   从主菜 → 零件
循环:     从手动 → 自动
```

## 六层架构

### L1: 调度层 (Scheduling)
- 定时触发 (cron)
- 事件触发 (webhook/file watch)
- 目标达成触发 (跑到达成条件才停)
- Hermes实现: loop_engine.py TriggerManager

### L2: 并行隔离层 (Isolation)
- git worktree: 每个Agent独立工作空间
- 文件锁: 防止并发写冲突
- 合并策略: 先隔离再合并
- Hermes实现: loop_engine.py ExecutionSandbox

### L3: 技能知识层 (Skills)
- 项目上下文: 启动方式、目录规则、命名规范
- 踩坑记录: 已知问题、失败模式
- 长期规则: 不随对话消失的固定约束
- Hermes实现: 384 SKILL.md + context注入

### L4: 外部工具层 (Tools)
- 接入外部系统: issue系统、数据库、CI、PR
- 不只"说"还要"做": 开分支→跑测试→开PR→关联工单
- Hermes实现: MCP协议 + 35+采集器 + API网关

### L5: 验证层 (Verification)
- 执行与验证分离: 不同模型/不同视角
- 自动重试+升级: 3次重试→通知人工
- Hermes实现: dual_review_engine + loop_verifier

### L6: 记忆层 (Memory)
- 跨会话状态: 做过什么、失败过什么
- 检查点: 从断点恢复而非重头开始
- "模型会忘，但仓库不会忘"
- Hermes实现: loop_checkpoint.py + Hy-Memory

## 关键教训

1. **loop能推进流程，不能替人担责任** — AI说"完成"≠真没问题
2. **成本控制** — loop反复试错token消耗大，不值得的任务不要loop
3. **刹车权** — 人必须保留判断、验收、停止的权力
