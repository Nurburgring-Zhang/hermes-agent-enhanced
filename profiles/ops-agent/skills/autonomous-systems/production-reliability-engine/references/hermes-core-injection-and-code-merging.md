# Hermes 核心注入与代码合并模式

2026-06-02 实战总结。两个独立的可重复模式。

---

## 模式1: Hermes Core 钩子注入

### 目标
在 Hermes 核心对话循环中注入增强能力，确保每轮对话自动执行，不在 LLM 控制范围内。

### 注入点

| 钩子 | 位置 | 时机 | 用途 |
|------|------|------|------|
| PRE | `agent/conversation_loop.py` L1000 附近 | system prompt 构建后、LLM 调用前 | 注入增强上下文到 system prompt |
| POST | `run_agent.py` run_conversation() | LLM 返回后、返回结果前 | 复盘/记忆提取/后处理 |

### 代码模板

**PRE 钩子（conversation_loop.py）：**
```python
# ── Hermes Strong Enhancement: PRE hook ──
try:
    import sys as _sys
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_pre_conversation
    _enhancement_text = safe_hook_pre_conversation(agent, user_message)
    if _enhancement_text:
        effective_system = (effective_system + "\n\n" + _enhancement_text).strip()
except Exception:
    pass  # Never let enhancement break the agent loop
```

**POST 钩子（run_agent.py run_conversation）：**
```python
result = run_conversation(self, user_message, system_message, ...)
# HERMES ENHANCEMENT: POST hook
try:
    import sys as _sys; from pathlib import Path
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_post_conversation
    final_response = result.get("final_response", "")
    safe_hook_post_conversation(self, final_response, user_message)
except Exception:
    pass
return result
```

### 关键设计决策

1. **try-except 包裹所有增强代码** — 任何异常不影响核心对话循环
2. **`Path.home()` 而非硬编码路径** — 用户无关，可迁移
3. **`_sys.path.insert(0, ...)` 而非 `sys.path.append`** — 确保增强模块优先加载
4. **短变量名前缀 `_`** — 避免与 Hermes 核心变量冲突
5. **零逻辑入侵** — 总共 10-15 行 try-except 代码

### 验证方法

```bash
# 验证 PRE 钩子
grep -c "safe_hook_pre_conversation" agent/conversation_loop.py
# 验证 POST 钩子
grep -c "safe_hook_post_conversation" run_agent.py
# 验证语法
python3 -c "import py_compile; py_compile.compile('agent/conversation_loop.py', doraise=True); print('OK')"
python3 -c "import py_compile; py_compile.compile('run_agent.py', doraise=True); print('OK')"
# 验证函数签名
python3 -c "
import sys; sys.path.insert(0, str(Path.home() / '.hermes/scripts'))
from agent_enhancement_manager import safe_hook_pre_conversation, safe_hook_post_conversation
import inspect
print(inspect.signature(safe_hook_pre_conversation))
print(inspect.signature(safe_hook_post_conversation))
"
```

### 注意事项

- 升级 Hermes 后需要重新注入（git pull 可能覆盖修改）
- 备份文件要先保存：`cp agent/conversation_loop.py /mnt/d/Hermes/备份/`
- 每次升级后检查 gti 冲突标记（`grep -n "<<<<<<<\|>>>>>>>" run_agent.py`）

---

## 模式2: 脚本合并为统一模块

### 目标
将多个功能重叠的独立脚本合并为一个统一模块，减少文件数量，消除重复逻辑，对外保持接口兼容。

### 合并步骤

**Step 1 — 识别重叠脚本：**
找出功能重复的脚本列表。常见重叠类型：
- 同一主题的不同实现版本（v1/v2/v3）
- 不同文件但操作同一数据库/API
- 互相调用的脚本
- CLI 入口不同的同一功能

**Step 2 — 备份原文件：**
```bash
cp script1.py /mnt/d/Hermes/备份/script1.py.bak
# ... 全部备份
```

**Step 3 — 创建统一模块：**
按模块组织：`compression_engine.py`、`memory_engine.py`、`orchestrator.py` 等。
文件顶部写清合并来源：
```python
"""
module.py — 统一模块
合并自: script1.py + script2.py + script3.py
能力无损，接口兼容，旧脚本均通过此模块转发。
"""
```

**Step 4 — 保留全部公共接口：**
原脚本的每个公共函数/类必须在新模块中存在。命名冲突时用别名：
```python
# 旧接口别名
from module import OldClass as NewClass
```

**Step 5 — 原文件改为转发器：**
```python
#!/usr/bin/env python3
"""转发器 — 功能已迁移到 module.py"""
from module import *  # 或具体类/函数
```
转发器必须：
- 保留原 CLI 入口（`if __name__ == "__main__"`）
- 保留原参数签名
- 兼容原 cron/import 调用路径

**Step 6 — 统一 CLI 入口：**
```python
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    # 按 cmd 分发
```

### 实际案例（2026-06-02）

| 统一模块 | 原脚本数 | 合并批次 |
|----------|---------|---------|
| `compression_engine.py` | 9 | 第一批 |
| `memory_engine.py` | 7 | 第二批 |
| `orchestrator.py` | 5 | 第三批 |
| `memory_tools.py` | 3 | 第四批 |

每个模块对应的旧脚本列表见各文件 docstring。

### 验证方法

```bash
# 语法检查
python3 -c "import py_compile; py_compile.compile('scripts/new_module.py', doraise=True); print('OK')"
# 旧 CLI 兼容
python3 scripts/old_script.py --help
# 旧 import 兼容
python3 -c "from scripts.old_script import OldClass; print('OK')"
# 功能测试
python3 scripts/new_module.py status
```

---

## 模式3: 外部项目集成模式

### 目标
将 GitHub 上的独立项目集成到 Hermes 系统中，非 Docker 迁移。

### 步骤

1. **clone 到 integrations 目录**：
   ```bash
   cd /mnt/m/Hermes/integrations
   git clone --depth 1 <repo_url>
   ```

2. **分析依赖**：检查 package.json、requirements.txt、pyproject.toml

3. **安装依赖**：
   - Python: `pip install -r requirements.txt`
   - Node.js: `npm install`
   - Golang/Rust 等: 按项目要求

4. **提取核心逻辑**：如果是大型项目，提取关键模块为 Python 桥接脚本

5. **注册到武器库**：桥接脚本放在 `~/.hermes/scripts/`，engine_core 自动扫描

6. **配置保活 cron（如果适用）**:
   ```
   */5 * * * * python3 scripts/bridge_launcher.py
   ```

### 项目示例

| 项目 | 类型 | 集成方式 |
|------|------|---------|
| hermes-webui | Python Web UI | 复制到 ~/.hermes/webui/ + 保活 cron |
| gbrain | TypeScript CLI | clone + npm install + Python 桥接脚本 |
| hermes-desktop | Electron 桌面 | clone + 提取会话/技能管理模块为 Python |
