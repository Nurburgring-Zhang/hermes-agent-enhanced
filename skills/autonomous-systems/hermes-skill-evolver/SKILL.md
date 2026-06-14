---
name: hermes-skill-evolver
description: 证据驱动Skill进化引擎 — 从复盘和会话证据中自动收集、分类、生成、应用Skill改进。底层能力，全自动执行。
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags: [skill-evolution, evidence-driven, self-improvement, task-retrospect, curator-evolver]
triggers:
  - "Skill进化"
  - "skill evolution"
  - "证据驱动"
  - "复盘→Skill"
  - "进化管道"
  - "skill_evolver"
  - "collect evidence"
  - "classify candidates"
  - "生成提案"
  - "受保护应用"
  - "hermes_skill_evolver"
  - "curator-evolver移植"
---

# Hermes 证据驱动Skill进化引擎

## Overview

基于 hermes-curator-evolver (pingchesu/hermes-curator-evolver) 的核心机制移植 + Hermes复盘反思引擎集成。从任务复盘证据中自动驱动Skill改进。

**底层能力声明**: Skill进化是Hermes的底层能力，所有对话、所有任务全部通用，完全自动执行、强制执行。规则已固化到AGENTS.md（格林主人最高指令 2026-05-31固化）。

## 全流程

```python
证据收集(复盘+候选队列) → 语义分类(skill_update/skill_new/replay/ignore)
    → 变体生成(4种策略) → 评分选优 → 受保护应用(SHA备份→验证→回滚)
    → SkillOpt验证门(分数>80%才接受)
```

## 工具命令

### 一站式全流程
```bash
cd ~/.hermes && python3 scripts/hermes_skill_evolver.py all
```

### 分步执行
```bash
# 收集证据（从复盘状态和候选队列）
python3 scripts/hermes_skill_evolver.py collect

# 分类证据（生成改进候选）
python3 scripts/hermes_skill_evolver.py classify

# 生成+应用改进
python3 scripts/hermes_skill_evolver.py evolve
```

### 在自进化集群中集成
模块7已在 `hermes_self_evolve_cluster.py` 中集成，每天03:00自动运行：
```python
# Phase 7: 证据驱动Skill进化
log_section("🧬 模块7: 证据驱动Skill进化")
evolve_result = skill_evolution_engine()
```

## 架构

```
scripts/hermes_skill_evolver.py
├── class EvidenceCollector  — 从复盘/候选队列收集证据
│   ├── collect_from_retrospectives()     — state.db retrospectives表
│   └── collect_from_candidates()         — retro_candidates.jsonl
├── classify_evidence()     — 规则引擎语义分类（5类）
├── class SkillProposalGenerator — 变体生成+评分选优
│   ├── 4种变体: verify-first / evidence-first / errors-first / minimal-inline
│   └── _score_proposal()  — 确定性评分函数
└── class GuardedApplier   — 受保护应用（SHA备份→写入→验证→回滚）
    ├── sha256_file()       — 写入前SHA256校验
    ├── backup_skill()      — 备份原SKILL.md
    ├── apply_proposal()    — 结构检查后写入
    └── _format_evidence_block() — 格式化受管证据块
```

## 核心机制详解

### 1. 证据收集

从两个数据源收集：
- **state.db retrospectives表**: 评分<60或包含改进建议的记录
- **data/retro_candidates.jsonl**: 复盘引擎写入的进化候选队列

```python
# EvidenceCollector自动处理双源合并
collector = EvidenceCollector()
evidence = collector.collect_all()
# 返回: [{source, is_error, text, tool_name, created_at, confidence}, ...]
```

### 2. 语义分类（规则引擎，零LLM成本）

借鉴curator-evolver `candidates.py` 的 `classify_record()` 逻辑：

| 类型 | 条件 | 动作 |
|------|------|------|
| `replay_benchmark` | `is_error=True` 或匹配错误模式 | 生成错误修复提案 |
| `skill_update` | 检测到工作流模式（编号步骤/关键词/shell命令） | 生成Skill更新变体 |
| `skill_new` | 检测到工作流但未关联已有skill | 生成新Skill提案 |
| `ignore` | 其他低置信度证据 | 跳过 |

```python
def classify_evidence(record: Dict) -> str:
    """规则引擎分类，不使用LLM"""
    if is_error or error_pattern.search(text):
        return TYPE_REPLAY
    if has_workflow and confidence >= 0.6:
        return TYPE_SKILL_UPDATE
    if has_workflow and "skill" not in text.lower():
        return TYPE_SKILL_NEW
    return TYPE_IGNORE
```

### 3. 变体生成（4种确定性策略）

每个候选生成最多4种变体，评分函数自动选优：

| 变体 | 策略 | 适用场景 | 评分加成 |
|------|------|---------|---------|
| `default-verify-first` | 先验证再改写 | 稳定skill微调 | +40 |
| `compact-evidence-first` | 精简证据直接改进 | 内容过时的skill | +30 |
| `errors-first` | 只修复错误 | 错误率高的执行 | +35 |
| `minimal-inline` | 最小改动内联补丁 | 小修小补 | +20 |

评分公式：`score = confidence * 50 + variant_bonus + evidence_length_bonus`

### 4. 受保护应用

借鉴curator-evolver `guarded_apply.py` 的9层门禁：

1. **SHA256校验** — 计算当前文件指纹
2. **备份** — 复制到 `data/skill_evolver_backups/<skill>_<ts>/SKILL.md`
3. **结构检查** — 验证YAML frontmatter完整性和最小内容长度
4. **写入** — 以受管证据块格式追加内容
5. **写入后SHA验证** — 确认文件已修改
6. **内容验证** — 读取验证文件是否可读且内容正常
7. **自动回滚** — 任何验证失败立刻恢复到备份

## 作业调度

| 触发时机 | 动作 | 实现 |
|----------|------|------|
| 每天03:00 | 自进化集群模块7：证据收集→分类→生成提案→受保护应用 | `hermes_self_evolve_cluster.py` 模块7 |
| 复盘评分<60 | 自动写入进化候选队列 | `hermes_retrospect.py` 的 `try_invoke_skillopt()` |
| 手动触发 | `python3 scripts/hermes_skill_evolver.py all` | CLI |

## 数据存储

### 证据缓存
- 文件: `reports/skill_evolution/current_evidence.json`
- 格式: JSON数组，每元素包含 source/is_error/text/tool_name/created_at/confidence

### 候选缓存
- 文件: `reports/skill_evolution/current_candidates.json`
- 格式: JSON数组，每元素包含 type/confidence/evidence/source/created_at

### 进化报告
- 文件: `reports/skill_evolution/evolution_<timestamp>.json`
- 内容: evidence_count, proposals_count, best_proposal, target_skill, applied

## 实战陷阱（2026-05-30发现）

### 1. 文件编辑风险
`skill_manage(action='patch')` 在文件被部分读取（offset/limit分页）后，patch操作可能丢弃大段函数体。**修改文件前必须完整读取**，或用整文件替换而非行内patch。

### 2. 评分阈值理解
证据驱动Skill进化的评分（70+）与复盘评分（满分100）含义不同：
- 进化评分70+意味着提案质量足够高，可以尝试应用
- 但最终应用与否取决于：目标skill是否存在、应用后验证是否通过
- 当前实现中：评分>=70且找到目标skill才应用，否则只生成报告

### 3. 证据源的空状态
当复盘评分都>60时，证据中有数据但分类后都标记为ignore。这是正常行为：
- 高质量会话不会触发Skill进化
- 只有评分<60或包含明确改进建议的记录才会进入进化管线
- 这确保了系统只在需要时才进行Skill修改

## 关联技能

- `task-retrospect` — 复盘引擎作为证据源；references/ecosystem-analysis.md 和 references/skill-evolution-patterns.md 共享
- `self-evolution-executor` — P1步骤：消费复盘候选队列（check-evolution）
- `production-reliability-engine` — 执行质量墙中的复盘集成
- `writing-plans` — 验收清单与复盘质量评估维度对齐
- `hermes-auto-tune` — Skill进化引擎的输出可作为自动调优的反馈信号
- `skills-orchestration-engine` — Dynamic Workflows的evolution_durable.py是新的进化候选投喂入口

## Dynamic Workflows 进化桥接（2026-06-09 新增）

`workflows/evolution_durable.py` 的 `EvolutionBridge` 将在 workflow 完成后自动：
1. 调用 `feed_retrospect()` 将复盘数据写入 `retro_candidates` 表（state.db）
2. 质量评分公式：100 - failed_tasks×10 - (1-completion_rate)×30 - (error?20:0)
3. 评分<60时调用 `trigger_evolution()` 即时触发进化
4. cron `*/30 * * * *` 自动检查候选队列，>=3个时触发进化集群

该表与 `self_evolve_cluster` 的 `consume_retro_candidates()` 消费逻辑完全兼容。
进化集群每天03:00自动消费，手动可调用：
```bash
cd ~/.hermes && python3 scripts/hermes_self_evolve_cluster.py
```

### 全链路闭环

```
workflow执行完成
  → runtime.finally块: retrospect_integration.run_retrospect()
  → runtime.finally块: evolution_bridge.feed_retrospect()  → retro_candidates表
  → runtime.finally块: 评分<60? trigger_evolution() → 即时触发self_evolve_cluster
  → cron */30: EvolutionBridge.trigger_evolution() → 候选>=3? 触发进化
  → 每天03:00: self_evolve_cluster.consume_retro_candidates() → skill改进
  → 下次workflow: preflight更准 + SDLC更全 + skill匹配更优 ← 进化闭环
```

**注意**: EvolutionBridge 是正向增强而非替代——它把 workflow 复盘数据格式化为 retro_candidates 表（state.db），而 self_evolve_cluster 的 consume_retro_candidates() 从该表消费。两者是上下游而非重复。

## 实战陷阱（2026-05-30发现 + 2026-06-09补充）

## 参考文件

- `references/skill-evolution-patterns.md` — 证据驱动Skill进化的核心模式总结（来自curator-evolver/SkillClaw源码）

## 回滚方案

### 全流程回退
1. `git revert HEAD` 恢复前一个提交
2. 删除 `scripts/hermes_skill_evolver.py`
3. 从 `data/skill_evolver_backups/` 恢复被修改的skill
4. 关闭AGENTS.md中的证据驱动Skill进化规则段落

### 单技能回退
从 `data/skill_evolver_backups/` 中找到该skill的最新备份：
```bash
ls ~/.hermes/data/skill_evolver_backups/<skill_name>_*/
cp <backup_path>/SKILL.md ~/.hermes/skills/<category>/<skill_name>/SKILL.md
```
