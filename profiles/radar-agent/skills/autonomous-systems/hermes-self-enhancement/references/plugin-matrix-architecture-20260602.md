# 插件矩阵架构 (2026-06-02实战)

## 核心文件

| 文件 | 作用 |
|------|------|
| `scripts/agent_enhancement_manager.py` | 插件管理器 — 67插件注册表+pre/post钩子 |
| `scripts/task_enhancement_engine.py` | 8大能力域综合引擎 |
| `scripts/forced_executor.py` | 武器强制调用(≥6武器×≥3阶段) |
| `scripts/restore_run_agent.py` | run_agent.py恢复脚本 |
| `scripts/task_queue_manager.py` | SQLite任务队列(并发5/重试3) |
| `hermes-agent/run_agent.py` | 7处注入: PRE/L12266/POST |

## `_PLUGIN_CALLERS` 注册表模式

每个插件对应一个确切的调用函数，不是通用猜测:

```python
_PLUGIN_CALLERS = {
    "forced_executor": lambda mod, ctx: _run_forced_executor(mod, task, ctx, agent_self),
    "engine_core": lambda mod, ctx: _run_engine_core(mod, ctx),
    "segment_manager": lambda mod, ctx: _run_segment_manager(mod, ctx),
    "model_router": lambda mod, ctx: _run_model_router(mod, task, ctx),
    # 其他用子进程调用
    "surgical_slicer": lambda mod, ctx: _run_script_module_subprocess(mod, ctx),
}
```

## 子进程调用输出压缩

```python
def _run_script_module_subprocess(mod, contexts):
    # 只取第一行含✅/❌/⚠️的摘要行
    for l in lines:
        if any(kw in l for kw in ['✅', '❌', '⚠️', '→']):
            summary = l[:150]
            break
    contexts.append(f"[{mod_name}] {summary}")
```

## PRE插件注入system prompt

22个PRE插件 → 合并 → `_force_context` → run_agent.py L12266注入

```python
# run_agent.py L12263-L12269
_plugin_ctx = locals().get('_plugin_force_context')
if _plugin_ctx:
    effective_system = (effective_system + "\n\n" + _plugin_ctx).strip()
```

## 67插件注册表(2026-06-02)

PRE 22个:
forced_executor, engine_core, segment_manager, layered_planner,
surgical_slicer, context_auto_assoc, context_failsafe, cross_session_cache,
session_init_check, wake_guide, agent_company, agent_orchestrator,
multi_agent_orch, capability_registry, master_integration, model_router,
auto_recall, task_resumer, auto_resume_check, camel_guard, monitor_engine,
task_enhancement

POST 46个:
gear_enforcer, task_boundary, consistency_guard, dod_checklist, tr_gate,
system_selfcheck, system_audit, lossless_claw,
hy_memory_orchestrator, l1_extractor, l2_scene, l3_persona,
episodic_injector, memory_evolution, memory_highway, parallel_memory,
tool_unloader, mermaid_builder, emergency_compressor,
reflexion_engine, experience_extractor, gepa_variator, auto_cleaner,
skill_evolver, self_evolution, self_enhance_v3, auto_tune,
hermes_retrospect, skillopt_trainer,
hermes_super_guardian, reflector_engine,
status_reporter, feedback_push, generate_report,
auto_healer, production_reliability, gear_vault,
gear_task_validator, gear_master, long_task_guardian,
task_enhancement
