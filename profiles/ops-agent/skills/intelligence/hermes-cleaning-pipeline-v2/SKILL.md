---
name: hermes-cleaning-pipeline-v2
description: Hermes 情报清洗管道v2 — 热点保底(前20条/平台自动放行) + 649宽泛白名单关键词(16分类)过滤
category: intelligence
---

# Hermes 情报清洗管道 v2

## 用途

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时

将 raw_intelligence 中的原始情报清洗到 cleaned_intelligence，应用热点保底 + 宽泛白名单过滤规则。

## 规则
1. **热点保底**: 每个平台每个子方向前20条直接放行（2026-05-28修复：之前阈值写的是<=8但实际条件用<=20，导致第9-20条的value_reasons错误标记为"白名单匹配"）
2. **白名单过滤**: 20条之后仅保留匹配宽泛白名单(649关键词，16大分类)的内容
3. **去重**: 先按数据库 title 精确去重，再按同一批内标题相似度去重
4. **噪声过滤**: 广告/推广/标题过短等

## 16大分类
AI/大模型、IT/开发、消费电子、通信/网络、新能源汽车、军事/国防、体育、格斗/MMA、美女/写真/摄影、电影/娱乐、旅游/地理、科学/科普、安全、游戏、机器人、社会热点

## 命令
```bash
cd /home/administrator/.hermes/scripts && python3 unified_cleaning_pipeline.py --batch 3000 --max-batches 10 --order-by-hot
```

## 脚本位置
/home/administrator/.hermes/scripts/unified_cleaning_pipeline.py

## 数据库
- raw_intelligence: 原始情报
- cleaned_intelligence: 清洗后情报（title有UNIQUE约束）
- agent字段标记为 "unified_cleaning_pipeline_v2"

## 备选工具：engine/cleaning_engine.py

当需要清理**历史大积压**（raw→cleaned）时，`engine/cleaning_engine.py` 是另一套无白名单过滤的清洗工具。
详见 `references/cleaning-engine-backlog-clear.md`。

核心区别：
- `unified_cleaning_pipeline.py`（本skill）→ 白名单过滤 + category_tags合并，适合日常增量
- `engine/cleaning_engine.py` → 纯去重+格式清洗，适合历史积压全量清理

## 🔴 陷阱：单一源噪声阻塞整个清洗队列

### 症状
`unified_cleaning_pipeline.py` 报告大量 `noise_filtered`，`new_cleaned=0`，但查询 `LEFT JOIN cleaned WHERE c.id IS NULL` 显示还有大量raw待清洗。原因是**一个高噪声源（如CSDN）占据了队列头部**，其所有记录都被 `is_noise()` 过滤，消耗了白名单热点保底计数器，后续非CSDN有价值记录永远排不到。

### 诊断方法
```sql
-- 检查未清洗数据的源分布
SELECT r.source, COUNT(*) as cnt
FROM raw_intelligence r
LEFT JOIN cleaned_intelligence c ON c.raw_id = r.id
WHERE c.id IS NULL
GROUP BY r.source ORDER BY cnt DESC;
```

如果单源（如 csdn）占了90%+ 的未清洗队列，且该源主要是无内容/入门教程标题，那么：
- 这些记录是噪声，**不应该被清洗**
- 但剩余非CSDN记录（如36kr/cnblogs/ithome/solidot）排在噪声后面，也洗不出

### 修复方案：源跳过定向清洗

不要用 `engine/cleaning_engine.py`（会连噪声一起清洗），而是写定向SQL+手动INSERT/UPDATE（已验证2026-05-30）：

```python
# 直接对非噪声源做定向清洗
import sqlite3, json
from datetime import datetime

conn = sqlite3.connect('/home/administrator/.hermes/data/intelligence.db')
c = conn.cursor()

c.execute('''
    SELECT r.id, r.title, r.content, r.url, r.source, r.platform,
           r.author, r.author_id, r.category, r.tags, r.category_tags,
           r.hot_score, r.published_at, r.collected_at
    FROM raw_intelligence r
    LEFT JOIN cleaned_intelligence c ON c.raw_id = r.id
    WHERE c.id IS NULL AND r.source != 'csdn'
      AND LENGTH(COALESCE(r.content,'')) > 50
    ORDER BY r.collected_at DESC
''')

# 对每条通过噪声+白名单检查的记录 INSERT INTO cleaned_intelligence
# 然后直接 UPDATE ai_score_total (用规则评分)
# 详见 references/source-tail-cleaning-pattern.md
```

### 源跳过清洗后的连锁操作

1. 清洗完成后检查是否有新cleaned记录未评分
2. **首选**：运行 `python3 scripts/hermes_intelligence_pipeline.py --mode score --limit 200`（已集成规则引擎，0秒级完成）
3. **备选**：运行 `ai_scoring_v2.py --batch 500`（旧版批量规则评分，效果相同）
4. 验证：`SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0`

### 经验法则
- 如果某个源的 `noise_filtered` 占总数的80%+，考虑跳过该源做定向清洗
- 空的CSDN入门教程标题（"什么是LLM"、"大模型科普"等）是正确过滤对象，不要为了清积压而降低噪声阈值
- 定向清洗后需要立即评分——这些数据是实时采集的，时效性高
- 该模式已在2026-05-30实测：49条非CSDN候选 → 14条通过清洗+评分 → 30条正确过滤

## 参考文档
- `references/source-tail-cleaning-pattern.md` — 单源噪声阻塞队列时的定向清洗+评分方案（含完整脚本模板和2026-05-30实测数据）
- `references/cleaning-engine-backlog-clear.md` — `engine/cleaning_engine.py` 备选清洗工具说明

## 已知问题
- 约2186条 raw_intelligence 的 title 已存在于 cleaned_intelligence 中（跨原始采集批次但内容相同），不会被重复清洗，这是预期行为。
- 低分数据（ai_score_total < 20）每天自动归档到 archive_cleaned 表

## 🔴 修复记录

### 修复1: category_tags 列丢失（2026-05-28）

#### 症状
`unified_collector_v5.py` 采集时向 `raw_intelligence.category_tags` 列写入了标签（如 `Photo|Camera|Match`、`MMA|Fight|Sports|Match`），但 `unified_cleaning_pipeline.py` 的 `clean_batch()` 函数在 SELECT 中没有包含 `category_tags` 列，INSERT 时只用 `item.get("tags", "")`（该列为空），导致所有采集端写的标签在清洗阶段**全部丢失**。

#### 影响范围
- 已清洗数据中 **1101条** 的 cleaned_intelligence.tags 为 NULL/空/General，但其对应的 raw_intelligence.category_tags 有值
- 摄影(Photo)、格斗(MMA/Fight)、芯片(Semi/Chip)、旅游(Travel)等通过 _match 平台采集的数据全部丢失标签
- 连锁效应：推送系统从 cleaned_intelligence.tags 读标签进行方向偏好排序 → 这些数据永远不会出现在推送候选池

#### 根因代码（clean_batch中）
```python
# 第370行 — 缺少 r.category_tags
SELECT r.id, r.title, r.content, r.url, ..., r.tags
# 改为 ✅
SELECT r.id, r.title, ..., r.tags, r.category_tags

# 第487行 — 只用tags，没用category_tags
item.get("tags", "") or ""
# 改为 ✅
merge_tags(item.get("tags", "") or "", item.get("category_tags", "") or "")
```

#### 修复
1. SELECT 查询中**新增 `r.category_tags` 列**
2. INSERT 语句中将 `tags` 和 `category_tags` **通过 `merge_tags()` 函数合并**写入
3. 新增 `merge_tags()` 工具函数：
```python
def merge_tags(tags: str, category_tags: str) -> str:
    """合并raw_intelligence.tags和category_tags到cleaned_intelligence.tags"""
    parts = set()
    for src in [tags, category_tags]:
        for p in str(src).split('|'):
            p = p.strip()
            if p:
                parts.add(p)
    return '|'.join(sorted(parts)) if parts else ''
```
4. **批量修复历史数据**（1101条）通过UPDATE JOIN完成

### 修复2: 热点保底value_reasons标签错误（2026-05-28）

#### 症状
热点保底逻辑实际使用 `position <= 20` 作为保底阈值，但第500行的 `value_reasons` 写死了 `if position <= 8`。导致第9-20条保底数据被错误标记为"白名单匹配"，但实际上它们是通过热点保底放行的。

#### 修复
```python
# 第500行
f"热点保底-{platform_prefix}-第{position}条" if position <= 20 else "白名单匹配"
# 之前是 position <= 8
```

该问题不影响数据清洗结果（保底逻辑本身是对的），只影响value_reasons标签的准确性。

### 教训
- `raw_intelligence` 和 `cleaned_intelligence` 的列结构不一致，需要手动维护映射
- 新加列（如 category_tags）必须同步更新所有读取它的SELECT
- 标签系统有两套命名格式：`extract_tags()` 输出 `Beauty_Photo`/`Sports_Fight`（用于cleaned.tags），采集器输出 `Photo|Camera|Match`（用于raw.category_tags），推送端只认前者。如果清洗管道不合并，后面的管道全断。
- 热点保底的阈值和记录标签需要保持同步：如果改了保底数量（<=8→<=20），对应的value_reasons字符串条件也要改

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
