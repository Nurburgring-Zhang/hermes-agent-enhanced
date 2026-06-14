# 评分积压清理记录 — 2026-05-30 (第三轮，零分条目定点清理)

## 背景
2026-05-30 13:33 UTC cron触发评分积压处理。全库15,128条中，`ai_score_total IS NULL OR =0` 共7条。

## 7条零分条目详情

| ID | 标题 | 来源 | 评分前状态 | 评分后总分 |
|----|------|------|-----------|-----------|
| 806272 | 璐璐和娜娜的瑞意之旅 - 黄金列车 | 旅游 | total=0, reasoning有JSON(被AI评了0分) | **46** |
| 806279 | 西法葡阳光假日 - 波尔图美好印象 | 旅游 | total=0, reasoning有JSON(被AI评了0分) | **36** |
| 806304 | 你怎么看待苏芒针对网友发起的名誉侵权案？ | zhihu | total=0, no reasoning | **34** |
| 806307 | 汽车行业利润率持续探底 | toutiao | total=0, no reasoning | **38** |
| 806309 | 全国六成手机膜来自这里 | weibo | total=0, no reasoning | **40** |
| 806311 | 曝赛力斯将发布新品牌赛豆科技 | toutiao | total=0, no reasoning | **38** |
| 806313 | 济宁大雪中的音乐节～张云雷 | douyin | total=0, no reasoning | **34** |

## 处理方式

新建 `scripts/score_zero_backlog.py`（从 `score_backlog_200_v2.py` 复制评分引擎，修改WHERE条件为 `ai_score_total IS NULL OR ai_score_total = 0`，DB路径修正为 `data/intelligence.db`）。

**不依赖任何现有脚本**：v1处理NULL不处理0，v2处理旧格式不过时条件，execute_ai_scoring跳过短内容。

## 关键发现

### 1. 存在两类"零分"数据

| 类型 | 特征 | 数量趋势 | 处理方式 |
|------|------|---------|---------|
| **A类**：总分=0且reasoning=`{'scarcity_reason':..., 'impact_reason':...}` | 被AI/规则引擎正确评了0分的纯娱乐内容 | 极少(2/7) | 无需重评，但分数应合理即可 |
| **B类**：总分=0且reasoning为空 | 完全没被评分引擎覆盖（短内容/非科技平台来源） | 少量(5/7) | 规则引擎评分 |

A类是"被正确评了低分但硬件字段为零"——规则引擎评分后的结果（34-46）才合理反映内容实际价值，但远低于正常新闻（通常55-80）。这证明**zero-score flag并不都表示未评分**。

### 2. 稳定态确认

这是连续第3次人工/cron评分清理，累计：
- 第一次：58条低分+1635孤立raw清理
- 第二次：2条短内容score=0
- 第三次：7条zero-score（含2条已评零分+5条真未评分）

**全库15,128条，当前余0条未评分、0条无reasoning的正常数据。** 系统已进入稳定态，新入库数据在清洗管道中被正常评分。

### 3. cron提示词问题

当前cron任务prompt为：
```
处理cleaned_intelligence中未评分的积压数据。工作目录~/.hermes/，运行 python3 scripts/hermes_intelligence_pipeline.py --mode score 来批量处理AI评分队列。每次处理200条。
```

**`--mode score` 不存在** — 该pipeline支持 `{all,route,index,generate,stats}`。每次cron触发后代理需先探索->发现->修正，浪费tokens。建议修改cron为直接调用 `python3 scripts/score_backlog_200.py || python3 scripts/score_zero_backlog.py`。

## 输出格式示例（用作参考）
```
📊 **cleaned_intelligence 积压评分处理完成**

**状态：**
- 全库总计 15,128 条记录
- v2 简略评分检查：0 条需要升级
- 零分/无评分条目：7 条 → 已全部评分

**结论：** ✅ 无积压。所有 15,128 条已全部完成评分。
```
