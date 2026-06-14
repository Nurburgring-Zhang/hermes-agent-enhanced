---
name: fde-sop-methodology
title: FDE (Forward Deployed Engineer) SOP Methodology
description: "Complete 8-step Forward Deployed Engineer SOP with LLM dual-track architecture integration. Uses Hermes LLM for intelligent judgment (task boundary detection/recall filtering/quality assessment). Rule-based fallback for reliability. Based on Palantir practice, 2026 OpenAI/Anthropic/Google deployments, and Microsoft SkillOpt research."
category: autonomous-systems
tags: [FDE, forward-deployed, methodology, SOP, skills-optimization, deployment, SkillOpt]
triggers:
  - "FDE"
  - "前沿部署工程师"
  - "forward deployed engineer"
  - "SOP methodology"
  - "deployment workflow"
  - "微软SkillOpt"
  - "skill optimization"
  - "负迁移检测"
  - "skill lifecycle"
---

# FDE (Forward Deployed Engineer) SOP Methodology

## Role Definition

## 触发条件
- 用户提及"部署"、"适配"、"客户接入"、"方案实施"时
- 涉及多步骤、多系统、多团队的复杂任务
- 需要先勘探再动手的未知环境任务
- 用户提及SkillOpt、验证门、负迁移检测时
- 需要批量补全Skill结构或执行A/B测试时
- "FDE"、"前沿部署工程师"、"forward deployed engineer"


FDE is NOT a "field support engineer." It is a complete, highly specialized engineering methodology.

**Core purpose**: "Transform generic AI/software systems into usable, reliable tools embedded in a specific client's business operations."

### FDE vs Traditional Implementation Engineer

| Traditional | FDE |
|---|---|
| Install per docs | Discover + solve problems |
| File bugs for R&D | Fix it yourself, drive product feedback |
| Respond per SLA | Proactively prevent |
| One-shot delivery | Continuous iteration |
| Use existing features | Write code to adapt |

## Sources

- **Palantir**: FDE role originator (2003-present)
- **OpenAI Deployment Company** (May 2026): $4B, acquired Tomoro (150 engineers)
- **Anthropic + Blackstone/Goldman Sachs** (May 2026): $1.5B independent entity
- **Google Cloud** (May 2026): CEO personally recruiting FDEs, 59 open positions
- **Microsoft SkillOpt** (arXiv:2605.23904, May 2026): Skill-as-trainable-state methodology
- **Microsoft Skill Lifecycle** (arXiv:2605.23899, May 2026): 25% negative transfer finding
- **Shanghai Jiao Tong / Shanghai Telecom**: First China FDE training program

## 8-Step SOP

```
① Client Triage ─→ ② Environment Recon ─→ ③ Requirement Deep Dive ─→ ④ Adaptation Design
     ↓                                                                          ↓
⑧ Continuous Monitoring ← ⑦ Knowledge Transfer ← ⑥ Validation & Testing ← ⑤ Implementation
```

### Step 1: Client Triage & Onboarding

**Purpose**: Quickly decide: take this project? How? Who?

- **SOP 1.1 Initial Contact**: Record client basics (industry, scale, tech maturity); identify core pain point in one sentence; assess product coverage vs customization needed.
- **SOP 1.2 Technical Pre-Screen**: Network environment, data format, compliance (GDPR/CCPA), security review needed.
- **SOP 1.3 Team Formation**: Assign 1 primary FDE ("field brain") + 1-2 remote support engineers + client POC (business + technical).
- **SOP 1.4 Entry Agreement**: NDA/compliance signed; access (VPN/repo/read-only DB/logs); SLA framework; communication channels.

**🔴 Critical Experience**: **The "Three Rejections"** — Reject: (1) clients who haven't clarified their own need, (2) incompatible tech stacks, (3) severe internal politics.

**✅ Stage Gate**: `technical_pre_screen_report.md` → 3 conclusions: take/reject, priority, effort estimate.

**→ Hermes mapping**: `task_boundary.py` L1.5 task boundary detection + `gear_vault` task registration.

### Step 2: Environment Reconnaissance

**Purpose**: Understand the client's technical environment before writing any code.

- **SOP 2.1 Infrastructure Audit**: Server/cloud topology, network (firewall/NAT/proxy/whitelist), auth (LDAP/OAuth/SSO), existing monitoring.
- **SOP 2.2 Data Pipeline Audit**: Data sources, formats, volume, latency requirements.
- **SOP 2.3 Security Compliance Audit**: Encryption (TLS/AES-256), audit logs, RBAC/ABAC, data residency.
- **SOP 2.4 Personnel Capability Assessment**: Client ops team skill level; business team technical understanding; decision-maker power structure.

**🔴 Critical Experience**: Spend **at least 1 day** on recon. Most adaptation problems come from "never imagined the environment would be this exotic" — internal-only networks, triple-proxied requests, custom auth protocols.

**✅ Stage Gate**: `environment_recon_report.md` with risk matrix (High/Medium/Low).

**→ Hermes mapping**: `search_files` + `terminal` for system audit; `read_file` for config review.

### Step 3: Requirement Deep Dive

**Purpose**: Translate business requirements into technical specifications.

- **SOP 3.1 Business Requirement Gathering**: Shadow client workflows (shadow! shadow! shadow!); interview ≥3 different roles; collect existing manual process docs.
- **SOP 3.2 Requirement Classification**: Must-have / Should-have / Nice-to-have / Out-of-scope.
- **SOP 3.3 Success Criteria Definition**: Quantitative KPIs — P99 latency, throughput, SLA %, MTBF.

**🔴 Critical Experience**: **"Watch what they do, not what they say."** (Palantir FDE golden rule) Shadowing for half a day is worth 10 requirement meetings.

**✅ Stage Gate**: `requirement_confirmation.md` signed by client business lead.

**→ Hermes mapping**: `l1_extractor.py` LLM extraction → `memory_semantic` to capture real user needs; `Hy-Memory` long-term recall to retain context across sessions.

### Step 4: Adaptation Design

**Purpose**: Design a "just-enough" adaptation — perfect fit without modifying product core.

- **SOP 4.1 Adaptation Strategy Selection** (ordered by risk):
  1. Config adaptation (fastest, lowest risk)
  2. Plugin/extension adaptation (flexible)
  3. API gateway adaptation (decoupled)
  4. Code-level adaptation (highest risk, last resort)

- **SOP 4.2 Skill Design (core deliverable)**:
  ```
  SKILL.md structure (FDE-edition):
  ├─ Meta (version, author, applicable environments, dependencies)
  ├─ Trigger conditions
  ├─ Standard procedure (exact step sequence)
  ├─ Error handling (known issues + recovery)
  ├─ Verification steps
  └─ Rollback plan
  ```

- **SOP 4.3 Risk Identification**: Single points of failure, data inconsistency, security, performance regression.

**🔴 Critical Experience**: **"Never fork the product."** Forking = impossible to upgrade = permanent technical debt.

**✅ Stage Gate**: Architecture review with ≥3 FDEs.

**→ Hermes mapping**: `skill_manage` to create/update FDE skills; `l1_extractor.py` → `memory_semantic` for requirement capture; `wake_guide.json` for shared state.

### Step 5: Implementation & Deployment

**Purpose**: Safely, reversibly deploy adaptation to production.

- **SOP 5.1 Sandbox Verification**: Isolated environment first; full functional tests; performance tests.
- **SOP 5.2 Gradual Rollout**: 1 node/user → monitor 24h → 10%/50%/100%.
- **SOP 5.3 Full Deployment**: Automated scripts (no manual ops); deployment logs; configuration version control.

**🔴 Critical Experience**: Never deploy to a single environment — always have staging.

**✅ Stage Gate**: Each rollout step must meet Success Criteria.

**→ Hermes mapping**: `delegate_task` for parallel workstreams (primary FDE + remote support); Gear system G0-G7 for interlocking validation; production-reliability-engine for step-by-step verification.

### Step 6: Validation & Testing

**Purpose**: Guarantee the system meets design requirements in the client's real environment.

- **SOP 6.1 Functional Validation**: End-to-end core flow; boundary conditions; exception paths.
- **SOP 6.2 Performance Validation**: Baseline comparison; stress test (15min peak); stability test (72h no failure).
- **SOP 6.3 Security Validation**: Basic penetration test; least-privilege check; audit log verification.
- **SOP 6.4 Disaster Recovery Drill**: Simulated failures (kill process/drop network/disk full); practice recovery; verify SLA.
- **SOP 6.5 Task Retrospect (Mandatory)**: After validation completes, run structured retrospection:
  ```bash
  python3 scripts/hermes_retrospect.py --session <session_id>
  ```
  Or via `inline_after_task()`. This feeds into Step 8's Skill Distillation.

**🔴 Critical Experience**: The drill must be REAL. Kill the process. Drop the network. Power off the server. Not a paper exercise.

**✅ Stage Gate**: 72h stability test + disaster recovery drill completed.

**→ Hermes mapping**: Production-reliability-engine (LoopState + CriticAgent + 3 layers of reflection + step validator + degradation interceptor); Gear G8 interlock.

### Step 7: Knowledge Transfer & Handoff

**Purpose**: Enable the client's team to operate independently.

- **SOP 7.1 Documentation Delivery**: Updated architecture diagram; Runbook; troubleshooting guide; FAQ.
- **SOP 7.2 Training Delivery**: Ops team training (≥2 sessions, recorded); business user training (≥1); Q&A archived.
- **SOP 7.3 Monitoring Handoff**: Alert thresholds confirmed; on-call schedule; escalation path.

**🔴 Critical Experience**: Training is complete only when the client team independently completes a failure recovery. FDE's ultimate goal: make yourself "optional."

**✅ Stage Gate**: Client team independently on-calls for 2 weeks with zero FDE intervention.

**→ Hermes mapping**: `wake_injector` + `auto_recall` guarantees knowledge persistent; `wake_guide.json` handoff state.

### Step 8: Continuous Monitoring & Evolution

**Purpose**: Ensure no degradation while accumulating cross-client reusable experience.

- **SOP 8.1 SLA Monitoring**: Automated SLA dashboard; anomaly alerting; periodic SLA reports (weekly/monthly).
- **SOP 8.2 Skill Distillation (most critical!)**: Transform per-client adaptations into generalized Skills.
  ```
  Client A adaptation → Abstraction → Generic Skill → Client B reuses
  Client B adaptation → Abstraction → Generic Skill → Client C reuses
  ```
- **SOP 8.3 Retrospect Aggregation**: Consume the retrospect candidate queue (`data/retro_candidates.jsonl`) daily to extract cross-client improvement patterns. Each low-scoring retrospect triggers a skill evolution candidate automatically.
- **SOP 8.4 Product Backfeed**: Identify missing features → Feature Requests; fold best practices into default configs; update FDE knowledge base.

**🔴 Critical Experience**: Extract ≥1 reusable Skill per client. This is where Microsoft SkillOpt's methodology directly maps — the Rollout + Reflection cycle is skill distillation.

**✅ Stage Gate**: SLA ≥99.X% for 3 consecutive months.

**→ Hermes mapping**: Self-evolution-cluster (daily 3am); SkillOpt validation gate integration (see references/skillopt-integration.md).

## 5-Layer Reliability Framework

| Layer | FDE Original | Hermes Mapping | Status |
|---|---|---|---|
| 1 | Checklist culture | Gear system G0-G8 interlocking | ✅ Existing |
| 2 | Peer review (Two-Pizza Team) | Gear inter-audit + production CriticAgent | ✅ Existing |
| 3 | Rollback guarantee | Triple-redundancy files + backup rules | ✅ Existing |
| 4 | Monitoring-first | Production-reliability-engine + SLA | ✅ Existing |
| 5 | Continuous learning | Self-evolution-cluster + **SkillOpt gate** | ✅ Active |

## Ecosystem Research & Capability Absorption

When analyzing external projects/papers for integration into Hermes, use `references/ecosystem-research-pattern.md`:

1. **Source Acquisition** - GitHub URLs, arxiv papers, technical concepts
2. **Deep Analysis** - README + source code per project (curl actual files)
3. **Parallel Research** - 3x delegate_task: code / web search / Hermes audit
4. **Gap Analysis** - coverage vs existing capability matrix
5. **Action Plan** - phased plan with effort estimates saved to `plans/<name>.md`

## Hermes Implementation

### FDE Skill Template

Every FDE-related SKILL.md must include:

```yaml
---
name: <skill-name>
fde:
  applicable_environments: [<client-types>]
  trigger_conditions: <what-scenarios>
  rollback_plan: <how-to-revert>
  verification_steps: <how-to-confirm>
---
```

### SkillOpt Validation Gate Integration

When updating any skill via `skill_manage(action='patch')`:
1. **Rollout batch**: Run the current skill against 3-5 test scenarios
2. **Reflection**: Compare success/failure trajectories
3. **Learning rate**: Only modify ≤3 rules per update cycle
4. **Validation gate**: Accept only if verified improvement over baseline
5. **Rejection buffer**: Record rejected edits as negative feedback

The concrete implementation lives at `scripts/skillopt_trainer.py`. See `references/skillopt-integration.md` for CLI usage, validation criteria, and 2026-05-29 scan results (121 skills audited).

### Negative Transfer Detection

Per Microsoft Skill Lifecycle paper (arXiv:2605.23899):
- **25% of model-generated skills cause negative transfer**
- Run A/B tests on high-frequency skills: compare performance with vs. without skill
- Flag skills where performance drops when skill is active
- See `references/negative-transfer-detection.md`

## 格林主人8条任务执行铁律 (2026-05-31固化)

当为格林主人执行任何任务时，必须严格按照以下规则执行。这覆盖了FDE SOP 8步的所有阶段：

1. **任务前全面回顾+全局预判**: 在执行任务前，必须先进行历史信息回顾、全网相关信息检索，获取全面的任务背景信息了解和要求、规则、标准的明确。进行全局纵览、全局预判、全局总观、全局预览，制定详细的任务总体规划。对复杂任务进行拆解（分阶段、分步骤、分方向）。需要明确的信息直接向格林主人提问。

2. **超限/中断自动拆解+继续**: 当遇到tokens量大/模型超限/输出限制/字数超长时，进行任务拆解分阶段逐步执行。遇到任务中断必须继续执行，高质量实现，回顾历史信息与文档。

3. **每阶段后必须复盘**: 每个阶段执行完毕后都必须进行阶段性任务复盘与历史信息回顾，确保任务方向不跑偏。每隔十分钟审查当前任务状态。

4. **完整后全局复盘**: 整个任务完整执行完毕后，再次进行历史信息回顾与全局复盘，确保所有要求、标准、条件均满足。

5. **真实实现+联网最佳方案+严苛测试**: 必须全部高质量实现，严禁简单实现/精简实现/批量实现。基于联网检索获取最佳方案。必须使用deep_code_architecture_analysis对代码库进行深度分析。必须进行严苛功能测试。

6. **强制循环完善→审核→测试循环**: 任务结束后，进行多次循环：全面的debug→全面深度极端详细的商用级代码审核→全面深度极端详细的商用级测试→全面的debug。

7. **中断主动自检恢复**: 遇到任务中断时，必须主动自检，恢复任务执行，一直到任务完整结束。回顾历史信息与文档明确标准、要求、规则。

8. **严禁降级实现**: 必须全部是高质量实现，严禁简单实现！严禁精简实现！严禁批量实现！严禁降级实现，严禁模拟实现，严禁只做示例，严禁占位符，严禁只写核心代码。禁止任何代码缩写，禁止任何功能降级，禁止任何虚拟实现，禁止任何占位符。不进行任何降级偷懒，不回避任何缺陷。

## Related Reference Files

| File | What it covers |
|------|---------------|
| `references/fullstack-project-audit-and-fix.md` | Full-stack project audit → fix → test → deliver workflow. Use when given an unfamiliar project directory to make runnable. Covers Vite proxy debugging, static asset path fixing, startup script patterns, and 7-step audit protocol. |

## Pitfalls

## 🔴 格林主人 2026-05-29 系统审计关键发现

2026-05-29 格林主人报告5个系统性问题: "偷懒、历史对话信息丢失、长任务中断、整体能力像白痴弱智、缺乏整体观念不会主动检索、技术降级实现"

**根因分析结果：**

| 问题 | 根因 | 修复 |
|:----|:-----|:-----|
| 偷懒/降级实现 | 缺少代码级强制验证门 — 只有SOUL.md文本规则无自动执行 | 新增pre_check.py + skillopt验证门 + G8激活检查 |
| 历史对话丢失 | wake_injector.py注入空字符串代替persona_context | 修复: 无user_input时注入persona_summary |
| 长任务中断 | memory_episodic缺created_at列导致schema异常 | ALTER TABLE + 移除try/except兼容代码 |
| 缺乏整体观念 | hy_memory_orchestrator.py用COUNT(*)报错直接跳过 | 修复L140-158，改用正确SQL |
| 降级不透明 | llm_bridge静默fallback无提示 | 修复: 每个fallback输出[SKIP]警告+后端列表 |

**系统当前状态（修复后）:**
- all capabilities audit: 35/35 PASSED
- DB: memory_semantic 59条, memory_episodic 13条, memory_scene 6条, memory_profile 3条
- SkillOpt: 1052条验证记录, 2个epochs
- Cron: 13条任务全部激活（采集、L1/L2/L3、情景注入、编排、审计、清理、自进化、唤醒、G8）
- Pre-check: 首次运行检测到3个问题（G8未运行、2个遗留状态文件）
- **遗留状态文件**: task_current.json + gear_checkpoint.json — 已完成任务的残留，待格林确认是否清理

**关键教训**: 文本规则不够。所有强制约束必须代码化（pre_check.py / skillopt验证门 / G8齿轮 / llm_bridge透明化）。
