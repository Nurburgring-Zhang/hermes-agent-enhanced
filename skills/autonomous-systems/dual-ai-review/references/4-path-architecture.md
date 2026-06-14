# 四路径底层强制架构（2026-06-12 升级发现）

## 四条注入路径一览

| 路径 | 文件位置 | 触发时机 | 覆盖范围 |
|------|---------|---------|---------|
| **第1条** 🏡 | plugins/dual_review/ (pre_tool_call hook) | 主Agent对话循环 | 对话会话 |
| **第2条** ⚠️ | workflows/executor.py (inject到execute_task) | runtime.run()被调用 | executor链(需要外部触发) |
| **第3条** ✅ | workflows/mandatory_executor.py → hermes chat -z 子进程 | daemon(5min)+cron(5min)+gear(1min) | 所有子Agent任务 |
| **第4条** 🆕 | model_tools.py (模块import时自动执行) | **每个Hermes进程启动时** | **所有进程(对话/cron/子Agent/批处理/gateway)** |

## 第4条路径的技术细节

### 为什么选 model_tools.py

1. 这是Hermes的工具注册中心，所有子模块都会import它
2. import顺序足够早（在conversation_loop之前）
3. 在任何Hermes进程中都存在（对话、cron、agent、gateway）
4. 不依赖任何外部事件或触发链

### 为什么不选其他文件

| 候选文件 | 问题 |
|---------|------|
| run_agent.py | cron任务不import run_agent.py |
| hermes_cli/__init__.py | gateway不经过CLI |
| agent/agent_init.py | cron进程不import agent路径 |

## 交互依赖

第4条路径和第1条路径不是替代关系：

```
第4条(进程启动) → 强制加载dual_review引擎 → 双审代码已注册
第1条(对话循环) → pre_tool_call触发 → dual_review引擎被调用
```

- 第4条做"注册性加载"（代码必须全局变量已有，等调用方来拿）
- 第1条做"运行时调用"（每次工具调用前问双审引擎）
- 两条路径一起保证：**进程启动时强制注册 + 对话循环中强制调用**

## 升级后恢复步骤

```bash
# 每次升级后都要做：
cd ~/.hermes/hermes-agent

# 1. 检查注入是否存在
grep -n '_force_init_all_enhancements' model_tools.py

# 2. 如果不存在，用备份恢复
cat /mnt/d/Hermes/备份/升级前备份_*/local_code_changes.patch | grep -A 80 'model_tools.py' > /tmp/model_tools_inject.patch
# 手动patch
python3 -c "
import sys
content = open('model_tools.py').read()
inject = open('/tmp/model_tools_inject.txt').read()
if '_force_init_all_enhancements' not in content:
    content += '\n' + inject
    open('model_tools.py', 'w').write(content)
"

# 3. 验证
python3 -c "import py_compile; py_compile.compile('model_tools.py', doraise=True); print('OK')"
```
