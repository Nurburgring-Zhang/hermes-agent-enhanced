# 旧格式简略评分→六维评分迁移指南

## 问题

cleaned_intelligence 表中历史遗留了两种**简略评分格式**，只有总分没有维度级评价：

```json
// 格式A — AI内容评分（约4,133条）
{"summary": "AI内容评分:35分"}
{"scarcity_reason": "score=16/30", "impact_reason": "score=5/30", "summary": "AI内容评分:36分"}

// 格式B — 纯摘要评分（约4,510条，无scarcity/impact等维度字段）
{"summary": "特斯拉4月欧洲销量强劲增长，延续重拾增长势头。"}
```

这些条目已有总分（ai_score_total），但缺少**维度级评分字段**（ai_score_scarcity / ai_score_impact / ai_score_tech_depth / ai_score_timeliness / ai_score_preference / ai_score_credibility 等），以及完整的 `ai_score_reasoning` JSON 结构。

## 检测方法

```sql
-- 格式A: 含有 "AI内容评分" 关键词
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_reasoning LIKE '%AI内容评分%';

-- 格式B: JSON但不含任何维度关键词
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_reasoning NOT LIKE '%scarcity%'
  AND ai_score_reasoning NOT LIKE '%impact%'
  AND ai_score_reasoning != ''
  AND ai_score_reasoning IS NOT NULL;

-- 完整检测: 已六维评分的条目（含scarcity + impact）
SELECT COUNT(*) FROM cleaned_intelligence
WHERE ai_score_reasoning LIKE '%scarcity%'
  AND ai_score_reasoning LIKE '%impact%';
```

## 迁移方法

### 1. 使用 `score_backlog_200_v2.py`（推荐）

脚本位置: `scripts/score_backlog_200_v2.py`

核心逻辑：
- 查询旧格式条目（`ai_score_reasoning LIKE '%AI内容评分%'` 或不含 `scarcity`/`impact` 关键词）
- 使用 **规则引擎评分**（关键词匹配 + 来源可信度 + 日期分析 + 偏好判断）
- 每次处理200条，写入完整的六维维度和结构化reasoning JSON
- 纯本地执行，无API依赖，约0.05秒/批

```bash
cd ~/.hermes
python3 scripts/score_backlog_200_v2.py
# 重复运行直到旧格式剩余为0
```

执行条件：
- `ai_score_total IS NOT NULL AND ai_score_total > 0`（已有分数）
- 旧格式 = `AI内容评分` or `内容感知` or 无`scarcity`/`impact`关键词
- 每批取 `ORDER BY id ASC LIMIT 200`

### 2. 基准性能（2026-05-29实测）

| 指标 | 值 |
|------|-----|
| 每批处理量 | 200条 |
| 每批耗时 | ~2-3秒（含DB读写） |
| 总计处理量 | ~15,800条 |
| 总耗时 | ~10分钟 |
| 升级覆盖率 | 0% → 100% |
| 升级后平均分 | ~43.4/100 |
| 全库平均分提升 | 37.6 → 41.5 |

### 3. 输出格式

迁移后每条条目的 `ai_score_reasoning` JSON结构如下：

```json
{
  "scarcity_reason": "首款/首次/里程碑",
  "impact_reason": "AI/芯片新品发布",
  "tech_depth_reason": "含5项技术细节",
  "timeliness_reason": "昨天",
  "preference_reason": "AI/芯片/新能源核心领域",
  "credibility_reason": "ithome(8分)",
  "summary": "总分56: 独家18 影响14 技术12 时效7 偏好9 可信8"
}
```

同时写入 ai_score_scarcity/impact/tech_depth/timeliness/preference/credibility 六个维度字段。

### 4. 规则引擎评分逻辑（核心维度）

| 维度 | 范围 | 方法 |
|------|------|------|
| 稀缺性 | 0-30 | 标题关键词检测（独家/首发/首次/泄露/曝光）+ 首发=26, 首次=18, 报告=14, 常规=10 |
| 影响力 | 0-30 | 事件类型检测（格局变化=24, 国家安全=18, 热销=16, 政策=18, 新品发布=8-14, 合作=12） |
| 技术深度 | 0-20 | 技术词汇密度 + 架构/性能参数检测（架构+参数+5术语=18, 架构+参数=15, 5+术语=12） |
| 时效性 | 0-10 | 日期正则匹配（今天=10, 昨天=9, 2天前=8, ... 4月=2, 去年=1） |
| 偏好匹配 | 0-10 | AI/芯片/新能源关键词评分累加，>=5分=9, >=3分=7, >=1.5=5, 其他=3 |
| 可信度 | 0-10 | 来源平台分级映射（ithome/36kr=8, hackernews=8, 微博=4, 贴吧=3） |

### 5. 特殊注意事项

- **格式A的检测**：`ai_score_reasoning LIKE '{%summary%}'` 会误匹配到已升级的 JSON（因为升级后的JSON也包含`"summary":`字段）。正确做法是用 `LIKE '%AI内容评分%'` 或排除 `scarcity_reason`。
- **短内容条目**：content 极短（如抖音只有"热度值:xxxx"）的条目，规则引擎会给出合理低分（~33-36），无需特别处理。
- **零分条目**：迁移后如果仍有 `ai_score_total = 0` 条目，需要单独手工评分（通常是个位数，数量极少）。

## 关联参考

- `references/batch-200-cron-pattern.md` — 通用批量评分模式（旧版）
- `scripts/score_backlog_200_v2.py` — 本模式使用的实际脚本
- `references/upgrade-rule-scored-to-ai-scored.md` — 规则评分→真正AI评分升级（不同路径）
