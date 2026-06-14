# Delegate Task 直接AI评分模式 — 处理有内容的规则评分积压

## 触发场景

当 cron 环境有以下条件时：

1. `ai_score_reasoning` 含有 `%规则评分%` 或 `%AI评分失败%`
2. `LENGTH(COALESCE(content,'')) > 50`（有真实内容可以理解）
3. `ai_sixdim_scorer.py` 和 `real_ai_scorer.py` 都不处理这些条目
4. 没有 DeepSeek API key 可用
5. 但可以调用 `delegate_task`（本系统内建）

**这个模式的典型症状：** 检查未评分数时发现少量（5-12条）规则评分条目，有内容但未被升级为真正AI评分。

## 完整工作流

### 1. 诊断：检查哪些规则评分条目有内容可评分

```sql
-- 检查有内容的规则评分条目
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE (ai_score_reasoning LIKE '%规则评分%')
  AND LENGTH(COALESCE(content,'')) > 50;

-- 查看具体条目
SELECT id, title, LENGTH(COALESCE(content,'')) as clen, 
       ai_score_total, ai_score_reasoning
FROM cleaned_intelligence 
WHERE (ai_score_reasoning LIKE '%规则评分%')
  AND LENGTH(COALESCE(content,'')) > 50
ORDER BY importance_score DESC;
```

### 2. 导出待评分条目到JSON

```python
import sqlite3, json
conn = sqlite3.connect('intelligence.db')

rows = conn.execute("""
    SELECT id, title, COALESCE(content,'') as content, 
           platform, source, author, tags, category, published_at, url
    FROM cleaned_intelligence 
    WHERE (ai_score_reasoning LIKE '%规则评分%')
    AND LENGTH(COALESCE(content,'')) > 50
    ORDER BY importance_score DESC
""").fetchall()

cols = ['id','title','content','platform','source','author','tags','category','published_at','url']
items = [dict(zip(cols, r)) for r in rows]

with open('reports/_batch_score_items.json', 'w') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"Exported {len(items)} items")
conn.close()
```

### 3. 用 delegate_task 进行真正AI六维评分

构造prompt时，对每条条目提供：
- ID（必须由AI原样返回）
- 标题
- 全部内容（400字符上限）
- 来源
- 发布时间

**prompt模板**（关键要点）：
- 明确要求输出严格JSON数组
- 每维度的说明+评分范围
- AI必须返回 `id` 字段以匹配数据库
- 输出格式示例要清晰

**六维评分范围**：
| 维度 | 范围 | 高分条件 |
|------|------|----------|
| scarcity | 0-30 | 独家/首发/一手 |
| impact | 0-30 | 行业变革/企业战略 |
| tech_depth | 0-20 | 具体技术细节/数据 |
| timeliness | 0-10 | 24h内 |
| preference | 0-10 | 匹配用户核心兴趣 |
| credibility | 0-10 | 官方/一手来源 |

### 4. 直接UPDATE数据库（不经过评分脚本）

评分结果从 delegate_task 返回后，**直接写SQL UPDATE**，不调用任何评分脚本：

```python
import sqlite3, json
from datetime import datetime

conn = sqlite3.connect('intelligence.db')
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

for s in scores:  # scores = delegate_task 返回的JSON
    item_id = s["id"]
    total = s["scarcity"] + s["impact"] + s["tech_depth"] + \
            s["timeliness"] + s["preference"] + s["credibility"]
    total = min(total, 100)

    reasoning = json.dumps({
        "scarcity_reason": s.get("scarcity_reason", ""),
        "impact_reason": s.get("impact_reason", ""),
        "tech_depth_reason": s.get("tech_depth_reason", ""),
        "timeliness_reason": s.get("timeliness_reason", ""),
        "preference_reason": s.get("preference_reason", ""),
        "credibility_reason": s.get("credibility_reason", ""),
        "summary": s.get("summary", ""),
    }, ensure_ascii=False)

    conn.execute("""
        UPDATE cleaned_intelligence SET
            ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
            ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
            ai_score_total=?, importance_score=?,
            ai_score_reasoning=?, ai_scored_at=?
        WHERE id=?
    """, (
        s["scarcity"], s["impact"], s["tech_depth"],
        s["timeliness"], s["preference"], s["credibility"],
        total, round(total / 10.0, 2),
        reasoning, now, item_id
    ))

conn.commit()
conn.close()
print(f"Saved {len(scores)} items")
```

### 5. 归档无内容碎片（content ≤ 50字符）

对于剩余的内容太短无法评分的规则评分条目，直接归档到 `archive_cleaned`：

```python
short_items = conn.execute("""
    SELECT id, title, COALESCE(content,''), ai_score_total, source
    FROM cleaned_intelligence 
    WHERE (ai_score_reasoning LIKE '%规则评分%')
    AND LENGTH(COALESCE(content,'')) <= 50
    ORDER BY importance_score DESC
""").fetchall()

# 创建 archive_cleaned 表（如果不存在）
conn.execute("""
    CREATE TABLE IF NOT EXISTS archive_cleaned 
    AS SELECT * FROM cleaned_intelligence WHERE 1=0
""")
conn.execute("ALTER TABLE archive_cleaned ADD COLUMN archived_at TEXT")
conn.execute("ALTER TABLE archive_cleaned ADD COLUMN archive_reason TEXT")

for r in short_items:
    item_id = r[0]
    row = conn.execute("SELECT * FROM cleaned_intelligence WHERE id=?", (item_id,)).fetchone()
    cols = [d[1] for d in conn.execute("PRAGMA table_info(cleaned_intelligence)").fetchall()]
    d = dict(zip(cols, row))

    cols_str = ','.join(cols)
    placeholders = ','.join(['?' for _ in cols])
    conn.execute(
        f"INSERT INTO archive_cleaned ({cols_str}, archived_at, archive_reason) VALUES ({placeholders}, ?, ?)",
        list(row) + [now, '碎片记录，无内容文本']
    )
    conn.execute("DELETE FROM cleaned_intelligence WHERE id=?", (item_id,))
```

## 关键陷阱

### 1. AI可能不返回 `id` 字段
即使prompt明确要求返回id，某些LLM（如deepseek-chat）仍然省略。如果批量大小=5，无法按位置匹配。**解决方案**：每delegate_task只传1-5条，按返回顺序匹配。

### 2. 内容短的条目评分不准
content < 100字符时，AI评分主要依靠标题和来源判断。最终得分会偏低（20-35分是正常范围）。

### 3. 归档后要验证无残留
```sql
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE ai_score_reasoning IS NULL 
   OR ai_score_reasoning = '' 
   OR ai_score_reasoning LIKE '%规则评分%'
   OR ai_score_reasoning LIKE '%AI评分失败%';
-- 期望结果: 0
```

### 4. 不要对 archive_cleaned 做评分回填
归档表中的条目不会进入推送候选池，不需要评分。

## 实测基准（2026-05-29）

| 指标 | 值 |
|------|-----|
| 待评分条目数 | 5条（有内容） |
| 碎片归档数 | 7条（0内容） |
| delegate_task耗时 | ~11秒/5条 |
| 评分覆盖（AI真正评分） | 5/5 = 100% |
| 最高分 | 84分（特斯拉Robotaxi） |
| 最低分 | 22分（大禹金融包销协议） |
| 最终cleaned中未评分残留 | 0条 ✅ |
