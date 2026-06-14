---
name: long-task-executor
description: 长程任务分段执行引擎。自动将长任务分段，每段做checkpoint，支持中断恢复和上下文漂移检测。
---

# Long Task Executor

## 何时使用
任务预计超过10步或跨越多个会话时。

## 执行模式

### 分段策略
1. 将总任务拆分为3-5段（每段3-8步）
2. 每段有独立的goal + checkpoint + 恢复指令
3. 段与段之间用handoff文档传递上下文

### 每段执行流程
1. 读段目标
2. 读上下文摘要（从上一段传递）
3. 执行步骤
4. 每3步做checkpoint:
   - 当前是否偏离段目标？
   - 上下文是否完整？
   - 是否需要调整策略？
5. 输出段结果 + 上下文摘要
6. 如果中断，用上下文摘要恢复

### 上下文漂移检测
每段开始时比较：
- 当前任务目标 vs 原始目标
- 如果偏差超过阈值，触发re-align

## 输出格式
每段完成后输出：
```
[SEGMENT N/M COMPLETE]
Goal: xxx
Steps completed: N
Key results: ...
Context summary: ...
Next segment: ...
```
