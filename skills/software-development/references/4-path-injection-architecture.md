# 4路径底层强制注入架构 — 2026-06-12实战

## 问题

对Hermes系统的每次增强（双AI互审、模型路由、规则引擎、前置三查等）都需要
注入代码才能生效。但单一路径的注入存在致命缺陷：

1. **只注入conversation_loop** → 只在对话时生效，cron/子Agent/批处理不生效
2. **只注入run_agent** → 只在对话完成后生效，工具调用时不受控制
3. **只依赖插件pre_tool_call hook** → 只在主Agent生效，子Agent无此hook
4. **每次升级git reset后所有注入丢失**

所以需要建立4条互为冗余的注入路径，确保在任何Hermes进程类型中都能自动生效。

## 4条路径

| 路径 | 注入文件 | 触发时机 | 覆盖范围 |
|------|---------|---------|---------|
| **P1: 进程启动** | `model_tools.py` | 模块import时 | **所有进程**（对话/cron/子Agent/批处理/网关） |
| **P2: 对话前PRE** | `conversation_loop.py` | 每次LLM调用前 | 对话会话 |
| **P3: 对话后POST** | `run_agent.py` | 每次对话完成后 | 对话会话 |
| **P4: CLI启动** | `hermes_cli/__init__.py` | 任何hermes命令 | CLI交互 |

### P1: 进程启动层（model_tools.py）**——最重要的路径**

`model_tools.py` 是所有Hermes进程都会import的文件（工具注册中心）。
在这里注入 `_force_init_all_enhancements()` 函数，在模块导入时自动执行：

```python
_INIT_DONE = False
def _force_init_all_enhancements() -> None:
    global _INIT_DONE
    if _INIT_DONE:
        return
    _INIT_DONE = True
    # 用 importlib.util 加载各个增强模块
    _re_path = os.path.join(_scripts_dir, "rule_enforcer.py")
    # ...加载代码...

_force_init_all_enhancements()  # 模块import时触发
```

**优势：**
- 不依赖任何外部调用（插件hook、executor、CLI）
- 在所有Hermes进程中自动生效
- 在conversation_loop的PRE hook之前执行
- cron、子Agent、后台批处理、gateway都受影响

### P2: 对话前PRE层（conversation_loop.py）

从system prompt构建处入手，注入增强上下文：

```python
effective_system = active_system_prompt or ""
# ── PRE hook ──
try:
    import sys as _sys
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_pre_conversation
    _enhancement_text = safe_hook_pre_conversation(agent, user_message)
    if _enhancement_text:
        effective_system = (effective_system + "\n\n" + _enhancement_text).strip()
except Exception:
    pass
```

**风险：** 每次升级可能重构conversation_loop，注入点会丢失。

### P3: 对话后POST层（run_agent.py）

在 run_conversation() 方法中注入POST hook：

```python
result = run_conversation(self, ...)
# ── POST hook ──
try:
    from agent_enhancement_manager import safe_hook_post_conversation
    safe_hook_post_conversation(self, final_response, user_message)
except Exception:
    pass
return result
```

### P4: CLI启动层（hermes_cli/__init__.py）

在模块顶层注入启动脚本调用：

```python
# [双审] 启动时加载双AI互审规则
import subprocess as _subprocess, os as _os
_startup_script = _os.path.expanduser("~/.hermes/scripts/startup_dual_review.sh")
if _os.path.exists(_startup_script):
    _subprocess.run(["bash", _startup_script], capture_output=True)
```

## 升级恢复清单

每次 `git reset --hard origin/main`（从v0.15.x→v0.16.x的浅克隆升级方式）后，
需要在升级后的代码中重新注入4条路径：

```bash
# 验证所有4条路径
echo "P1: $(grep -c '_force_init_all_enhancements' model_tools.py)"
echo "P2: $(grep -c 'safe_hook_pre_conversation' agent/conversation_loop.py)"
echo "P3: $(grep -c 'safe_hook_post_conversation' run_agent.py)"
echo "P4: $(grep -c 'startup_dual_review' hermes_cli/__init__.py)"
# 每个都应输出 >0
```

注入点的精确行号可能变化（因为升级后代码重构），但上下文附近的关键锚点不变：
- P2: `effective_system = active_system_prompt or ""` 前后
- P3: `def run_conversation(` 方法体中的 `return run_conversation(...)`
- P1: 文件末尾 `check_tool_availability()` 之后

## 验证命令

```bash
# 验证4条路径语法
for f in model_tools.py agent/conversation_loop.py run_agent.py hermes_cli/__init__.py; do
    python3 -c "import py_compile; py_compile.compile('/home/administrator/.hermes/hermes-agent/$f', doraise=True); echo 'PASS: $f'"
done

# 验证增强子系统
python3 -c "
import sys; sys.path.insert(0, '/home/administrator/.hermes/scripts')
from rule_enforcer import get_status
s = get_status()
print(f'规则引擎: 启用={s[\"enabled\"]} | 规则={s[\"rules\"]} | 统计={s[\"enforcement_count\"]}')
"

# 验证对话
hermes chat -q "ping" --quiet -t terminal
# 期望: 正常响应
```
