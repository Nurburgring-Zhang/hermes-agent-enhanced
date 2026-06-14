# Pipeline Run: 2026-05-30 21:03 — value_level Data Healing + Expert Routing

## Situation

Cron job triggered to process "unscored backlog" via `hermes_intelligence_pipeline.py --mode score`. However:
- `--mode score` does NOT exist (mode must be `all/route/index/generate/stats`)
- All 15,324 records in `cleaned_intelligence` were ALREADY scored (ai_score_total all non-null)
- But 118 records had corrupted `value_level`: 100 with `0`, 18 with `'pending'` string

## What Was Done

### Step 1: Database Diagnosis Found Two Issues

```sql
-- value_level distribution
SELECT DISTINCT value_level, COUNT(*) FROM cleaned_intelligence GROUP BY value_level;
-- Result: 2(10350), 1(2756), 3(1203), 4(618), 5(271), 0(100), 'pending'(18)
```

### Step 2: Fix value_level Data Corruption

118 records had invalid value_level. Script-based healing:

```python
UPDATE cleaned_intelligence 
SET value_level = CASE 
    WHEN ai_score_total >= 80 THEN 5
    WHEN ai_score_total >= 60 THEN 4
    WHEN ai_score_total >= 40 THEN 3
    WHEN ai_score_total >= 20 THEN 2
    ELSE 1
END
WHERE value_level IS NULL OR value_level = 0 OR value_level = 'pending';
```

### Step 3: Fix Pipeline crash (⭐⭐ * 'pending')

Two functions in `hermes_intelligence_pipeline.py` crashed with:
```
TypeError: can't multiply sequence by non-int of type 'str'
```

Root cause: `stars = "⭐" * item["value_level"]` where value_level could be `'pending'`.

Fix applied to both `write_diary()` and `write_memory()`:
```python
vl = int(item["value_level"]) if item["value_level"] else 0
stars = "⭐" * vl
```

Additionally, the `f-string` got corrupted during patching, requiring a full file rewrite.

### Step 4: Run Pipeline (--mode all)

```bash
python3 scripts/hermes_intelligence_pipeline.py --mode=all
```

Results:
- **200 items** processed (48h, 4+ stars)
- **402 routes** to expert queue (19 domains)
- **200 RAG indexes** created
- **50 P0 tasks** generated (5-star items)
- Domain breakdown: AI/ML(139), Frontend/UX(68), Network/Comm(44), Security(25), Art/Design(23), Economics(22), Software Eng(13), Math/Theory(13), Mobile/IoT(9), Cloud(8), Physics/Materials(7), Product/Biz(6), Mgmt/Comm(6), DevOps(5), Data/Storage(4), Legal(3), Bio/Med(2), Content/Creative(1), QA(1)

### Step 5: Expert Queue Stats After Processing

```sql
-- expert_consult_queue: 812 pending items
-- RAG index: 2,087 entries
-- All 15,324 cleaned items scored (0 zero-scores, 8,877 low/20-39, 5,277 med/40-59, 1,162 high/60+)
```

## Key Insights

1. **value_level 'pending' is a real data quality issue** — it comes from cleaning pipeline SQL that uses `DEFAULT 'pending'` or leaves it NULL, but later code assumes it's an integer. The healing pattern is a simple CASE on ai_score_total.

2. **Both `write_diary()` and `write_memory()` in pipeline.py have the same `stars` pattern** — fixing one but not the other leaves a half-broken pipeline.

3. **`--mode score` doesn't exist** — the pipeline checks for new 4+ star data and routes/indexes/tasks it, but doesn't score. For scoring, use `ai_scoring_v2.py --batch 500` or `real_ai_scorer.py`.

4. **Pipeline processes LIMIT 200 per run** — if there are 479+ items in 48h, it takes 3 runs to catch up. Since pipeline has no "already processed" tracking (no processed_at flag), subsequent runs re-process the same items (INSERT OR IGNORE in queue).
