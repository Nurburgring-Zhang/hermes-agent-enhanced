---
name: hermes-agent-operations
description: "Hermes Agent 运维操作 — 多profile隔离、memory provider配置、gateway管理、外部API集成(NVIDIA/Agnes等)"
category: hermes
---

# Hermes Agent 运维操作

覆盖：multi-profile管理、memory provider插件、gateway服务、外部免费API集成。

### Absorbed Skills (consolidated)

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `hermes-system-self-audit` | Subsection — system self-check checklist and health audit | `references/hermes-system-self-audit-complete.md` |

The absorbed skill provides a system health audit checklist: cron auto-pause detection, database health verification, backup recovery method signatures, four-layer deployment validation (script exists → cron runs → data fresh → dialogue layer active). See the reference for the full checklist.

## 一、Multi-Profile 多实例隔离

Hermes Agent支持通过 `-p/--profile` 参数创建完全隔离的实例。

### 核心原则

每个profile是**完全独立**的Agent实例：
- 独立的 config.yaml / .env / memory / skills / logs
- 独立的 systemd user unit (通过 `gateway install`)
- 不共享任何状态

### 操作命令

```bash
# 创建profile
hermes profile create <name>          # 创建在 ~/.hermes/profiles/<name>/
hermes profile list                    # 列出所有profile及其状态

# 操作特定profile
hermes -p <name> setup                # 配置API key和模型
hermes -p <name> gateway start        # 启动gateway
hermes -p <name> gateway install      # 安装systemd服务
hermes -p <name> logs --tail          # 查看日志

# default profile特殊处理
hermes gateway start                  # default不用-p
hermes -p cron-bot gateway start      # 其他profile用-p
```

### 批量管理脚本

```bash
#!/bin/sh
# ~/.local/bin/hermes-gateways
set -eu
profiles="default cron-bot"
action="${1:-}"
case "$action" in
  start|stop|restart|status)
    for p in $profiles; do
      echo "==> $action $p"
      if [ "$p" = "default" ]; then hermes gateway "$action"
      else hermes -p "$p" gateway "$action"; fi
    done ;;
  *) echo "Usage: hermes-gateways {start|stop|restart|status}" ;;
esac
```

安装后确保: `chmod +x ~/.local/bin/hermes-gateways`

### 后台运行保障

```bash
# 开启linger — SSH断开后systemd user服务继续运行
sudo loginctl enable-linger "$USER"

# 查看所有Hermes gateway服务
systemctl --user list-units 'hermes-gateway-*'

# 日志查看
tail -f ~/.hermes/logs/gateway.log ~/.hermes/profiles/*/logs/gateway.log
```

### 典型部署场景

```
default — 主对话实例, 接Telegram/微信, 日常问答和任务执行
cron-bot — 定时任务专用, 采集/推送/自进化, 不占对话模型资源
dev — 开发测试隔离环境, 不影响生产
```

## 二、Memory Provider 插件

Hermes内置记忆只有2200字符。通过memory provider插件扩展到无限空间。

### 8种可用插件

| 名称 | 费用 | 部署 | 特点 |
|------|:----:|:----|:-----|
| Holographic | 免费 | 本地 SQLite | FTS5全文搜索+HRR向量检索, 信任评分自动遗忘, 隐私最好 |
| Honcho | 免费/付费 | 云端/自部署 | 最强推理, 辩证推理理解上下文意图 |
| Mem0 | 付费 | 云端 | 最流行, LLM事实提取+语义搜索, 自动去重 |
| RetainDB | $20/月 | 云端 | 最精准控制, 向量+BM25+重排混合搜索, 7种记忆类型 |
| Hindsight | 免费/付费 | 本地/云端 | 中等智能 |
| ByteRover | 付费 | 云端 | 自动提取 |
| OpenViking | 免费/付费 | 本地/云端 | 轻量级 |
| Supermemory | 付费 | 云端 | 需API Key |

### Holographic（推荐方案）

选择理由：隐私第一、零成本、纯本地、够用。

```bash
# 配置
hermes config set memory.provider holographic

# 验证
hermes memory status
# 应显示: Provider: holographic, Status: available

# 数据库位置
~/.hermes/memory_store.db  (SQLite, 4KB+)
```

Holographic与Hy-Memory的关系：
- Holographic: 对话层短期记忆, 自动注入, 负责"认识我"
- Hy-Memory (active_memory.db): 结构化长期记忆, 按需查询, 负责"知识"
- AutoCleaner: 两者兼顾的清理机制

9种操作: add / search / probe / related / reason / contradict / update / remove / list
fact_feedback: 点赞/踩，低分自动遗忘

## 三、外部免费API集成

### NVIDIA build.nvidia.com (v2 — 多key多模型 + fallback链)

147个模型免费调用, OpenAI兼容格式, 国内直连, 不绑卡。

```
base_url: https://integrate.api.nvidia.com/v1
key格式: nvapi-xxxxxxxx
```

#### config.yaml providers字段（v12+格式）

新版config.yaml使用 `providers:` 字典（非 `custom_providers:` 列表），每个条目是一个带完整配置的provider：

```yaml
providers:
  nvidia-deepseek:
    api: https://integrate.api.nvidia.com/v1
    api_key: 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
    default_model: deepseek-ai/deepseek-v4-pro
    name: NVIDIA-DS
  nvidia-glm:
    api: https://integrate.api.nvidia.com/v1
    api_key: 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
    default_model: z-ai/glm-5.1
    name: NVIDIA-GLM
  nvidia-kimi:
    api: https://integrate.api.nvidia.com/v1
    api_key: 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
    default_model: moonshotai/kimi-k2.6
    name: NVIDIA-Kimi
  nvidia-nemotron:
    api: https://integrate.api.nvidia.com/v1
    api_key: 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
    default_model: nvidia/nemotron-3-ultra-550b-a55b
    name: NVIDIA-Nemotron
```

`providers:` 支持字段: `api`(base_url), `api_key`, `key_env`(env var name), `default_model`, `name`, `models`(dict), `context_length`, `api_mode`/`transport`, `extra_body`, `request_timeout_seconds`, `stale_timeout_seconds`, `discover_models`。

#### fallback_providers链（限流自动切换）

fallback chain在config.yaml的 `fallback_providers:` 列表，当主模型429/超时时自动按序切换：

```yaml
fallback_providers:
  - provider: nvidia-deepseek
    model: deepseek-ai/deepseek-v4-pro
  - provider: nvidia-glm
    model: z-ai/glm-5.1
  - provider: nvidia-kimi
    model: moonshotai/kimi-k2.6
  - provider: nvidia-nemotron
    model: nvidia/nemotron-3-ultra-550b-a55b
    extra_body:
      chat_template_kwargs:
        enable_thinking: true
      reasoning_budget: 16384
```

fallback链的provider值可以是：
- `providers:`字典中的key名（如 `nvidia-deepseek`）→ 自动通过 `_get_named_custom_provider()` 解析
- `openrouter` → 使用已配置的OpenRouter API key
- `custom` → 通过OPENAI_BASE_URL/OPENAI_API_KEY环境变量解析
- 标准provider名（`deepseek`, `anthropic`等）

限流切换机制：429时设60秒冷却，`_fallback_index++`，跳到链上下一个。支持base_url去重防止循环fallback到相同端点。

#### ⚠️ `hermes config set` 陷阱

`hermes config set` 会把dict/list序列化成JSON内联字符串，而不是YAML对象：
```yaml
# BAD — 不能这样
providers: '{"nvidia":{"api":"...","api_key":"..."}}'
fallback_providers: '[{"provider":"nvidia","model":"..."}]'

# GOOD — 手动修复后
providers:
  nvidia:
    api: https://...
    api_key: nvapi-...
fallback_providers:
  - provider: nvidia
    model: ...
```

修复方法：用python3 load yaml -> json.loads字符串 -> yaml.dump写回。

#### OpenRouter free模型

OpenRouter的free模型（带`:free`后缀）作为fallback chain的最后一层：

```yaml
  - provider: openrouter
    model: moonshotai/kimi-k2.6:free
  - provider: openrouter
    model: sourceful/riverflow-v2.5-pro:free
  - provider: openrouter
    model: nvidia/nemotron-3-ultra-550b-a55b:free
  - provider: openrouter
    model: openrouter/owl-alpha
```

注意：OpenRouter free模型限流严格，只适合做最后的保底fallback。

#### 内存中存储API keys的权衡

- config.yaml直接写api_key：最简单但key暴露在配置文件中
- key_env + .env：安全但需要提前在.env定义变量
- 纯环境变量：通过 credential_pool 自动发现
- 推荐：敏感环境用 key_env 引用.env变量，非敏感场景直接写api_key

### Agnes AI 免费全模态

全球AI Lab第9名, Claw-Eval国内前7, 无限期免费。
- Agnes-2.0-Flash: 文本, 1M上下文, 工具调用
- Agnes-Image-2.0-Flash: 图像编辑, 背景替换
- Agnes-Video-V2.0: 音画同步, 720P/1080P

```yaml
providers:
  agnes:
    api: https://api.agnes.ai/v1
    api_key: agnes_key
    default_model: agnes-2.0-flash
    name: Agnes AI
```

### API Key获取的工作流

1. 用户通过消息提供KEY → 写入config.yaml的providers字典或.env
2. 用 `python3 -c "from openai import OpenAI; ..."` 验证API连通性
3. AI不能在用户不提供KEY的情况下自动配置

### 配置验证方法

```python
from openai import OpenAI
client = OpenAI(base_url='https://integrate.api.nvidia.com/v1', api_key='nvapi-xxx')
# 测试简单调用
r = client.chat.completions.create(
    model='deepseek-ai/deepseek-v4-pro',
    messages=[{'role':'user','content':'Say hi in 3 words.'}],
    max_tokens=50
)
print(r.choices[0].message.content)
```

## 六、代码合并模式（2026-06-02 新增）

当多个脚本功能重叠时，用统一模块替代多个脚本，旧脚本保留为轻量转发器。

### 合并标准流程

1. **分析重叠** — 读取所有待合并脚本的完整代码，提取类定义/函数签名/CLI入口
2. **备份** — 旧脚本备份到 `/mnt/d/Hermes/备份/`
3. **创建统一模块** — 新建 `<name>.py`，按模块组织，保留全部公开接口
4. **创建转发器** — 旧脚本改为 `from <new_module> import *` 或 `from <new_module> import <OldClass>`
5. **验证** — 执行旧脚本的命令行参数验证转发器正常工作
6. **提交** — git add + git commit

### 实例：21→4脚本合并（2026-06-02）

| 批次 | 旧脚本 | 新模块 | 大小 |
|------|--------|--------|------|
| 压缩引擎 | lossless_claw + emergency_compressor + rtk_compressor + context_compressor + compress_soul_static + compression_fidelity_validator + memory_compress + run_compression + archive_compressor | `compression_engine.py` | 37KB |
| 记忆引擎 | hermes_memory_engine + hermes_memory_engine_v2 + unified_memory_core + hierarchical_memory + active_memory + memory_highway + init_active_memory_db | `memory_engine.py` | 58KB |
| 编排器 | unified_memory_orchestrator + memory_orchestrator_v3 + memory_integration + hy_memory_orchestrator + parallel_memory_orchestrator | `orchestrator.py` | 12KB |
| 工具集 | memory_index + memory_stats + memory_search_test | `memory_tools.py` | 5KB |

### 转发器模板

```python
#!/usr/bin/env python3
"""转发器 — 功能已迁移到 <new_module>.<Class>"""
from <new_module> import <Class>
import sys, json
if __name__ == "__main__":
    # 转发旧的CLI参数到新模块
    ...
```

## 七、Hermes底层注入模式（2026-06-02 新增）

增强能力必须注入到Heres核心文件 `run_agent.py` 和 `agent/conversation_loop.py`，而不是靠外部脚本"手动调用"。

### PRE钩子注入点（对话前、LLM调用前）
文件: `agent/conversation_loop.py`
位置: `effective_system` 构建后、`if agent.ephemeral_system_prompt:` 之前

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
    pass
```

### POST钩子注入点（对话返回后）
文件: `run_agent.py`
位置: `run_conversation()` 方法中

```python
result = run_conversation(self, ...)
# HERMES ENHANCEMENT: POST hook
try:
    import sys as _sys; from pathlib import Path
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_post_conversation
    safe_hook_post_conversation(self, result.get("final_response", ""), user_message)
except Exception:
    pass
return result
```

### 注意事项
- 两个钩子都包裹在 try-except 中
- 代码注入在核心文件中，不是外部脚本
- 升级后必须 grep 确认注入点未被覆盖
- 硬编码路径需使用 `Path.home()`

### 升级保护
每次 `hermes update` 后：
1. grep `safe_hook_pre` 确认PRE钩子还在
2. grep `safe_hook_post` 确认POST钩子还在
3. grep `startup_dual_review` 确认 `hermes_cli/__init__.py` 双审启动注入还在
4. 如果丢失，重新注入

### ⚠️ Shallow Clone 升级陷阱
Hermes Agent 通常通过 shallow clone（`git clone --depth=1`）安装。当从另一个 shallow clone fetch 新版本时，`git merge` 会触发 **"refusing to merge unrelated histories"** 错误，导致所有文件出现 CONFLICT（因为两个 shallow clone 没有共同的祖先 commit）。

**正确升级路径（shallow→shallow）**：
```bash
cd ~/.hermes/hermes-agent
git fetch --depth=1 origin main    # fetch 最新版本
git reset --hard origin/main       # 直接重置，不要 merge
```
`git reset --hard` 会完全覆盖本地修改（untracked 文件保留），所以**必须在 reset 前备份所有自定义文件**。

**升级前备份清单**：
```bash
mkdir -p /mnt/d/Hermes/备份/upgrade_$(date +%Y%m%d_%H%M)/
# 备份关键文件
cp ~/.hermes/hermes-agent/expert_system.py /mnt/d/Hermes/备份/upgrade_*/ 
cp ~/.hermes/hermes-agent/tools/device_tools.py /mnt/d/Hermes/备份/upgrade_*/ 
cp ~/.hermes/hermes-agent/tools/rag_memory_tool.py /mnt/d/Hermes/备份/upgrade_*/ 
cp ~/.hermes/hermes-agent/tools/tirith_security.py /mnt/d/Hermes/备份/upgrade_*/
cp ~/.hermes/hermes-agent/hermes_cli/monitoring_commands.py /mnt/d/Hermes/备份/upgrade_*/
cp ~/.hermes/hermes-agent/load_security.py /mnt/d/Hermes/备份/upgrade_*/
cp ~/.hermes/config.yaml /mnt/d/Hermes/备份/upgrade_*/
# crontab 备份
crontab -l > /mnt/d/Hermes/备份/upgrade_*/crontab_backup.txt
```
注意：`~/.hermes/config.yaml`、`~/.hermes/scripts/`、`~/.hermes/skills/` 不在 git 仓库内，`git reset --hard` 不会影响它们。只有 `hermes-agent/` 目录内的自定义文件需要手动备份恢复。

## 八、Claude Code `.claude/skills` 模式借鉴

Claude Code 2.1.157 支持 `.claude/skills/` 目录下的插件自动加载:
- 无需marketplace, 本地插件自动识别
- 可包含: slash commands, agents, hooks, MCP servers, skills
- `claude plugin init <name>` 脚手架创建

Hermes skills (`~/.hermes/skills/`) 当前需手动 skill_view() 加载。
可以借鉴自动发现机制 — 在skill目录中增加可执行入口(hooks/scripts/agents)。

## 五、常见问题

### 🔴 对话中切换模型（/model slash command）

`hermes model` 是交互式TUI，**不能**通过子进程调用（报错：`requires an interactive terminal`）。`hermes config set model` 改的是配置文件，**不影响已运行的对话**。

**正确切换方式**：用户在对话中直接输入 `/model deepseek-v4-pro` ——这是hermes内置的模型切换slash command，立即生效。

**Agent侧的正确响应**：当发现当前模型不对时，告知用户用 `/model <模型名>` 切换，**不要说"无法切换"**。

### profile创建后API key错误
新profile没有API key, 需要运行 `hermes -p <name> setup` 配置。
或者在profile目录的.env中设置环境变量。

### gateway无法启动
检查: `journalctl --user -u hermes-gateway-<name>.service --no-pager -n 50`
常见原因: 端口冲突、API key无效、模型名不存在。
特定修复: `hermes -p cron-bot gateway start` 报错 → 检查profile目录是否有正确的config.yaml。

### memory provider切换后旧数据还在吗？
Holographic和内置记忆是独立的。切换后旧的内置记忆还在但不会被新provider读取。
建议先确认Holographic工作正常后再清理内置记忆。

### 是否需要在config.yaml显式设置memory.provider？
是的。`hermes config set memory.provider holographic` 必须在config.yaml中明确设置。

### WSL网关IP连接问题
Ollama跑在Windows上,WSL通过`172.31.32.1:11434`访问。如果连接失败:
1. Win侧: 确认Ollama已启动 (`localhost:11434`)
2. WSL侧: `curl http://172.31.32.1:11434/api/tags` 验证连通
3. 防火墙: 确认Windows防火墙没有阻止WSL入站
