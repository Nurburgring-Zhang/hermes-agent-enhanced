# cleaning_engine.py — 备选原始清洗工具（用于清理大积压）

## 概述

`engine/cleaning_engine.py` 是 Hermes 的**原始全量清洗引擎 v4**，与 `scripts/unified_cleaning_pipeline.py`（v2白名单版）是**两套独立的清洗工具**。

| 特性 | `engine/cleaning_engine.py` | `scripts/unified_cleaning_pipeline.py` |
|------|---------------------------|--------------------------------------|
| 过滤逻辑 | 仅去重+格式标准化 | 热点保底+649宽泛白名单关键词过滤 |
| 每个平台上限 | 可配置（`--max`参数） | 硬编码前20条保底 |
| agent标记 | ''（空） | 'unified_cleaning_pipeline_v2' |
| 适用场景 | 历史积压清理（无过滤全量进） | 日常增量（白名单过滤） |

## backlog 清理场景

当 raw_intelligence 有大量旧数据一直未被清理（如 `LEFT JOIN cleaned WHERE c.id IS NULL > 0` 的数字持续增长），改用 `cleaning_engine.py` 的原因是：

1. **无白名单过滤**：旧数据很多不匹配白名单关键词（如社会热点、体育、旅游等），`unified_cleaning_pipeline.py` 会跳过它们
2. **平台上限可调**：默认 `--max 100`，但积压常涉及上千条/平台。调高至500甚至1000可以一次大面积清理
3. **无标签合并**：不处理 `category_tags` 列，纯格式清洗

## 使用命令（积压清理版）

```bash
cd ~/.hermes

# 常规清理（72小时内、每平台100条）
python3 engine/cleaning_engine.py

# 历史积压清理（30天、每平台500条）
# ✅ 实战验证：2026-05-30 清理8533条 raw→cleaned
python3 engine/cleaning_engine.py --hours 720 --max 500

# 极端积压（全量、每平台1000条）
python3 engine/cleaning_engine.py --hours 2160 --max 1000
```

## 清理完成后的连锁操作

清理后，新增的 `cleaned_intelligence` 条目都未经评分（`ai_score_total` 为 NULL），必须接着运行评分：

```bash
# 步骤1: raw→cleaned（积压清理）
python3 engine/cleaning_engine.py --hours 720 --max 500

# 步骤2: 规则引擎批量评分
python3 batch_score_200_d.py

# 步骤3: 检查是否有短内容残留（<50字符被batch_score跳过）
python3 -c "
import sqlite3
db = sqlite3.connect('/home/administrator/.hermes/intelligence.db')
c = db.cursor()
c.execute(\"SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0\")
print(f'剩余未评分: {c.fetchone()[0]}')
db.close()
"

# 步骤4: 如有残留，手动补基础分（详见 execute-ai-scoring 的 short-content-scoring 参考）
```

## 实战数据（2026-05-30）

- 原始积压：4585条 raw 未清洗
- 清理参数：`--hours 720 --max 500`（30天范围）
- 结果：50个平台，**+8533条** 新增 cleaned（部分raw因url_hash重复被跳过）
- 随后评分：48条规则引擎评分（平均50.2）+ 16条短内容补分（基础3.0）
- 最终：15246条 cleaned 全部评完，0积压

## 局限性

- 没有白名单过滤 → 大量低质数据也进入 cleaned（如 Baidu Hot Search 标题、douyin 视频元数据等）
- 不处理 `category_tags` → 标签可能比 v2 管道弱
- 新增条目 agent 字段为空，无法区分是哪个清洗工具产生的
- 强烈建议清理后做低分归档：`ai_score_total < 20` 的条目应归档到 `archive_cleaned`
