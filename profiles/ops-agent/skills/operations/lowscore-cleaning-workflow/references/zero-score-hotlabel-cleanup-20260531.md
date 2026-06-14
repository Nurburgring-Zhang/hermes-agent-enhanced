# 2026-05-31 零分数据归档 — 热点标签元数据

## 背景
cleaned_intelligence中发现了9条ai_score_total=0的数据，来自微博/抖音/百度等热点平台。
这些条目的content字段不是文章内容，而是元数据标签（如"Label:新 Score:290209"、"实时上升 | 视频:1 | 讨论:1"）。

## 根因
统一采集器(v5)采集了热点平台的标签数据，这些数据被清洗管道正常处理进入cleaned_intelligence，
但评分脚本发现content无实质内容，无法做六维评分，留下了0分占位。

## 修复方法
```python
items = conn.execute("""
    SELECT id, cleaned_id, title, source, content, ai_score_total, ai_scored_at
    FROM cleaned_intelligence 
    WHERE ai_score_total = 0 
      AND (ai_scored_at IS NULL OR ai_scored_at = '')
    ORDER BY id
""").fetchall()

# 对每条做判断：有content但content是元数据的，给低分归档；无content的，同理
# 使用score_item()函数做最终评分
from scripts.hermes_intelligence_pipeline import calc_item_scores

for item in items:
    scores = calc_item_scores(item[2] or '', item[4] or '', item[3] or '', '')
    total = scores['total']
    # 写回数据库
    conn.execute("""UPDATE cleaned_intelligence SET
        ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
        ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
        ai_score_total=?, ai_score_reasoning=?, ai_scored_at=?
        WHERE id=?""",
        (scores['scarcity'], scores['impact'], scores['tech_depth'],
         scores['timeliness'], scores['preference'], scores['credibility'],
         total, scores['reasoning_json'], now, item[0]))
```

## 验证SQL
```sql
SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0;
-- 应为0
SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = '';
-- 应为0
```

## 结果
- 9条数据评分范围14-23分（低分符合内容质量）
- 64条score<20归档到archive_cleaned
- 最终 cleaned_intelligence = 15,065条，100%评分
