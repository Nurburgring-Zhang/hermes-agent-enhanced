# 2026-06-12 进程启动层注入 — 第4条强制路径

## 发现背景

在 Hermes v0.15.1→v0.16.0 升级过程中发现：所有之前的增强能力注入路径都依赖某种"触发时机"：

| 路径 | 依赖 | 覆盖范围 |
|------|------|---------|
| pre_tool_call hook | 主Agent对话循环 | ❌ cron/子Agent/批处理不覆盖 |
| POST hook(run_agent) | 对话完成 | ❌ 后台进程不覆盖 |
| CLI启动脚本 | 用户输入命令 | ❌ gateway/daemon不覆盖 |
| cron任务 | crontab存在 | ✅ 但不是所有进程 |

## 解决方案：model_tools.py 进程级强制加载

**`model_tools.py`** 是所有Hermes进程的第一个核心模块被import（工具注册中心）。这意味着：
- 对话进程（`hermes chat`）— 导入 ✅
- cron任务处理器（`hermes cron run`）— 导入 ✅
- 子Agent进程（delegate_task）— 导入 ✅
- 批处理脚本（batch_runner.py）— 导入 ✅
- gateway进程（`hermes gateway run`）— 导入 ✅
- 子进程（`hermes chat -z`）— 导入 ✅

### 注入方式

在 `model_tools.py` 末尾添加（核心文件：`~/.hermes/hermes-agent/model_tools.py`）：

```python
_INIT_DONE = False
def _force_init_all_enhancements() -> None:
    global _INIT_DONE
    if _INIT_DONE:
        return
    _INIT_DONE = True
    
    _scripts_dir = os.path.join(os.path.expanduser("~/.hermes"), "scripts")
    _agent_dir = os.path.join(os.path.expanduser("~/.hermes"), "agent")
    
    # 1. Force-load dual_review_engine
    # 2. Force-load agent_enhancement_manager
    # 3. Run startup_dual_review.sh
    # 4. Verify model_router importable

_force_init_all_enhancements()
```

### 与其他路径的关系

第4条路径不是替代其他路径，而是**兜底**：
- 第1条路径（pre_tool_call hook）— 负责对话时的实时监督
- 第4条路径（model_tools.py）— 负责进程启动时的强制加载
- 第5条路径（cron齿轮系统）— 负责后台周期性自检

三者是正交互补关系，不是替代关系。

## 验证方法

```bash
# 1. 检查代码存在
grep '_force_init_all_enhancements' ~/.hermes/hermes-agent/model_tools.py

# 2. 验证语法
python3 -c "import py_compile; py_compile.compile('/home/administrator/.hermes/hermes-agent/model_tools.py', doraise=True); print('OK')"

# 3. 验证真实import
python3 -c "import sys; sys.path.insert(0, '/home/administrator/.hermes/hermes-agent'); import model_tools; print(f'OK: {model_tools.__name__}')"

# 4. 验证增强管理器在import后预加载
python3 -c "
import sys; sys.path.insert(0, '/home/administrator/.hermes/hermes-agent')
import model_tools
import importlib.util
spec = importlib.util.spec_from_file_location('em', '/home/administrator/.hermes/scripts/agent_enhancement_manager.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
s = mod.get_plugin_status()
print(f'增强管理器: {s[\"loaded\"]}/{s[\"total\"]} 插件')
"
# 注意：插件是惰性加载的，loaded=0/66 是正常的
# 关键验证是 import 不报错 + 所有hook函数可调用
```

## 升级注意事项

每次 Hermes 升级后必须重新注入 `model_tools.py`：
1. `git reset --hard origin/main` 会清除注入
2. 需要用备份的patch文件重新注入
3. 升级后先用上述验证方法确认注入生效
