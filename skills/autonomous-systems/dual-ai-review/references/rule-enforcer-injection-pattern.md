# 规则强制执行引擎注入模式 — 2026-06-12 实战

## 背景

rule_enforcer.py (27KB, 13条规则) 在代码层面定义完整，但**运行时从未被调用**。
agent_enhancement_manager.py注册了它但 safe_hook_pre() 中没有调用 _try_load()。
conversation_loop.py 和 run_agent.py 导入了它的函数但函数名不存在。

## 注入失败模式汇总

### 失败模式1: 写进代码但无import路径

**症状**: 代码存在、注册表存在、逻辑完整 — 但运行路径从未经过它。

**根因**: 把"代码存在"等同于"代码生效"。实际上如果没有任何其他模块import/调用它，
它就是一个死文件。cron不会自动扫描新文件加入执行计划。

**修复**: 在多条入口路径中注入调用：
- model_tools.py (进程启动层 — 任何Hermes进程都import)
- agent_enhancement_manager.py (对话前/后钩子 — 每个对话都会触发)
- tool_executor.py (每次工具调用 — 最细粒度拦截)
- conversation_loop.py (每次LLM调用 — system prompt注入)

**经验**: 一个文件如果只有定义没有import，它就是死的。
至少要有一条触发路径。

### 失败模式2: import路径错误

**症状**: `from agent.rule_enforcer import rule_enforcer` 导致
`No module named 'agent.rule_enforcer'` — 文件在 scripts/ 不在 agent/。

**修复**: 用动态importlib加载，指定绝对路径：

```python
from pathlib import Path
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "rule_enforcer",
    str(Path.home() / ".hermes" / "scripts" / "rule_enforcer.py")
)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    rule_enforcer = _mod
else:
    rule_enforcer = None  # 降级: 规则不生效但不炸
```

**经验**: scripts/ 下的文件不要假设 `from agent.xxx import xxx` 能工作。
用完整路径+importlib是安全方式。

### 失败模式3: 返回值类型不匹配

**症状**: `pre_tool_intercept()` 返回 `{"action": "pass"}` (dict)，
但调用端写的是 `if _pre_result != "pass"` (比较dict != str) → 永远为真。

**修复**: 统一使用 `.get("action", "pass")` 模式:

```python
_pre_action = _pre_result.get("action", "pass") if isinstance(_pre_result, dict) else "pass"
if _pre_action in ("warn", "block"):
    # 拦截
```

**经验**: 所有拦截器返回值应该是统一格式的dict: `{"action": "pass"|"warn"|"block", "reason": "..."}`。
调用端永远用 `.get("action")` 而不是直接比较返回值。

### 失败模式4: 被调用的函数名不存在

**症状**: conversation_loop.py 执行 `from rule_enforcer import pre_conversation_hook`
但 rule_enforcer.py 中没有定义这个函数（只有post版本）。

**修复**: 在 rule_enforcer.py 中添加缺失的函数：

```python
def pre_conversation_hook(task: str) -> str:
    """在对话开始前执行R2前置三查，返回检查摘要注入system prompt"""
    try:
        pc = PreCheck.execute(task)
        return f"[Rules] {pc['summary']}"
    except Exception:
        return ""
```

**经验**: 注入点导入的函数名必须与源文件定义的一致。
第一次注入时验证两端对齐。

### 失败模式5: 插件注册但无 _try_load 调用

**症状**: agent_enhancement_manager.py 的 PLUGIN_REGISTRY 中有
`("rule_enforcer", ...)` 但 safe_hook_pre_conversation() 中
没有对应的 `_try_load("rule_enforcer", ...)` 调用。

**修复**: 在 safe_hook_pre 和 safe_hook_post 中添加 _try_load 调用，
放在 task_enhancement 后面：

```python
# 阶段8: 综合任务执行增强(8大能力域)
_try_load("task_enhancement", lambda mod: _run_task_enhancement(mod, task, contexts), contexts)
# SOUL.md规则强制
_try_load("rule_enforcer", lambda mod: _run_script_module_subprocess(mod, contexts), contexts)
```

**经验**: 在注册表里加条目不等于它会自动执行。
safe_hook_pre 中的 _try_load 调用列表才是真正的执行计划。

## 正确的注入模式

### 4层注入（已验证工作）

| 层 | 文件 | 位置 | 触发时机 | 覆写范围 |
|------|------|------|---------|---------|
| 进程启动 | model_tools.py | 文件末尾 `_force_init_all_enhancements()` | 模块import时 | 所有Hermes进程 |
| 工具调用 | tool_executor.py | concurrent/sequential路径 pre/post | 每次工具调用 | 主Agent工具 |
| 对话前 | conversation_loop.py | effective_system构建后 | 每次LLM调用 | 主Agent对话 |
| 对话后 | run_agent.py | run_conversation返回后 | 每次对话完成 | 主Agent对话 |

### 确保规则文件真的活着的自检方法

```bash
# 1. 检查是否有import路径
grep -rn "from rule_enforcer import\|import rule_enforcer" ~/.hermes/scripts/ ~/.hermes/hermes-agent/ | grep -v __pycache__

# 2. 检查导入是否实际工作
python3 -c "
import sys; sys.path.insert(0, '/home/administrator/.hermes/scripts')
from rule_enforcer import get_status
s = get_status()
print(f'规则引擎: {s[\"enabled\"]}')
print(f'规则: {s[\"rules\"]}')
"

# 3. 检查注入点的函数名是否匹配
grep "pre_conversation_hook" ~/.hermes/scripts/rule_enforcer.py
grep "pre_conversation_hook" ~/.hermes/hermes-agent/agent/conversation_loop.py
```

### 一次注入的checklist

- [ ] 规则文件存在且语法正确
- [ ] 至少有一条import路径到它（不能是死文件）
- [ ] 调用端导入了正确的函数名（两边对齐）
- [ ] 返回值类型正确（dict actions vs string comparison）
- [ ] import路径是动态的（scripts/下的文件不要用相对import）
- [ ] 降级处理：如果加载失败，系统不炸
- [ ] 注册表 + _try_load 调用双确认（plugin system）
