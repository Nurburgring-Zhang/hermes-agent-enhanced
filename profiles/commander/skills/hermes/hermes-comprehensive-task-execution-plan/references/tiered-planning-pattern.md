# Tiered Enhancement Planning Pattern (P0-P3)

## Structure

Enhancement tasks (non-greenfield) follow a **P0 → P1 → P2 → P3** tier system:

| Tier | Horizon | What | Cadence |
|:----:|:--------|:-----|:--------|
| **P0** | This conversation | Foundation layer. Must be deployed before session ends. | Immediate |
| **P1** | This week | Core functional upgrades. | Day-level |
| **P2** | Next week | Quality/review infrastructure. | Week-level |
| **P3** | Next month | Advanced evolution. | Sprint-level |

## Validation Gate for Each Tier

Before declaring a tier item "done", pass through:

```
1. File exists    → stat -c%s <path>
2. Auto-running   → crontab -l | grep <name>  
3. Output correct → python3 -c "import json; d=json.load(open(...))"
4. Layer active   → head -5 ~/.hermes/SOUL.md (is it really the indexed version?)
```

## Tier Template for Plan Documents

```markdown
### P{X}-{N}: Feature Name

**Background:** Why this needs to change.

**Implementation:**
| File | Change |
|------|--------|
| `path/to/file.py` | What to add/change |

**Verification:**
- `command to verify step 1`
- `command to verify step 2`

**Priority:** P{X} | **Estimate:** {N}h
```

## Anti-Patterns to Avoid

- ❌ Declaring done after file exists but cron not deployed
- ❌ Verifying with "I tested it earlier" instead of a re-runnable command
- ❌ Memory-level claims ("I remember fixing that") — always read the file
- ❌ Saying "完全实现" without enumerating the 4 verification layers

## Signals That Trigger Re-Planning

- User asks "核实" or "真的完成了吗"
- User provides a corrective preference about workflow
- A cron-check finds 0 entries where there should be N
- Files exist only as `.pyc` (bytecode) but `.py` source is gone
