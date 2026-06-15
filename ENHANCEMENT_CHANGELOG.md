# Hermes - Enhancement Changelog
# Complete list of ALL enhancements over official Hermes Agent (Nous Research)
# Official: https://github.com/NousResearch/hermes-agent

## ============================================================================
## OVERVIEW: 150+ Enhancement Modules | 13 Major Systems | 311+ Custom Scripts
## ============================================================================

Official Hermes provides: TUI interface, Telegram/Discord/Slack/WhatsApp gateway,
basic memory (FTS5 + nudges), basic skills (create/improve), cron scheduler,
subagent delegation, multi-model support, 6 terminal backends.

This enhanced pack adds the following systems ON TOP of official Hermes:

---

## 1. Hy-Memory P0-P3: LLM-Driven 4-Layer Memory Architecture
**Official**: Basic FTS5 memory with periodic nudges
**Enhanced**: Full 4-layer LLM-driven memory pipeline

- `l1_extractor.py` — Three-strategy L1 fact extraction (LLM semantic + rule engine + scenario sharding)
  - Extracts persona/episodic/instruction structured facts
  - FTS5 index auto-maintenance, 56+ fact types across 15 categories
- `l2_scene_scheduler.py` — L2 scene induction auto-scheduler
  - Auto-triggers when new facts reach threshold (10 entries)
  - Local LLM (LM Studio/Ollama) scene summarization
  - Fallback: rule-based category grouping
- `l3_persona_scheduler.py` — L3 user profile auto-generation
  - Four-layer deep scan (L1 basic / L2 interests / L3 interaction / L4 cognitive)
  - Hy-Memory exact prompt transplant
- `episodic_injector.py` — Episodic memory injection engine
- `hy_memory_orchestrator.py` — Full pipeline orchestration (L1→L2→L3)
- `auto_recall.py` — Four-route retrieval (FTS5 + structmem + mp + semantic), RRF fusion top-5
- `tool_unloader.py` — Tool result >2KB auto-offload to refs/*.md, context keeps summary only
- `tool_wrapper.py` v2.0 — Global auto-offload hooks (monkey-patch all tool calls)
- `mermaid_builder.py` — Mermaid task canvas from offload entries (200-500t replaces several Kt)
- `emergency_compressor.py` — Three-level cascade compression (mild 50%/aggressive 85%/emergency 92%)
- `memory_engine.py` — Memory highway + keyword evolution engine
- `memory_evolution_v2.py` — Deep memory evolution with parallel lifecycle management
- `memory_highway.py` / `memory_index.py` / `memory_orchestrator_v3.py` / `memory_tools.py`
- `unified_memory_core.py` / `parallel_memory_orchestrator.py`

### Cron Schedule: 8 automated jobs
- L1 extraction: every 2h | L2 scene: every 6h | L3 profile: daily 5AM
- Episodic injection: every 30min | Full pipeline: hourly
- Audit: every 2h | Cleanup: daily 3AM | Self-evolution: daily 3:30AM

---

## 2. Gear System G0-G8: 9-Layer Self-Discipline Architecture
**Official**: No equivalent
**Enhanced**: 9 interlocking gears for autonomous operation

| Layer | Gear | Frequency | Function |
|-------|------|-----------|----------|
| G0 | gear_vault | On-demand | Task registration center, chain-signed credentials |
| G1 | gear_enforcer | Every 1min | Interrupt detection + AI scoring + wake_guide writing |
| G2 | context_failsafe | Every 5min | Merge breakpoints → recovery_pack, verify G1 heartbeat |
| G3 | gear_context_compressor | Per-conversation | Compression + recovery, verify G2 recovery packs |
| G4 | context_guardian | Every 5min | Background checkpoint solidification, verify G3 timeliness |
| G5 | hermes_super_guardian | Every 15min | Full-system fallback, verify G4 audit |
| G6 | gear_task_validator | Every 30min | Full-chain integrity, verify G0→G5 |
| G7 | wake_guide | Every 1min | Output wake guide, verify G6 results |
| G8 | production_loop_cron | Every 10min | Production-grade reliability engine |

### Triple Redundancy Files (system survives if any one is alive):
- task_current.json | gear_checkpoint.json | audit_snapshot.json
- recovery_pack.json | gear_registry.json (chain-signed)

---

## 3. Production Loop Engine: End-to-End Reliability
**Official**: No equivalent
**Enhanced**: 8-module production reliability system

- `production_loop/loop_state.py` — Global state management
- `production_loop/main_loop.py` — Deterministic main loop
- `production_loop/dag_manager.py` — DAG task graph
- `production_loop/engine.py` — Core execution engine
- `production_loop/verification.py` — Step verifier
- `production_loop/security.py` — 7-layer permission system
- `production_loop/agent_committee.py` — Critic Agent (independent auditor)
- Three-layer reflection: operational (every step) / strategic (every 3 steps) / goal (every 10 steps)
- ReFlect deterministic error detection (7 rules)
- DegradationPreventer (5 degradation pattern detection)
- `production_loop_cron.py` — Cron scheduler: check/10min, critic/30min, deep_check/2h

---

## 4. Evolution V3: 18-Module Self-Enhancement System
**Official**: Basic skill self-improvement during use
**Enhanced**: Full autonomous evolution with genetic optimization

- `self_enhancement_v3_loop.py` — V3.1 7-channel/IFC/DPW integrated self-enhancement
- `v3_daemon.py` — V3 intelligent daemon with Hooks + sub-agent persistence
- `task_engine.py` — Dual-planner + witness + 3-level correction engine
- `experience_engine.py` — Auto experience extraction, cross-task reuse
- `semantic_engine_v2.py` — Semantic embedding v2 + bilingual drift detection
- `seven_channel_memory.py` — 7-channel parallel retrieval (semantic/entity/diffusion/Hopfield etc.)
- `channels_v2.py` — Extended channels: diffusion activation + entity graph + Hopfield association
- `memory_lifecycle.py` — Long-term memory data lifecycle management
- `self_check_engine.py` — Full-system self-check and self-maintenance
- `hooks_engine.py` — 6-event hooks engine, fully event-driven
- `subagent_manager.py` — Sub-agent auto-management (persistence/isolation/smart scheduling)
- `information_fidelity_core.py` — IFC v1: unified validation/compression/encryption
- `ifc_core_v2.py` — IFC v2: commercial-grade DFloat11 + Blosc2
- `gepa_optimizer.py` — GEPA genetic optimizer + Merkle tree execution trace verification
- `hash_chain_auditor.py` — Chain-hash audit: tamper-proof operation audit log
- `commercial_test.py` — Extreme multi-condition commercial-grade evaluation
- `full_system_test_v3.py` — Full integration test v3

---

## 5. Three-Layer Cognitive Architecture
**Official**: Single agent loop
**Enhanced**: Monitor → Reflector → Model Router

- `agent/monitor.py` — Monitoring layer (every minute)
- `agent/reflector.py` — Reflection layer (every minute)
- `agent/model_router.py` — Smart model routing (every 5 minutes)
- `scripts/consistency_guard.py` — Consistency guardian (every minute)
- `scripts/segment_manager.py` — Segment state management
- `scripts/checkpoint_recorder.py` — Auto checkpoint saving
- `scripts/layered_planner.py` — Hierarchical planning
- `scripts/auto_healer.py` — Degradation auto-repair (every 5 minutes)

---

## 6. Context Management System (6 Scripts, Every Minute)
**Official**: Basic context window management
**Enhanced**: Surgical context slicing with cross-session caching

- `scripts/context_packer.py` — General context packing (every minute)
- `scripts/surgical_context_slicer.py` — Surgical context slicing (every minute)
- `scripts/context_auto_assoc.py` — Auto context association (every minute)
- `scripts/context_index_system.py` — Context index system (every minute)
- `scripts/cross_session_cache.py` — Cross-session context caching (every minute)
- `scripts/compression_fidelity_validator.py` — Compression fidelity verification (every 10min)
- `scripts/token_surgery.py` — Hierarchical context compression
- `scripts/token_optimizer.py` — Token optimization engine v2
- `scripts/token_watermark_daemon.py` — Token watermark monitoring + auto-compression
- `scripts/lossless_claw.py` — Lossless-Claw context compression (60-70% reduction)
- `scripts/lcm_dag_engine.py` — LCM DAG hierarchical incremental summarization

---

## 7. Agent Company: 130 Agents / 12 Departments Multi-Agent System
**Official**: Subagent delegation (up to 3 parallel)
**Enhanced**: Full organizational structure with 130 expert agents in 12 departments

- `agent_company_engine.py` — 130-agent / 12-department automated operations
- `agent_company_runner.py` — Fully automated running engine
- `agent_company_cron_orchestrator.py` — Automated pipeline with independent cron
- `agent_matching_pipeline.py` — Smart matching: high-score intel → match agents → deep analysis
- `agent_isolation_engine.py` — Agent isolation v2: each expert gets isolated sub-agent
- `pipeline_orchestrator.py` — 12-stage full pipeline orchestration
- `orim_orchestrator.py` — Multi-Agent dispatch hub
- `scripts/agent_export.py` / `agent_export_engine.py` — Intelligence-driven AI analysis reports

---

## 8. Data Collection Layer: 35+ Platform Collectors
**Official**: web_search, web_fetch tools
**Enhanced**: Full multi-platform intelligence collection system

### Aggregated Collectors
- `unified_collector_v5.py` — Unified collector, 35+ platforms, terminal + browser dual-mode
- `hermes_mega_collector.py` — Full-capability aggregated collector with parallel dedup
- `hermes_ultimate_collector.py` — Ultimate v2: unified_collector_v5 + new collectors + RSS

### Platform-Specific Collectors (20+ platforms)
- **Xiaohongshu**: 5 versions + CloakBrowser anti-detection + RedCrack SDK (X-S/X-B3/X-Xray)
- **WeChat**: 9 versions + direct scan + MCP + Bing + content enhancer
- **Douyin/TikTok**: TikTokDownloader SDK
- **Toutiao/Baidu/Bilibili**: Browser + API dual-strategy
- **Zhihu/Weibo/Douban**: Dedicated collectors
- **HackerNews/ArXiv/GitHub/Medium**: International platforms
- **RSS**: Universal RSS aggregation

### Anti-Crawl Bypass
- `ANTI_CRAWL_MATRIX.md` — Platform anti-crawl strategy matrix
- `RedCrack/` — Xiaohongshu anti-crawl cracking SDK
- CloakBrowser integration for reCAPTCHA bypass
- Multi-context rotation for rate limit avoidance

---

## 9. Intelligence Processing Pipeline
**Official**: No equivalent
**Enhanced**: Full data processing pipeline

- `unified_cleaning_pipeline.py` — Unified cleaning pipeline (26KB)
- `ai_scoring_daemon.py` / `ai_scoring_v2.py` — AI scoring with LLM
- `real_ai_scorer.py` — Real AI scoring engine
- `ai_sixdim_scorer.py` — 6-dimension AI scoring
- `batch_import_clean.py` — Batch import + cleaning
- `spam_filter.py` — Spam filter engine
- `rebuild_spam_filter.py` — Advanced spam filter rebuild
- `lowscore_cleaner.py` — Low-score data auto-cleanup
- `segment_manager.py` — Data segment management
- `tr_gate.py` — TR quality gate
- `dod_checklist.py` — Definition of Done checklist

---

## 10. Push & Delivery System
**Official**: cron-based delivery to any platform
**Enhanced**: Intelligent push with quality gates and time-decay

- Time-based filtering (>14 days + AI<80 = discard)
- Time-decay scoring (>7 days decay, >14 days strong decay)
- 72-hour triple dedup (SQL + main flow + record check)
- `hermes_push_v3` skill — 4-stage push pipeline
- Pushplus WeChat integration
- Quality-first candidate pool selection

---

## 11. Enhanced SOUL.md + AGENTS.md (Agent Personality & Rules)
**Official**: Default personality, no custom rules
**Enhanced**: Comprehensive rule system for autonomous operation

### SOUL.md Enhancements:
- Anti-hallucination iron law (highest priority)
- 5 behavioral guidelines
- Rule 0: autonomous capability baseline
- Hy-Memory P0-P3 full integration
- 9-layer gear system integration
- LLM degradation transparency requirement
- Forced step 0.5: skill_manage auto-verification gate
- Forced step -1: global search before every task
- Context compression rules (index-based dynamic extraction)
- Skills composition/parallel/chain-call rules

### AGENTS.md Enhancements:
- 8 permanent execution rules
- Post-task reflection (mandatory)
- Execution quality wall (checkpoint every step, milestone every 3)
- Long-task execution guarantee (>15 steps requires hierarchical planning)
- Evidence-driven skill evolution (score < 60 auto-triggers improvement)
- Three-layer structured reflection (operational/strategic/goal)
- CaMeL security guardrails (16 sensitive tool categories, 5 injection patterns)
- Auto-tuning rules (5 core parameters, A/B testing)
- Push system optimization rules

---

## 12. Additional Enhancement Systems

### Self-Evolution Cluster
- `hermes_self_evolve_cluster.py` — Nightly 3AM autonomous execution
- `hermes_auto_tune.py` — Nightly 4AM parameter auto-tuning
- `self_evolution_engine.py` — GenericAgent + SuperMemory + autonomous skill generation
- `self_enhance_loop.py` — Self-enhancement loop every 5 minutes, 24/7
- `self_pua_engine.py` — Self-drive engine

### Security Layer
- `hermes_camel_guard.py` — CaMeL security guardrails (trust boundary separation, 16 tool categories, 5 injection detection, 3-level response)
- `encryption_layer.py` — AES-256-GCM data encryption
- `remove_all_security_restrictions.py` — Force permission removal (for development)

### SkillOpt Training System
- `skillopt_trainer.py` — Skill quality validation + training loop
- Validation gate (score < threshold → reject modification)
- Negative migration scanning
- Stats and risk reporting

### Reflection Engine
- `reflexion_engine.py` — Structured reflection every 30 minutes
- `experience_extractor.py` — Experience extraction every hour
- `hermes_retrospect.py` — Retrospective audit every 15 minutes

### Progress & Task Management
- `tools/progress_tool.py` — Progress tracking tool (every 30min)
- `scripts/task_enhancement_engine.py` — Task enhancement engine
- `scripts/task_queue_manager.py` — Task queue management
- `scripts/task_resumer.py` — Task breakpoint resumption
- `scripts/long_task_guardian.py` — Long-task guardian (triple redundancy)

### WebUI & Dashboard
- `webui_launcher.py` — WebUI keepalive (every 5min)
- `unified_dashboard.py` — Unified dashboard
- `hermes_webui.py` — Web UI server

### External Integrations
- `gbrain_bridge.py` — GBrain knowledge bridge (hourly sync)
- Pushplus WeChat push integration
- Playwright browser automation

### Systemd Services
- `hermes-gateway.service` — Enhanced gateway with auto-restart (300s exponential backoff)
- `hermes-eternal.service` — Eternal guardian daemon (never stops, 5s restart)

---

## 13. Skills: 150+ Custom Skills
**Official**: Bundled skills (software-development, autonomous-ai-agents, etc.)
**Enhanced**: 150+ additional skills across all domains

### Custom Skill Categories:
- **AI/ML Experts**: AutoML, CV, DL Architecture, Ethics, Federated, Knowledge Graph, Model Compression, Multimodal, NLP, RL, Transformer
- **Domain Experts**: Bio-Medicine, Blockchain, Cloud-Infra, Comms-Networks, Data-Storage, DevOps, Economics-Finance, Education, Energy, Engineering, Legal, Management, Marketing, Media, Mobile-IoT, Physics, Psychology, QA, Robotics, Security, Supply-Chain
- **Production Systems**: Agent-Company, Agent-Export, Agent-Matching, Pipeline-Orchestrator, Production-Chain, Run-Company-Pipeline
- **Memory Systems**: Memory-Evolution-V2, Memory-Domain (AI, Products, Frontend, Software Engineering, Comprehensive), Parallel-Memory-Orchestrator, RAG-Memory-Enhanced
- **Collection**: Ultimate-Collector, WeChat (9 variants), Xiaohongshu, Toutiao, Bing
- **Quality**: AI-Scoring, QC-Threshold-Optimization, Source-Cleanup-Tag, Unified-Cleaning-Pipeline
- **Infrastructure**: Context-Guardian-Recovery, Long-Running-Task-Infrastructure, Long-Task-Guardian, Task-Resumer, Task-Scheduler
- **Evolution**: Hermes-Self-Evolve-Cluster, Self-Evolution-Agent-Cycle, Evolution-Fix-Actions
- **Security**: Hermes-CaMeL-Guard, Red-Teaming
- **Delivery**: Hermes-Push-V3, V7-Auto-Pipeline, V8-Final-Push

### Extras:
- `hermes-plugin-lineworks` — LINE Works platform integration plugin
- `hermes-agent-docker` — Docker deployment configuration
- `hermes-hud` — Heads-Up Display dashboard (separate project)

---

## 14. Cron Automation: 50+ Scheduled Jobs
**Official**: User-defined cron jobs
**Enhanced**: 50+ automated cron jobs covering all subsystems

Full crontab preserved in `config/crontab_backup.txt`

---

## Cross-Platform Compatibility
- Linux (Ubuntu/Debian/Arch): Full support
- macOS: Full support (systemd services → launchd)
- WSL2: Full support (primary development platform)
- Termux: Supported (Android)
- Docker: Configuration provided in extras/hermes-agent-docker
