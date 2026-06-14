# 评分积压状态快照 — 2026-05-29 (第二次清理)

## 场景
Cron 要求："处理cleaned_intelligence中未评分的积压数据。每次处理200条。"

## 诊断结果（2026-05-29 21:33）

| 检查项 | 结果 | 判定 |
|--------|------|------|
| cleaned_intelligence 总记录 | **15,975** 条 | — |
| ai_score_total IS NULL | **0** 条 | ✅ |
| ai_score_total=0（真正未评分，无reasoning） | **2** 条 | ✅ 已处理 |
| ai_score_total=0（有JSON reason, 纯娱乐） | **3** 条 | ✅ 评分正确，无需处理 |
| 六维全=0且有JSON reason | 3条（douyin娱乐） | ✅ 正常 |
| score_backlog_200_v2.py 待处理 | **0** 条 | ✅ 升级脚本也正常（但其WHERE条件已过时，见陷阱#7） |
| ai_score_queue 未完成 | **0** 条 | ✅ |
| 最新评分时间 | 今日实时 | ✅ |

## 本次处理
- 升级 **2 条**真正未评分数据（ID=805246, 805251）
- 评分引擎：复用 score_backlog_200_v2.py 的规则引擎函数
- 处理后 total=37分（特斯拉）和 40分（高水平科技自立自强）
- 3条 douyin 娱乐内容（六维全0但有JSON reason）— 评分正确，不需要清理

## 关键发现

### score_backlog_200_v2.py 已过时
脚本的 WHERE 条件是寻找旧格式（`'%AI内容评分%'` 等），但所有数据都已升级为JSON格式。这个脚本当前找到 **0 条**而真正的积压是另外的形态。修复方式：
- 已补充到 lowscore-cleaning-workflow 的陷阱#7

### 数据质量概览
- 已评分总数: 15,970 条
- 平均分: 41.5
- 高质量(>=60): 1,068 条 (6.7%)
- 低质量(<20): 55 条 (0.3%) — 需等待 lowscore_cleaner 清理
- 三个评分维度覆盖率差（tech_depth=238 缺失, preference=249 缺失, timeliness=96 缺失）但reasoning字段完整—这些`=0`的维度是因为内容确实不含相关特征，评分正确
