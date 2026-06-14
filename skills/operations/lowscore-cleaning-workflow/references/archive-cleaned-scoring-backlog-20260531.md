# archive_cleaned 评分积压清理 — 2026-05-31

## 发现
`scripts/hermes_intelligence_pipeline.py --mode score` 只查 `cleaned_intelligence` 表，**不查 `archive_cleaned` 表**。

2026-05-31 21:04 运行 `--mode score` 报告：
- `cleaned_intelligence`: 3条积压 ✅ 已处理
- `archive_cleaned`: **223条积压**（完全未触及）

## 清理方法
直接手动调用 `calc_item_scores` 对 `archive_cleaned` 评分（与pipeline scoring逻辑一致）：

```python
import sqlite3, sys
sys.path.insert(0, '.')
from scripts.hermes_intelligence_pipeline import calc_item_scores
from datetime import datetime

conn = sqlite3.connect('data/intelligence.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('''
    SELECT id, title, COALESCE(content,'') as content,
           source, platform, published_at
    FROM archive_cleaned
    WHERE (ai_score_total IS NULL OR ai_score_total = 0)
    AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '')
    ORDER BY id ASC LIMIT 200
''').fetchall()

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for row in rows:
    scores = calc_item_scores(
        row['title'] or '', row['content'] or '',
        row['source'] or '', row['platform'] or ''
    )
    conn.execute('''UPDATE archive_cleaned
        SET ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
            ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
            ai_score_total=?, importance_score=?, ai_score_reasoning=?, ai_scored_at=?
        WHERE id=?''', (
            scores['scarcity'], scores['impact'], scores['tech_depth'],
            scores['timeliness'], scores['preference'], scores['credibility'],
            scores['total'], scores['importance_score'],
            scores['reasoning_json'], now, row['id']
        ))
conn.commit()
conn.close()
```

## 评分统计
- 清理量: 224条（223条正常 + 1条脏数据删除）
- 平均分: 35.5，范围 33-52
- 低分(<40): 202条 (90.2%)
- 最高分: 52 — "Langflow：这个拖拽式AI工作流神器正在颠覆传统编程"

## 脏数据清理
`archive_cleaned` 中发现1条 `id=NULL` 的脏数据：
- title: "当老师说可以穿自己喜欢的衣服"
- source: douyin
- content: 仅42字符（"热度值:7673370 | group_id:..."）
- 整行都非NULL值但id为NULL → 需要 DELETE

```sql
DELETE FROM archive_cleaned WHERE id IS NULL;
```

## 结论
pipeline的 `--mode score` 已可用（区别于技能中旧陷阱#8的记录），但只覆盖 `cleaned_intelligence`。`archive_cleaned` 的评分需要手动补跑。建议在pipeline `score_mode()` 函数中加入对 `archive_cleaned` 表的处理，或至少在技能中记录手动修补代码。
