# 管道断裂模式：数据在采集→清洗→评分→推送 三个接口丢失

## 核心洞见
Hermes 的数据管道有4个阶段、3个接口。数据可以在任何一个接口丢失。排查"为什么有数据但推送不到"时，**不要只查推送系统**——查所有3个接口。

```
[采集] → 接口1 → [清洗] → 接口2 → [评分] → 接口3 → [推送]
```

## 接口1: 采集→清洗 (raw_intelligence → cleaned_intelligence)

### 症状
- raw_intelligence 中有大量数据
- cleaned_intelligence 中对应数据量很少
- 或 cleaned 数据中有大量 NULL/空 tags

### 根因模式

**模式A: category_tags 列丢失（2026-05-28发现）**
- raw_intelligence 有 `category_tags` 列（存放 `Photo|Camera|Match` 等）
- cleaned_intelligence 有 `tags` 列（存放 `Beauty_Photo|Tech` 等）
- 两个列格式不同，清洗管道 SELECT 时没有读取 `category_tags`

**诊断命令:**
```sql
-- 检查已清洗数据是否有标签丢失
SELECT COUNT(*) FROM cleaned_intelligence c 
JOIN raw_intelligence r ON c.raw_id = r.id 
WHERE r.category_tags IS NOT NULL AND r.category_tags != '' 
AND (c.tags IS NULL OR c.tags = '' OR c.tags = 'General');
```

**修复:**
1. SELECT 查询加 `r.category_tags`
2. INSERT 时用 `merge_tags(tags, category_tags)`
3. 批量回填历史数据（同上的UPDATE SQL）

**模式B: tags 格式不统一**
- `extract_tags()` 输出 `Beauty_Photo`/`Sports_Fight`/`Travel_Food` — 推送端认这种格式
- 采集器手写 `Photo|Camera|Match` — 推送SQL不认这种格式
- 清洗时如果不做格式转换或合并，后续全断

## 接口2: 清洗→评分 (cleaned_intelligence → ai_score)

### 症状
- cleaned_intelligence 有数万条数据
- 大部分 `ai_score_total IS NULL OR ai_score_total = 0`
- 增删改查评分队列为空

### 根因模式
**模式A: AI评分cron缺失**
- 没有定时跑 `hermes_intelligence_pipeline.py --mode score`
- 或评分脚本有未捕获异常静默退出

**模式B: ai_score_queue 表结构问题**
- 评分系统期望数据在 `ai_score_queue` 表中排队
- 但数据直接在 cleaned_intelligence 中等待被评分
- 如果评分脚本只读queue、不直接读cleaned，会出现"全部积压"但queue为空的矛盾状态

**诊断命令:**
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0')
unscored = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM ai_score_queue')
queued = c.fetchone()[0]
print(f'cleaned中未评分: {unscored}')  
print(f'ai_score_queue排队: {queued}')
# 如果unscored>0且queued=0，说明评分脚本不走queue，直接读cleaned
# 这属于正常行为，但需要确认评分脚本确实在读cleaned
c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE date(ai_scored_at)=date(\"now\",\"localtime\")')
scored_today = c.fetchone()[0]
print(f'今日已评分: {scored_today}')
# 如果scored_today=0且unscored>0，评分cron死了
conn.close()
"
```

### 修复
- 创建cron: `*/30 * * * * cd ~/.hermes && python3 scripts/hermes_intelligence_pipeline.py --mode score`
- 或直接调用评分函数

## 接口3: 评分→推送 (cleaned_intelligence → push)

### 症状
- cleaned_intelligence 数据量正常
- 大部分数据 `ai_score_total > 0`（评分正常）
- `is_processed=0`（待推送）的数据很多
- 但推送出来的候选池中没有某个方向的内容

### 根因模式

**模式A: 推送SQL的WHERE条件太窄**
- `get_candidates_balanced()` 中 WHERE 条件只认特定标签名
- 如 `tags LIKE '%Sports_Fight%'` 但不匹配 `tags LIKE '%Fight%'`
- 从 category_tags 合并进来的标签名与推送端期望的不一致

**诊断命令:**
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
c = conn.cursor()
# 检查待推送数据中某方向标签的评分
c.execute('''SELECT ai_score_total, tags, title FROM cleaned_intelligence 
    WHERE is_processed=0 AND ai_score_total > 0
    AND tags LIKE '%Fight%' OR tags LIKE '%Photo%' OR tags LIKE '%Chip%'
    ORDER BY ai_score_total DESC LIMIT 10''')
for row in c.fetchall():
    print(f'ai={row[0]}, tags={row[1]}, title={row[2][:50]}')
conn.close()
"
```

**模式B: AI评分太低 → 被高评分数据挤出候选池**
- 推送SQL有 `ai_score_total >= 15` 门槛
- 但300个候选中，AI/EV数据评分在86-98分
- 摄影/格斗数据评分在40-50分 → 300个名额被AI数据占满

**诊断命令:**
```bash
# 看最高300条评分区间
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
c = conn.cursor()
c.execute('''SELECT ai_score_total FROM cleaned_intelligence 
    WHERE is_processed=0 AND ai_score_total > 0 
    ORDER BY ai_score_total DESC LIMIT 300''')
scores = [r[0] for r in c.fetchall()]
print(f'TOP300评分区间: {min(scores):.0f} - {max(scores):.0f}')
print(f'中位数: {sorted(scores)[len(scores)//2]:.0f}')
conn.close()
"
```

**修复：**
1. 扩展SQL的tags LIKE条件（加 `%Photo%`, `%Fight%`, `%Chip%` 等）
2. 添加降级条件：`importance_score >= 50 OR personal_match_score >= 10` 绕过tags过滤
3. 或者减少候选池中的AI数据占比（但不是好主意，AI数据确实是最高质量的）

## 通用排查流程

当遇到"**数据在管道中消失了**"的问题时：

```
Step 1: 确定数据进了raw_intelligence
  → SELECT COUNT(*) FROM raw_intelligence WHERE date(collected_at)=date('now','localtime')
  
Step 2: 确定数据进了cleaned_intelligence  
  → SELECT COUNT(*) FROM cleaned_intelligence WHERE date(cleaned_at)=date('now','localtime')
  → 检查标签是否保留:
    SELECT c.tags FROM cleaned_intelligence c JOIN raw_intelligence r ON c.raw_id=r.id 
    WHERE r.category_tags IS NOT NULL LIMIT 5

Step 3: 确定数据被评分
  → SELECT COUNT(*) FROM cleaned_intelligence WHERE date(ai_scored_at)=date('now','localtime')

Step 4: 确定数据能进推送候选
  → cd ~/.hermes && python3 scripts/hermes_v12_push.py --draft 2>&1 | grep -iE 'photo|camera|fight|travel'
```

**何时停手**：如果前三步都通过了但推送还是不出现某方向内容，说明评分不够高被挤出了。这不是断裂问题，是正常的优先队列行为。
