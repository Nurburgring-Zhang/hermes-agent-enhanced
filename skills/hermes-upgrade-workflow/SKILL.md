---
name: hermes-upgrade-workflow
description: Hermes Agent非破坏性升级工作流 - 在WSL2中安全升级Hermes同时保留所有自定义文件
version: 2.0.0
author: Hermes
triggers:
  - "升级Hermes"
  - "hermes upgrade"
  - "迁移Hermes"
  - "update hermes"
  - "比较版本差异"
  - "升级前对比"
---

# Hermes 非破坏性升级工作流

## 核心原则

**永远不要用 `git reset --hard`**。自定义文件在 `hermes_cli/` 和 `tools/` 目录中，git不追踪这些文件，但reset会清空工作区。

## 升级前全面对比

在升级前，必须对比当前增强版 vs 官方新版本的功能差异，评估升级风险和收益。

### 执行方法

```bash
# 1. 获取当前版本
hermes --version

# 2. 查看官方Release Notes（浏览器打开）
# 打开 https://github.com/NousResearch/hermes-agent/releases

# 3. 比较落后了哪些commit
cd ~/.hermes/hermes-agent
git rev-list --left-right --count HEAD...origin/main
git log --oneline HEAD..origin/main | wc -l

# 4. 检查本地修改
git status --short
git diff --stat
```

### 对比维度矩阵

升级前需要从以下维度逐一比对：

| 维度 | 检查项 |
|------|--------|
| 核心代码修改 | 检查 conversation_loop.py / run_agent.py / hermes_cli/__init__.py 的本地注入 |
| 自定义新增文件 | 检查 expert_system.py / tools/*.py / hermes_cli/monitoring_commands.py 等 |
| 自定义脚本 | ~/.hermes/scripts/ 目录下所有自定义脚本是否与新版本兼容 |
| config.yaml | 检查provider配置、credential_pool、fallback_providers等自定义配置 |
| cron任务 | crontab -l 检查所有自建cron是否会因版本变更受影响 |
| skills列表 | 检查自定义skills与新版本是否兼容（新版本可能精简默认技能） |
| 记忆系统 | 检查自定义记忆模块(L1/L2/L3/情景等) |
| 安全系统 | 检查tirith/CaMeL/自定义安全模块 |

### 官方v0.16.0 vs 我们增强版对比案例（标杆）

升级前输出完整对比报告，包含：
- 官方新增的能力（我们没有的 — 升级价值点）
- 我们独有的增强（官方没有的 — 需要在升级后重新适配保留的）
- 风险矩阵（升级后可能被覆盖的代码点）

## 标准升级流程

### Step 1: 备份所有自定义文件（全面版）

```bash
BACKUP_DIR=/mnt/d/Hermes/备份/升级前备份_$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 1. 配置文件
cp ~/.hermes/config.yaml $BACKUP_DIR/config.yaml.bak
cp ~/.hermes/.env $BACKUP_DIR/env.bak

# 2. 核心契约文档
cp ~/.hermes/AGENTS.md $BACKUP_DIR/AGENTS.md.bak
cp ~/.hermes/SOUL.md $BACKUP_DIR/SOUL.md.bak 2>/dev/null

# 3. 本地代码修改（patch文件）
cd ~/.hermes/hermes-agent
git diff > $BACKUP_DIR/local_code_changes.patch
git diff --cached > $BACKUP_DIR/staged_changes.patch 2>/dev/null

# 4. 新增的自定义文件
for f in expert_system.py load_security.py tools/device_tools.py \
  tools/rag_memory_tool.py tools/path_security.py tools/tirith_security.py \
  hermes_cli/monitoring_commands.py; do
  if [ -f "$f" ]; then
    cp "$f" "$BACKUP_DIR/$(echo $f | tr '/' '_')"
  fi
done

# 5. 自定义脚本目录
cp -r ~/.hermes/scripts/ $BACKUP_DIR/scripts/

# 6. skills列表
ls ~/.hermes/skills/ > $BACKUP_DIR/skills_list.txt

# 7. cron配置
crontab -l > $BACKUP_DIR/cron_list.txt

# 8. 版本信息
hermes --version > $BACKUP_DIR/version.txt
```

### Step 2: 检查git状态

```bash
cd ~/.hermes/hermes-agent
git remote -v
git branch -vv
git rev-list --left-right --count HEAD...origin/main  # 看落后多少commit
```

### Step 3: 升级操作

**⚠️ 先判断git clone类型，再决定操作方式。**

#### 方式A: 完整clone（推荐，无特殊限制）

```bash
cd ~/.hermes/hermes-agent
git fetch origin
git merge origin/main --no-edit
```

如果merge失败（冲突），用 `git merge --abort` 中止，手动解决后重试。

#### 方式B: shallow clone（`--depth=1`，GitHub不可达时的首选）

当 `git fetch --depth=1` 创建了浅克隆时，`git merge` 会报 `refusing to merge unrelated histories`。
此时必须用 reset 方式替换主分支（前提：所有本地修改已被stash/备份）：

```bash
cd ~/.hermes/hermes-agent

# 1. 备份所有自定义文件（必须 — reset会清空工作区）
# 包括: tools/*.py, hermes_cli/monitoring_commands.py, 
#        expert_system.py, load_security.py 等非git文件
# 实际操作中，untracked files (??) 不会被reset清除，但modified files会被覆盖

# 2. stash本地代码修改
git stash push -m "pre-upgrade-$(date +%Y%m%d)" -- agent/conversation_loop.py hermes_cli/__init__.py run_agent.py

# 3. shallow fetch（可能因GFW超时，可尝试多次）
git config http.version HTTP/1.1
git fetch --depth=1 --no-tags origin +refs/heads/main:refs/remotes/origin/main

# ⚠️ 如果step 3持续超时（GitHub不可达），尝试Windows curl绕道：
# WSL中git fetch超时但Windows可能可以访问（2026-06-11实战经验）
# 通过/mnt/c/访问Windows的curl.exe下载release tarball
# 注意下载很慢~80KB/s，42MB需~8分钟，给足--max-time
curl.exe -L --connect-timeout 15 \
  "https://github.com/NousResearch/hermes-agent/archive/refs/tags/v2026.6.5.tar.gz" \
  --max-time 600 -o C:\Users\Administrator\hermes-release.tar.gz

# 在WSL中解压用于对比：
mkdir -p /tmp/hermes-v0.16.0
tar xzf /mnt/c/Users/Administrator/hermes-release.tar.gz -C /tmp/hermes-v0.16.0 --strip-components=1

# 如果下载中断，核心文件(run_agent.py, conversation_loop.py)通常在tarball前半段
# shallow fetch后不要用git merge（会海量冲突），改用git reset --hard

# 5. reset到远程（丢弃本地未stash的修改）
git reset --hard origin/main

# 6. 验证版本
hermes --version  # 期望: v0.16.0
```

**关键提醒**:
- `git reset --hard` 会丢弃所有**已追踪但未commit**的修改。确保所有有价值的本地修改已stash或备份
- 未追踪文件（`??`状态如 tools/device_tools.py）不会被reset清除 — 它们不是git仓库的一部分
- config.yaml 和 .env 在 ~/.hermes/ 目录，不在hermes-agent仓库中，不受影响
- 升级后再从stash恢复修改、重新注入代码

### Step 4: 验证升级成功

```bash
hermes --version
git log --oneline -3
```

### Step 5: 检查自定义文件状态

```bash
git status --short
```
- `??` 开头的是未追踪文件（自定义文件，正常）
- `hermes_cli/main.py` 如果变成repo版本（检查内容是否包含自定义commands）

### Step 6: 恢复自定义被覆盖的代码

升级后hermes-agent目录的所有核心文件已回到官方v0.16.0版本。需要重新注入4处核心修改：

```bash
cd ~/.hermes/hermes-agent

# 1. conversation_loop.py — PRE hook
# 找到 effective_system = active_system_prompt or ""
# 在它和 if agent.ephemeral_system_prompt 之间插入
# 插入代码:
"""
        # ── Hermes Strong Enhancement: PRE hook ──
        # Inject enhancement context into system prompt before LLM call
        try:
            import sys as _sys
            _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
            from agent_enhancement_manager import safe_hook_pre_conversation
            _enhancement_text = safe_hook_pre_conversation(agent, user_message)
            if _enhancement_text:
                effective_system = (effective_system + "\\n\\n" + _enhancement_text).strip()
        except Exception:
            pass  # Never let enhancement break the agent loop
"""

# 2. run_agent.py — POST hook
# 找到 def run_conversation(...):
# 将其中的 return run_conversation(self, ...)
# 改为:
"""
        result = run_conversation(self, user_message, system_message, conversation_history, task_id, stream_callback, persist_user_message)
        # HERMES ENHANCEMENT: POST hook - runs after each conversation turn
        try:
            import sys as _sys; from pathlib import Path
            _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
            from agent_enhancement_manager import safe_hook_post_conversation
            final_response = result.get("final_response", "")
            safe_hook_post_conversation(self, final_response, user_message)
        except Exception:
            pass
        return result
"""

# 3. hermes_cli/__init__.py — 启动时加载双审
# 在 docstring """ 之后，import os 之前插入:
"""
# [双审] 启动时加载双AI互审规则
import subprocess as _subprocess, os as _os
_startup_script = _os.path.expanduser("~/.hermes/scripts/startup_dual_review.sh")
if _os.path.exists(_startup_script):
    _subprocess.run(["bash", _startup_script], capture_output=True)
"""

# 4. model_tools.py — 进程级强制加载（2026-06-12新增）
# 在文件末尾的 check_tool_availability() 函数之后添加:
# (复制自备份或skills目录中的注入模板)

# 4. model_tools.py — 进程级强制加载（2026-06-12新增）
# 在文件末尾的 check_tool_availability() 函数之后添加 _force_init_all_enhancements()
# 详见 ~/.hermes/skills/autonomous-systems/dual-ai-review/references/rule-enforcer-v1.md

# 5. rule_enforcer.py — 规则强制执行引擎（2026-06-12新增）
# 文件在 ~/.hermes/scripts/rule_enforcer.py，git不追踪，自动保留
# 但需确认被 model_tools.py 的强制加载入口正确引用
# 检查: grep -n 'rule_enforcer' ~/.hermes/hermes-agent/model_tools.py
# 期望: 返回3处（加载代码）

# 6. tool_executor.py — 工具调用拦截面（2026-06-12新增）
# agent/tool_executor.py中被子Agent插入了6处pre/post_tool_intercept调用
# 以及顶部的动态import（importlib.util from scripts/rule_enforcer.py）
# 升级后需要验证这些代码仍然存在：
# grep -n 'rule_enforcer\|pre_tool_intercept\|post_tool_intercept' agent/tool_executor.py
# 期望: 顶部import + 6处拦截点（4处并发路径 + 2处顺序路径）

# 7. agent_enhancement_manager.py — 规则引擎插件注册（2026-06-12新增）
# 文件在 ~/.hermes/scripts/，git不追踪，自动保留
# PLUGIN_REGISTRY中应包含 ("rule_enforcer", "scripts/rule_enforcer.py", "both", True, ...)
# PRE阶段: _try_load("rule_enforcer", ...) 在 safe_hook_pre_conversation 中
# POST阶段: _try_load("rule_enforcer", ...) 在 safe_hook_post_conversation 中

# 8. battle_commander.py / forced_executor.py / task_enhancement_engine.py
# 这三个文件的pre/post_conversation_hook在2026-06-12被修复/新增
# 文件在 ~/.hermes/scripts/，git不追踪，自动保留
# 检查: grep -n 'def pre_conversation_hook' ~/.hermes/scripts/battle_commander.py
# 期望: 存在（否则从备份恢复）

# 语法验证所有被修改的核心文件
for f in agent/conversation_loop.py run_agent.py hermes_cli/__init__.py model_tools.py agent/tool_executor.py; do
    python3 -c "import py_compile; py_compile.compile('/home/administrator/.hermes/hermes-agent/$f', doraise=True); print('$f: OK')"
done
```

### 注意事项
- `model_tools.py` 的注入是最新增加的第4条路径（2026-06-12），旧版本的备份patch中可能没有这个文件，需要手动添加上面的模板
- 注意 `hermes_cli/__init__.py` 中的v0.16.0版本号已从 `__version__ = "0.15.1"` 变成 `__version__ = "0.16.0"`

## 升级后适配清单

升级后需要立即验证和修复以下内容：

### 核心代码注入点验证

1. `agent/conversation_loop.py` — 检查PRE hook注入点是否被重构
2. `run_agent.py` — 检查POST hook调用点是否变动
3. `hermes_cli/__init__.py` — 检查启动加载是否正常

### 验证步骤

```bash
# 验证自定义文件存在
ls -la ~/.hermes/hermes-agent/hermes_cli/monitoring_commands.py
ls -la ~/.hermes/hermes-agent/tools/device_tools.py
ls -la ~/.hermes/hermes-agent/expert_system.py

# 验证配置兼容
hermes --version
hermes config check
hermes doctor --fix

# 验证cron任务
crontab -l | wc -l
```

### 常见v0.16.0迁移问题

- config.yaml provider格式变更 — v0.16.0可能重构了provider配置结构
- model路由名称变更 — 新模型名可能与旧版本不同
- skills目录格式变更 — v0.16.0精简了默认技能集，自定义技能可能不受影响
- conversation_loop API变动 — 874 commits可能涉及核心循环重构

## 关键发现（经验教训）

### Hermes git repo位置
- 在 `~/.hermes/hermes-agent/`，不是 `~/.hermes/`
- 自定义文件在 `hermes_cli/` 和 `tools/` 目录中

### 被覆盖的高风险文件
| 文件 | 风险 | 恢复方式 |
|------|------|----------|
| `hermes_cli/main.py` | **高** — 最易被覆盖 | 从备份恢复 |
| `hermes_cli/monitoring_commands.py` | 低 — git不追踪 | 自动保留 |
| `tools/device_tools.py` | 低 — git不追踪 | 自动保留 |
| `tools/rag_memory_tool.py` | 低 — git不追踪 | 自动保留 |
| `load_security.py` | 低 — git不追踪 | 自动保留 |

### 常见hermes doctor警告（可忽略）
- `MiniMax (China) HTTP 404` — 检测端点问题，不影响实际使用
- `ripgrep not found` — 可选依赖
- `docker not found` — 禁用Docker是硬性规则
- `npm vulnerability` — WhatsApp bridge等可选组件

### 需要关注的hermes doctor警告
- `Config version outdated (v12 → v22)` — 运行 `hermes doctor --fix` 自动迁移
- `tinker-atropos not found` — 可选子模块
- `Browser tools (node binary missing)` — WSL2常见问题，用Python API补救

## 配置迁移

hermes doctor --fix 会自动处理：
- `stt.model` → provider-specific config
- `compression.summary_*` → `auxiliary.compression`
- Config v12 → v22

## 升级后验证清单
- [ ] `hermes --version` 显示新版本
- [ ] `git rev-list --left-right --count HEAD...origin/main` 显示 `0 0`
- [ ] 自定义文件存在于 `hermes_cli/` 和 `tools/` 目录
- [ ] `hermes doctor` 无致命错误
- [ ] Hermes正常响应命令
- [ ] PRE hook在conversation_loop中正常注入
- [ ] POST hook在run_agent中正常触发
- [ ] 双审启动脚本正常加载
- [ ] 3处核心注入点语法正确

---

_本Skill版本v2.0基于2026-06-11 v0.15.1到v0.16.0升级对比实战更新。_

### Step 7: Phase-0 环境变量安全迁移（env-secure Credential Pattern）

每次升级后（或新部署时），必须执行API密钥安全化流程。这是一个独立的Phase-0工程，可在升级后分批执行。

#### 背景

config.yaml中所有api_key字段必须是 `${ENV_VAR_NAME}` 格式的环境变量引用，而非明文。对应密钥值存储在 `~/.hermes/.env`（权限chmod 600）。

#### 实现步骤

**1. 创建 `scripts/env_loader.py`**

```python
# Hermes 环境变量安全加载器
# 被 model_tools.py 在模块初始化时自动加载
# 支持从配置替换 ${ENV_VAR} 格式

import os, re, logging
from pathlib import Path

_ENV_REF_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}')

def load_env_file(env_path=None):
    \"\"\"加载 .env 文件并设置到 os.environ\"\"\"
    if env_path is None:
        env_path = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes')) / '.env'
    if not env_path.exists():
        return {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip().strip("'\"")
    return {}
```

**2. 在 `model_tools.py` 中添加启动加载（在Plugin discovery之前）**

```python
# Hermes 环境变量安全加载器
try:
    import sys
    _hermes_scripts = str(Path(__file__).resolve().parent.parent / 'scripts')
    if _hermes_scripts not in sys.path:
        sys.path.insert(0, _hermes_scripts)
    from env_loader import init_env
    init_env()
except Exception as e:
    logger.debug("env_loader init failed (non-fatal): %s", e)
```

**3. 修改 config.yaml 替换密钥**

```bash
# 每条密钥执行:
sed -i 's|api_key: 实际密钥值|api_key: ${ENV_VAR_NAME}|' config.yaml
```

**4. 创建 `scripts/env_config_resolver.py`**（可选，当config需要运行时解析时）

如果Hermes的yaml加载器不支持 `${ENV}` 语法，就需要在config加载后、使用前做环境变量替换：

```python
def resolve_config_env(config):
    \"\"\"递归替换配置中所有 ${ENV_VAR} 为os.environ值\"\"\"
    if isinstance(config, dict):
        return {k: resolve_config_env(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [resolve_config_env(item) for item in config]
    elif isinstance(config, str) and '${' in config:
        var_name = config[2:-1]
        return os.environ.get(var_name, config) if config.startswith('${') else config
    return config
```

#### 密钥发现流程

```bash
# 找出所有明文密钥
grep -rn 'api_key: nvapi\|api_key: sk-\|token: [a-f0-9]\{32,\}' config.yaml

# 映射到环境变量名
# 每个provider需要唯一的ENV名称:
#   nvidia-deepseek → NVIDIA_DEEPSEEK_API_KEY
#   nvidia-glm → NVIDIA_GLM_API_KEY  
#   deepseek (built-in) → DEEPSEEK_API_KEY
#   deepseek (custom_providers) → DEEPSEEK_CUSTOM_API_KEY
#   pushplus.token → PUSHPLUS_TOKEN
```

#### 验证清单

- [ ] `.env` 文件存在且权限为600
- [ ] `.gitignore` 包含 `.env`、`config.yaml`、`*.db`
- [ ] `config.yaml` 中所有api_key为 `${ENV_VAR}` 格式
- [ ] `model_tools.py` 启动时能成功加载.env
- [ ] 所有provider的密钥能通过环境变量正常解析
- [ ] 无`nvapi-`或`sk-`开头值残留在config.yaml中
- [ ] 所有API base_url为HTTPS

#### 已知限制

- 当前Hermes YAML加载器（~/.hermes/hermes-agent/agent/curator.py _load_config）不支持YAML中的 `${ENV}` 语法。只能在代码层的 `model_tools.py` 中通过 `resolve_config_env()` 做替换。
- 如果需要让Hermes的provider解析机制支持 `${ENV}`，需要在 `hermes_cli/runtime_provider.py` 或 `agent/curator.py` 的 `resolve_runtime_provider` 中添加替换逻辑。

#### 参考链接

- `~/.hermes/scripts/env_loader.py` — 完整实现（Phase-0产物）
- `references/env-secure-credential-pattern.md` — 更完整的实现与讨论

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
