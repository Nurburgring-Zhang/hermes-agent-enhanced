# 清理管道 category_tags 列丢失修复记录

## 发现时间
2026-05-28 全面复盘阶段

## 问题表现

在全面审计中，运行 `--stats` 看到 photo_match 有11条、mma_match有4条、fengniao有4条数据，但推送系统从不推送这些内容。

## 排查过程

1. 检查 `raw_intelligence` → 确认 `category_tags` 字段有值（如 `Photo|Camera|Match`）
2. 检查 `cleaned_intelligence` → 对应数据的 `tags` 字段为空或 `General`
3. 检查 cleaning 管道（`unified_cleaning_pipeline.py`）→ SELECT 查询中**没有** `r.category_tags`
4. 确认 INSERT 只用 `item.get("tags", "")` → 空的 → 标签全部丢失
5. 批量修复1101条历史数据 → 确认标签合并成功

## 受影响的子系统

```
采集 (unified_collector_v5.py)
  ↓ (写入 raw_intelligence.category_tags = "Photo|Camera|Match")
清洗 (unified_cleaning_pipeline.py)  ← ❌ 没读这个列!
  ↓ (cleaned_intelligence.tags = "" 或 "General")
推送 (hermes_v12_push.py)
  ↓ (SQL要求 tags LIKE '%Photo%')  ← ❌ tags是空的，匹配不到
用户收不到摄影/格斗/芯片内容
```

## 修复后的数据流

```
采集 → raw.category_tags = "Photo|Camera|Match"
  ↓
清洗 → merge_tags(tags, category_tags) → cleaned.tags = "Photo|Camera|Match|Fight|..."
  ↓
推送 → SQL WHERE tags LIKE '%Photo%' → 候选池中 ✅
```

## 验证命令

```sql
-- 修复前检查
SELECT COUNT(*) FROM cleaned_intelligence c 
JOIN raw_intelligence r ON c.raw_id = r.id 
WHERE r.category_tags IS NOT NULL AND r.category_tags != '' 
AND (c.tags IS NULL OR c.tags = '' OR c.tags = 'General');
-- 修复后检查
SELECT c.tags, r.category_tags, c.title
FROM cleaned_intelligence c 
JOIN raw_intelligence r ON c.raw_id = r.id 
WHERE r.category_tags LIKE '%Photo%' OR r.category_tags LIKE '%Fight%'
LIMIT 10;
```

## 类似问题的检查清单

| 检查项 | SQL/命令 |
|--------|---------|
| raw_intelligence 有 category_tags 但 cleaned 没有 | 见上方修复前检查 |
| new_cleaned 数据仍然缺少标签 | 跑一次 clean_batch 然后查最新5条 |
| 推送候选池没有某方向数据 | `python3 scripts/hermes_v12_push.py --draft 2>&1 | grep -E "Photo\|Fight\|Camera"` |
