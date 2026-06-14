---
name: execute-ai-scoring
description: Cron-safe batch AI scoring via real_ai_scorer.py → delegate_task. Processes 20 items per batch with real AI content understanding.
category: intelligence
tags:
  - ai-scoring
  - delegate-task
  - batch-scoring
  - real-ai-scorer
related_skills:
  - ai-six-dimension-scoring-pipeline
---

# Execute AI Scoring — real_ai_scorer.py Workflow

Used when a cron job or interactive session needs to process backlog items with **genuine AI content understanding** (not rule-based keyword matching).

### ⚠️ Known Cmd: `hermes_intelligence_pipeline.py --mode score` DOES NOT EXIST

### 🔍 Operational Finding: After Full Backlog Scoring, Always Verify Numeric Integrity

### 🚨 PITFALL: `LIKE '%规则%'` False-Positives After Delegate-Task Upgrade (2026-05-30)

**Problem**: The format-diagnostic query `CASE WHEN ai_score_reasoning LIKE '%规则%' THEN 'rule_only'` produces **false positives** on properly-upgraded items. After delegate_task generates new reasoning text, common Chinese words like "规则更新", "规则指南", "规则发布", "规则说明" in the reasoning body cause `%规则%` to match even though the item is already in proper JSON format with summary.

**Real-world example (2026-05-30)**: After upgrading 11 items via delegate_task, the query showed "3 remaining rule_only" — but all 3 had `ai_score_reasoning` containing `"summary"` and were legitimately `new_json_format`. They matched `%规则%` only because their reasoning text naturally contained "规则" (e.g. ID=804961 "顺风车高速费到底该谁出？哈啰发布规则指南").

**Fix for diagnostic queries**: After detecting items by `LIKE '%规则%'`, **cross-verify** with `AND ai_score_reasoning NOT LIKE '%summary%'`:
```sql
-- WRONG: catches false positives
WHEN ai_score_reasoning LIKE '%规则%' THEN 'rule_only'

-- CORRECT: only catches rule-only WITHOUT summary
WHEN ai_score_reasoning LIKE '%规则%' 
  AND ai_score_reasoning NOT LIKE '%summary%' 
  THEN 'rule_only'
```

**Fix for `ai_score_upgrade_batch.py`**: If it uses `LIKE '%规则%'` as its primary query, it's safe because its target table should have old-style reasoning that doesn't contain `summary`. But the diagnostic queries that **display** counts need the cross-verify.

**Better diagnostic query** (proven on 2026-05-30, 15,051 items):
```sql
SELECT 
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
    WHEN ai_score_reasoning LIKE '{%' THEN 'json_without_summary'
    ELSE 'other_text_format'
  END as fmt,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY fmt ORDER BY cnt DESC;
```

This avoids all false-positives: `%summary%` is the definitive signal of proper JSON format.

### 🧩 "No Backlog" Completeness Verification Checklist (2026-05-30)

When the initial diagnostic shows "truly_unscored: 0", do NOT declare done yet. Run the full checklist:

```sql
-- Step 1: Truly unscored (standard)
SELECT COUNT(*) FROM cleaned_intelligence
WHERE (ai_score_total IS NULL OR ai_score_total = 0)
  AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '');

-- Step 2: Phantom zero (reasoning exists, total=0) ← EASY TO MISS
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_total = 0
  AND ai_score_reasoning IS NOT NULL AND ai_score_reasoning != '';

-- Step 3: Old-format items hiding behind false-positive LIKE '%规则%'
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_reasoning LIKE '%规则%'
  AND ai_score_reasoning NOT LIKE '%summary%';

-- Step 4: Old-format items with 'AI评分' placeholder text
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_reasoning LIKE '%AI评分%';

-- Step 5: Definitive format distribution (no false positives)
SELECT 
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
    ELSE 'other'
  END as fmt,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY fmt ORDER BY cnt DESC;
```

If all 5 steps show 0 (except `new_json_format = total`), backlog is genuinely clean.

**Root cause**: The `scoring_detail` (six individual columns + `ai_score_reasoning`) and `score_total` (`ai_score_total`) are **updated by different paths**. Some scoring flows set `ai_score_reasoning` (including JSON with summary) but neglect to write the `ai_score_total` and `importance_score` columns. This creates **phantom unscored items** — items that *appear* scored (have reasoning JSON, full six-dimension per-column scores) but show `ai_score_total=0`.

**Real-world example (2026-05-30)**: After clearing all 5 truly unscored items from a 14,988-record table, 2 items remained at `ai_score_total=0`. Both had full AI reasoning JSON in `ai_score_reasoning`, complete `ai_score_scarcity/impact/tech_depth/timeliness/preference/credibility` columns populated... but `ai_score_total` was 0. The content was short (42 chars each, douyin novel topics), so only the reasoning was written, not the total. The `=0` made them invisible to `ai_score_total=0 AND reasoning IS NULL` queries but querying `ai_score_total=0 AND reasoning NOT NULL` revealed them.

**Prevention**: When verifying completion, use THREE queries not one:
```sql
-- Query A: Truly unscored (no reasoning, no total)
SELECT COUNT(*) FROM cleaned_intelligence
WHERE (ai_score_reasoning IS NULL OR ai_score_reasoning = '')
  AND (ai_score_total IS NULL OR ai_score_total = 0);

-- Query B: Phantom zero (has reasoning but total=0) ← EASY TO MISS
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_total = 0
  AND ai_score_reasoning IS NOT NULL AND ai_score_reasoning != '';

-- Query C: Has content > 25c but total=0 (items that SHOULD have been scored)
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_total = 0
  AND LENGTH(COALESCE(content,'')) > 25;

-- Full picture
SELECT 
  SUM(CASE WHEN ai_score_total = 0 AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '') THEN 1 ELSE 0 END) as truly_unscored,
  SUM(CASE WHEN ai_score_total = 0 AND ai_score_reasoning IS NOT NULL AND ai_score_reasoning != '' THEN 1 ELSE 0 END) as has_reasoning_no_total,
  SUM(CASE WHEN ai_score_total > 0 THEN 1 ELSE 0 END) as scored
FROM cleaned_intelligence;
```

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


## ⚠️ Essential Prerequisite: raw→cleaned Before Scoring

Before scoring `cleaned_intelligence` items, **check that the raw→cleaned pipeline has run**. New items in `raw_intelligence` don't automatically flow to `cleaned_intelligence`.

**Quick check:**
```bash
cd ~/.hermes && python3 -c "
import sqlite3
db = sqlite3.connect('intelligence.db')
c = db.cursor()
# Raw not yet cleaned
c.execute('''SELECT COUNT(*) FROM raw_intelligence r
  LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id WHERE c.id IS NULL''')
raw_pending = c.fetchone()[0]
# Unscored in cleaned
c.execute('''SELECT COUNT(*) FROM cleaned_intelligence
  WHERE ai_score_total IS NULL OR ai_score_total = 0
  AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '')''')
unscored = c.fetchone()[0]
print(f'raw→cleaned pending: {raw_pending} | cleaned unscored: {unscored}')
db.close()
"
```

If `raw_pending > 0`, run cleaning first. See `hermes-cleaning-pipeline-v2` skill for `engine/cleaning_engine.py backlog clear` approach.

**Proven workflow (2026-05-30, 2nd validation — 15,268 items, zero backlog):**
```
Step 1: python3 engine/cleaning_engine.py --hours 720 --max 2000  → 14,010 new cleaned items
Step 2: python3 scripts/score_backlog_200.py                       → 11 items scored, 99.99% coverage
Step 3: Verify: 0 truly unscored, 2 phantom zero (legitimate short-content)
Result: 15268 items, 99.99% scored, 0 backlog
```

See `references/cron-safe-rule-engine-scorer.md` for the full clean-then-score workflow with diagnostic sequel.

Valid modes: `all`, `route`, `index`, `generate`, `stats`. There is no `--mode score`.
For scoring, use either `batch_score_200_d.py` (rule-based, fast) or `real_ai_scorer.py` + delegate_task (AI-based).

## Quick Start (single session)

```bash
cd ~/.hermes && python3 scripts/real_ai_scorer.py
```

This:
1. Reads the 20 highest-importance unscored items from `cleaned_intelligence`
2. Generates a prompt file at `reports/_ai_scoring_prompt.json`
3. **Then use delegate_task** to read the prompt and perform real AI scoring

## Alternative: Batch rule-based scoring (for large backlogs)

```bash
cd ~/.hermes && python3 scripts/score_backlog_200.py
```

Script at `~/.hermes/scripts/score_backlog_200.py` — rule-engine scoring, 200 per batch, ~0.3s.
Uses: keyword matching (batch2_ai_scorer.py logic ported), source credibility map, date regex.
Six-dimension scores (0-100), saves directly to `cleaned_intelligence`.

**Works on**: items where `(ai_score_total IS NULL OR = 0) AND (ai_score_reasoning IS NULL OR '')`.
**Covers the `=0` blind spot** that other scorers miss.

**Two-pass strategy for full backlog**: Run with `ORDER BY id ASC` (old first), then `ORDER BY id DESC` (recent first). Repeat until 0 remaining.

## Multi-batch Chaining (cron mode)

For sequential processing of multiple 20-item batches in one session:

```bash
# Round 1
python3 scripts/real_ai_scorer.py
# → delegate_task with context: read _ai_scoring_prompt.json, score, save to DB

# Round 2-4 (repeat — script auto-picks next 20 unscored)
python3 scripts/real_ai_scorer.py
# → delegate_task again with different ai_scored_at timestamp
```

**Key parameters**:
- Batch size: 20 (hardcoded in `real_ai_scorer.py` line 173)
- Sort order: `importance_score DESC, cleaned_at DESC`
- Selection filter: `ai_score_reasoning IS NULL OR '' OR LIKE '%规则评分%'`
- Time per batch: ~82-145s
- Verified throughput: 80 items in ~7 min (4 batches sequential)

## Database Status Distinction

⚠️ **Critical: `ai_score_total = 0` is NOT the same as NULL.**

Two distinct "unscored" states:

| Condition | Meaning | Typical cause |
|-----------|---------|--------------|
| `ai_score_total IS NULL` | Never touched by any scorer | Items that bypassed all scoring pipelines |
| `ai_score_total = 0 AND (ai_score_reasoning IS NULL OR '')` | Treated as "scored 0" by old pipeline | Old pipeline set 0 as placeholder (264 items found 2026-05-29) |
| `ai_score_total = 0 AND ai_score_reasoning NOT NULL` | Legitimately scored 0 | Rare, check reasoning |

**The query for finding truly unscored items MUST use both conditions:**
```sql
WHERE (ai_score_total IS NULL OR ai_score_total = 0)
  AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '')
```

**Beware of the ORDER BY trap:** 
- `ORDER BY id DESC` → picks **recent** items first (good for normal operation)
- `ORDER BY id ASC` → picks **old** items first (need this to clear historical backlog)
- To clear ALL backlog, run TWO passes: one DESC, one ASC

Three categories of unscored items (as of 2026-05-29, after full cleanup):

| Status | Query pattern | Count (typical) | Action |
|--------|--------------|:---------------:|--------|
| Truly unscored | `(ai_score_total IS NULL OR = 0) AND reasoning IS NULL OR ''` | ~0 ✅ | Rule-engine batch before AI upgrade |
| Rule-only scored | `ai_score_reasoning LIKE '%规则评分%'` | ~0 ✅ | Real AI scoring via delegate_task |
| AI scored (any format with summary) | `LIKE '%summary%'` | ~15,618 | Done ✅ |

**Concrete DB snapshot (2026-05-29, after full cleanup using rule-engine batch scorer):**
- Total `cleaned_intelligence`: 15,618 records
- All items scored (ai_score_total > 0): 15,618 ✅ **Zero unscored backlog**
- Of which >=80: 244 | 60-79: 699 | 40-59: 3,171 | 20-39: 11,392 | <20: 112

## Tips for cron-job scoring commands

When asked to "score backlog items" interactively:
1. First check `hermes_intelligence_pipeline.py --mode stats` for overview
2. If truly unscored exists → run `batch_score_200_d.py` repeatedly until 0
3. For high-value rule-only items → use `ai_score_upgrade_batch.py` (direct DeepSeek API, up to 200 items) or `delegate_task` with full item descriptions
4. `batch_score_200_d.py` can be run safely multiple times — it auto-skips already-scored

## Alternative: Rule-Scored → AI-Scored Upgrade

`scripts/ai_score_upgrade_batch.py` converts existing rule-scored items (those with `ai_score_reasoning LIKE '%规则%'`) to genuine AI scoring via the same `score_items_via_openrouter()` function used by `hermes_ai_scoring.py`.

```bash
cd ~/.hermes && python3 scripts/ai_score_upgrade_batch.py
```

**Key difference from other paths**:
- **Target**: Items that already have a rule-based score but need a real AI understanding score
- **Query**: `ai_score_reasoning LIKE '%规则%'` (not `ai_scored_at IS NULL`)
- **Batch size**: 2 per API call (hardcoded), max 200 items per run
- **⚠️ Timeout risk**: At ~8s per API call, 194 items = 97 calls ≈ 776s. If cron timeout is 600s, expect ~140-160 items processed per run. The remaining items stay in rule-scored state and can be picked up next run.
- **No progress loss on timeout**: `score_items_via_openrouter()` uses incremental saving every 5 batches, so partial progress is never lost.

| Column | Range | Description |
|--------|-------|-------------|
| ai_score_scarcity | 0-30 | 独家性 |
| ai_score_impact | 0-30 | 影响力 |
| ai_score_tech_depth | 0-20 | 技术深度 |
| ai_score_timeliness | 0-10 | 时效性 |
| ai_score_preference | 0-10 | 偏好匹配 |
| ai_score_credibility | 0-10 | 可信度 |
| ai_score_total | 0-100 | 六维总和 |
| importance_score | 0-10 | total/10.0 |
| ai_score_reasoning | TEXT | JSON理由 |
| ai_scored_at | TEXT | 评分时间戳 |

## Save Pattern

After sub-agent scores all items, write to DB with:
```python
conn.execute('''UPDATE cleaned_intelligence SET
    ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
    ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
    ai_score_total=?, importance_score=?, ai_score_reasoning=?, ai_scored_at=?
    WHERE id=?''', (...))
```

`ai_score_reasoning` must be a JSON string with keys:
```json
{
  "scarcity_reason": "...",
  "impact_reason": "...",
  "tech_depth_reason": "...",
  "timeliness_reason": "...",
  "preference_reason": "...",
  "credibility_reason": "...",
  "summary": "一句话总结"
}
```

## Pitfalls

- Each delegate_task's `context` MUST contain the full six-dimension scale definitions, or the sub-agent will invent its own scale
- Use unique `ai_scored_at` timestamps per batch for traceability
- The script picks items by `importance_score DESC`, so highest-value items get scored first
- @27000+ rule-only-scored items still waiting for real AI review — batch of 20 per cron cycle adds ~730 real-AI-scored items per year. Consider batching up to 100 if token budget allows.

## ⚡ Parallel Sub-Batch Delegate-Task Scoring (2026-05-29实战验证)

**Problem**: 40-item single delegate_task consistently fails (output length limit).  
**Solution**: Split the backlog into 20-item sub-batches, run 3 concurrently.

### Core Pattern

```bash
# 1. Diagnose first (intelligence.db only — cleaned_intelligence.db has diff schema)
cd ~/.hermes
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
cur = conn.execute('''
  SELECT 
    CASE 
      WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
      WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
      WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored_placeholder'
      WHEN ai_score_reasoning LIKE '%规则%' AND ai_score_reasoning NOT LIKE '%summary%' THEN 'rule_only'
      WHEN ai_score_reasoning LIKE '{%' THEN 'json_format'
      ELSE 'other_text'
    END as fmt,
    COUNT(*) as cnt
  FROM cleaned_intelligence
  GROUP BY fmt ORDER BY cnt DESC
''')
for r in cur.fetchall(): print(f'{r[0]}: {r[1]}')
conn.close()
"
```

### Parallel Sub-Batch Workflow (race-proven in production)

```
Step 1: Query top unscored items, save to JSON file (truncate content to 250 chars)
Step 2: Split into batches of 20 items per file
Step 3: Launch 3 delegate_tasks in parallel, each scoring one 20-item sub-batch
Step 4: Each sub-agent reads file → scores → writes result JSON → writes to SQLite
Step 5: Repeat for remaining sub-batches

Batch size rule: 20 items × ~250c content = ~9KB per batch. 
40 items (~19KB) → sub-agent reads file ok but hits output-limit truncation during response.
20 items (~9KB) → reliable, ~55s per batch.
```

### Implementation Template

Each delegate_task must include in its `context`:
- Full 6-dimension scale table (copy from real_ai_scorer.py lines 88-96)
- User interest keywords with weights
- Items file path (`/home/administrator/.hermes/reports/scoring_batches/sub/batch_N_of_10.json`)
- Result save path
- SQLite update command (one-liner python3 -c)

**The DB write command pattern:**
```python
python3 -c "
import sqlite3,json
conn=sqlite3.connect('/home/administrator/.hermes/data/intelligence.db')
scores=json.load(open('RESULT_FILE.json'))
from datetime import datetime
now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
saved=0
for s in scores:
    total=s['scarcity']+s['impact']+s['tech_depth']+s['timeliness']+s['preference']+s['credibility']
    total=min(total,100)
    reasoning=json.dumps({k:s.get(k,'') for k in ['scarcity_reason','impact_reason','tech_depth_reason','timeliness_reason','preference_reason','credibility_reason','summary']},ensure_ascii=False)
    conn.execute('UPDATE cleaned_intelligence SET ai_score_scarcity=?,ai_score_impact=?,ai_score_tech_depth=?,ai_score_timeliness=?,ai_score_preference=?,ai_score_credibility=?,ai_score_total=?,importance_score=?,ai_score_reasoning=?,ai_scored_at=? WHERE id=?',(s['scarcity'],s['impact'],s['tech_depth'],s['timeliness'],s['preference'],s['credibility'],total,round(total/10,2),reasoning,now,s['id']))
    saved+=1
conn.commit();conn.close()
print(f'DONE:{saved}')
"
```

### Throughput Benchmarks (2026-05-29, real production data)

| Batch type | Items | Time | Rate | Notes |
|------------|:----:|:----:|:----:|-------|
| 25 rule_only+old_json upgrade | 25 | ~81s | 0.31 items/s | First batch, includes cold start |
| Single 40-item delegate_task | 40 | ~118s | 0.34 items/s | One sub-agent got through (batch_3) |
| 3×20 parallel sub-batches | 60 | ~55s | 1.09 items/s | **Fastest** — 3.2× single-batch rate |
| 200 items in 10×20 sub-batches | 200 | ~335s | 0.60 items/s | Total across 5×3-parallel waves |
| Remaining 162 low-value items | 162 | ~280s | 0.58 items/s | Same pattern, progressively lower scores |

### Pitfalls (from 2026-05-29 production run)

1. **Chinese quotation marks break JSON**: Items with `"底线要求"` (全角引号) in their content cause JSON decode errors when writing results. Fix: generate result JSON via Python's `json.dump()` instead of direct file write, or sanitize with `.replace('"', '"').replace('"', '"')`.

2. **File encoding issues with write_file**: The delegate_task's `write_file` with `content_as_text=true` sometimes fails on emoji/special chars. Safer: have the sub-agent write the JSON via `python3 -c "json.dump(scores, open('path','w'), ensure_ascii=False)"`.

3. **Data inflow during processing**: New items arrive from the collection pipeline while scoring is running. Don't re-query mid-session — use the original snapshot file. The final `truly_unscored` count may increase due to new data, not because old items were missed.

4. **Two DB misconception**: `intelligence.db` is the canonical store. `cleaned_intelligence.db` is a separate older database. Always check `intelligence.db` first.

### Combining with other upgrade paths

| Source format | Actions | Best approach |
|---------------|---------|---------------|
| `ai_score_reasoning IS NULL` | Not scored at all | Direct delegate_task scoring |
| `LIKE '%规则%'` | Rule engine scored | Delegate-task AI upgrade |
| `LIKE '{%'` without summary | Old JSON format | Delegate-task AI upgrade (reprocess) |
| **Plain text descriptions** (e.g. `"六维评分: 稀缺性=5/30, 影响力=5/30..."` or `"稀缺性(14/30): 中等稀缺; 影响力(22/30)..."`) | **Old plain-text format** — has scores embedded as Chinese text descriptions, not JSON. Invisible to `{%` detection, `%规则%`, and `%summary%` | **Format-only upgrade** via delegate_task: preserve scores, regenerate ai_score_reasoning as structured JSON with summary |
| Content < 50 chars | Micro-content, often garbage | Score via delegate_task if title has value, archive otherwise |

### ⚡ Format-Only Upgrade (保留分数，只升级reasoning格式)

For items that already have valid scores but use an old plain-text `ai_score_reasoning` format. No need to re-score — just regenerate the reasoning field as proper JSON.

**Use case**: `other_plain_text` category in format diagnosis — items with descriptions like `"稀缺性(14/30): 中等稀缺; 影响力(22/30)..."` in their reasoning field.

**Pattern** (proven on 76 items in 2 parallel delegate_tasks, ~47s total):
```
1. Query items: WHERE ai_score_reasoning NOT LIKE '%summary%' AND NOT LIKE '{%'
2. Export to JSON files (19-20 items per batch → ~9KB, safe for delegate_task)
3. In each delegate_task: read items → preserve existing_scores → generate new structured JSON reasoning for each item
4. DB UPDATE: only touch ai_score_reasoning and ai_scored_at, leave score columns unchanged
5. Launch 2 delegate_tasks in parallel for 76 items → ~47s
```

**Key difference from full AI scoring**: The sub-agent doesn't re-evaluate scores. Its job is purely to interpret the existing scores and generate proper `scarcity_reason/impact_reason/.../summary` fields. This is much faster (~0.6 items/s vs ~0.3 items/s for full scoring).

**Pitfall**: The plain-text format contains embedded score values (e.g. `稀缺性(14/30)`) that the sub-agent might interpret as new scores. Explicitly tell it to **preserve existing_scores** and only format the reasoning text.

## 🆕 Direct Delegate-Task Scoring (bypass real_ai_scorer.py, fastest path)

When you need batch AI scoring and want to skip the `real_ai_scorer.py` prompt-file detour:

1. **Query unscored items** directly from `intelligence.db` (Python or SQL)
2. **Send items to delegate_task** in a single call with full item data (id, title, content[:300], source, published_at)
3. **Save results** to DB with the standard UPDATE query

**Key advantages over real_ai_scorer.py flow:**
- No intermediate prompt file needed
- Sub-agent gets the full scoring context directly
- Can handle items with content < 50 chars (which real_ai_scorer.py filters out)
- Can process unlimited batch sizes (20 is just a default for prompt readability)
- ~21s for 14 short-content items, ~65s for 5 full-content items

**Caveat:** Each delegate_task's context MUST include the full six-dimension scale definitions, or the sub-agent will invent its own scale. Copy the exact table from real_ai_scorer.py's prompt.

```python
# Pattern: direct delegate_task scoring (no real_ai_scorer.py needed)
items = conn.execute("""
    SELECT id, title, content, source, platform, published_at
    FROM cleaned_intelligence
    WHERE ai_score_reasoning IS NULL OR ai_score_reasoning = ''
    ORDER BY importance_score DESC
    LIMIT 20
""").fetchall()

# Then delegate_task with context containing:
# - full 6-dim scale table (copy from real_ai_scorer.py line 88-96)
# - keyword weight hints (from keyword_weights table)
# - item list with id, title, content[:300], source, published_at
# - instruction: output JSON array, each element with id + 6 scores + reasons + summary
```

## 🆕 Delegate-Task AI评分升级（旧格式→AI评分，2026-05-29实战验证）

当 `ai_scored_at IS NOT NULL` 但 `ai_score_reasoning` 是旧格式文本/规则评分时，用delegate_task分批升级：

```bash
# 1. 诊断盲区
cd ~/.hermes && python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
cur = conn.execute('''
  SELECT 
    CASE 
      WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
      WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
      WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored_placeholder'
      WHEN ai_score_reasoning LIKE '%规则%' AND ai_score_reasoning NOT LIKE '%summary%' THEN 'rule_only'
      ELSE 'other'
    END as fmt,
    COUNT(*) as cnt
  FROM cleaned_intelligence
  GROUP BY fmt ORDER BY cnt DESC
''')
for r in cur.fetchall(): print(f'{r[0]}: {r[1]}')
conn.close()
```

如果`other`类别>0且`new_json_format`远小于总量，说明有大量旧格式数据待升级。

**完整工作流**详见 `references/delegate-task-ai-upgrade-pattern.md`。

**已验证**：57条旧格式数据（Batch1 20条/~191s + Batch2 20条/~68s + 最终3条）全部升级为带summary的AI评分格式。

### 🚨 Critical: Blind Spot — Non-Standard `ai_score_reasoning` Formats

The three-category model (truly unscored / rule-only / AI scored) has a **4th hidden category**: items scored by older systems that produce `ai_score_reasoning` matching **neither** `%规则%` **nor** `%AI评分%`.

**Real-world example (2026-05-29):**
- `cleaned_intelligence` had 15,051 items total
- `ai_score_reasoning IS NULL OR ''`: **0** → looked complete
- `LIKE '%规则%'`: **12** → small
- `LIKE '%AI评分%'`: **9,739** → most
- **Remaining: 5,300+ items** with non-standard reasonings (old-format JSON keys like `"scarcity": {...}`, plain-text sentences like `"比亚迪率先为城市领航安全兜底..."`, abbreviated JSON with missing fields) — **invisible to both batch_score and ai_score_upgrade_batch**

**Implications:**
- `batch_score_200_d.py` skips these (it only targets truly NULL reasoning)
- `ai_score_upgrade_batch.py` skips these (its query matches `%规则%` only)
- These items look "scored" from a total-count perspective but may have been scored by different systems/standards
- If you run the upgrade script and see 1-12 items when you expect hundreds, the blind spot is likely active

**The true diagnostic query** to see ALL non-AI-scored items (any format):

```sql
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_reasoning IS NOT NULL AND ai_score_reasoning != ''
  AND ai_score_reasoning NOT LIKE '%评分%'
  AND ai_score_reasoning NOT LIKE '%summary%'
  AND LENGTH(COALESCE(content,'')) > 100;
```

Or more broadly, categorize every reasoning format present:

```sql
SELECT 
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored'
    WHEN ai_score_reasoning LIKE '%规则%' THEN 'rule_only'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
    WHEN ai_score_reasoning LIKE '{"scarcity":%' THEN 'old_json_format_without_summary'
    ELSE 'other_text_format'
  END as format_category,
  COUNT(*) as count
FROM cleaned_intelligence
GROUP BY format_category
ORDER BY count DESC;
```

**Remedy:** When the blind spot is active, the fix is to either:
1. Expand `ai_score_upgrade_batch.py`'s query to include `OR ai_score_reasoning NOT LIKE '%评分%'` (if those items genuinely need rescoring)
2. Or accept that older-format scores are "good enough" and only worry about truly unscored + rule-only items

- `references/near-zero-backlog-final-steps.md` — 🆕 2026-05-30: Near-zero backlog final steps pattern. When only <10 items remain, use manual triage instead of batch scripts. Covers phantom-zero detection (has reasoning JSON but total=0), zero-content garbage archiving, and the `LIKE '%规则%'` false-positive cross-verify.

## See Also

- `references/cron-safe-rule-engine-scorer.md` — 🆕 2026-05-29: Standalone rule-engine batch scorer (score_backlog_200.py), proven on 264 items in ~30s. For cron jobs where delegate_task is unavailable.
- `ai-six-dimension-scoring-pipeline` skill — richer umbrella skill with rule-engine and API-based scoring methods
- `references/delegate-task-batch-scoring.md` — parallel file-shard approach for larger batches (250+ items)
- `references/delegate-task-item-by-item.md` — item-by-item AI scoring with full context in delegate_task call (20 items, ~41s), best for high-value HN/technical items
- `references/scoring-backlog-diagnostics.md` — SQL queries for categorizing all ai_score_reasoning formats, detecting blind spots (`old_plain_text` category), and assessing true backlog completeness
- `references/delegate-task-ai-upgrade-pattern.md` — 🆕 2026-05-29: Delegate-task旧格式→AI评分升级模式，57条实战验证，含盲区检测、导出脚本、评分模板
- `references/parallel-sub-batch-recipe.md` — 🆕 2026-05-29: Exact step-by-step recipe for parallel sub-batch scoring, proven on 342+ items in ~37 min.

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
