# Dynamic Workflows ↔ 复盘反思桥接

`workflows/retrospect_integration.py` 将 Dynamic Workflows 系统与复盘反思引擎对接。

## 对接方式

### 自动触发

由 `workflows/runtime.py` 的 `finally` 块自动调用（**不可绕过**）：

```python
# runtime.py line 265-280
if wf.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
    build_result = WorkflowResult(...)
    retro_result = await retrospect_integration.run_retrospect(wf, build_result)
    feed_result = evolution_bridge.feed_retrospect(wf, build_result)
```

### 调用链

```
workflow执行完成
  → runtime.finally块
    → retrospect_integration.run_retrospect(wf, result)
      → delegate_task(goal="执行完整任务复盘反思（5步结构化流程）")
        → 子Agent执行5步复盘（目标回顾→过程回溯→质量评估→经验提取→知识固化）
    → evolution_bridge.feed_retrospect(wf, result)
      → 写入retro_candidates表（state.db）
      → 质量评分<60? 触发即时进化
    → gear_integration.write_to_wake_guide()
    → gear_integration.notify_production_loop()
```

## RetrospectIntegration 类

```python
class RetrospectIntegration:
    def configure(self, delegate_task_fn): ...  # 注入delegate_task
    
    async def run_retrospect(self, wf, result) -> Dict:
        """执行5步复盘，返回复盘结果"""
    
    async def extract_to_memory(self, wf, result, retrospect) -> Dict:
        """将关键发现提取到Hy-Memory系统"""
```

### 输入格式

复盘喂给delegate_task的context JSON：
```json
{
  "workflow_name": "deep-research",
  "workflow_description": "研究与AI Agent 2026",
  "total_phases": 3,
  "completed_tasks": 7,
  "failed_tasks": 0,
  "duration_seconds": 312.5,
  "status": "completed",
  "has_adversarial": true,
  "phase_results": [
    {"name": "搜索", "mode": "fan_out_in", "tasks": 3},
    {"name": "验证", "mode": "parallel", "tasks": 2},
    {"name": "报告", "mode": "sequential", "tasks": 1}
  ]
}
```

## EvolutionBridge 的 feed_retrospect() 质量评分公式

```python
quality_score = 100.0
if result.failed_tasks > 0:
    score -= min(result.failed_tasks * 10, 40)
if result.total_phases > 0:
    completion_rate = result.completed_phases / result.total_phases
    score -= (1.0 - completion_rate) * 30
if result.error:
    score -= 20
if result.duration_seconds > 300:
    score += 5  # 长任务加分
return max(0, min(100, score))
```

## 与 hermes_retrospect.py 的关系

**两者互补而非重复**：

| 维度 | hermes_retrospect.py | retrospect_integration.py |
|------|---------------------|--------------------------|
| 触发方式 | cron G4(每15分钟) | workflow完成时强制触发 |
| 数据源 | state.db messages表 | WorkflowResult结构化数据 |
| 输出 | 复盘报告+进化候选 | retro_candidates表+Hy-Memory |
| 适用场景 | 所有会话/任务 | 仅Dynamic Workflows |

## 数据流

```
hermes_retrospect.py  → retro_candidates.jsonl  → self_evolve_cluster 模块6
retrospect_integration.py → retro_candidates表 (state.db) → self_evolve_cluster consume_retro_candidates()
                                                          → 每天03:00自动消费
                                                          → cron */30: 候选>=3触发即时
```
