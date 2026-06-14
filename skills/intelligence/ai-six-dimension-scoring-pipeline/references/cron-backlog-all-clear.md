# 积压评分"全部清零"确认模式 — Cron诊断参考

## 场景：cron要求"处理未评分积压"，返回"全部已评分"

### 预期输出

```json
{
  "mode": "score",
  "limit": 200,
  "processed": 0,
  "skipped": 1,
  "score_stats": {},
  "top_scores": [],
  "bottom_scores": [],
  "message": "无未评分数据，cleaned_intelligence全部已评分"
}
```

- `processed: 0` = 本次未处理新数据
- `skipped: 1` = 跳过了处理（因为不需要）
- 这不是错误，这是**正确认证**——系统健康

### 一键确认库存

```python
import sqlite3
c = sqlite3.connect('/home/administrator/.hermes/intelligence.db')
cur = c.cursor()

# 真正的未评分积压（需要关注）
clean_null = cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0").fetchone()[0]

# 队列情况
queue_pending = cur.execute("SELECT COUNT(*) FROM ai_score_queue WHERE status='pending'").fetchone()[0]

# raw层未处理（需由清洗管道处理，不是评分问题）
raw_total = cur.execute("SELECT COUNT(*) FROM raw_intelligence").fetchone()[0]

print(f"cleaned_intelligence 待评分: {clean_null}")
print(f"ai_score_queue pending: {queue_pending}")
print(f"raw_intelligence 原始数据: {raw_total}（等待清洗管道）")

# 评分分布
total_clean = cur.execute("SELECT COUNT(*) FROM cleaned_intelligence").fetchone()[0]
cur.execute("SELECT ai_score_total FROM cleaned_intelligence")
scores = [r[0] for r in cur.fetchall() if r[0] is not None]
if scores:
    a = sum(1 for s in scores if s >= 80)
    b = sum(1 for s in scores if 60 <= s < 80)
    c_ = sum(1 for s in scores if 40 <= s < 60)
    d = sum(1 for s in scores if s < 40)
    print(f"评分分布({len(scores)}/{total_clean}): >=80:{a}  60-79:{b}  40-59:{c_}  <40:{d}")
    print(f"平均分: {sum(scores)/len(scores):.1f}  最高: {max(scores)}  最低: {min(scores)}")

c.close()
```

### 正常行为特征

| 指标 | 正常值 | 异常信号 |
|------|--------|----------|
| `cleaned_intelligence` 待评分 | 0（全部清零） | >0 → 需要评分 |
| `ai_score_queue pending` | 0 | >0 → 队列中有待处理 |
| 评分覆盖 | 100% | <100% 检查新入库数据 |
| `raw_intelligence` 积压 | 持续有新数据（正常） | 数万条且不在下降 = 清洗管道卡住 |

### 注意事项

- `raw_intelligence` 中大量原始数据是正常的——它持续增长，清洗管道会处理
- 只有当 `cleaned_intelligence` 中有 `ai_score_total IS NULL` 条目时才需要评分
- 评分积压清零不表示数据管道停止——`raw_intelligence` 持续有新数据=采集正常
- `archive_cleaned` 中有大量 0 分数据是历史状态，**不需要处理**

### 🔴 边缘情况：score=0 但 reasoning 非空（`--mode score` 跳过条目）

**场景**：`hermes_intelligence_pipeline.py --mode score` 返回 `processed: 0`，但 `SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0` 显示有数据。

**根因**：`--mode score` 的 SQL 条件是 `(ai_score_total IS NULL OR ai_score_total = 0) AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '')`。如果某条数据的 `ai_score_total = 0` 且 `ai_score_reasoning` **非空**（例如之前被规则评分系统标记为无情报价值），`--mode score` 会跳过它——因为它的 reasoning 字段已有内容，不需要重评。

**诊断**：
```sql
SELECT id, title, ai_score_total, 
       SUBSTR(ai_score_reasoning, 1, 60) as reason_preview,
       ai_scored_at
FROM cleaned_intelligence 
WHERE ai_score_total = 0 
  AND (ai_score_reasoning IS NOT NULL AND ai_score_reasoning != '')
ORDER BY id;
```

**正常判断**：如果 `ai_score_reasoning` 包含合理的解释（如"洛天依原创手书PV，属于艺术创作，非情报"、"内容仅为抖音热搜标题，无独家或深度信息"等），说明**之前系统已经正确标记了这些数据为低质**，不需要重评。

**修复**：只需补充 `ai_scored_at` 时间戳，确保这些条目有完整的元数据：
```sql
UPDATE cleaned_intelligence 
SET ai_scored_at = datetime('now')
WHERE ai_score_total = 0 
  AND (ai_score_reasoning IS NOT NULL AND ai_score_reasoning != '')
  AND ai_scored_at IS NULL;
```

**典型数量**：通常 1-5 条。这些是内容为纯标题/标签/元数据的数据，被规则评分系统打 0 分并附有完整的 reasoning 解释。

### 🔴 常见错误：检查 `cleaned_intelligence.db` 而非 `intelligence.db`

**场景**：`sqlite3 ~/.hermes/data/cleaned_intelligence.db` 连接到一个 1.7MB 的小型**独立数据库**（只有 `cleaned_intelligence` 表，1393 条数据），而主数据库是 `~/.hermes/data/intelligence.db`（94MB，`cleaned_intelligence` 表 14828 条数据）。

**根因**：历史上可能存在一个独立的 `cleaned_intelligence.db` 与主库 `intelligence.db` 中的 `cleaned_intelligence` 表**重名但不同库**。

**正确检查方法**：
```bash
# ✅ 主库（用于评分积压判断）
sqlite3 ~/.hermes/data/intelligence.db "SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL;"

# ❌ 错误的小库（用于其他目的，不是评分判断来源）
sqlite3 ~/.hermes/data/cleaned_intelligence.db "SELECT COUNT(*) FROM cleaned_intelligence;"
```
