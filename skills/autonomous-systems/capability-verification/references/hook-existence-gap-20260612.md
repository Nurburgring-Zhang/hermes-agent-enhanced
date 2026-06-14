# 2026-06-12 Hook存在性缺口审计

## 症状
agent_enhancement_manager.py 的 PLUGIN_REGISTRY 中注册了 `battle_commander` 和 `forced_executor`，但这两个模块在2026-06-12之前 **没有暴露 `pre_conversation_hook` 和 `post_conversation_hook` 函数**。

enhancement manager的 safe_hook_pre_conversation() 通过 hasattr() 检查来调用每个插件的 hook：
```python
if hasattr(mod, 'pre_conversation_hook'):
    ctx = mod.pre_conversation_hook(task)
    contexts.append(ctx)
```
由于这两个模块没有 `pre_conversation_hook`，hasattr返回False，它们**被注册了但永远不会被触发**。

这是"注册了但不可达"——capability-verification的第4种死链模式。

## 受影响模块

| 模块 | 2026-06-12前状态 | 修复 | 行数 |
|------|------------------|------|------|
| battle_commander.py | pre=False post=False | 添加pre_conversation_hook + post_conversation_hook | +17行 |
| forced_executor.py | pre=False post=False(不需要post) | 添加pre_conversation_hook | +12行 |

## 修复模板

### battle_commander
```python
def pre_conversation_hook(task: str) -> str:
    """PRE钩子：对话前执行武器调度"""
    commander = BattleCommander()
    report = commander.command(task)
    return report["summary"]

def post_conversation_hook(task: str, response: str) -> None:
    """POST钩子：对话后记录战斗日志"""
    commander = BattleCommander()
    report = commander.command(task)
    import logging
    logging.getLogger(__name__).info(f"Battle report: {report['summary']}")
```

### forced_executor
```python
def pre_conversation_hook(task: str) -> str:
    """PRE钩子：对话前强制执行武器调用"""
    executor = LLMForcedExecutorV3()
    llm_resp = executor.query_llm(executor.build_weapon_query(task))
    if not llm_resp:
        plan = executor._fallback_plan(task)
    else:
        plan = executor.parse_llm_plan(llm_resp)
    return f"[LLMForcedExecutorV3] {plan.get('total_weapons_selected', 0)}武器×{plan.get('total_segments', 0)}阶段"
```

## 验证命令

```bash
cd ~/.hermes && python3 -c "
import sys; sys.path.insert(0, 'scripts')
import importlib.util

for name in ['battle_commander', 'forced_executor', 'task_enhancement_engine']:
    spec = importlib.util.spec_from_file_location(name, f'scripts/{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pre = hasattr(mod, 'pre_conversation_hook')
    post = hasattr(mod, 'post_conversation_hook')
    print(f'{name}: pre={pre} post={post}')
    if pre:
        try:
            r = mod.pre_conversation_hook('test task')
            print(f'  -> {type(r).__name__} ({len(str(r))} chars)')
        except Exception as e:
            print(f'  -> ERROR: {str(e)[:80]}')
"
```

## 经验教训
- **注册表有条目 ≠ hook函数存在** — 增强管理器通过hasattr动态检测hook，不报错也不警告。唯一的发现方式是主动运行hook存在性检查。
- **所有被注册到PLUGIN_REGISTRY的模块必须都暴露pre和post hook**（除非是pure pre-only或pure post-only模块，但这种情况很少）。
- **2026-06-12修复后**：所有3个模块都通过了hook存在性检查，并且pre_hook返回了有意义的内容（>50 chars）。
