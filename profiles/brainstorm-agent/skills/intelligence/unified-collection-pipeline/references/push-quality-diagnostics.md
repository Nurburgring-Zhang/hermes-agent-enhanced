# Push Quality Diagnostics — Dedup Windows, Old Data Leakage, Repetition Patterns

## Class of Problem

User complains about "重复推送" / "旧闻太多" / "信息不新鲜". The root cause is almost never the PushPlus API — it's always a **time-window mismatch** between candidate selection and dedup exclusion, or **old-published data** masquerading as fresh content.

## Systematic Diagnostic Flow

### Step 0: Check Push Schedule

First, establish which cron agents are triggering pushes:

```bash
# Check Hermes Agent cron jobs (the primary scheduler for v12 push)
cat ~/.hermes/cron/jobs.json | python3 -c "
import json,sys
data=json.load(sys.stdin)
jobs=data if isinstance(data,list) else data.get('jobs',[])
for j in jobs:
    n=j.get('name','?')
    if 'v12' in n or '推送' in n or 'push' in n.lower():
        print(f\"  {j.get('schedule_display','?'):13s} | {n:30s} | 启用:{j.get('enabled')} | 最后:{str(j.get('last_run_at','?'))[:16]}\")
"

# Check system crontab for push jobs
crontab -l 2>/dev/null | grep -iE 'push|v9|v11|v12'
```

**Key findings from real data (2026-05-30)**:
- 4 v12 push jobs: 0:00, 8:00, 14:00, 20:00 — each via Hermes Agent cron with `--push` flag
- No system crontab push jobs (all via Hermes cron)
- **Common bug**: cron job runs WITHOUT `--push` flag → scripts silently enter DRY RUN → log shows "DRY RUN" but user sees nothing in WeChat
- **Another bug**: same-title news gets re-pushed across different cron runs because the dedup window is shorter than the interval between runs

### Step 1: Diagnose the Dedup Time Window Mismatch

**The single most common bug pattern**: candidate selection uses a WIDE time window, but dedup exclusion uses a NARROW time window.

```python
# In hermes_v12_push.py, push_v12() — check these two values:
candidates = get_candidates_balanced()  # Line 791, typically 72h window
already_pushed = set(... WHERE push_time >= ? ..., (datetime.now() - timedelta(hours=6),))  # Line 782-783, typically 6h window
```

**The mismatch**: If candidates span 72h but dedup only excludes 6h:
- A news item pushed at 8:00 AM is NOT excluded at 14:00 PM (8h gap > 6h window)
- Same item gets pushed 6+ times across 3 days
- **Real example**: "龙虾 OpenClaw 工程师示警" was pushed **6 times** (5/24 08:17, 14:17, 22:17, 5/25 08:00, 14:17, 22:17)

**Diagnostic SQL**:
```sql
-- Find titles pushed more than once
SELECT title, COUNT(*) as cnt, MIN(push_time), MAX(push_time)
FROM push_records 
GROUP BY title 
HAVING cnt > 1 
ORDER BY cnt DESC 
LIMIT 20;

-- Check if gaps between same-title pushes are < 6h (dedup failure)
SELECT title, push_time FROM push_records 
WHERE title IN (
    SELECT title FROM push_records GROUP BY title HAVING COUNT(*) >= 2
)
ORDER BY title, push_time;
```

### Step 2: Diagnose Old-Data Leakage into Candidate Pool

`get_candidates_balanced()` filters by `collected_at >= 72h ago` — this is the **collection** timestamp, NOT the **publication** timestamp. Old articles (2014-2025) recently re-collected pass through.

**Diagnostic SQL**:
```sql
-- Count old data in 72h collection window
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE collected_at >= datetime('now', '-3 days')
AND published_at NOT LIKE '2026%' AND published_at != '';

-- Check source of old data
SELECT source, COUNT(*) FROM cleaned_intelligence 
WHERE collected_at >= datetime('now', '-3 days')
AND published_at NOT LIKE '2026%' AND published_at != ''
GROUP BY source ORDER BY COUNT(*) DESC;
```

**Real data** (2026-05-30): **1134 non-2026 items** in 72h candidate pool, with items as old as **2009**.

### Step 3: Cross-Day Repetition Analysis

Even with dedup fixed within a 24h window, the same title can reappear tomorrow because:
- The candidate pool resets every cron run (same 72h SQL window)
- The dedup window uses a rolling 6h window, not a per-title max-count

```python
# Record-keeping check: are same titles appearing across multiple days?
SELECT title, DATE(push_time), COUNT(*) 
FROM push_records 
GROUP BY title, DATE(push_time)
HAVING COUNT(*) > 1;
```

### Step 4: Verify the Push Script's Dedup Logic Directly

Read lines 778-830 of `hermes_v12_push.py`:

```python
# Line 782-783: dedup window
cutoff = (datetime.now() - timedelta(hours=6)).isoformat()  
#   ^^^ 6h is TOO SHORT for 4x/day push + 72h candidate window

# Line 738-741: record_pushed() dedup check
existing = c.execute(
    "SELECT id FROM push_records WHERE title=? AND push_time >= ?",
    (title, (datetime.now() - timedelta(hours=24)).isoformat())
).fetchone()
#   ^^^ This checks 24h, but only when writing — doesn't prevent in-memory selection
```

### Step 5: Fixed-Pool Stagnation Check

If candidate pool is fixed (e.g., 300 items from 72h window) and pushes happen 4x/day:
- First push: takes top 25
- Second push: takes next 25 from remaining 275
- **Same 300 items**, just re-ranked
- By 4th push, some items from the first push are now >6h old → re-appear in candidate pool

**Solution**: Add `AND NOT EXISTS (SELECT 1 FROM push_records WHERE title = c.title AND push_time >= ?)` to the candidate SQL, or expand dedup to 72h.

## Three Common Bugs and Their Fixes

### Bug A: 6h Dedup Window → 72h Leakage

**Symptoms**: Same headline appears 6+ times across 3 days in WeChat push.

**Root cause**: `already_pushed` set (line 783) only checks `push_time >= 6h ago`. A 14h gap between pushes means the item is NOT in this set.

**Fix**: Expand dedup window to match candidate window:
```python
# OLD:
cutoff = (datetime.now() - timedelta(hours=6)).isoformat()
# NEW:
cutoff = (datetime.now() - timedelta(hours=72)).isoformat()  # match get_candidates_balanced() window
```

**Also fix** the `record_pushed()` dedup (line 738-741):
```python
# OLD: 24h check
# NEW: 72h check (or better: max 2 pushes per title ever)
existing_count = c.execute(
    "SELECT COUNT(*) FROM push_records WHERE title=?", (title,)
).fetchone()[0]
if existing_count >= 2:
    continue  # hard limit: never push the same title more than twice
```

### Bug B: Published_at Timestamp Parsing Failures

**Symptoms**: Some pushed items have `published_at` like `"Wed, 30 Apr 2014 09:38:00 +0800"` or `"Fri,"` (day-name only).

**Root cause**: `is_recent_published()` (line 352-369) returns `None` for malformed dates, and the caller only checks `>= 15` ai_score, not the time.

**Real data**: 2880+ cleaned_intelligence records have `published_at` starting with day names (Mon/Tue/Wed/Thu/Fri/Sat/Sun) instead of ISO dates — these are all parsing failures from different collectors.

**Fix**: Add a `published_at` sanity check in `get_candidates_balanced()`:
```sql
-- OLD: no published_at filter
-- NEW:
AND (published_at LIKE '2026%' OR published_at IS NULL)
```

### Bug C: Cron Jobs Running Without --push Flag

**Symptoms**: v12_push.log shows "DRY RUN" but no error. User doesn't receive push.

**Root cause**: The cron job prompt says "command: python3 scripts/hermes_v12_push.py" without `--push`. The script defaults to dry-run.

**Verification**: Search v12_push.log for "DRY RUN":
```bash
grep "DRY RUN" ~/.hermes/logs/v12_push.log | wc -l
```
If >0, the cron job needs to be updated to add `--push`.

## Full Diagnostic Quick-Command

Run from `~/.hermes/`:

```bash
python3 << 'PYEOF'
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/intelligence.db')
c = conn.cursor()

print("=== PUSH QUALITY DIAGNOSTIC ===\n")

# 1. Push schedule
print("[1] Push records in last 24h:")
c.execute('SELECT push_time, COUNT(*) FROM push_records WHERE push_time >= ? GROUP BY push_time ORDER BY push_time',
           ((datetime.now() - timedelta(hours=24)).isoformat(),))
for pt, cnt in c.fetchall():
    print(f"  {pt}: {cnt}条")

# 2. Duplicate titles
c.execute('SELECT title, COUNT(*) FROM push_records GROUP BY title HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 10')
dups = c.fetchall()
print(f"\n[2] Top repeated titles (total: {len(c.fetchall() if hasattr(c, 'fetchall') else dups)}):" if False else f"\n[2] Top repeated titles:")
for title, cnt in dups:
    print(f"  [{cnt}x] {title[:55]}")

# 3. Old data in candidate pool
cutoff_72h = (datetime.now() - timedelta(hours=72)).isoformat()
c.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE collected_at >= ? AND published_at NOT LIKE '2026%' AND published_at != ''",
          (cutoff_72h,))
old_in_pool = c.fetchone()[0]
print(f"\n[3] Non-2026 items in 72h candidate pool: {old_in_pool}")

# 4. Published_at parsing issues
c.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE published_at GLOB '[A-Z][a-z][a-z],*'")
dayname_issues = c.fetchone()[0]
print(f"[4] Records with day-name timestamp (parsing failures): {dayname_issues}")

conn.close()
print("\n=== DONE ===")
PYEOF
```

## Known Resolutions (2026-05-30)

| Issue | Root Cause | Fix | Status |
|-------|-----------|-----|--------|
| 906 titles repeated across pushes | 6h dedup window vs 72h candidate window | Expand to 72h dedup + per-title max=2 | ⬜ Not yet applied |
| 1134 old items in candidate pool | SQL filters by collected_at not published_at | Add `published_at LIKE '2026%'` to SQL | ⬜ Not yet applied |
| Day-name timestamps (2880+ records) | Multiple collectors output non-ISO date formats | Fix in cleaning pipeline | ⬜ Known issue |
| Cron DRY RUN | Cron prompt missing `--push` flag | Update cron job description | ⬜ Validate |

## See Also

- `unified-collection-pipeline` — parent umbrella skill covering the full collection→cleaning→scoring→push pipeline
- `hermes-pushplus-troubleshooting` — PushPlus delivery failure diagnosis (different class of problem: API reachability vs content quality)
- `unified-collection-pipeline/references/health-radar-scan-20260528.md` — 10-dimension health scan that includes push health as one dimension
- `unified-collection-pipeline/references/three-pipeline-break-pattern-20260528.md` — collection→cleaning→scoring pipeline break points
