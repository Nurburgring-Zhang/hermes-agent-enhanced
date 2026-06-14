# Ecosystem Research & Capability Absorption Pattern

> How to deeply analyze external projects, extract patterns, assess fit for Hermes, and produce actionable integration plans.
> Applicable when: "深度分析文章", "研究这个项目能否集成", "看看xxx有什么值得借鉴"

---

## 1. Core Workflow

```
┌─────────────────────────────────────────────────┐
│           Ecosystem Research Workflow             │
├─────────────────────────────────────────────────┤
│                                                    │
│  ① Source Acquisition    ② Deep Analysis          │
│  ┌─────────────────┐    ┌─────────────────┐      │
│  │ • 提取项目链接    │    │ • README概览     │      │
│  │ • 提取技术关键词   │    │ • 核心源码分析    │      │
│  │ • 提取方法/概念   │    │ • 架构机制提取    │      │
│  └────────┬────────┘    └────────┬────────┘      │
│            ↓                      ↓               │
│  ③ Parallel Research             │               │
│  ┌─────────────────────────────────────────┐    │
│  │ • 分3路: 项目源码 / 全网检索 / 现有盘点   │    │
│  │ • 使用delegate_task并行执行              │    │
│  └────────────────┬────────────────────────┘    │
│                    ↓                              │
│  ④ Gap Analysis   ⑤ Action Plan                  │
│  ┌──────────────┐ ┌─────────────────────┐       │
│  │ • 能力对标    │ │ • Phase制定         │       │
│  │ • 差距识别    │ │ • 移植优先级        │       │
│  │ • 可移植性评估 │ │ • 实施时间线        │       │
│  └──────────────┘ └─────────────────────┘       │
└─────────────────────────────────────────────────┘
```

## 2. Source Acquisition

### From article / reference text
```python
PATTERNS = {
    "github": r"github\.com/[\w-]+/[\w.-]+",
    "arxiv":  r"arxiv\.org/abs/[\d.]+",
    "paper": r"\[([^\]]+)\]\(https?://[^)]+\)",  # markdown links
}
```

### Technical concept extraction
- Framework names (ReAct, Plan-and-Solve, Reflexion, etc.)
- Method names (SkillOpt, CaMeL, etc.)
- Architecture patterns (Plugin Hook, Proxy Intercept, etc.)
- Quality attributes (reliability, safety, evolution, isolation)

## 3. Deep Analysis — Per Project Template

For each project/paper, collect:

### 3.1 Project Overview
```
- Name / URL
- Core purpose (1 sentence)
- Architecture diagram (text or mermaid)
- Tech stack
```

### 3.2 Core Mechanism (must read source code)
```
- Key files: <filename.py> → N lines → purpose
- Core algorithm / data flow
- What problem does it solve?
- How does it solve it? (step by step)
- Dependencies / constraints
```

### 3.3 What's Transferable to Hermes
```
- Specific mechanisms (list each with source code evidence)
- Architecture patterns (e.g., "Plugin Hook pattern", "Client Proxy pattern")
- Code snippets that can be adapted
```

### 3.4 What's NOT transferable or low priority
```
- Environment-specific (e.g., Nacos/S3 storage)
- Too coupled to other systems
- Already covered by existing Hermes capabilities
```

## 4. Parallel Research Strategy

Use `delegate_task` to run 3 research streams simultaneously:

```
delegate_task #1: Project source code deep analysis
  → curl README, read core files, extract patterns

delegate_task #2: Web search for methodology / concepts
  → search AI agent frameworks, self-improvement, quality control

delegate_task #3: Audit existing Hermes capabilities
  → check scripts/, skills/, cron, evolution engines
```

Each task produces structured output, then the orchestrator merges, gaps-analysis, and produces the plan.

## 5. Gap Analysis Format

| Dimension | Coverage | Existing | Gap |
|-----------|----------|----------|-----|
| 技能自动进化 | 90% | 4套引擎 | 缺少证据驱动闭环 |
| 任务中断恢复 | 95% | 三层冗余 | wake_guide残留 |
| 安全护栏 | 0% | 无CaMeL | 需要信任边界分离 |
| ... | ... | ... | ... |

Severity: 🔴 High / 🟡 Medium / 🟢 Low

## 6. Action Plan Structure

```
## Phase 1: (Priority, N days)
  ├─ 1.1 Action — what to build
  ├─ 1.2 Rationale — why this first
  └─ 1.3 Quick win — something implementable NOW

## Phase 2: (Priority, N days)
  ...
```

Each action item should answer:
- **What**: what to implement
- **Source**: which project/paper it's from
- **Mechanism**: the specific pattern/technique
- **Hermes mapping**: where it integrates (scripts/skills/gear/cron)
- **Effort**: estimate (hours/days)

## 7. Output Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Research report | conversation (summarized) | All project analyses |
| Gap analysis | conversation | Comparison matrix |
| Action plan | `plans/<name>.md` | Structured plan with phases |
| Memory entry | memory tool | Key findings for future recall |
| Skill references | `skills/xx/references/` | Detailed patterns for reuse |

## 8. Typical Time Allocation

| Phase | Duration | Notes |
|-------|----------|-------|
| Source acquisition | 5-10 min | Extract URLs and concepts from article |
| Deep analysis (per project) | 15-30 min | 5 projects → ~2h with parallel delegates |
| Web search | 15-20 min | Cover methodology + concepts |
| Hermes audit | 10-15 min | Check existing capabilities |
| Gap analysis | 5-10 min | Compare and prioritize |
| Plan writing | 10-15 min | Structured output |
| **Total** | **~2-3h** | With 3 parallel delegates, ~1.5h wall-clock |

## 9. Pitfalls

- **Don't stop at README**: Real architecture lives in source code files. Always `curl` or `read_file` the actual implementation files.
- **Don't miss the "why"**: Understanding why a project chose its architecture is more valuable than the architecture itself.
- **Don't overestimate transferability**: A pattern that works for a different Agent ecosystem may not map cleanly. Always consider Hermes constraints (cron-driven, gear-interlocked, SOUL.md governed).
- **Don't produce analysis without action**: Every research session must end with an actionable plan. Analysis without execution is wasted tokens.
- **Don't ignore existing overlap**: Hermes already has 4 evolution engines, 7 memory systems, etc. Check first before recommending new ones.
