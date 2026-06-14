# 双AI互审固化层清单

| 层 | 位置 | 机制 | 持久性 |
|----|------|------|--------|
| SOUL.md | ~/.hermes/SOUL.md | 核心规则段,不可违反 | 每次对话加载 |
| AGENTS.md | ~/.hermes/AGENTS.md | 规则8,固化级指令 | 每次对话加载 |
| config.yaml | ~/.hermes/config.yaml | dual_ai_review.enabled=true | 系统配置 |
| MEMORY.md | ~/.hermes/MEMORY.md | 日常记录 | 每次对话注入 |
| dual-ai-review skill | ~/.hermes/skills/autonomous-systems/dual-ai-review/ | 完整流程定义 | 按需加载 |
| cron | 每分钟 | 检测完整性 | 持续后台 |
| CLI启动器 | hermes_cli/__init__.py | 启动时自动检查 | 每次启动 |
| startup脚本 | ~/.hermes/scripts/startup_dual_review.sh | 启动时自动检查 | 每次启动 |
| 5个核心skill前置依赖 | production-reliability-engine等 | 调用链锁死 | 每次调用 |

## 验证命令
grep "双AI互审" ~/.hermes/SOUL.md
grep "规则8" ~/.hermes/AGENTS.md
grep "dual_ai_review" ~/.hermes/config.yaml
grep "双AI互审永久固化" ~/.hermes/MEMORY.md
ls ~/.hermes/skills/autonomous-systems/dual-ai-review/SKILL.md
grep "dual-review-integrity" ~/.hermes/cron/jobs.json 2>/dev/null
