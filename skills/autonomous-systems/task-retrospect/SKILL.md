---
name: task-retrospect
description: Hermes 任务复盘反思引擎 — 每次任务完成后自动进行结构化复盘，五维度质量评估，经验提取，驱动Skill进化。底层能力，所有对话/任务全部通用，完全自动执行、强制执行。
version: 1.1.0
author: Hermes Agent
domain: autonomous-systems
tags: [retrospect, reflection, quality, task-evaluation, self-improvement]
triggers:
  - "复盘"
  - "retrospect"
  - "任务反思"
  - "质量评估"
  - "任务审查"
  - "质量墙"
  - "执行质量"
  - "任务复盘"
  - "经验提取"
  - "进化候选"
---

# Hermes 任务复盘反思引擎

## Overview

基于 Reflexion + Self-Refine + CRITIC + 软件工程回顾会议方法论构建。每次任务完成后自动执行结构化复盘，从"目标回顾→过程回溯→质量评估→经验提取→知识固化"形成完整闭环。

**底层能力声明**: 复盘是Hermes的底层能力，所有对话、所有任务全部通用，完全自动执行、强制执行。规则已固化到AGENTS.md（格林主人最高指令 2026-05-31固化）。

## 复盘流程（5步）

### Step 1: 目标回顾
对比原始任务目标和实际完成，识别差距。

### Step 2: 过程回溯
回溯每一步执行情况、遇到的阻力和错误。

### Step 3: 质量评估（五维度）
| 维度 | 权重 | 说明 |
|------|------|------|
| 功能性 | 25% | 功能是否完整实现 |
| 正确性 | 25% | 结果是否经验证 |
| 完整性 | 20% | 是否覆盖边界情况 |
| 质量 | 15% | 是否符合最佳实践 |
| 可维护性 | 15% | 是否清晰可读 |

### Step 4: 经验提取
提取可复用的模式、教训、改进建议。

### Step 5: 知识固化
输出复盘报告 + 触发Skill改进 + 写入记忆。

## 三层反思结构化规则

任务执行中必须进行结构化反思，按三层递进（规则已固化到AGENTS.md，格林主人最高指令 2026-05-31固化）：

### 操作层（每步后）
这一步做得对不对？结果是否符合预期？需要修正吗？

### 策略层（每3步后）
当前策略是否仍然有效？是否需要换方法？消耗是否正常？

### 目标层（每10步后）
整体方向是否正确？是否需要重新规划？原始目标是否还成立？

## 执行质量墙

每次任务过程中必须插入强制检查点（规则已固化到AGENTS.md）：

1. **每步检查** — 每完成一个子任务，验证输出是否符合预期
2. **里程碑检查** — 每3个子任务，检查整体方向是否正确
3. **方向对齐** — 任务中途检查是否偏离原始目标（复杂任务必做）

## 复盘→Skill进化管道

复盘反思引擎与SkillOpt验证门形成闭环：

```
执行任务 → hermes_retrospect.py复盘 → 五维评分
                                     ├─ 评分<60 → 写入retro_candidates.jsonl
                                     ├─ 保存到state.db retrospectives表
                                     └─ 报告到reports/retrospectives/

每天03:00自进化集群 → consume_retro_candidates() → 输出改进模式
每天22:00 cron → hermes_retrospect.py --daily-summary → 趋势分析
```

## 核心工具

### 复盘引擎（单次复盘）
```bash
python3 scripts/hermes_retrospect.py --session <session_id>
```

### 中断恢复复盘
```bash
python3 scripts/hermes_retrospect.py --from-wake
```

### 每日汇总
```bash
python3 scripts/hermes_retrospect.py --daily-summary
```

### 检查进化候选队列
```bash
python3 scripts/hermes_retrospect.py --check-evolution
```

### 内联调用（供其他模块集成）
```python
from scripts.hermes_retrospect import inline_retrospect, inline_after_task

# 任务完成后直接复盘
inline_after_task({
    "task_id": "xxx",
    "title": "任务描述",
    "steps": [...],
    "started_at": "...",
})
```

## 作业调度

| 触发时机 | 动作 | 实现 |
|----------|------|------|
| 每次任务完成 | 自动触发复盘 → 评分 → 写入DB + 候选队列 | `inline_after_task()` 或 `hermes_retrospect.run()` |
| 任务中断后恢复 | 中断复盘 → 记录原因 → 提示改进 | `hermes_retrospect.py --from-wake` |
| **Dynamic Workflows完成** | **自动触发复盘 → 提取到Hy-Memory** | **`workflows/retrospect_integration.py` → Runtime的finally块** |
| 每天22:00 | 每日汇总 → 当天所有复盘趋势分析 | cron: `0 22 * * *` |
| 每天03:00 | 消费复盘候选 → 输出改进模式 | `hermes_self_evolve_cluster.py` 模块6 |
| 评分<60 | 自动写入进化候选队列 | `retro_candidates.jsonl` |

## 数据存储

### state.db retrospectives 表
```sql
CREATE TABLE IF NOT EXISTS retrospectives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    session_title TEXT,
    total_score REAL,
    quality_level TEXT,
    error_rate REAL,
    tools_used TEXT,
    root_causes TEXT,
    improvements TEXT,
    retro_json TEXT,
    created_at TEXT
);
```

### 复盘报告文件
- 单次复盘：`reports/retrospectives/retro_<日期>_<id>.json`
- 日常汇总：`reports/retrospectives/daily_summary_<日期>.json`

### 进化候选队列
- 文件：`data/retro_candidates.jsonl`
- 格式：每行JSON `{"source":"retrospect","score":55,"improvements":[...], ...}`
- 消费方：`hermes_self_evolve_cluster.py` 模块6

## 关联技能

- `dual-ai-review` — 双AI互审系统，复盘报告必须接受互审验证
- `hermes-skill-evolver` — 证据驱动Skill进化引擎，复盘低分候选的消费方
- `production-reliability-engine` — 生产级可靠性，复盘是质量墙的执行层
- `fde-sop-methodology` — FDE 8步SOP的Step 6(Validation)和Step 8(Evolution)依赖复盘
- `writing-plans` — 规划模板中的验收清单与复盘的质量评估维度对齐
- `self-evolution-executor` — 自进化执行器消费复盘候选队列
- `hermes-self-enhancement` — 自我强化增强需要复盘输出作为输入
- `hermes-camel-guard` — CaMeL安全日志可作为复盘证据源，注入事件应纳入质量评估的安全维度
- `hermes-auto-tune` — 复盘平均评分是自动调优的主要决策依据

## 技术实现

文件: `scripts/hermes_retrospect.py` (654行)

核心类: `HermesRetrospect`
- `load_session(session_id)` — 从state.db加载会话（支持sessions+messages双表结构）
- `load_from_existing_data(data)` — 直接从数据加载
- `extract_tools_and_steps(messages)` — 从消息提取工具调用步骤
- `assess_quality(steps)` — 五维度质量评估
- `generate_retrospect()` — 生成完整复盘报告
- `save_report()` — 保存文件
- `save_to_db()` — 存入state.db
- `try_invoke_skillopt()` — 触发Skill进化候选
- `should_trigger_skill_evolution()` — 判断是否需要进化
- `run(session_id, session_data)` — 一站式复盘全流程

## 实战陷阱（2026-05-30发现）

### 1. state.db 的表结构陷阱
`state.db`的`sessions`表并无内嵌`messages`字段。消息实际存储在独立的`messages`表中，通过`session_id`关联。
```python
# ❌ 错误：假设sessions表有messages列
c.execute("SELECT messages FROM sessions WHERE id=?", (sid,))

# ✅ 正确：从messages表加载
c.execute("SELECT role, content, tool_calls FROM messages WHERE session_id=? ORDER BY id", (sid,))
```

### 2. tool_calls 字段类型陷阱
`messages`表中的`tool_calls`字段可能是`JSON字符串`或已解析的`Python列表`，取决于写入方式。
```python
# 必须做类型检查
parsed_tcs = tool_calls
if isinstance(tool_calls, str):
    parsed_tcs = json.loads(tool_calls)
# 然后遍历
for tc in parsed_tcs:
    fn = tc.get("function", {}) if isinstance(tc, dict) else {}
```

### 3. 质量评分中的错误率解读
复盘的质量评估使用`error_rate`（工具调用失败步数/总步数），但注意：
- **探索性任务**（如系统诊断、代码审核）天然有高错误率（33-47%），实际是正常的探索成本
- **执行性任务**（如代码生成、数据推送）低错误率（<15%）代表高质量
- **评分阈值**：探索性任务B级（60-80分）就算正常，执行性任务应追求A级（80+分）

## 相关参考文件

- `references/ecosystem-analysis.md` — 4个Hermes生态项目源码深度分析（curator-evolver/SkillClaw/CaMeL/LINE WORKS），可借鉴的核心机制和移植方案
- `references/skill-evolution-patterns.md` — 证据驱动Skill进化的模式总结，来自curator-evolver源码分析和自学能力研究

## 回滚方案

### 复盘引擎回退
1. `git revert HEAD` 
2. 恢复到上一个版本的 `scripts/hermes_retrospect.py`
3. 确认 `state.db` 中 `retrospectives` 表仍可读

### AGENTS.md规则回退
- 移除 `/home/administrator/.hermes/AGENTS.md` 中的 "复盘反思规则"、"执行质量墙规则"、"长期任务执行保障规则" 三个段落
- 恢复 "生产级可靠性引擎" 段落到原来的内容
