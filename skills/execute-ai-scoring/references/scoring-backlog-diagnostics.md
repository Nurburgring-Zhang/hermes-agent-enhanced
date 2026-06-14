# Scoring Backlog Diagnostic Queries

Quick-reference SQL queries to assess the true state of unscored/underscored items in `cleaned_intelligence`.

## Quick Health Check

```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 1 ELSE 0 END) as truly_unscored,
    SUM(CASE WHEN ai_score_reasoning IS NOT NULL AND ai_score_reasoning != '' THEN 1 ELSE 0 END) as any_scored,
    SUM(CASE WHEN ai_score_total >= 70 THEN 1 ELSE 0 END) as high_value,
    SUM(CASE WHEN ai_score_total < 20 AND ai_score_reasoning IS NOT NULL THEN 1 ELSE 0 END) as low_value
FROM cleaned_intelligence;
```

## Categorize All Reasoning Formats

Reveals the blind spot: items scored by older systems that match neither `%规则%` nor `%AI评分%`.

**6 known formats (verified on 15,051 items, 2026-05-30):**

| Category | Detection | Meaning | Pitfall |
|----------|-----------|---------|---------|
| `truly_unscored` | `IS NULL OR ''` | Never scored | None |
| `new_json_format` | `LIKE '%summary%'` | Proper JSON with summary and reasons | **This is the definitive signal** — items that match `%规则%` but NOT `%summary%` are the real rule-only items |
| `ai_scored` | `LIKE '%AI评分%'` | Old format with "AI评分" placeholder text | Usually has summary but empty/placeholder individual reasons |
| `rule_only` | `LIKE '%规则%'` AND NOT `LIKE '%summary%'` | Rule engine scored, needs AI upgrade | **🚨 False-positive trap**: Chinese text naturally contains "规则" (规则更新, 规则指南). Always cross-verify with `NOT LIKE '%summary%'` |
| `json_without_summary` | `LIKE '{%'` AND NOT `LIKE '%summary%'` | Old JSON format, missing summary field | None |
| `other_text_format` | NOT `{%` AND NOT `%summary%` AND NOT `%规则%` AND NOT `%AI评分%` | Plain Chinese text with embedded scores | Invisible to upgrade scripts |

### 🚨 Critical: `LIKE '%规则%'` False-Positive Bug (Discovered 2026-05-30)

The query `WHEN ai_score_reasoning LIKE '%规则%' THEN 'rule_only'` **false-positives** on properly-upgraded items.

**Why**: After delegate_task generates new reasoning text, items like "顺风车高速费到底该谁出？哈啰发布规则指南" (ID=804961) have "规则指南" in their reasoning body. The `%规则%` match catches them even though they already have `summary` in their JSON.

**Fix**: Always use `NOT LIKE '%summary%'` as a guard:
```sql
WHEN ai_score_reasoning LIKE '%规则%' 
  AND ai_score_reasoning NOT LIKE '%summary%' 
  THEN 'rule_only'
```

**Better primary query** (avoids all false-positives):
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

```sql
SELECT 
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
    WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored_placeholder'
    WHEN ai_score_reasoning LIKE '%规则%' AND ai_score_reasoning NOT LIKE '%summary%' THEN 'rule_only'
    WHEN ai_score_reasoning LIKE '{%' THEN 'json_without_summary'
    ELSE 'other_text_format'
  END as format_category,
  COUNT(*) as count
FROM cleaned_intelligence
GROUP BY format_category
ORDER BY count DESC;
```

## Find Items That Both Upgrade Scripts Miss

```sql
SELECT id, title, ai_score_total, 
       SUBSTR(ai_score_reasoning, 1, 80) as reason_preview,
       LENGTH(COALESCE(content,'')) as content_len
FROM cleaned_intelligence
WHERE ai_score_reasoning IS NOT NULL AND ai_score_reasoning != ''
  AND ai_score_reasoning NOT LIKE '%评分%'
  AND ai_score_reasoning NOT LIKE '%summary%'
  AND LENGTH(COALESCE(content,'')) > 200
ORDER BY ai_score_total DESC
LIMIT 20;
```

## Detect Old Plain-Text Format (Format-Only Upgrade Candidates)

Items that have scores embedded in Chinese plain text (not JSON) and need format-only upgrade:

```sql
-- Check count
SELECT COUNT(*) as old_plain_text_count
FROM cleaned_intelligence
WHERE ai_score_reasoning IS NOT NULL AND ai_score_reasoning != ''
  AND ai_score_reasoning NOT LIKE '%summary%'
  AND ai_score_reasoning NOT LIKE '{%';

-- Preview samples
SELECT id, title, ai_score_total, SUBSTR(ai_score_reasoning, 1, 100) as reasoning_prev
FROM cleaned_intelligence
WHERE ai_score_reasoning IS NOT NULL AND ai_score_reasoning != ''
  AND ai_score_reasoning NOT LIKE '%summary%'
  AND ai_score_reasoning NOT LIKE '{%'
LIMIT 10;

-- Export for format-only upgrade (preserve scores, regenerate reasoning JSON)
SELECT id, title, content, source, platform, published_at,
       ai_score_scarcity, ai_score_impact, ai_score_tech_depth,
       ai_score_timeliness, ai_score_preference, ai_score_credibility,
       ai_score_total, importance_score
FROM cleaned_intelligence
WHERE ai_score_reasoning IS NOT NULL AND ai_score_reasoning != ''
  AND ai_score_reasoning NOT LIKE '%summary%'
  AND ai_score_reasoning NOT LIKE '{%'
ORDER BY ai_score_total DESC;
```

## Find Non-standard Format Samples

```sql
SELECT DISTINCT 
  CASE 
    WHEN ai_score_reasoning LIKE '{%' AND ai_score_reasoning LIKE '%"scarcity"%' AND NOT ai_score_reasoning LIKE '%"scarcity_reason"%' THEN 'old_score_format'
    WHEN ai_score_reasoning LIKE '{%' AND ai_score_reasoning LIKE '%"scarcity_reason"%' THEN 'new_score_format'
    ELSE 'plain_text_format'
  END as format_type,
  COUNT(*) as count
FROM cleaned_intelligence
WHERE ai_score_reasoning IS NOT NULL AND ai_score_reasoning != ''
  AND ai_score_reasoning NOT LIKE '%评分%'
  AND ai_score_reasoning NOT LIKE '%规则%'
GROUP BY format_type;
```
