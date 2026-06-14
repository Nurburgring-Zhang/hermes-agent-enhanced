# 2026-06-02 强制上下文token优化记录

## 优化目标

PRE 21个插件每天轮流注入6825 chars到system prompt, 其中大量固定信息重复。
目标: 减少到2000 chars以内, 保留核心约束。

## 优化前后对比

| 插件 | 优化前(chars) | 优化后(chars) | 节省 |
|------|--------------|--------------|------|
| forced_executor | ~500 | ~150 | 70% |
| capability_registry | 731 | 42 | 94% |
| agent_orchestrator | 421 | 35 | 92% |
| master_integration | 420 | 35 | 92% |
| layered_planner | 418 | 35 | 92% |
| monitor_engine | 417 | 35 | 92% |
| task_resumer | 415 | 35 | 92% |
| auto_recall | 414 | 35 | 92% |
| wake_guide | 413 | 35 | 92% |
| context_auto_assoc | 396 | 35 | 91% |
| surgical_slicer | 359 | 35 | 90% |
| auto_resume_check | 336 | 35 | 90% |
| 其他10个小插件 | ~1276 | ~500 | 61% |
| **总计** | **6767** | **2045** | **69%** |

## 实现方式

1. `_run_script_module_subprocess`: 从子进程输出中提取关键摘要行(150 chars)
2. `_run_forced_executor`: 从500+chars详细报告→一行摘要+核心约束

## 核心约束保留

压缩后system prompt中仍然包含:
- "X武器×Y阶段已系统执行" — LLM知道武器被调用了
- "基于结果汇报,禁止输出示例,禁止说我来执行" — 强制约束
- 武器库数量 — LLM知道有什么可用
- 安全检查结果 — LLM知道安全已过
- 段状态 — LLM知道当前对话进度
