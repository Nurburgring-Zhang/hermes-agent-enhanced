# 智慧评分管道操作指南 (Intelligence Scoring Ops)

## 可用评分脚本清单

| 脚本 | 用途 | 评分类型 |
|------|------|----------|
| `scripts/hermes_ai_scoring.py` | AI六维内容理解评分(LLM) | 规则引擎(无API) |
| `scripts/ai_scoring_v2.py` | AI六维评分v2 — 全量评分引擎 | 规则引擎 |
| `scripts/execute_ai_scoring.py` | AI评分执行引擎(delegate_task) | LLM真评分 |
| `scripts/real_ai_scorer.py` | 真正AI评分器(调用DeepSeek) | LLM API评分 |
| `scripts/score_backlog_200.py` | 批量规则引擎评分(200条/次) | 规则引擎 |
| `scripts/score_backlog_200_v2.py` | 升级简略评分为六维(200条/次) | 规则引擎 |
| `scripts/lowscore_cleaner.py` | 低分数据清理(<20自动归档) | 清理工具 |

## 评分积压检查流程

```python
import sqlite3
db = sqlite3.connect('data/intelligence.db')
cur = db.cursor()

# 1. 基础: NULL和0值
cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0")

# 2. 深层: 非数字类型
cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE typeof(ai_score_total) != 'real' AND typeof(ai_score_total) != 'integer' AND ai_score_total > 0")

# 3. 旧格式: JSON/文本评分
cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE CAST(ai_score_total AS TEXT) LIKE '{%' OR CAST(ai_score_total AS TEXT) LIKE '%summary%'")

# 4. 六维全零但有总分
cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_scarcity=0 AND ai_score_impact=0 AND ai_score_tech_depth=0 AND ai_score_timeliness=0 AND ai_score_preference=0 AND ai_score_credibility=0 AND ai_score_total=0")

# 5. 六维和不等于总分
cur.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE (ai_score_scarcity + ai_score_impact + ai_score_tech_depth + ai_score_timeliness + ai_score_preference + ai_score_credibility) != ai_score_total AND ai_score_total > 0")
```

## 常见管线命令

- `hermes_intelligence_pipeline.py` 支持: `--mode {all, route, index, generate, stats}` — **没有 score 模式**
- 批量评分用独立脚本，不在 pipeline 内
- `hermes_ai_scoring.py` 支持: `--backfill N`(回填N条), `--dry-run`(预览), `--full`(全量)
- `execute_ai_scoring.py` 通过 `--batch /path/to/batch.json` 配合delegate_task做LLM真评分

## 六维评分标准

- **稀缺性** 0-30: 独家/首发/一手信息
- **影响力** 0-30: 影响范围(行业级/公司级/产品级)
- **技术深度** 0-20: 技术细节/数据支撑/分析深度
- **时效性** 0-10: 24h内/48h内/一周内
- **偏好匹配** 0-10: 格林主人兴趣匹配度(从keyword_weights读取)
- **来源可信度** 0-10: 官方/一手/媒体/自媒体

## 坑点 (PITFALLS)

1. `hermes_intelligence_pipeline.py` **没有** `--mode score` — 不要尝试
2. SQLite中ai_score_total是REAL类型，不要用字符串比较
3. 六维和与总分不一致是两套引擎(AI vs 规则)的数据并存导致的，不影响排序
4. 最低有效分是20分(规则引擎下限)，没有1-19分的记录
