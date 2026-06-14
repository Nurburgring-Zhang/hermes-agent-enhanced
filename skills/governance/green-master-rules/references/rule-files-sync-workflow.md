# Rule Files Sync Workflow

**Context:** SOUL.md §八 rules must be mirrored identically across 4 files.
**Trigger:** Any update to §八 rules content.
**Files to keep in sync:**

| File | Path | Format | Audience |
|------|------|--------|----------|
| SOUL.md | `~/.hermes/SOUL.md` | Full markdown | Hermes core |
| AGENTS.md | `~/.hermes/AGENTS.md` | Full markdown | All AI agents (Claude Code, Copilot, Cline, Aider) |
| CLAUDE.md | `~/.hermes/CLAUDE.md` | Compact markdown | Claude Code |
| .cursorrules | `~/.hermes/.cursorrules` | JS-comment rules | Cursor / Windsurf |

## Sync Protocol

### When updating SOUL.md §八:
1. **Update SOUL.md first** — full verbose version, all rules in detail
2. **Update AGENTS.md** — same level of detail as SOUL.md. This is the canonical agent-facing copy.
3. **Update CLAUDE.md** — compact version. Each rule as a single bold paragraph. Preserve all 7 strengthening points but in fewer words.
4. **Update .cursorrules** — JS-comment concise version. Each rule as single dash line with `**` emphasis on new enforcement points.

### Consistency checks per rule:

| Rule | Signal to verify | grep pattern |
|------|-----------------|--------------|
| R2 中断恢复 | "主动自检" must exist | `grep -c "主动自检"` |
| R3 阶段性复盘 | "确认无误后" or "确认无误才" | `grep -c "确认无误"` |
| R4 全局复盘 | "严禁任何虚假" or "虚假/降级" | `grep -c "严禁任何虚假\|虚假/降级"` |
| R5 深度自检 | "深度自检" must exist | `grep -c "深度自检"` |
| R6 强制循环 | "至少3轮" must exist | `grep -c "至少3轮"` |
| R7 降级禁令 | "不等用户指出" must exist | `grep -c "不等用户指出"` |

### When NOT to sync:
- Cosmetic-only changes (typo fix, formatting, version number)
- Adding examples or references (those go in SOUL.md only)
- OI/tech content (only lives in SOUL.md §九)

## File-specific notes

### CLAUDE.md format tradeoffs
Compact means:
- R2: `**任务中断→必须主动自检、自动恢复继续执行！！！回顾历史文档→明确标准→高质量实现！** 每10分钟自审查，卡死立刻恢复。**任何中断不得终止任务，必须执行到完整结束。**`
- R3: `**任何任务每个阶段执行完毕后：阶段性复盘+历史回顾→确保方向不跑偏→确认所有要求标准条件满足→确认无误才进下一阶段。**`
- R7 uses bullet list for prohibitions, bold for critical enforcement.

### .cursorrules RULES format
JS-comment style. Each rule is a single `- RULE_N: ...` line. Use `**bold**` for emphasis. Keep each rule under 200 chars. The Cursor IDE loads these into system prompt — long rules eat context.
