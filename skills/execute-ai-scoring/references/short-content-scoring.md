# Short-Content Scoring Pattern (delegate-task bypass)

## Problem

`real_ai_scorer.py` (line 56) filters out items where `LENGTH(COALESCE(content,'')) > 50`:

```python
AND LENGTH(COALESCE(content,'')) > 50
```

This means zhihu questions, weibo posts, and short-item Baidu/toutiao entries are **permanently skipped** by the normal scoring pipeline. They accumulate as "unscored" even after all normal backlog runs complete.

## Root Cause

Many social-platform items have content < 50 chars because:
- Zhihu questions are just the title (content is empty or very short)
- Weibo posts are often headlines with minimal context
- Douyin/fast-share entries carry only metadata

These items have **importance_score** > 0 (based on platform weighting) but never get AI scoring.

## Fix: Direct delegate_task scoring (bypass real_ai_scorer.py)

```python
# 1. Query even short-content items
items = conn.execute("""
    SELECT id, title, COALESCE(content,'') as content,
           source, platform, published_at
    FROM cleaned_intelligence
    WHERE ai_score_reasoning IS NULL OR ai_score_reasoning = ''
    ORDER BY importance_score DESC
""").fetchall()

# 2. Score via delegate_task with context including:
#    - 6-dim scale table (0-30,0-30,0-20,0-10,0-10,0-10)
#    - user preference keywords
#    - item details (even short content + title)
# 3. Save results to DB (same UPDATE query as normal scoring)
```

**2026-05-29 result:** 14 short-content items scored in ~22s via single delegate_task call.
Scores were reasonable because even with short/no content, title + source + platform was enough for AI judgment.

## Query to Detect Remaining Short Scorable Items

```sql
SELECT COUNT(*) as short_unscored
FROM cleaned_intelligence
WHERE (ai_score_reasoning IS NULL OR ai_score_reasoning = '')
  AND LENGTH(COALESCE(content,'')) <= 50
  AND LENGTH(COALESCE(title,'')) > 5;
```
