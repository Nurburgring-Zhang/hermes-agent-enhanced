# Changelog

All notable changes to Hermes Agent Enhanced.

## [v0.16.0-enhanced-R3] — 2026-06-15

### Polish Round 3 — Final Migration
- Migrated 9 core modules with full integration
- Fixed all F821 (undefined name) lint errors
- Integrated unified_collector pipeline
- Performance optimization pass on core modules
- API documentation (Google-style docstrings) for loop_engine, rule_enforcer, resilience_patterns
- Added Loop Engineering chapter to README
- Created CHANGELOG.md

### Polish Round 2 — Loop Engineering Framework
- Implemented Loop Engineering execution engine (loop_engine.py)
- Added 6-phase lifecycle: wake → plan → execute → verify → record → sleep
- Task DAG with topological sort and parallel isolation
- Token budget tracking with cost estimation
- Trigger watcher: cron, webhook, file watch, continuous
- Video pipeline integration
- Execution sandbox with git worktree isolation

### Polish Round 1 — Code Quality Pass
- Code quality improvements on 4 subsystems
- Lint fixes and formatting
- Test coverage improvements

### Migration
- Migrated 17 systems (47 files) from hermes-enhanced-pack
- Merged artifacts from remote sync
- Security: removed 25 NVIDIA API keys from profile configs
- Fixed pip install — removed deprecated license classifier, added LICENSE file

## [v0.16.0-enhanced-R2] — 2026-06-15 (Sprint Final)

### P3 Modules + Deployability (Final Sprint)
- P3 modules: performance_profiler, security_sandbox, secret_manager, plugin_manager
- Deployability improvements
- Production readiness validation

### Sprint 3
- 268 new tests added
- 3 P2 modules: audit_system, error_framework, dual_review_engine
- AGENTS_v2 specification
- auto_ci dynamic cycle (30-minute loop)
- Removed vault secrets from git tracking

### Sprint 2
- 153 new tests added
- 3 security modules: env_loader, prompt_guard, security_sandbox
- Ruff cleanup pass

### Sprint 1
- 890 tests passing
- CI 4/4 green (lint, test, coverage, security)
- Security audit: 0 HIGH vulnerabilities
- Complete P0 fixes
- Documentation baseline: README, CONTRIBUTING, SECURITY

## [v0.16.0-enhanced-R1] — 2026-06-15

### Initial Enhanced Release
- Based on NousResearch Hermes Agent v0.16.0
- 14-rule enforcement engine (rule_enforcer.py — 1454 lines)
- Ministry ABC multi-agent orchestration (ministry_abc.py — 914 lines)
- Resilience patterns: 10 components (446 lines)
- Gear-driven automation: G0-G7 gear system
- Intelligence collection pipeline: 48 collectors
- Memory system: LLM dual-track architecture
- Agent Company: 12 departments, 130 agents
- 378+ skill modules
- Model intelligent routing

### Key Modules
| Module | Lines | Description |
|--------|-------|-------------|
| rule_enforcer.py | 1454 | R1-R14 rule enforcement engine |
| ministry_abc.py | 914 | Multi-agent orchestration |
| resilience_patterns.py | 446 | Circuit breaker, retry, rate limit, etc. |
| audit_system.py | 858 | Audit trail (Scale AI + AWS CloudTrail) |
| error_framework.py | 549 | RFC 7807 Problem Details |
| dual_review_engine.py | 202 | Dual AI cross-review |
| env_loader.py | 101 | API key security |
| auto_ci.py | 142 | 30-minute CI cycle |
| gear_enforcer.py | 954 | G0-G7 gear enforcement |
| unified_collector_v5.py | 2093 | 48 intelligence collectors |
| memory_engine.py | 918 | LLM dual-track memory |
| loop_engine.py | 1315 | Loop Engineering execution engine |

## Versioning

This project follows a modified semver:
- **Base**: Hermes Agent upstream version (currently v0.16.0)
- **Enhanced**: Release round suffix (-R1, -R2, -R3)

## Legend

- `feat`: New feature
- `fix`: Bug fix
- `security`: Security improvement
- `polish`: Code quality, documentation, performance
- `chore`: Maintenance, tooling
