# Delegate-Task Item-by-Item AI Scoring Pattern

## When to use this

When you have 10-30 high-value items (usually HN/arXiv/technical) that were only rule-scored and need genuine AI content understanding with individual analysis.

This is **different** from `real_ai_scorer.py` which generates a prompt file to a sub-agent — this embeds item details directly in the `context` parameter so the sub-agent has all the information in one turn.

## Pattern (used 2026-05-28 for 20 HN items)

```python
# Call delegate_task with context containing full item descriptions
delegate_task(
    context="""
以下是N条情报条目...规则评分:
- 条目 #id — Title | 来源 | content-length | 规则分N分
- 条目 #id — Title | 来源 | content-length | 规则分N分
...
每条给出AI六维评分并保存。
""",
    goal="""用AI对以下情报条目做真正的内容理解六维评分。
每条给出 scarcity(0-30), impact(0-30), tech_depth(0-20),
timeliness(0-10), preference(0-10), credibility(0-10)，合计总分0-100。

输出JSON数组格式，含评分原因和中文summary。

完整评分标准：
- 稀缺性0-30: 独家首发25-30,深度分析15-24,转载5-14,普通0-4
- 影响力0-30: 行业变革25-30,公司战略15-24,产品更新5-14,一般0-4
- 技术深度0-20: 具体技术细节15-20,有分析8-14,普通0-7
- 时效性0-10: 24h内9-10,48h内7-8,一周内4-6,更早0-3
- 偏好匹配0-10: 完全匹配9-10,部分5-8,不相关0-4
- 可信度0-10: 官方一手9-10,知名媒体7-8,普通4-6,不明0-3

输出JSON格式：
[
  {
    "id": 12345,
    "scarcity": 0-30,
    ...
    "scarcity_reason": "中文原因",
    ...
    "summary": "一句话价值总结(中文)"
  }
]
""",
    toolsets=["web"]  # optional, for verification
)
```

## Save results to DB

After sub-agent returns JSON, execute UPDATE statements:

```python
import sqlite3, json
from datetime import datetime

conn = sqlite3.connect('/home/administrator/.hermes/intelligence.db')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

for s in scores:  # scores = JSON from sub-agent
    item_id = s["id"]
    total = s["scarcity"] + s["impact"] + s["tech_depth"] + s["timeliness"] + s["preference"] + s["credibility"]
    total = min(total, 100)
    reasoning = json.dumps({
        "scarcity_reason": s["scarcity_reason"],
        "impact_reason": s["impact_reason"],
        "tech_depth_reason": s["tech_depth_reason"],
        "timeliness_reason": s["timeliness_reason"],
        "preference_reason": s["preference_reason"],
        "credibility_reason": s["credibility_reason"],
        "summary": s["summary"],
    }, ensure_ascii=False)

    conn.execute("""UPDATE cleaned_intelligence SET
        ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
        ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
        ai_score_total=?, importance_score=?, ai_score_reasoning=?, ai_scored_at=?
        WHERE id=?""", (
        s["scarcity"], s["impact"], s["tech_depth"],
        s["timeliness"], s["preference"], s["credibility"],
        total, round(total/10.0, 2), reasoning, now, item_id
    ))

conn.commit()
conn.close()
```

## Performance characteristics

| Metric | Value |
|--------|-------|
| Items per batch | 20 |
| Duration (deepseek-chat) | ~41s (7 API calls, 2638+3886 tokens) |
| Items per context character | ~130 chars/item (title + summary) |
| Model used | deepseek-chat (via sub-agent) |
| Cost per batch | ~6524 tokens (I+O) |

## Items best suited for this pattern

- **Show HN** / **Launch HN** items — genuine AI understanding needed to assess technical merit
- **arXiv papers** — abstract-level scoring needs content understanding, not keyword match
- **Unique-source items** where source credibility is ambiguous
- Items with **high rule-score but unknown real value** (rule engine can over-score it-home content)

## Items to skip for this pattern

- Short social media blurbs (<200 chars)
- Duplicate/topic-hash content
- Rule-score below 40 (low quality, not worth AI analysis)
