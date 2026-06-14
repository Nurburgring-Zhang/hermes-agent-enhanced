# Missing ai_scored_at Timestamp Edge Case

## Scenario

All items have `ai_score_total > 0` with proper JSON `ai_score_reasoning`, but **7 items** have `ai_scored_at IS NULL`. The items are fully scored — just missing the timestamp field.

## Diagnosis

```sql
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE ai_score_total > 0 AND ai_scored_at IS NULL;
-- → 7 (or any small number)
```

These items have:
- `ai_score_total > 0` (e.g., 23, 36, 43)
- `ai_score_reasoning` as proper JSON with scarcity/impact/tech_depth/... dimensions
- `ai_scored_at IS NULL` — the only thing missing

**This is NOT a scoring backlog.** These items were scored by a code path that didn't set the timestamp field (e.g., the original `batch2_ai_scorer.py` or a manual UPDATE that omitted `ai_scored_at`).

## Fix

Simple SQL patch — set the timestamp to now (or the `collected_at` time):

```python
import sqlite3
from datetime import datetime

db = sqlite3.connect('intelligence.db')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
count = db.execute('''
    UPDATE cleaned_intelligence 
    SET ai_scored_at = ?
    WHERE ai_scored_at IS NULL AND ai_score_total > 0
''', (now,)).rowcount
db.commit()
print(f'Fixed {count} items with missing timestamps')
db.close()
```

## Root Cause

The `batch2_ai_scorer.py` or similar batch scoring scripts may set all six dimension scores and `ai_score_total` but forget `ai_scored_at`. This is a harmless data inconsistency — no content is missing, no scoring needs to be redone.

## Detection Pattern

Part of the "all clear" confirmation checklist (see `cron-backlog-entry-point.md`):

```sql
-- Step 1: check real backlog
SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0;

-- Step 2: check timestamp integrity (this edge case)
SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NULL;
```

If Step 1 = 0 and Step 2 > 0: apply the SQL fix above. Only if Step 1 > 0 do you need actual scoring.

## All-Clear Snapshot (2026-05-30)

| Check | Result |
|-------|--------|
| cleaned_intelligence total | 15,994 |
| ai_score_total IS NULL | 0 |
| ai_score_total = 0 | 0 |
| ai_scored_at IS NULL (after fix) | 0 |
| Score range | 20.0 - 100.0 |
| Average score | 41.7 |
| Scoring pipeline health | ✅ All items fully scored with JSON reasoning |
