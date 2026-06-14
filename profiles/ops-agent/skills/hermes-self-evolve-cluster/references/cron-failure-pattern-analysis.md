# Cron Failure Pattern Analysis

## Detected in 2026-05-30 self-evolution run

### Observed Pattern
capability_evolve detected **9 cron tasks failing** with `Script not found`:
```
[降级] context-packer: Script not found: /home/administrator/.hermes/scripts/script
[降级] context-index-system: Script not found: /home/administrator/.hermes/scripts/script
[降级] G1齿轮执行器: Script not found: /home/administrator/.hermes/scripts/script
[降级] hy-memory-recall-inject: Script not found: /home/administrator/.hermes/scripts/python
[降级] hy-memory-l1-extract-daily: Script not found: /home/administrator/.hermes/scripts/python
```

### Root Cause
The capability_evolve module reads cron job `script` fields from state.db, but the script name extraction logic truncates the path:

- `scripts/hermes_xxx.py` → truncates to `scripts/script` (first 14 chars of `hermes_xxx.py` = `script`)
- `python3 scripts/hermes_xxx.py` → truncates to `scripts/python` (first 6 chars of `python3` = `python`)

This is **not a real file loss** — it's a name truncation bug in the scanning logic of `hermes_self_evolve_cluster.py`.

### How to Verify (Real vs Fake)
```bash
# Real check: list all cron jobs with their actual script paths
cd ~/.hermes && python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/state.db')
if os.path.exists(db):
    conn = sqlite3.connect(db, timeout=10)
    c = conn.cursor()
    for row in c.execute('SELECT id, name, script, schedule, status FROM cron_jobs'):
        print(f'{row[0][:12]} | {row[1]:45s} | {row[2][:50]} | {row[3]:20s} | {row[4]}')
    conn.close()
"
```

### Failure Pattern Classification
| Pattern | Signal | Action |
|---------|--------|--------|
| `Script not found: scripts/script` | Truncation bug in scanner | Ignore (verify with above SQL first) |
| `Script not found: scripts/python` | `python3 xxx.py` parsed as script=`python3` | Ignore (command prefix extraction failure) |
| `Script not found: /path/to/file.py` + file truly missing | Real loss | Restore or remove cron job |
| `exit code != 0` but script exists | Runtime error | Check script logs |

### Historical Context
The same 9 cron tasks have been showing as failed since at least 2026-05-28 (based on prior self-evolution logs). They are repeatedly detected and "paused" each cycle. The pause action is cosmetic — the cron jobs continue to exist in state.db with `status=paused`. The root fix is to either:
1. Fix the script name truncation in `hermes_self_evolve_cluster.py`'s scanning logic
2. Or accept that these are known false positives and filter them from capability_evolve's recommendation output

### Related Skills
- `capability-verification` — has "采集量暴跌误报诊断" section (same class of false-positive)
- `cron-audit-and-cleanup` — cron audit workflow for confirmed failures
