# Cron-Safe Rule-Engine Batch Scorer

**Created:** 2026-05-29  
**Proven on:** 264 items (200 recent + 64 old) in ~30s total

## Purpose

A standalone, dependency-free rule-engine scorer for cron jobs that need to process large backlogs (200+ items) without delegate_task, DeepSeek API, or any external service. Runs in <1s per batch of 200.

## Logic (copied from batch2_ai_scorer.py)

Six-dimension rule-engine scoring:

| Dimension | Range | Heuristics |
|-----------|-------|-----------|
| Scarcity | 0-30 | "全球首/独家"=26, "首款/首次"=18, "泄露/曝光"=20, "报告/调研"=14, default=10 |
| Impact | 0-30 | "颠覆/改变格局"=24, "认证/标准"=18, "政策/监管"=18, "AI/芯片发布"=14, default=8 |
| Tech Depth | 0-20 | arch+perf params=18, arch+perf=15, 5+ tech terms=12, 3+ terms=8, 1+ term=6, default=4 |
| Timeliness | 0-10 | Date regex matching against today (5月29日=10, 5月28日=9, ..., 4月=2, 2025年=1) |
| Preference | 0-10 | AI/ML keywords counter: >=5=9, >=3=7, >=1.5=5, else=3 |
| Credibility | 0-10 | Source map: ithome/36kr/HN=8, weibo=4, tieba=3, default=6. +1 for citations |

Total is capped at 100 (min 0).

## Usage

```bash
cd ~/.hermes && python3 scripts/score_backlog_200.py
```

Outputs: log to `logs/score_backlog_<date>.log` + stdout summary with TOP10 and BOTTOM5.

## Pattern: Clearing ALL Backlog (Two-Pass Strategy)

The `score_backlog_200.py` script uses `ORDER BY id ASC LIMIT 200` by default (oldest first). To clear the **entire** backlog:

### Pass 1: Old data first (default)
```bash
python3 scripts/score_backlog_200.py
```
→ Clears oldest 200 items

### Pass 2: Recent data (patch ORDER BY)
Edit the SQL in `score_backlog_200.py`:
```python
ORDER BY id DESC  # instead of ASC
```
```bash
python3 scripts/score_backlog_200.py
```
→ Clears most recent 200 items

### Repeat until 0
Run `python3 scripts/score_backlog_200.py` in same ORDER direction until output says "无未评分数据".

## Production Results (2026-05-29)

| Phase | Direction | Items | Avg Score | Min | Max |
|-------|-----------|:-----:|:---------:|:---:|:---:|
| Pass 1 | DESC (recent) | 200 | 43.4 | 36 | 58 |
| Pass 2 | ASC (old) | 64 | 42.8 | 34 | 62 |
| **Total** | | **264** | **43.2** | **34** | **62** |

## File Location

`/home/administrator/.hermes/scripts/score_backlog_200.py` — created 2026-05-29 for this specific purpose. Can be run repeatedly; auto-skips already-scored items.

## Proven End-to-End Workflow: Clean Then Score (2026-05-30)

When cron asks to "process scoring backlog", the correct two-step sequence is:

```bash
# Step 1: Clean raw→cleaned (brings in new items)
cd ~/.hermes && python3 engine/cleaning_engine.py --hours 720 --max 2000

# Step 2: Score the newly cleaned items
python3 scripts/score_backlog_200.py
```

**Real-world result (2026-05-30)**: Cleaning produced 14,010 new cleaned items, of which only 11 were truly unscored — the rest arrived already scored from the upstream pipeline. This is typical: the collection+cleaning pipeline pre-scores most items, leaving only a small tail of edge cases (short-content, rare sources) for `score_backlog_200.py` to handle.

**Key insight**: The unscored count after cleaning is almost always much smaller than the new-item count. Don't expect 14K items to score — expect 0-50 max. If you see 0 truly unscored after cleaning, the system is healthy.

### Diagnostic Sequel

After Step 2, verify with the three-query picture to catch phantom zeros:

```bash
cd ~/.hermes && python3 -c "
import sqlite3
conn = sqlite3.connect('data/intelligence.db')
c = conn.execute('''
  SELECT 
    SUM(CASE WHEN ai_score_total=0 AND (ai_score_reasoning IS NULL OR ai_score_reasoning='') THEN 1 ELSE 0 END),
    SUM(CASE WHEN ai_score_total=0 AND ai_score_reasoning IS NOT NULL AND ai_score_reasoning!='' THEN 1 ELSE 0 END),
    SUM(CASE WHEN ai_score_total>0 THEN 1 ELSE 0 END),
    COUNT(*)
  FROM cleaned_intelligence
''').fetchone()
print(f'truly_unscored={c[0]} phantom_zero={c[1]} scored={c[2]} total={c[3]}')
conn.close()
"
```

### What to Skip

- Do NOT run `--mode score`: it does not exist in `hermes_intelligence_pipeline.py`
- Do NOT check `raw_intelligence` for all-clear: new data flows in constantly from collectors, so pending-raw count is always >0
- Do NOT re-score already-scored items: `score_backlog_200.py` auto-skips them

## Limitations vs AI Scoring

- Rule engine misses semantic nuance (e.g., "蓝色起源火箭爆炸" scored 36 because it lacks AI/ML keywords)
- Cannot detect industry-disrupting events that don't use trigger keywords
- Timeliness is regex-based against explicit dates, can't infer "today from context"
- Use as first-pass bulk scorer, then use delegate_task for high-value items (score >= 60+)

## Pitfall: DB Path Issue

The script's `DB_PATH = HERMES + "/data/intelligence.db"` may fail if `data/intelligence.db` is a broken symlink or the script runs from a different working directory. The canonical database is at `~/.hermes/intelligence.db` (~94MB, actual data store). If the script reports 0 unscored items when you expect hundreds, check the DB path first.

**Fix**: Change `DB_PATH = HERMES + "/data/intelligence.db"` to `DB_PATH = HERMES + "/intelligence.db"` in the script. (Fixed 2026-05-30 during backlog scoring of 14,988-record table.)
