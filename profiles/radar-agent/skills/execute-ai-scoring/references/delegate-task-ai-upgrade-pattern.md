# Delegate-task AI评分升级实战 — 57条旧格式→AI评分升级

> 2026-05-29 实战记录。将57条旧格式文本评分/规则评分升级为带JSON summary的新格式AI评分。

## 背景

`cleaned_intelligence` 中的 `ai_score_reasoning` 存在多种非标准格式：
- 纯文本理由（如 `"英伟达服务器供应链瓶颈预警..."`）
- 旧格式评分（如 `"稀缺性(17/30): 独家/首发信息; 影响力(16/30): 中等影响..."`）
- 规则评分（`"method":"规则引擎评分v4"`）

这些条目 **看起来已经评分过**（`ai_scored_at IS NOT NULL`），但评分质量参差不齐。

## 检测盲区的SQL

```sql
-- 列出所有评分格式的分类
SELECT 
  CASE 
    WHEN ai_score_reasoning IS NULL OR ai_score_reasoning = '' THEN 'truly_unscored'
    WHEN ai_score_reasoning LIKE '%AI评分%' THEN 'ai_scored'
    WHEN ai_score_reasoning LIKE '%规则%' THEN 'rule_only'
    WHEN ai_score_reasoning LIKE '%summary%' THEN 'new_json_format'
    ELSE 'other_text_format'
  END as fmt,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY fmt
ORDER BY cnt DESC;

-- 找出所有"other"格式——需要升级的目标
SELECT id, title, source, importance_score, ai_score_total,
       substr(ai_score_reasoning, 1, 100) as reason_preview
FROM cleaned_intelligence
WHERE ai_score_reasoning NOT LIKE '%评分%'
  AND ai_score_reasoning NOT LIKE '%summary%'
  AND LENGTH(COALESCE(content,'')) > 100
  AND importance_score > 3
ORDER BY importance_score DESC;
```

## 升级流程

### 第1步：导出候选数据

```python
# prep_batch.py — 导出待升级的数据到JSON
import sqlite3, json

DB_PATH = "/home/administrator/.hermes/intelligence.db"
OUTPUT = "/home/administrator/.hermes/reports/_batch_ai_score_input.json"
BATCH_SIZE = 20

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.execute("""
    SELECT id, title, content, source, url,
           ai_score_total as current_score,
           ai_score_reasoning as current_reasoning,
           importance_score
    FROM cleaned_intelligence
    WHERE 
      (ai_score_reasoning LIKE '%规则%')
      OR 
      (ai_score_reasoning NOT LIKE '%评分%'
       AND ai_score_reasoning NOT LIKE '%summary%'
       AND LENGTH(COALESCE(content,'')) > 100
       AND importance_score > 3)
    ORDER BY importance_score DESC
""")
rows = cur.fetchall()
conn.close()

batch = rows[:BATCH_SIZE]
items = [{'id': r['id'], 'title': r['title'], 
          'content': (r['content'] or '')[:500], 
          'source': r['source'],
          'current_score': r['current_score'],
          'importance': r['importance_score']} for r in batch]

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
```

### 第2步：delegate_task评分模板

在delegate_task的context中提供六维评分指南和DB写入SQL：

```
context: |
  六维评分指南（严格遵循）：
  - scarcity(0-30): 独家性。常规报道8-15，独家信息16-25，全球首发26-30
  - impact(0-30): 影响力。普通产品6-12，影响行业13-20，改变格局21-30
  - tech_depth(0-20): 技术深度。摘要2-6，细节7-12，架构/原理/性能数字13-18，底层原理19-20
  - timeliness(0-10): 时效性。1天内9-10，3天内7-8，1周内5-6
  - preference(0-10): 偏好匹配。AI/ML/芯片/新能源8-10，科技产品6-7，其他4-5
  - credibility(0-10): 可信度。IT之家/36氪8分，hackernews 8分

goal: |
  读取 INPUT_FILE，逐条AI六维评分后UPDATE到DB：
  UPDATE cleaned_intelligence SET 
    ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
    ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
    ai_score_total=?, importance_score=?, ai_score_reasoning=?, ai_scored_at=?
  WHERE id=?

  ai_score_reasoning必须是JSON: {"scarcity_reason":"...","impact_reason":"...",
    "tech_depth_reason":"...","timeliness_reason":"...","preference_reason":"...",
    "credibility_reason":"...","summary":"一句话总结"}
```

### 第3步：写入验证

```sql
-- 确认是否写入成功
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE ai_scored_at >= '2026-05-29 09:35' 
  AND ai_scored_at < '2026-05-29 09:40';

-- 检查特定ID的评分详情
SELECT id, ai_score_total, ai_scored_at,
       substr(ai_score_reasoning, 1, 80) as reason
FROM cleaned_intelligence
WHERE id IN (801103, 801104, 437249);
```

## 性能基准

| 批次 | 条数 | 方式 | 耗时 | 成功率 |
|------|:----:|------|:----:|:------:|
| Batch 1 | 20 | delegate_task | ~191s | 20/20 (100%) |
| Batch 2 | 20 | delegate_task | ~68s | 20/20 (100%) |
| 规则评分批 | 24 | batch_score_200_d.py | ~0.3s | 24/24 (100%) |

## ⚠️ 关键陷阱

1. **delegate_task的context中必须提供六维评分Scale定义**，否则子代理会发明自己的评分标准
2. **评分理由格式必须严格一致**：`{"scarcity_reason":"...", "summary":"..."}` — 否则后续分类SQL无法匹配
3. **不要依赖现有评分字段**（current_score/importance）— 它们是旧评分，要完全重新理解评分
4. **ai_scored_at时间戳递增**：每条+1秒，避免时间戳重复

## 相关

- 本模式已固化到 `batch_score_200_d.py`（规则评分）和delegate_task模板
- 检查[`scoring-backlog-diagnostics.md`](./scoring-backlog-diagnostics.md)中的盲区检测SQL
