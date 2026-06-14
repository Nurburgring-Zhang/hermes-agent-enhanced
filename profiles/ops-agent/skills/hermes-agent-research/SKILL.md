---
name: hermes-agent-research
description: Hermes Agent (NousResearch) 架构研究笔记 - 学习自 github.com/NousResearch/hermes-agent
category: research
version: 1.0
---

# Hermes Agent (NousResearch) 架构研究报告

## 来源

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

- GitHub: https://github.com/NousResearch/hermes-agent
- 86.3k stars, 11.7k forks, 4198 commits
- 活跃开发: 38分钟前有最新commit

---

## 核心架构

### 项目结构
```
hermes-agent/
├── run_agent.py          # AIAgent class — 核心对话循环
├── model_tools.py        # 工具编排 + discover_builtin_tools()
├── toolsets.py           # 工具集定义 _HERMES_CORE_TOOLS
├── hermes_state.py       # SessionDB — SQLite FTS5会话搜索
├── cli.py                # HermesCLI — 交互式CLI编排
├── agent/
│   ├── prompt_builder.py    # 系统提示词组装
│   ├── context_compressor.py # 自动上下文压缩
│   ├── prompt_caching.py    # Anthropic提示缓存
│   ├── auxiliary_client.py  # 辅助LLM客户端
│   ├── model_metadata.py    # 模型上下文长度
│   └── trajectory.py        # 轨迹保存
├── tools/
│   ├── registry.py       # 中心化工具注册表
│   ├── approval.py        # 危险命令检测
│   ├── terminal_tool.py   # 终端编排
│   ├── file_tools.py      # 文件操作
│   ├── web_tools.py       # Web搜索/提取
│   ├── browser_tool.py    # Browserbase自动化
│   ├── code_execution_tool.py  # execute_code沙箱
│   ├── delegate_tool.py   # 子Agent委托
│   └── mcp_tool.py        # MCP客户端(~1050行)
├── hermes_cli/
│   ├── commands.py        # 中心化命令注册表
│   ├── skills_config.py   # 技能配置
│   ├── skills_hub.py      # 技能中心
│   └── models.py          # 模型目录
├── gateway/
│   ├── platforms/         # Telegram, Discord, Slack, WhatsApp, Signal
│   └── run.py             # 网关主循环
├── cron/                  # 调度器
├── skills/                # 技能目录(~50+技能)
└── tests/                 # ~3000测试
```

---

## AIAgent Class 核心循环

```python
class AIAgent:
    def chat(self, message: str) -> str:
        """简单接口 — 返回最终响应字符串"""
    
    def run_conversation(self, user_message, system_message, 
                         conversation_history, task_id) -> dict:
        """完整接口 — 返回dict含final_response + messages"""
```

**Agent循环** (完全同步):
```python
while api_call_count < self.max_iterations:
    response = client.chat.completions.create(
        model=model, messages=messages, tools=tool_schemas
    )
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = handle_function_call(tool_call.name, tool_call.args, task_id)
            messages.append(tool_result_message(result))
        api_call_count += 1
    else:
        return response.content
```

---

## 工具注册表系统

### 中心化注册表 (tools/registry.py)
- 所有工具在导入时通过 `registry.register()` 注册
- 提供schema + handler + dispatch

### _HERMES_CORE_TOOLS (toolsets.py)
```python
_HERMES_CORE_TOOLS = [
    # Web
    "web_search", "web_extract",
    # Terminal
    "terminal", "process",
    # File
    "read_file", "write_file", "patch", "search_files",
    # Vision
    "vision_analyze", "image_generate",
    # Skills
    "skills_list", "skill_view", "skill_manage",
    # Browser
    "browser_navigate", "browser_snapshot", "browser_click",
    "browser_type", "browser_scroll", "browser_vision", ...
    # Planning
    "todo", "memory", "session_search", "clarify",
    # Code
    "execute_code", "delegate_task",
    # Cron
    "cronjob",
    # Messaging
    "send_message",
    # Home Assistant
    "ha_list_entities", "ha_get_state", "ha_list_services", "ha_call_service",
]
```

### 工具集组合 (TOOLSETS)
```python
TOOLSETS = {
    "web": {"tools": ["web_search", "web_extract"], "includes": []},
    "browser": {"tools": ["browser_navigate", ...], "includes": []},
    "file": {"tools": ["read_file", "write_file", "patch", "search_files"], "includes": []},
    "skills": {"tools": ["skills_list", "skill_view", "skill_manage"], "includes": []},
    "code_execution": {"tools": ["execute_code"], "includes": []},
    "delegation": {"tools": ["delegate_task"], "includes": []},
    "hermes-acp": {...},  # 编辑器集成
    "hermes-api-server": {...},  # OpenAI兼容API
}
```

---

## 子Agent委托系统 (delegate_tool.py)

### 关键参数
- `max_concurrent_children`: 默认3
- `max_depth`: 2级 (禁止递归)
- `default_toolsets`: ["terminal", "file", "web"]

### 被阻止的工具 (子Agent不可用)
```python
DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",   # 禁止递归委托
    "clarify",         # 禁止用户交互
    "memory",          # 禁止写入共享内存
    "send_message",     # 禁止跨平台副作用
    "execute_code",     # 子Agent应逐步推理
])
```

### 进度回调
- CLI: 树形视图显示子Agent进度
- Gateway: 批量工具名中继到父Agent

---

## Skills 系统

### 目录结构
```
~/.hermes/skills/
├── <skill-name>/
│   ├── SKILL.md        # 主指令(必需)
│   ├── references/     # 支持文档
│   ├── templates/      # 输出模板
│   └── assets/         # 辅助文件
```

### SKILL.md 格式 (YAML Frontmatter)
```yaml
---
name: skill-name        # 必需, max 64 chars
description: 简短描述   # 必需, max 1024 chars
version: 1.0.0          # 可选
license: MIT            # 可选
platforms: [macos]      # 可选 — macos/linux/windows
prerequisites:           # 可选
  env_vars: [API_KEY]
  commands: [curl, jq]
compatibility: Requires X  # 可选
metadata:                # 可选
  hermes:
    tags: [fine-tuning, llm]
  related_skills: [peft, lora]
---

# 技能标题
完整指令内容...
```

### 渐进式披露
1. `skills_list`: 仅列出元数据(节省token)
2. `skill_view`: 加载完整指令
3. `skill_view(name, file_path)`: 按需加载引用文件

### 技能配置
- 可全局启用/禁用
- 可按平台配置 (telegram/cli/discord等)

---

## 内存与记忆系统

### SessionDB (hermes_state.py)
- SQLite + FTS5全文搜索
- 跨会话召回

### Honcho 用户建模
- dialectic user modeling
- 兼容 agentskills.io 开放标准

### 记忆类型
- **MEMORY.md**: 持久化个人笔记
- **USER.md**: 用户画像
- **session_search**: 搜索历史会话

---

## 消息网关 (Messaging Gateway)

### 支持平台
- Telegram, Discord, Slack, WhatsApp, Signal, Email
- Home Assistant, QQBot

### 统一命令
所有平台共享相同的slash命令接口

---

## Cron 调度系统

### 特性
- 内置cron调度器
- 支持向任意平台投递
- 自然语言任务定义
- 无人值守运行

### 投递平台
origin, local, telegram, discord, slack, whatsapp, signal, matrix, mattermost, homeassistant, dingtalk, feishu, wecom, email, sms

---

## MCP 集成

### MCP客户端 (tools/mcp_tool.py, ~1050行)
- 连接任意MCP服务器
- 自动工具发现
- 支持stdio和HTTP传输

---

## 安全机制

### 命令审批
- 危险命令检测 (approval.py)
- DM配对验证
- 容器隔离 (Docker/Singularity)

### 提示注入检测
```python
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "you are now",
    "disregard your",
    ...
]
```

---

## OURS vs Hermes Agent (NousResearch)

| 特性 | 我们的Hermes | Hermes Agent (NousResearch) |
|------|-------------|---------------------------|
| 架构 | Multi-Agent集群 | AIAgent单类 + 工具集 |
| 工具系统 | 散落各处 | 中心注册表 |
| Skills | 散落 | 标准化YAML + 渐进披露 |
| 内存 | MEMORY.md | FTS5 + Honcho |
| 子Agent | delegate_task | 完整隔离 + 进度回调 |
| MCP | 基础 | ~1050行完整客户端 |
| 消息网关 | 无 | 10+平台 |
| Cron | 基础 | 完整 + 平台投递 |

---

## 增强建议

### 高优先级
1. [ ] 中心化工具注册表 (参考tools/registry.py)
2. [ ] Skills采用YAML frontmatter标准
3. [ ] FTS5会话搜索
4. [ ] MCP客户端增强
5. [ ] 子Agent进度回调

### 中优先级
6. [ ] 消息网关集成 (Telegram/Discord)
7. [ ] 命令审批系统
8. [ ] 提示注入检测
9. [ ] 上下文压缩

### 低优先级
10. [ ] Skin/Theme引擎
11. [ ] 轨迹压缩研究
12. [ ] 批量轨迹生成

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
