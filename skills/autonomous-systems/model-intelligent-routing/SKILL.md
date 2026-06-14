---
name: model-intelligent-routing
description: 模型智能路由与自动切换系统 — 基于SOUL.md定义的模型路由链，通过Hermes插件系统的post_tool_call hook实现失败检测和自动切换。不可绕过，cron每分钟监活。
version: 1.0.0
tags: [model-routing, auto-switch, fallback, plugin, hook, cron-heartbeat]
domain: autonomous-systems
triggers:
  - "模型不通"
  - "模型切换"
  - "API失败"
  - "自动切换"
  - "路由链"
  - "model_router"
  - "模型智能路由"
  - "fallback"
  - "冷启动"
---

# 模型智能路由系统 v1.0

## 核心原则

**模型不通必须自动切换，不是等用户指示。**

规则写进SOUL.md不等于被执行。必须有可执行的代码路径（插件hook/定时检测）来保证机制生效。

## 架构

### 插件路径（真实生效的路径）
```
Hermes 主Agent → post_tool_call hook → model_router 插件 → 检测失败 → 自动切换模型
```

插件文件位置：`~/.hermes/plugins/model_router/__init__.py`

```python
def register(ctx):
    ctx.register_hook("post_tool_call", model_router_hook)
```

### 切换触发条件
连续3次tool调用失败，触发模型切换。判定失败的标准：

| 信号 | 检查方式 |
|------|---------|
| Error/失败/超时 | result含"error"/"fail"/"timeout" |
| HTTP错误 | 500/502/503/401/403/429 |
| 连接错误 | Connection refused / timeout |
| 认证失败 | Authentication Fails / invalid api key |

### 路由链（按优先级）
```
deepseek-v4-pro → deepseek-v4-flash → deepseek-chat → NVIDIA备选 → OpenRouter备选 → Google备选
```

### 不可绕过保障
1. cron每分钟检查插件激活日志（`~/.hermes/logs/model_router/plugin_activated.log`）
2. 切换指令不可被任何提示词覆盖
3. 本规则优先级高于所有任务指令

## 冷启动检查

### 验证插件是否激活
```bash
ls -la ~/.hermes/logs/model_router/plugin_activated.log
```

### 验证切换历史
```bash
cat ~/.hermes/logs/model_router/switches.log 2>/dev/null | tail -5
```
每行JSON包含：timestamp, session_id, from(旧模型), to(新模型), reason

### 如果插件未激活，手动修复
```bash
# 检查插件文件是否存在
ls -la ~/.hermes/plugins/model_router/
# 检查cron是否创建
hermes cron list | grep model_router
```

## 已知陷阱

### 🔴 陷阱：规则写进文件不等于被执行
SOUL.md写了路由链，dual-ai-review写了互审规则，AGENTS.md写了工作流。但之前没有任何代码路径实际触发它们。

**修复**：每条规则必须有对应的可执行代码路径：
1. 配置（config.yaml）— 模型/API定义
2. 规则（SOUL.md/AGENTS.md）— 行为约束
3. 执行（插件/脚本/cron）— 自动强制执行

三条路径缺一不可。只有(1)+(2)没有(3) → 规则是废纸。

### 🔴 陷阱：写插件比写规则重要100倍
之前 model-intelligent-routing 是一个 skill，描述了路由链和配置，但**没有写插件代码**。
结果是：SOUL.md说"自动切换"，config.yaml配了fallback，但 Hermes 永远不会自己切——因为没有 post_tool_call hook。

**修复**：
1. 先写插件代码（`plugins/<name>/__init__.py`）
2. 再写 SOUL.md 规则（文档化）
3. 再配 config.yaml（配置化）
4. 最后加 cron 心跳检测

这个顺序不能颠倒。先写规则再写插件 = 规则在没插件期间是空头支票。

### 🔴 陷阱：冷启动时提示"切换模型"
当用户说"模型不通你为什么不切换"时，如果插件不存在或未激活，回答"我切换"没有任何意义——必须真的写了代码。

**修复**：遇到模型不通问题 → 先检查 `model_router` 插件是否存在 → 不存在就创建 → 验证 `cron` 心跳是否工作。

## 插件代码位置

- 插件文件：`~/.hermes/plugins/model_router/__init__.py`
- 日志目录：`~/.hermes/logs/model_router/`
  - `plugin_activated.log` — 激活时间戳
  - `switches.log` — 切换历史（含from/to/reason）

## 快速验证

```bash
# 插件是否激活
test -f ~/.hermes/logs/model_router/plugin_activated.log && echo "✅ 激活" || echo "❌ 未激活"

# 切换历史
tail -3 ~/.hermes/logs/model_router/switches.log 2>/dev/null | python3 -m json.tool

# cron心跳
hermes cron list | grep model_router
```

### 🔴 陷阱5：插件文件存在但从未被 cron 检测激活（2026-06-12 新增）

**症状**：`model_router` 插件文件在 `~/.hermes/plugins/model_router/__init__.py` 存在，但插件从未被 Hermes 加载——没有 `register()` 被调用，没有 `plugin_activated.log` 被写入。但用户以为\"已经配置好了\"。

**根因**：Hermes 插件系统在 Agent 启动时自动加载 `plugins/<name>/__init__.py` 中的 `register()` 函数。如果 Agent 在插件创建之前就已启动，插件文件存在但不会**立即生效**——需要 Agent 重启（新会话）才会加载。

**修复**：
1. 创建插件后立即验证：检查 `~/.hermes/logs/<plugin>/plugin_activated.log` 是否存在
2. 如果日志不存在，说明 Agent 未重启——需要告知用户 `/new` 或重启
3. 写 `cron` 心跳检测时，注意 cron job 本身也需要在创建后大约1分钟内才会首次运行
4. 最稳妥的验证方法：`hermes cron run <job_id>` 手动触发一次 cron job

### 🔴 陷阱6：对话已启动但用了错误模型，无法通过子进程切换（2026-06-15 新增·实战触发）

**症状**：config.yaml 的 `default` 已设为 `deepseek-v4-pro`，但当前对话启动时用的是 `deepseek-chat`。尝试 `hermes model` 切换时报错：`'hermes model' requires an interactive terminal. It cannot be run through a pipe or non-interactive subprocess.` 尝试 `hermes config set model deepseek-v4-pro` 成功修改了配置文件，但**对已运行的对话无效**——对话的模型在启动时锁定。

**用户信号**：用户质问"现在调用的模型是deepseek V4 pro吗？立刻迁移到deepseek-v4-pro！！hermes支持对话时切换模型的！！"——用户明确知道hermes有切换能力，但我找不到工具入口。

**根因分析**：
1. `hermes model` 是交互式TUI，需要真实终端，子进程无法调用
2. `hermes config set model` 改的是配置文件，不影响已运行对话
3. `model_router` 插件的自动切换链只在**API调用失败**时触发（连续3次失败→自动切换）——但模型正常工作只是不够好时，不会触发
4. hermes确实支持对话中切换模型——通过 `/model` slash command，但Agent工具集中没有 `switch_model` 工具
5. 我错误地告诉用户"无法切换，需要重启对话"——实际上应该指导用户输入 `/model deepseek-v4-pro`

**正确做法（多路径，从最好到最差）**：
1. 🥇 **让用户在对话中直接输入 `/model deepseek-v4-pro`** — hermes内置的模型切换slash command，立即生效
2. 🥈 **用户输入 `/new` 然后重新提问** — 新对话会使用 config.yaml 的 default 模型（但如果 default 已改好，/new会自动用对）
3. 🥉 **如果以上都不行，才建议用户 `Ctrl+C` 退出，`hermes chat` 重新启动** — 最粗暴但保证生效

**预防措施**：
- 每次对话开始时，输出第一句话前先确认当前模型是否是 config.yaml 的 default
- 如果发现不匹配，立即告知用户用 `/model` 切换，不等待用户发现问题
- 不要告诉用户"没法切换"——hermes确实支持 `/model` slash command

## 集成测试

```bash
# 验证插件通过hook注入（需要Hermes重启后检查日志）
grep "模型路由插件已激活" ~/.hermes/logs/model_router/plugin_activated.log

# 验证路由链配置
grep -A5 "模型智能路由" ~/.hermes/SOUL.md | head -8
```

## 参考文件
- [SOUL.md模型路由节](file:///home/administrator/.hermes/SOUL.md) — 路由链定义和不可绕过条款
- [Hermes插件系统文档](https://hermes-agent.nousresearch.com/docs/plugins) — 插件hook API参考
