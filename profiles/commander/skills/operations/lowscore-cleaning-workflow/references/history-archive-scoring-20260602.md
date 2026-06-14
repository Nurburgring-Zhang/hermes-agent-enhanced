# history_archive 未评分积压处理记录 (2026-06-02)

## 发现背景
2026-06-02 cron任务检查 `cleaned_intelligence` 时发现全部已评分（14,342条），但进一步检查 `history_archive` 表发现 **5,504条未评分记录**。

## history_archive 表结构
```
id, title, platform, source, url,
ai_score_total, ai_score_scarcity, ai_score_impact, ai_score_tech_depth,
ai_score_timeliness, ai_score_preference, ai_score_credibility,
summary, importance_score, value_level,
collected_at, archived_at, compressed_from_id
```

**关键差异**：
- 无 `content` 字段（非压缩表，原文不保留）
- `summary` 字段全部为空（25557条全部 `summary_len=0`）
- 只有 `id, title, source, platform` 可用于评分

## 处理方法
不能复用 `calc_item_scores`（需要content字段），必须基于标题+来源+平台做轻量级规则评分。

评分脚本：内联Python（临时 `scripts/score_history_archive.py`，用后清理）

## 处理结果
- **处理批次**: 28轮（27×200 + 1×104）
- **处理总计**: 5,504条全部评分完成
- **评分分布**:
  - < 40: 189-197条/批（均值~190/200 = 95%）
  - 40-60: 3-27条/批
  - ≥ 60: 极少（只有1条=60分）
  - 均分: ~33.0（基于标题评分，低是正常的）
- **最终状态**: history_archive 25,557条全部已评分，0条未评分

## 高分样例（仅基于标题）：
- id=5198, score=60: "性能超越GPT-4!全球首个让大模型真正看懂复杂手术的开源技术方案来了"
- id=936, score=55: "鸿蒙智行发布智界 V9 白车身结构，全球首发全维包裹安全气囊"
- id=1612, score=53: "MiniMax 发布 MaxHermes，全球首个云端沙箱 Hermes"
- id=1195, score=58: "荣威联合火山引擎发布全球首个 AI 原生汽车序列\"家越\""
- id=4752, score=54: "GPT-Image-2 图片很难一眼看出 AI 味..."

## 后续检查点
- pipeline的 --mode score 只查 cleaned_intelligence，不会自动覆盖 history_archive
- 如果 history_archive 再次产生未评分数据（例如清洗管道新插入未评分的归档数据），需要手动或用cron跑上面代码
- 建议在cron prompt中增加: "检查cleaned_intelligence + history_archive + archive_cleaned三个表的未评分状态"

## 最终评分统计（处理后）
| 分段 | 数量 |
|------|------|
| < 40 | 12,207 |
| 40-60 | 12,172 |
| 60-80 | 1,049 |
| ≥ 80 | 129 |
| **合计** | **25,557** |
| **平均分** | **41.23** |
