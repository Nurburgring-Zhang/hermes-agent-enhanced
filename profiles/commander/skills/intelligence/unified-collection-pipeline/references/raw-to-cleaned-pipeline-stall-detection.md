# Raw→Cleaned Pipeline Stall Detection

## Problem

Cleaned data is fully scored, but raw items accumulate without being cleaned. The scoring pipeline (`--mode score`) finds nothing because it only checks `cleaned_intelligence.ai_score_total IS NULL`.

## How to Detect

```sql
-- Check raw → cleaned gap
SELECT COUNT(*) FROM raw_intelligence r
LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id
WHERE c.id IS NULL;
```

If >100, raw items are not flowing into cleaned — they'll never get scored or pushed regardless of score backlog being "empty".

## Drill Down

```sql
-- By source (to find which collectors are stalling)
SELECT r.source, r.collected_at, COUNT(*) as cnt
FROM raw_intelligence r
LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id
WHERE c.id IS NULL
GROUP BY r.source
ORDER BY cnt DESC;

-- By date (to see how old the clog is)
SELECT MIN(r.collected_at), MAX(r.collected_at)
FROM raw_intelligence r
LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id
WHERE c.id IS NULL;
```

## Real-World Example (2026-06-02)

| Check | Result |
|-------|--------|
| cleaned_intelligence total | 14,809 |
| cleaned unscored | **0** — looks clean |
| raw → cleaned gap | **1,413** — real problem hidden |
| Dominant source | CSDN (1,376 items, 97%) |
| Date range | 2026-05-27 ~ 2026-06-02 (7 days stalled) |

## Why This Happens

CSDN is collected by `csdn_blog_collector.py` (independent collector wrapped in unified collector). It self-manages its own DB writes. When wrapped via `wrap_csdn()`, it inserts to `raw_intelligence` directly, but the **cleaning pipeline may not pick up those raw records** if:

1. The cleaning pipeline's SELECT query filters on records it hasn't seen yet
2. The cleaning pipeline uses `cleaned_at` timestamps that exclude newly-batched raw items
3. The cleaning pipeline runs via cron but the CSDN collector's raw insertion rate outpaces cleaning

## How to Fix

### Quick: manually run cleaning mode
```bash
cd ~/.hermes && python3 scripts/hermes_intelligence_pipeline.py --mode all --limit 500
```
Or if the cleaning is in a separate script:
```bash
cd ~/.hermes && python3 scripts/unified_cleaning_pipeline.py
```

### Permanent: add raw→cleaned gap monitoring to health checks
Add this check to any cron that does pipeline monitoring:

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('intelligence.db')
gap = c.execute('''
  SELECT COUNT(*) FROM raw_intelligence r
  LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id
  WHERE c.id IS NULL
''').fetchone()[0]
if gap > 200:
    print(f'WARNING: raw→cleaned gap = {gap}')
c.close()
"
```

## Prevention

When checking pipeline health, always verify **both** gates:
- ✅ `cleaned_intelligence` has no unscored backlog (standard check)
- ✅ raw → cleaned gap is small (<200) (easy to miss)
