# 低分清理实战记录 — 2026-05-29

## 场景：5条未评分+124条历史低分积压

### 现场诊断结果
- cleaned_intelligence: 15,692条总记录
- 真正未评分 (ai_score_total IS NULL): 0条
- 得分为0 (ai_score_total=0): 5条（均为value_level=0或1的无内容标签数据）
- 有分但<20: 124条（历史积压，从未被清理过）
- 有分>=20: 15,563条

### 5条未评分的实际情况
不是"没评过分"，而是用规则评分时无法处理内容为纯标签/元数据的条目（douyin热度值、weibo标签、百度热点摘要、头条无内容标题）。这些条目的 `content` 字段存储的是 `"Label:新 Score:170992"` 或 `"热度值:7617031 | group_id:xxx"` 这类元数据而非文章正文。

### 正确的处理方式
对无实际内容的条目，**不需要调用LLM评分**（浪费token）。直接：
1. value_level=0 + 无内容 → score=2（标题党/无实质内容）
2. value_level=1 + 纯元数据 → score=17（标签信息）
3. 立即归档到archive_cleaned + 从主库删除

### 归档SQL（精确复制所有列）
```sql
INSERT OR IGNORE INTO archive_cleaned 
(id, raw_id, title, content, url, source, platform, author, category,
 importance_score, value_level, value_reasons, is_ai_related, language,
 chinese_ratio, is_processed, published_at, collected_at, cleaned_at,
 agent, personal_match_score, source_type, author_id, url_hash, tags,
 ai_score_scarcity, ai_score_impact, ai_score_tech_depth, ai_score_timeliness,
 ai_score_preference, ai_score_credibility, ai_score_total, ai_score_reasoning,
 ai_scored_at, archived_at, archive_reason)
SELECT id, raw_id, title, content, url, source, platform, author, category,
       importance_score, value_level, value_reasons, is_ai_related, language,
       chinese_ratio, is_processed, published_at, collected_at, cleaned_at,
       agent, personal_match_score, source_type, author_id, url_hash, tags,
       ai_score_scarcity, ai_score_impact, ai_score_tech_depth, ai_score_timeliness,
       ai_score_preference, ai_score_credibility, ai_score_total, ai_score_reasoning,
       ai_scored_at, datetime('now'), 'auto: ai_score_total<20'
FROM cleaned_intelligence
WHERE ai_score_total < 20;
```

### 清理结果
- 归档到archive_cleaned: 129条
- 删除: 129条
- 清理孤立raw数据: 10,340条
- 最终cleaned_intelligence: 15,563条（全部已评分>=20）
