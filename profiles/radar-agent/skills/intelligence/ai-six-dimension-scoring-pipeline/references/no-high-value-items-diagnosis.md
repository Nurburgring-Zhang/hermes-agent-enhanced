# 🔴 已评分但无高价值数据的诊断指南

## 场景描述

所有 `cleaned_intelligence` 数据已有完整六维评分，但 `value_level` 全部为 0 或 1：
- `value_level=0`: 10691 条
- `value_level=1`: 5383 条
- `value_level>=4`: 0 条

此时 `hermes_intelligence_pipeline.py --mode all` 输出：
```
[情报] 获取到0条4+星情报
✅ 完成: 路由0条 | 索引0条 | 任务0个
```

## 这不是故障

低 value_level **≠ 评分系统故障**。value_level 由评分系统基于六维总分计算：
- `importance_score = ai_score_total / 10` → 0-10 间
- `value_level = 0` (无价值) 或 `1` (低价值) 因为大多数内容是娱乐/短视频/旅游攻略，与科技情报无关

## 诊断步骤

### 1. 确认评分覆盖
```sql
SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_scored_at IS NULL;
```
→ 如果 = 0，评分已全部完成

### 2. 检查 value_level 分布
```sql
SELECT value_level, COUNT(*) FROM cleaned_intelligence GROUP BY value_level;
```

### 3. 检查六维总分分布
```sql
SELECT 
  CASE 
    WHEN ai_score_total IS NULL THEN 'NULL'
    WHEN ai_score_total = 0 THEN '0'
    WHEN ai_score_total BETWEEN 1 AND 19 THEN '1-19'
    WHEN ai_score_total BETWEEN 20 AND 39 THEN '20-39'
    WHEN ai_score_total BETWEEN 40 AND 59 THEN '40-59'
    WHEN ai_score_total >= 60 THEN '60+'
  END as range,
  COUNT(*) as cnt
FROM cleaned_intelligence
GROUP BY range
ORDER BY MIN(ai_score_total) NULLS FIRST;
```

### 4. 查看低分内容来源
```sql
SELECT source, COUNT(*) as cnt, ROUND(AVG(ai_score_total), 1) as avg
FROM cleaned_intelligence
WHERE value_level <= 1
GROUP BY source
ORDER BY cnt DESC
LIMIT 10;
```

## 典型低分来源（2026-05-30实测）

| 来源 | 特征 | 原因 |
|------|------|------|
| douyin | 42字符短视频标题 | 无实质内容 |
| toutiao | 20-31字符社会新闻 | 内容过短 |
| qyer | 旅游攻略(468-500字符) | 非科技领域 |
| weibo | 20字符短消息 | 内容过短 |

## 应对方案

### A. 等待新数据采集
低分数据不会进入推送候选池，这是正常行为。新采集的高价值数据（AI/芯片/科技类）会得到40-80分。

### B. 检查最新采集数据质量
```sql
SELECT id, ai_score_total, importance_score, 
       substr(title, 1, 40), source, substr(cleaned_at, 1, 19)
FROM cleaned_intelligence
ORDER BY id DESC
LIMIT 10;
```

### C. 确认采集器是否正常运行
```bash
cd ~/.hermes
python3 scripts/hermes_intelligence_pipeline.py --mode stats
```
→ `total_cleaned` 在增长说明有数据正常流入。

### D. 低分数据自动清理
如果堆积过多，按 SOUL.md 规则：
- `cleaned_intelligence` 中 `ai_score_total < 20` 的数据应归档到 `archive_cleaned` 再删除
- 使用 `lowscore_cleaner.py` 或手动 SQL

## 关键结论

**已评分+无高价值数据 ≠ 需要跑评分。** 这是数据源的分布问题——采集器近期采集了大量低价值娱乐内容，而非评分系统故障。评分完成后，`--mode all` 返回0是该 pipeline 的预期行为（它只处理 value_level>=4 的条目）。
