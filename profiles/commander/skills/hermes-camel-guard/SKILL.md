---
name: hermes-camel-guard
description: CaMeL信任边界安全护栏 — 信任分离(可信控制vs不可信数据)、16个敏感工具9类能力分类、5种注入模式检测、工具循环防护(重复失败/同工具链式/幂等无进展)、三级响应(allow/warn/block/halt)、三级运行模式(off/monitor/enforce)。基于hermes-agent-camel(nativ3ai)源码移植。
version: 1.0.0
author: Hermes Agent
domain: security
tags: [camel, trust-boundary, security, guardrails, injection-detection, tool-loop-protection]
triggers:
  - "安全护栏"
  - "CaMeL"
  - "camel guard"
  - "注入检测"
  - "工具循环防护"
  - "敏感工具"
  - "信任边界"
  - "prompt injection"
  - "guardrails"
  - "tool_guardrails"
  - "camel_guard"
  - "--camel-guard"
  - "hermes_camel_guard"
---
# Hermes CaMeL 安全护栏引擎

## Overview

基于 hermes-agent-camel (nativ3ai/hermes-agent-camel) 的 camel_guard.py(964行) + tool_guardrails.py(455行) 源码移植。在Agent与生产环境之间构建信任边界安全锁。

**底层能力声明**: CaMeL安全护栏是Hermes的安全底层能力，所有敏感工具调用全部覆盖。规则已固化到AGENTS.md（格林主人最高指令 2026-05-31固化）。可选启用，默认monitor模式。

## 核心机制（6层）

### 1. 信任边界分离

将消息分为两类：
- **可信控制输入** — 系统提示、已批准Skill、用户指令（可信任）
- **不可信数据输入** — 工具输出、外部检索上下文、外部返回数据（不可信）

不可信数据添加 `[CaMeL: UNTRUSTED TOOL DATA]` 前缀，与可信控制分开处理。

### 2. 16个敏感工具 → 9类能力

| 能力类别 | 工具列表 | 风险 |
|---------|---------|------|
| `command_execution` | terminal, execute_code | 🔴 高 |
| `file_mutation` | write_file, patch | 🔴 高 |
| `skill_mutation` | skill_manage | 🔴 高 |
| `browser_interaction` | browser_click/press/type/navigate/scroll | 🟡 中 |
| `external_messaging` | send_message | 🟡 中 |
| `persistent_memory` | memory | 🟡 中 |
| `scheduled_action` | cronjob | 🟡 中 |
| `delegation` | delegate_task | 🟡 中 |
| `external_side_effect` | process_kill, process_write | 🟡 中 |

**可信工具白名单**（不拦截）：clarify, skill_view, skills_list, todo, read_file, search_files, session_search, memory(read-only), web_search, vision_analyze

### 3. 5种注入模式检测

| 模式 | 正则 | 说明 |
|------|------|------|
| 忽略已发指令 | `ignore (previous\|all\|above\|prior) instructions` | Agent被要求忽略原有指令 |
| 对用户隐藏 | `do not tell the user` | Agent被要求隐瞒行为 |
| 秘密提取 | `(reveal\|show\|print\|dump).*(system prompt\|api key\|token\|secret\|credential)` | 窃取系统提示/凭据 |
| 系统提示覆盖 | `system prompt override` | 覆盖系统提示 |
| 嵌入副作用 | `send_message\|tweet\|email\|dm\|post this` | 嵌入对外操作指令 |

### 4. 输出指令劫持检测

检测Agent输出中是否包含被外部数据注入的指令（如 `begin your reply with:`, `respond with:`, `output exactly:` 等）。

### 5. 工具循环防护

基于 `tool_guardrails.py` 的三类检测：

| 检测类型 | 触发条件 | 阈值(warn) | 阈值(halt) |
|---------|---------|-----------|-----------|
| `exact_failure` | 相同工具+相同参数连续失败 | 2次 | 5次 |
| `same_tool_failure` | 同工具不同参数连续失败 | 3次 | 8次 |
| `no_progress` | 幂等工具返回相同结果 | 2次 | 5次 |

每次返回 `ToolGuardrailDecision(allow/warn/block/halt)`。

### 6. 三级运行模式

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `off` | 完全关闭，不拦截任何调用 | 调试/开发环境 |
| `monitor` | 记录日志但不阻止（默认） | 生产环境渐进式部署 |
| `enforce` | 记录+阻止所有未授权调用 | 高安全要求场景 |

## 工具命令

```bash
# 检查消息安全性
python3 scripts/hermes_camel_guard.py check --message "用户指令" --mode enforce

# 检查工具调用权限
python3 scripts/hermes_camel_guard.py check-tool --tool terminal --args '{"command":"rm -rf /"}' --mode enforce

# 显示状态和能力映射
python3 scripts/hermes_camel_guard.py status

# 执行monitor模式安全检查
python3 scripts/hermes_camel_guard.py monitor
```

## 配置方式

通过 `--camel-guard` CLI 参数或在 `~/.hermes/config.yaml` 中配置：
```yaml
camel_guard:
  mode: monitor  # off | monitor | enforce
  log_file: logs/camel_guard.log
```

## 与其他安全的互动

CaMeL与 `security-permissions-system` 是互补关系：
- `security-permissions-system` = RBAC权限+审批工作流+凭据管理+沙箱（主动安全控制）
- `hermes-camel-guard` = 信任边界+注入检测+工具循环防护（被动安全防御）

两者结合形成 Hermes 安全防御体系的"主动+被动"双保险。

## 集成方式

### production_loop（自动集成）

`production_loop_cron.py` 已集成CaMeL安全检查，每10分钟自动运行：
- **check模式(每10分钟)**: 读取CaMeL日志 → 统计注入事件 → 追踪敏感工具调用
- **critic模式(每30分钟)**: CaMeL趋势分析 → 安全事件聚合
- **deep_check模式(每2小时)**: 验证CaMeL脚本和日志文件完整性

审计快照包含CaMeL信息：
```json
{
  "camel_guard": {
    "injection_events": 0,
    "sensitive_tools_called": [],
    "status": "safe"
  }
}
```

### 代码集成

CaMeL是可选的轻量级模块（单文件~500行），通过monkey-patch或config.yaml启用，不干扰现有系统运行：

```python
from scripts.hermes_camel_guard import CamelGuard

guard = CamelGuard(mode="monitor")

# 在每次工具调用前检查
if guard.is_active():
    decision = guard.check_tool_call(tool_name, args)
    if not decision["allowed"]:
        return {"error": decision["message"]}

# 在每次工具调用后记录
guard.check_tool_result(tool_name, args, result_text, failed=is_error)
```

## 实战陷阱（2026-05-30发现）

### 1. 注入检测的False Positive风险
当前5种注入检测模式是基于nativ3ai/camel_guard.py的正则表达式。在中文语境下，某些正常指令可能触发"嵌入副作用指令"检测。如果发现误报，应调整 `SUSPICIOUS_PATTERNS` 列表而非关闭整个系统。

### 2. enforce模式的破窗效应
enforce模式会阻止所有未授权的敏感工具调用。但如果在日常工作中大量使用 `send_message`、`cronjob` 等工具，enforce模式会导致频繁阻塞。建议初始使用monitor模式，逐步收紧。

### 3. 工具名映射完整性
`SENSITIVE_TOOL_CAPABILITIES` 字典需要与Hermes的实际工具名保持一致。如果有自定义工具或新工具未在字典中列出，它们会被视为非敏感工具而放行。monitor模式下应定期检查日志确认覆盖完整性。

## 数据存储

- 日志文件: `logs/camel_guard.log`
- 日志格式: 每行JSON `{"ts":"...","type":"tool_blocked","tool":"terminal","mode":"enforce",...}`
- 日志可被复盘引擎消费，用于分析安全事件趋势

## 关联技能

- `security-permissions-system` — RBAC权限控制+审批工作流，与CaMeL互补
- `task-retrospect` — 复盘引擎可消费CaMeL安全日志，将安全事件纳入质量评估
- `production-reliability-engine` — 生产级可靠性引擎中的降级检测与CaMeL的工具循环防护重叠
- `fde-sop-methodology` — FDE的Step 5(Deploy)和Step 6(Validation)应包含CaMeL安全检查

## 参考文件

- `references/camel-architecture.md` — CaMeL信任边界架构详解（来自nativ3ai/hermes-agent-camel源码分析）
- `references/injection-patterns.md` — 5种注入模式的详细检测规则和规避策略

## 回滚方案

1. 关闭CaMeL: 设置 `mode=off` 或在config.yaml中移除 `camel_guard:` 段落
2. 删除日志: `rm ~/.hermes/logs/camel_guard.log`
3. 从AGENTS.md中移除CaMeL安全护栏规则段落
4. 删除脚本: `rm ~/.hermes/scripts/hermes_camel_guard.py`
