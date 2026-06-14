---
name: openclaw-workspace-migration
description: Migrate from OpenClaw workspace to another agent system - complete framework integration with philosophy merging, memory architecture, and protocol preservation
category: migration
complexity: high
reusability: high
created: 2026-04-08
based_on: Real migration from OpenClaw to Hermes-compatible workspace
---

# OpenClaw Workspace Migration & Integration

## When to Use

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Use this skill when you need to:
- Migrate from OpenClaw (or similar workspace-based agent) to a new agent system
- Integrate OpenClaw's operational philosophy into an existing agent framework
- Bootstrap a new workspace following OpenClaw patterns
- Merge multiple operational frameworks while preserving core mandates

## Prerequisites

- Access to the existing OpenClaw installation (typically `~/.openclaw/workspace/`)
- Ability to create files in the target workspace directory
- Understanding of the target agent's core principles (to avoid conflicts)

## The Approach

### Phase 1: Discovery & Analysis

1. **Locate OpenClaw workspace**
   ```bash
   # Check common locations
   ls ~/.openclaw/workspace/
   ls ~/.openclaw/
   # May exist at custom paths from openclaw.json
   ```

2. **Read core workspace files** (all in workspace root):
   - `SOUL.md` - Core philosophy and identity
   - `AGENTS.md` - Workspace protocols, memory system, safety rules
   - `TOOLS.md` - Local environment notes (empty template, check if populated)
   - `IDENTITY.md` - Agent self-description template
   - `USER.md` - Human profile template
   - `BOOTSTRAP.md` - First-run conversation guide
   - `HEARTBEAT.md` - Periodic check tasks
   - (optional) `MEMORY.md` - Long-term memory (if exists)

3. **Read system configuration**:
   ```bash
   cat ~/.openclaw/openclaw.json
   ```
   Extract:
   - Agent defaults (model, workspace path, concurrency limits)
   - Gateway configuration (port, auth mode, denied commands)
   - Skills installation preferences
   - Models and providers

4. **Check existing memory structure**:
   ```bash
   ls ~/.openclaw/workspace/memory/ 2>/dev/null || echo "No daily notes"
   # Check if MEMORY.md exists in workspace root
   ```

### Phase 2: Framework Assessment & Conflict Resolution

1. **List existing hard mandates** (from target agent's SOUL.md or memory)
   - Docker prohibition?
   - Complete implementation requirements?
   - Quality vs speed priorities?
   - Security constraints?

2. **Identify potential conflicts**:
   - OpenClaw allows Docker? → Need to override with "Docker forbidden"
   - Different memory architecture? → Merge or choose one
   - Conflicting automation principles? → Resolve by keeping stricter rule

3. **Decision rule**: When in doubt, preserve BOTH - document the target agent's mandates as absolute, and treat OpenClaw as advisory philosophy that doesn't override hard rules.

### Phase 3: SOUL.md Merging

1. **Read current SOUL.md** from target agent
2. **Add new section** after "Vibe" or similar: "OpenClaw Heritage — Operational Principles"
3. **Copy OpenClaw's key protocols verbatim**:
   - Session Initialization Protocol (step-by-step reading sequence)
   - Memory Architecture (daily notes + long-term, security rule about MEMORY.md)
   - Write It Down - No Mental Notes
   - External vs Internal Actions
   - Group Chat Etiquette (when to respond, when to stay silent, reactions)
   - Heartbeats vs Cron (with concrete examples)
   - Tools vs Skills Separation
   - Platform Formatting rules
   - Safety reminders

4. **Preserve all existing mandates** - do not modify original content

### Phase 4: Workspace Bootstrap

Create these files in the **target workspace root** (usually `~/workspace` or desktop):

```
IDENTITY.md    # Template: Name, Creature, Vibe, Emoji, Avatar
USER.md        # Template: Name, pronouns, timezone, notes, context
AGENTS.md      # Full copy from OpenClaw (operational protocols)
TOOLS.md       # Empty template for local notes
HEARTBEAT.md   # Empty template with comment structure
MEMORY.md      # Template with structure and examples (main sessions only)
BOOTSTRAP.md   # First-run conversation script
SYSTEM.md      # Configuration summary (from openclaw.json)
```

### Phase 5: Memory Infrastructure

```bash
mkdir -p /target/workspace/memory
touch /target/workspace/memory/$(date +%Y-%m-%d).md
```

Create `memory/heartbeat-state.json`:
```json
{
  "lastChecks": {
    "email": null,
    "calendar": null,
    "weather": null,
    "mentions": null,
    "project_status": null
  },
  "checkRotation": ["email", "calendar", "weather", "mentions", "project_status"],
  "notes": "Track periodic checks here"
}
```

### Phase 6: State Tracking

Create `.openclaw/workspace-state.json` to record migration:
```json
{
  "version": 2,
  "mergedFrom": "OpenClaw",
  "mergeDate": "2026-04-08T11:30:00Z",
  "bootstrapSeededAt": "2026-04-08T11:30:00Z",
  "status": "fully_merged",
  "components": ["SOUL.md", "IDENTITY.md", ...]
}
```

### Phase 7: Memory Entry

Add to persistent memory (memory tool):
```
OpenClaw Migration Completed (YYYY-MM-DD):

✅ Full system merge accomplished:
- Merged SOUL.md with OpenClaw operational philosophy
- Created complete workspace: IDENTITY.md, USER.md, AGENTS.md, TOOLS.md, HEARTBEAT.md, MEMORY.md, BOOTSTRAP.md, SYSTEM.md
- Established memory architecture: daily notes + long-term MEMORY.md (main session only)
- Implemented security rule: MEMORY.md never loaded in shared contexts
- Added heartbeat tracking with memory/heartbeat-state.json
- Preserved hard mandates: [list your specific mandates]

Key protocols now active:
- Session init: Read SOUL.md → USER.md → memory files → MEMORY.md (if main)
- External vs Internal actions distinction
- Group chat etiquette (when to speak/react)
- Platform-specific formatting rules
- Proactive heartbeat checks (2-4x daily)
- Tools vs Skills separation
```

## Verification Checklist

After migration, verify:

```
✅ SOUL.md contains both original mandates AND OpenClaw Heritage section
✅ AGENTS.md exists and matches OpenClaw's protocol
✅ IDENTITY.md, USER.md, TOOLS.md, HEARTBEAT.md, MEMORY.md, BOOTSTRAP.md created
✅ SYSTEM.md documents configuration (gateway, models, agents)
✅ memory/ directory exists with today's date file
✅ memory/heartbeat-state.json exists
✅ .openclaw/workspace-state.json exists
✅ All file permissions are correct (600 for sensitive, 644 for docs)
```

## Common Pitfalls & Mitigations

| Pitfall | Mitigation |
|---------|------------|
| OpenClaw workspace not at `~/.openclaw/workspace` | Check `openclaw.json` for `agents.defaults.workspace` path |
| Conflicting Docker stance | Explicitly document "Docker forbidden" in merged SOUL; OpenClaw heritage doesn't override |
| MEMORY.md security rule forgotten | Add prominent comment in AGENTS.md: "MEMORY.md ONLY for main sessions" |
| Forgetting to create memory/ directory | Always `mkdir -p memory` before first session |
| Overwriting existing user's IDENTITY.md/USER.md | Never overwrite; if files exist, read them first and only add missing sections |
| Missing heartbeat-state.json tracking | Create immediately after memory/ directory |

## Adapting to Other Systems

To migrate from a different framework (AutoGPT, BabyAGI, etc.):

1. Follow same discovery pattern - locate their "soul" or philosophy files
2. Extract their operational protocols (session init, memory handling, tool usage)
3. Merge with target agent's hard mandates using this skill's conflict resolution approach
4. Create workspace structure matching their conventions while preserving target's security model

The key is **respectful integration**: honor the source system's wisdom without compromising the target's non-negotiable rules.

## Post-Migration

1. **Fill IDENTITY.md** - Have the agent define itself (name, creature, vibe, emoji)
2. **Fill USER.md** - Document the human's preferences and context
3. **First session** - Follow BOOTSTRAP.md conversation script, then delete it
4. **Daily operation** - Follow AGENTS.md protocols exactly
5. **Memory hygiene** - Every few days, review recent memory/YYYY-MM-DD.md files and distill into MEMORY.md

---

**Skill Metadata**
- Complexity: High (multi-file integration, framework merging, security considerations)
- Tested: Yes (real OpenClaw → Hermes migration)
- Version: 1.0.0
## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
