# Self-Recovery Engine Pattern

## Core Principle

The system **must detect and fix its own degradation** without waiting for the user to notice. User correction from this session: "为什么不是Hermes主动检查" — passive waiting is not acceptable.

## Components

| Component | File | Runs | Job |
|:----------|:-----|:-----|:----|
| ConsistencyGuard | `scripts/consistency_guard.py` | Every 5 turns | Checks files/crons/gear/context. Reports anomalies. |
| AutoHealer | `scripts/auto_healer.py` | Every 5 min cron | Matches known anomaly patterns, runs predefined fixes. Escalates after 3 consecutive failures. |
| SelfRecovery | `scripts/self_recovery.py` | On demand (`--check` or no flag) | Scans backup drives (M:/D:/C:/), restores missing files + cron. Runs full test suite. |

## Known Auto-Repairable Patterns

| Anomaly | Detection | Fix | Status |
|:--------|:----------|:----|:-------|
| context_index sections=0 | consistency_guard | Run `context_index_system.py auto` | ✅ Verified |
| File missing (.py deleted) | consistency_guard | Restore from /mnt/d/Hermes/备份/ | ✅ Implemented |
| Cron entry missing | consistency_guard | Re-add from internal registry | ✅ Implemented |
| Gear not healthy | consistency_guard | Restart gear_enforcer via cron | ✅ Implemented |

## Deployment Verification Baseline

On first deployment, record a health baseline:

```bash
# Run and save
stat -c%s ~/.hermes/scripts/context_packer.py
crontab -l | grep -cE "context_|surgical|consistency"
python3 -c "import json; d=json.load(open('~/.hermes/reports/context_index.json')); print(len(d['sections']))"
```

Then on subsequent checks, compare against baseline. Any regression triggers auto-repair.

## Anti-Patterns

- ❌ Waiting for the user to verify the system is running
- ❌ "I fixed it" without showing a re-runnable verification command
- ❌ Only checking file existence, not checking whether the file's output is actually being consumed
