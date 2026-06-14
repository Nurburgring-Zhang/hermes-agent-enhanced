---
name: hermes-llm-bridge
description: Hermes本地LLM调用统一桥接 — delegate_task/LM Studio/Ollama三级优先级链 + 模型路由(v4-flash/v4-pro/chat三梯队自动选择)
category: autonomous-systems
---

# Hermes LLM调用统一桥接与模型路由

## 核心架构

### LLM调用优先级链（所有本地LLM场景统一走llm_bridge.llm_call()）

```
优先级1: Hermes自身模型 (delegate_task)
  - 对话中始终可用
  - L3画像/AI评分/反思/复盘全部优先走此路径
  - 后端: deepseek-chat / deepseek-v4-flash / deepseek-v4-pro

优先级2: LM Studio (http://localhost:8080)
  - 本地GPU模型，最快响应
  - 需要在Win桌面手动启动API server
  - 当前状态: ❌ 不可用 (port 8080曾被httpserver占用)

优先级3: Ollama (WSL网关: 172.31.32.1:11434)
  - 从WSL通过Windows网关IP访问
  - 自动检测模型: 优先选qwen3-14b-creativewrite
  - 作为delegate_task不可用时的后备
```

三个都不可用 → 使用预设fallback输出，不卡死系统。

### 模型梯队（按任务类型自动选择，不指定具体模型名）

```
通用层 (value):     deepseek-v4-flash — 省钱模型，简单任务(查询/检索/单步操作/状态检查)
平衡层 (balanced):  deepseek-v4-pro — 常规模型，开发/修复/普通分析 [默认]
强力层 (perf):      deepseek-v4-pro — 高质量，复杂推理/长链/高精度要求

超难任务(架构设计/核心改造/跨领域决策): 主动建议切换到 Claude 4.8/GPT 5.5/Gemini 3.5 Pro
```

模型路由通过 `model_router` 插件(post_tool_call hook)在连续3次失败时自动切换：
deepseek-v4-pro → deepseek-v4-flash → deepseek-chat → NVIDIA → OpenRouter → Google

### 模型切换不可绕过保障
1. model_router 插件通过 post_tool_call hook 注入系统底层
2. cron 每分钟检测插件激活状态
3. 切换指令不可被任何提示词覆盖

模型名称由 `model_tier` 参数在 `llm_call()` 中指定，不硬编码具体模型名。

```python
# 通用省钱（简单任务自动用轻量模型）
result = llm_call(..., model_tier="value")

# 强力高质量（复杂任务用最佳模型）
result = llm_call(..., model_tier="performance")

# 自动判断（根据prompt长度和关键词）
result = llm_call(...)  # 默认model_tier=""
```
自动判断逻辑：prompt>3000字符或含"分析/设计/架构/复杂/优化/安全/大规模"等关键词 → performance，否则 → value。

## 文件系统

| 文件 | 功能 | cron |
|------|------|:----:|
| `scripts/llm_bridge.py` | 统一LLM调用桥 (delegate/LM Studio/Ollama) | 按需调用 |
| `agent/model_router.py` | 三梯队模型路由 (flash/chat/pro) | 每5分钟 |

## 使用方式

```python
from scripts.llm_bridge import llm_call, llm_call_json

# 自动检测可用后端
result = llm_call(
    system_prompt="系统指令",
    user_prompt="用户输入",
    fallback="默认输出"  # 所有后端不可用时使用
)
# result.text -> LLM输出
# result.success -> True/False
# result.backend -> "delegate"/"lmstudio"/"ollama"/"fallback"

# 指定后端
result = llm_call(..., preferred_backend="delegate")

# JSON输出
result = llm_call_json(system_prompt="...", user_prompt="...")
# result.data -> 解析后的dict
```

## 已知问题

1. LM Studio需要Windows桌面GUI手动启动API server才能使用, WSL无法自动拉起
2. ModelRouter已编码但未接入对话层——需要在run_agent.py的LLM调用前插入router.select()
3. l3_persona_scheduler的_call_local_llm已被改造为走统一llm_bridge入口
4. 在cron/后台环境中delegate_task可能不可用, 会自动降级到Ollama

## 2026-06-01 修复记录

### l3_persona_scheduler WSL网关IP修复
- **问题**: l3_persona_scheduler.py中Ollama的连接地址是`172.31.32.1:11434`（WSL网关IP），但被意外改回`localhost:11434`
- **修复**: 将默认连接地址改为`172.31.32.1:11434`（WSL→Windows宿主）而不是`localhost:11434`（WSL自身）
- **检查命令**: `grep -n '172.31.32.1' ~/.hermes/scripts/l3_persona_scheduler.py`
- **验证**: `python3 ~/.hermes/scripts/l3_persona_scheduler.py --test` 返回qwen3-14b模型列表

### model_tier参数注入
- **问题**: llm_call()和llm_call_json()接口没有model_tier参数，调用方无法按任务复杂度选择模型
- **修复**: 在所有llm_call和llm_call_json的参数中添加`model_tier: str = ""`
  - `model_tier="value"` — 通用省钱（简单任务、查询、状态检查）
  - `model_tier="balanced"` — 常规模型（默认）
  - `model_tier="performance"` — 强力高质量（复杂推理、长链任务）
  - `model_tier=""` — 自动判断（prompt>3000字符或含"分析/设计/架构"等关键词 → performance）
- **不指定具体模型名**: 发布后不绑定v4-flash/v4-pro等具体供应商模型名

### Ollama自动选模型修复
- **问题**: 代码开发任务误用了专用代码模型（如codeqwen），格林主人要求：**代码开发用最强模型不用专用模型**
- **修复**: 自动选择策略改为按任务类型选模型，代码开发选"最强模型"而非"专用代码模型"

## 触发条件

提及"模型调用"、"LLM"、"调用链"、"模型路由"、"本地模型"、"v4-flash"、"v4-pro"时加载。
