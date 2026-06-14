# 评分积压清理记录 — 2026-05-30

## 背景
cleaned_intelligence 中存在58条积压数据（ai_score_total IS NULL 或 =0），
用户要求处理"未评分的积压数据"。

## 清理流程

### Step 1: 评分积压处理
使用 `score_backlog_200.py` 规则引擎评分：
- 处理: **53条**（完全未评分，ai_score_total IS NULL）
- 最低分: 33 | 最高分: 52 | 平均: 38.3
- 来源: 混合（头条、虎嗅、HN、B站、知乎等）
- 工具: `python3 scripts/score_backlog_200.py`

### Step 2: 低分数据清理
使用 `lowscore_cleaner.py --threshold 20 --fast`：
- 处理后清理: **58条**低分(ai_score_total < 20)
- 孤立raw数据: **1635条**（3天以上未清洗）
- DB体积: **372MB → 90MB**（-76%）

### Step 3: 最终验证
- cleaned_intelligence 总记录: **14,911条**
- 已评分(>0): **14,911条**（100%）
- 未评分(0/null): **0条**
- 低分(<20): **0条**
- 最低分: 20 | 最高分: 100

## 关键发现
1. `hermes_intelligence_pipeline.py --mode score` 不存在（支持的模式: all/route/index/generate/stats）
2. `score_backlog_200.py`（v1）处理 `ai_score_total IS NULL` 条目 — 仍然有效
3. `score_backlog_200_v2.py`（v2）处理旧格式简略评分升级 — 已无匹配数据
4. `scripts/lowscore_cleaner.py` 内置 `compressed_data` 列自动检测 — 稳定运行

## 注意
- DB路径双副本问题需排查: `lowscore_cleaner.py` 连接 `~/.hermes/intelligence.db` 但Python查询走 `~/.hermes/data/intelligence.db`
