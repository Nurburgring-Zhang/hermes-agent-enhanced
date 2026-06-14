---
name: lowscore-cleaning-workflow
title: 低分数据清理工作流
description: 系统清理Hermes intelligence.db中AI评分低于阈值的低质量数据。诊断→清理→管道改造全流程。
version: 1.0
author: Hermes
trigger: manual_on_demand
readiness: available
---

# 低分数据清理工作流

## 触发条件
- 用户反馈"AI评分积压"、"数据清理"、"过滤无效"
- wake_guide.json 显示大量待评分数据
- 怀疑 cleaned_intelligence 堆积低质量数据

## 诊断步骤

> **前置参考：** 如果需要深入诊断评分状态（四维扫描、评分引擎选择、API故障排查等），参见 [`ai-six-dimension-scoring-pipeline`](../intelligence/ai-six-dimension-scoring-pipeline/SKILL.md) 技能，该技能专门覆盖评分引擎的诊断、故障树和恢复流程。本skill聚焦于**已评分数据的清理和归档**。

### 0. 先确认数据库文件存在
```bash
cd ~/.hermes && python3 -c "
import os
for f in os.listdir('.'):
    if f.endswith('.db'):
        print(f'{f}: {os.path.getsize(f)//1024//1024} MB')
"
```
cleaned_intelligence 数据可能在 intelligence.db 中，也可能不单独存在。先找库再查表。

### 1. 查库结构（全表+列+行数）
```bash
cd ~/.hermes && python3 << 'Q'
import sqlite3, os
# 尝试多个可能的DB文件名
dbs = [f for f in os.listdir('.') if f.endswith('.db')]
for db_name in ['intelligence.db', 'cleaned_intelligence.db']:
    if db_name not in dbs:
        print(f'[跳过] {db_name} 不存在')
        continue
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    tables = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f'=== {db_name} ===')
    for tname in tables:
        cols = [col[1] for col in c.execute(f"PRAGMA table_info({tname})").fetchall()]
        cnt = c.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
        print(f"  {tname}: {cnt}行, cols={cols}")
    conn.close()
Q
```

### 2. 查评分分布（四维扫描）
不只看 bucket 分布，还要查多个不同维度的未评分状态：

```bash
cd ~/.hermes && python3 << 'Q'
import sqlite3
conn = sqlite3.connect('intelligence.db')  # or the correct DB
c = conn.cursor()

# ① 基础bucket分布
print('=== 评分bucket分布 ===')
dist = c.execute("""
    SELECT CASE 
        WHEN ai_score_total < 20 THEN '0-19(低)'
        WHEN ai_score_total < 40 THEN '20-39(中低)'
        WHEN ai_score_total < 60 THEN '40-59(中)'
        WHEN ai_score_total < 80 THEN '60-79(中高)'
        ELSE '80+(高)' END as bucket,
        COUNT(*) as cnt, ROUND(AVG(ai_score_total), 1) as avg
    FROM cleaned_intelligence WHERE ai_score_total IS NOT NULL
    GROUP BY bucket ORDER BY bucket
""").fetchall()
for b, cnt, avg in dist:
    print(f"  {b}: {cnt}条 (均分{avg})")

# ② 四维未评分检查
print('\n=== 未评分检查 ===')
for check, sql in [
    ('真正未评分 (total IS NULL)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL'),
    ('得分为0 (total=0)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0'),
    ('有分但无时间戳 (>0 AND scored_at IS NULL)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NULL'),
    ('正常已评分 (>0 AND scored_at NOT NULL)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NOT NULL'),
    ('总行数', 'SELECT COUNT(*) FROM cleaned_intelligence'),
]:
    r = c.execute(sql).fetchone()[0]
    print(f'  {check}: {r}')

# ③ ai_score_queue 状态
print('\n=== ai_score_queue状态 ===')
try:
    q = c.execute('SELECT status, COUNT(*) FROM ai_score_queue GROUP BY status').fetchall()
    for s, cnt in q:
        print(f'  status={s}: {cnt}条')
except:
    print('  无ai_score_queue表')

# ④ 得分为0的来源分布（帮助判断是否批量问题）
print('\n=== 得分为0的来源TOP10 ===')
c.execute('''
    SELECT source, platform, COUNT(*) as cnt FROM cleaned_intelligence 
    WHERE ai_score_total = 0 
    GROUP BY source ORDER BY cnt DESC LIMIT 10
''')
for r in c.fetchall():
    print(f'  {r[0]:>20}: {r[2]:>4}条')

conn.close()
Q
```

### 3. 查孤立raw数据
```bash
c.execute('SELECT COUNT(*) FROM raw_intelligence r LEFT JOIN cleaned_intelligence c ON r.id=c.raw_id WHERE c.raw_id IS NULL AND r.collected_at < datetime("now", "-3 day")')
```

## ⚠️ pipeline --mode score模式说明

`scripts/hermes_intelligence_pipeline.py` **已有 `score` 模式**（line 761）。它基于规则引擎 (`calc_item_scores`) 处理 `cleaned_intelligence` 表中 `ai_score_total IS NULL OR =0 AND reasoning IS NULL` 的条目。每次处理上限由 `--limit` 控制。

### ⚠️ 已知限制：只查cleaned_intelligence，不查archive_cleaned和history_archive

`score` 模式的 SQL 只查 `cleaned_intelligence` 表。**`archive_cleaned` 表和 `history_archive` 表中有积压评分数据时不会被处理**。

- **`archive_cleaned`** — 归档的旧清理数据，schema类似但无content字段，需要`calc_item_scores`手动处理
- **`history_archive`** — 压缩归档的历史数据（25557条），schema更精简——只有`id, title, platform, source, url, summary, collected_at`等字段，**无content**。评分必须基于`title+source+platform`做轻量级规则评分。千万不能直接用`calc_item_scores`（它依赖content字段）。

**`history_archive`手动评分方法（无content时的降级方案）：**

当`history_archive`表中出现未评分积压时（schema：`id, title, source, platform, summary`，summary字段通常为空），不能复用`calc_item_scores`（它需要content字段）。必须写内联规则评分，只基于标题+来源+平台：

```python
import sqlite3
conn = sqlite3.connect('intelligence.db')
c = conn.cursor()

# 可信来源列表（同calc_item_scores）
trusted_sources = ['36kr', '虎嗅', '品玩', '极客公园', '界面', '财新', '第一财经',
                   '澎湃', '腾讯科技', '新浪科技', '网易科技', 'cnbeta', 'ithome',
                   'arxiv', 'github', 'huggingface', 'nature', 'ieee']
tech_terms = ['transformer', 'cnn', 'rnn', 'lstm', 'attention', 'diffusion', 'vae', 'gan',
              'bert', 'gpt', 'llm', 'rag', 'fine-tuning', '强化学习', '深度学习', '神经网络',
              'kubernetes', 'docker', '微服务', 'serverless', 'gpu', 'tpu', '量化',
              '剪枝', '蒸馏', 'embedding', 'token', '参数', '算法', '架构', '协议',
              'ai', '人工智能', '大模型', '机器人', '自动驾驶', '芯片']

# 获取未评分的archive记录
c.execute('SELECT COUNT(*) FROM history_archive WHERE ai_score_total IS NULL OR ai_score_total = 0')
total = c.fetchone()[0]
print(f'Unscored: {total}')

rows = c.execute('''
    SELECT id, COALESCE(title,"") as title, COALESCE(source,"") as source,
           COALESCE(platform,"") as platform
    FROM history_archive
    WHERE ai_score_total IS NULL OR ai_score_total = 0
    ORDER BY id ASC LIMIT 200
''').fetchall()

for row in rows:
    item_id, title, source, platform = row
    combined = f"{title} {source} {platform}".lower()
    
    # SCARCITY (0-30)
    if any(kw in combined for kw in ['全球首', '业界首款', '全球首个', '独家']):
        scarcity = 26
    elif any(kw in combined for kw in ['首款', '首次', '首发', '里程碑']):
        scarcity = 18
    else:
        scarcity = 10
    
    # IMPACT (0-30)
    if any(kw in combined for kw in ['改变格局', '颠覆', '变革', '引领']):
        impact = 24
    elif any(kw in combined for kw in ['发布', '推出', '新品', '开源']):
        impact = 14
    elif any(kw in combined for kw in ['收购', '融资', 'ipo', '上市']):
        impact = 16
    else:
        impact = 8
    
    # TECH DEPTH (0-15)
    found_terms = [t for t in tech_terms if t in combined]
    tech_depth = min(15, 3 + len(found_terms) * 2) if found_terms else 3
    
    # TIMELINESS (0-10) — archived data default 3
    timeliness = 3
    if any(kw in combined for kw in ['刚刚', '今日', '今天', '分钟前']):
        timeliness = 9
    elif any(kw in combined for kw in ['昨日', '昨天', '本周']):
        timeliness = 7
    
    # PREFERENCE (0-10)
    if any(kw in combined for kw in ['ai', '人工智能', '大模型', 'llm', 'gpt', 'deepseek', '机器人']):
        preference = 8
    elif any(s in source.lower() for s in ['csdn', 'github', 'arxiv', 'huggingface']):
        preference = 7
    else:
        preference = 5
    
    # CREDIBILITY (0-5)
    if source and any(s in source.lower() for s in trusted_sources):
        credibility = 4
    elif platform and any(p in platform.lower() for p in ['news', 'tech', 'media']):
        credibility = 3
    else:
        credibility = 2
    
    total = scarcity + impact + tech_depth + timeliness + preference + credibility
    importance_score = round(total / 10.0, 1)
    
    c.execute('''UPDATE history_archive SET ai_score_scarcity=?, ai_score_impact=?,
        ai_score_tech_depth=?, ai_score_timeliness=?, ai_score_preference=?,
        ai_score_credibility=?, ai_score_total=?, importance_score=? WHERE id=?''',
        (scarcity, impact, tech_depth, timeliness, preference, credibility,
         total, importance_score, item_id))

conn.commit()
conn.close()
```

注意：这类评分结果偏低是正常现象（均值33左右，90% < 40），因为history_archive无正文，只能靠标题判断。这是归档数据的固有特性。

**`archive_cleaned`手动评分方法（有content可用calc_item_scores）：**

```python
import sys
sys.path.insert(0, '.')
from scripts.hermes_intelligence_pipeline import calc_item_scores

conn = sqlite3.connect('data/intelligence.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('''
    SELECT id, title, COALESCE(content,'') as content,
           source, platform, published_at
    FROM archive_cleaned
    WHERE (ai_score_total IS NULL OR ai_score_total = 0)
    AND (ai_score_reasoning IS NULL OR ai_score_reasoning = '')
    ORDER BY id ASC LIMIT 200
''').fetchall()
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for row in rows:
    scores = calc_item_scores(row['title'] or '', row['content'] or '',
                               row['source'] or '', row['platform'] or '')
    conn.execute('''UPDATE archive_cleaned SET ai_score_scarcity=?,
        ai_score_impact=?, ai_score_tech_depth=?, ai_score_timeliness=?,
        ai_score_preference=?, ai_score_credibility=?, ai_score_total=?,
        importance_score=?, ai_score_reasoning=?, ai_scored_at=?
        WHERE id=?''', (scores['scarcity'], scores['impact'],
        scores['tech_depth'], scores['timeliness'], scores['preference'],
        scores['credibility'], scores['total'], scores['importance_score'],
        scores['reasoning_json'], now, row['id']))
conn.commit()
conn.close()
```

如果发现未评分的积压数据，遵循以下两步流程：

## 两步流程：先评分、再清理

### 第1步：评分积压处理（预清理）

在清理低分数据前，先确保所有数据已评分。工具选择：

| 工具 | 功能 | 适用条件 | 注意 |
|------|------|----------|------|
| `score_backlog_200.py` | 规则引擎评分，处理 `ai_score_total IS NULL` | **完全未评分**的数据（新入库从未被评） | 上限200条，平均38分，来源多为HN/虎嗅/B站等 |
| `score_backlog_200_v2.py` | 遗留格式六维评分升级 | `ai_score_reasoning` JSON不完整（不含scarcity/impact的维度描述） | ✅ **仍有效**（2026-05-30处理64条），见陷阱#7 |
| `score_zero_backlog.py` | 规则引擎评分，处理 `ai_score_total IS NULL OR =0` | 零分/未评分条目（A类已评0分+B类真未评分） | 复用v2评分引擎，修正DB路径和WHERE条件。2026-05-30新建。见 `scripts/score_zero_backlog.py` |

**推荐顺序：**
```bash
# 1a. 先用score_backlog_200.py（处理真正未评分的）
cd ~/.hermes && python3 scripts/score_backlog_200.py

# 1b. 如果仍有残留未评分，改用execute_ai_scoring.py（AI评分）
python3 scripts/execute_ai_scoring.py --batch scripts/ai_batch_to_score.json

# 1c. 再检查旧的score_backlog_200_v2.py（旧格式，通常0条）
python3 scripts/score_backlog_200_v2.py
```

**验证评分状态：**
```bash
python3 -c "
import sqlite3
c = sqlite3.connect('data/intelligence.db').cursor()
for check, sql in [
    ('总记录数', 'SELECT COUNT(*) FROM cleaned_intelligence'),
    ('未评分(IS NULL)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL'),
    ('得分为0(=0)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0'),
    ('已评分(>0)', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0'),
]:
    print(f'  {check}: {c.execute(sql).fetchone()[0]}')
c.close()
"
```

### 第2步：清理低分数据（低分清理）

评分完成后，执行低分清理：

```bash
# 预览
python3 scripts/lowscore_cleaner.py --dry-run

# 实际清理（推荐--fast跳过VACUUM，避免生产环境锁库）
python3 scripts/lowscore_cleaner.py --fast
```

典型结果（2026-05-30实测）：
- 58条低分(ai_score_total<20) + 1635条孤立raw数据被清理
- DB体积: 372MB → 90MB（-76%）

## 清理执行

### 方案A：直接SQL（无专用脚本也可执行）
`lowscore_cleaner.py` 可能不存在。直接内联 Python 也可以安全清理：

```bash
cd ~/.hermes && python3 << 'PYEOF'
import sqlite3, json, time
from datetime import datetime

conn = sqlite3.connect('intelligence.db')
cur = conn.cursor()

# ---- STEP 1: 诊断 ----
null_scores = cur.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL').fetchone()[0]
zero_scores = cur.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0').fetchone()[0]
partial_ts = cur.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NULL').fetchone()[0]
print(f'未评分: {null_scores}, 得分为0: {zero_scores}, 有分无时间戳: {partial_ts}')

# ---- STEP 2: 归档+删除0分项（建议先跑）----
if zero_scores > 0:
    items = cur.execute('''
        SELECT id, title, platform, source, url, collected_at 
        FROM cleaned_intelligence WHERE ai_score_total = 0 ORDER BY id
    ''').fetchall()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for item in items:
        compressed = json.dumps({
            'title': item[1], 'platform': item[2], 'source': item[3],
            'collected_at': item[5], 'score_total': 0
        }, ensure_ascii=False)
        cur.execute('''
            INSERT INTO archive_cleaned 
            (title, platform, source, archived_at, compressed_data, ai_score_total, ai_score_reasoning, ai_scored_at)
            VALUES (?, ?, ?, ?, ?, 0, '', ?)
        ''', (item[1], item[2] or '', item[3] or '', now, compressed, now))
    
    ids = [item[0] for item in items]
    for i in range(0, len(ids), 200):
        batch = ids[i:i+200]
        cur.execute(f'DELETE FROM cleaned_intelligence WHERE id IN ({",".join(["?"]*len(batch))})', batch)
    print(f'归档并删除了 {len(ids)} 条0分数据')

# ---- STEP 3: 修补时间戳 ----
if partial_ts > 0:
    cur.execute('''
        UPDATE cleaned_intelligence 
        SET ai_scored_at = collected_at || ' 23:59:59'
        WHERE ai_score_total > 0 AND ai_scored_at IS NULL
    ''')
    print(f'修补了 {cur.rowcount} 条时间戳')

conn.commit()
conn.close()
PYEOF
```

如果确认低分清理有效，再决定是否创建 `lowscore_cleaner.py`。

### 方案B：使用 lowscore_cleaner.py（推荐）
`lowscore_cleaner.py` 已在 `~/.hermes/scripts/lowscore_cleaner.py`，支持 `--dry-run`、`--fast`、`--threshold N`、`--zero-only` 参数。功能：
1. 扫描 cleaned_intelligence 中 ai_score_total < 20（默认）的数据
2. 归档到 archive_cleaned 表（保留评分明细）
3. 从 cleaned_intelligence 删除
4. 清理 raw_intelligence 中3天以上未清洗的孤立数据
5. VACUUM 回收空间

#### ⚠️ 兼容性处理：`compressed_data` 列自动检测
脚本会自动检测 `archive_cleaned` 表是否有 `compressed_data` 列：
- **有** → 用压缩字段方式归档（节省空间）
- **无** → 回退到完整字段插入（自动添加列也可）：`ALTER TABLE archive_cleaned ADD COLUMN compressed_data TEXT DEFAULT NULL;`

如果执行报该列错误，只需手动添加一次该列即可修复。

### 关键命令
```bash
# 预览（先做这个！）
python3 scripts/lowscore_cleaner.py --dry-run

# 实际清理
python3 scripts/lowscore_cleaner.py

# 快速清理（不VACUUM，有compressed_data Bug）
python3 scripts/lowscore_cleaner.py --fast
```

### 注册cron
```bash
cronjob action=create name="低分数据自动清理-每4小时" schedule="0 */4 * * *" \
  prompt="执行低分清理: cd ~/.hermes && python3 scripts/lowscore_cleaner.py --fast" \
  deliver=local
```

### 改造清洗管道
在 `unified_cleaning_pipeline.py` 的 `clean_batch()` 函数末尾（conn.close()之前）添加：
```python
low_cut = conn.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total < 20").fetchone()[0]
if low_cut > 0:
    # 归档低分数据到archive_cleaned
    # 从cleaned_intelligence删除
    # commit
```

## 验证
```bash
python3 -c "
import sqlite3; c=sqlite3.connect('intelligence.db'); \
  print('低分残留:', c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total>0 AND ai_score_total<20').fetchone()[0]); \
  print('archive:', c.execute('SELECT COUNT(*) FROM archive_cleaned').fetchone()[0]); \
  print('未评分:', c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total=0').fetchone()[0]); \
  c.close()
"
```

## 关联技能
- [`ai-six-dimension-scoring-pipeline`](../intelligence/ai-six-dimension-scoring-pipeline/SKILL.md) — AI评分引擎的诊断、故障树和评分工具选择流（本skill涉及的评分状态诊断参见此技能）
- [`hermes-db-maintenance`](../operations/hermes-db-maintenance/SKILL.md) — 通用数据库维护（WAL检查点、vacuum、大小监控），处理完评分积压后常需跟DB维护

## 关联参考
- `references/all-clear-confirmation-20260529.md` — 第一次"全已评分"确认（2026-05-29），含上游管道确认流程和输出模板
- `references/all-clear-confirmation-20260530.md` — 第三次连续"全已评分"确认（2026-05-30），证明系统已进入稳态，含三次对比数据和"这个cron任务可以降频"建议
- `references/all-clear-confirmation-20260530-v2.md` — 第四次连续确认（2026-05-30 10:05），手动处理5条零内容条目，首次发现v2脚本WHERE条件已过时
- `references/all-clear-confirmation-20260530-v3.md` — **第五次连续确认**（2026-05-30 15:32），确认`score_backlog_200.py`对`ai_score_total=0+已有reasoning`的条目正确跳过，零积压持续稳定
- `references/all-clear-confirmation-20260531.md` — **第七次连续确认**（2026-05-31 00:04），15,381条全已评分，稳态运营已验证7次。`--mode score` 不存在的cron陷阱持续有效。
- `references/score-backlog-cleanup-20260530-v2.md` — 2026-05-30第二轮清扫（短内容尾数）：清理最后2条score=0的短内容条目，采用内联Python规则评分而非现有脚本
- `references/score-backlog-cleanup-20260530-v3.md` — 2026-05-30第三轮清扫（零分条目定点清理）：7条score=0，新建score_zero_backlog.py，确认稳态。含A/B两类零分区分和cron提示词bug分析
- `references/history-archive-scoring-20260602.md` — 2026-06-02 history_archive 5504条未评分积压处理记录。包含history_archive表结构说明、评分方法、高分样例、最终统计

## 参数参考
- 默认阈值: ai_score_total < 20
- 高分(≥60): 保留优先推送
- 中分(20-59): 保留正常推送  
- 低分(<20): 归档+删除
- cron频率: 每4小时
- raw孤立数据清理: 3天以上

## 陷阱
1. 先 `--dry-run` 预览再实际清理
2. 大库 VACUUM 可能锁库数秒
3. cleaned 数据可能比 raw 多（多源累加），这是正常的
4. archive_cleaned 表必须有正确的列结构
### 5. **⚠️ "未评分积压"陷阱**：用户要求"处理未评分积压"时，`ai_score_queue` 可能已经全部是 `scored` 状态。实际检查 `cleaned_intelligence.ai_score_total IS NULL` 往往为0。真正的积压可能是：
   - **得分为0的数据**（`ai_score_total = 0`）— 已评分但被评了0分，需要清理归档
   - **有分无时间戳**（`ai_score_total > 0 AND ai_scored_at IS NULL`）— 评分动作已完成但时间戳字段缺失，需要修补
   - **所有六维=0但有JSON reason**（`ai_score_scarcity=0 AND ... AND ai_score_credibility=0 AND ai_score_reasoning LIKE '{%'`）— 被AI评分正确打了0分的数据（纯娱乐内容），不是积压，不需要处理
   - **所有六维=0且无reasoning** — 真正未评分的积压数据，需要用规则引擎评分（复用score_backlog_200_v2.py的score_item函数）
   - 不要直接认为"有积压"就找评分工具，先做六维完整诊断再决定行动

### 6. **🔴 "全已评分"时的上游管道确认**：当 cleaned_intelligence 中 0 条未评分，后续正确步骤不是直接输出"无积压"结束。必须再做两项确认来判断系统是否健康：
   - **确认 raw→cleaned 清洗管道健康**：`SELECT COUNT(*) FROM raw_intelligence r LEFT JOIN cleaned_intelligence c ON r.id=c.raw_id WHERE c.id IS NULL` — 如果有大量未清洗 raw 数据，检查其来源分布（`GROUP BY r.source`）。CSDN 低质科普被过滤是正常行为；ithome/sina_tech 被批量过滤可能表示清洗管道故障。
   - **确认三条评分路径都找不到积压**：①标准SQL：`ai_score_total IS NULL`→0 ②全维度=0且无reasoning→0 ③`score_backlog_200.py`（标准规则引擎评分）：返回"0条" ✅
   - 注意：**`ai_score_total=0` 但 `ai_score_reasoning` 有JSON的条目是已评分的**——这是正确行为。`score_backlog_200.py` 的 WHERE 条件 `(IS NULL OR =0) AND (reasoning IS NULL)` 正确排除了这类条目，不要误判为"漏筛"。
   - 三项都确认后，再输出"无需处理"结论。

### 7. **🟡 score_backlog_200_v2.py 仍然有效（2026-05-30修正）**：

   先前此陷阱声称 v2 已无实际匹配数据，但 **2026-05-30 17:35实测推翻了这一判断**：`score_backlog_200_v2.py` 成功处理了 **64条**遗留格式数据。

   **工作原理**：v2查找 `ai_score_reasoning` 不含 `scarcity` 或 `impact` 关键词的条目（即 reasoning 是旧格式纯文本而非JSON格式）。虽然外观上所有条目都有JSON格式reasoning，但部分条目的score_items函数生成的JSON缺失维度级描述——v2把这些升级为完整的六维JSON。

   **关键发现**：
   - **DB路径已正确**：脚本第13行 `DB_PATH = HERMES + "/data/intelligence.db"` — 注意这与一些会话中记录的"路径错误"不同。脚本当前版本已使用正确路径。如果运行时报错，检查该行。
   - **v2不处理 `ai_score_total IS NULL` 的条目**——这是v1的工作。v2处理的是**已有分数但有格式缺陷**的数据。
   - **v2 vs v1 分工**：v1 → `ai_score_total IS NULL`（完全未评分），v2 → `ai_score_reasoning` 格式不完整（简略评分→六维JSON）。两个脚本互补而非重叠。

   **推荐使用顺序**：先v1，再v2，构成完整的积压清理链。
   
   **关于真正的积压剩余**：
   - **`(ai_score_total IS NULL OR =0) AND (ai_score_reasoning IS NULL OR '')`** — 完全没评过的数据（极少，用v1处理或直接内联Python）
   - **`ai_score_total = 0 AND ai_score_reasoning LIKE '{%'`** — 被评了0分且有JSON reason的数据（纯娱乐，无需重新评分）
   - **`ai_score_total IS NULL AND LENGTH(COALESCE(content,'')) < 30`** — 零内容条目（Baidu Hot Search/Click:0 Score:0），评分工具全部跳过，必须手动SQL UPDATE
   如果需要处理真正的积压，复用v1的score_item函数比依赖v2更可靠。

### 8.  **⚠️ pipeline --mode score 已存在（2026-05-31更新）**：`hermes_intelligence_pipeline.py` **已有 `score` 模式**（line 761），基于规则引擎评分。旧版本技能说它不存在是因为该模式是后来加入的。现在可用，但它**只查 `cleaned_intelligence`，不查 `archive_cleaned`**。处理积压时须手动补跑 archive_cleaned（见本技能 pipeline 模式说明章节中的代码）。

### 9. **🔴 value_level 数据健康陷阱（2026-05-30新发现）**：

   **问题**：cleaned_intelligence.value_level 可能包含脏数据——值为 `'pending'`（字符串）或 `0`（整数），而非预期的 1-5。来源是清洗管道 SQL 的 `DEFAULT 0` 或遗留代码 INSERT 时未设置值。

   **影响**：所有读取 value_level 的代码（包括 pipeline 的 `write_diary()` 和 `write_memory()` 中的 `"⭐" * value_level`）都会因 `TypeError` 崩溃。

   **并行Bug**：`write_diary()` 和 `write_memory()` 中有两个独立的 `"⭐" * item["value_level"]` 语句——修复一个漏掉另一个，管道仍然会崩。必须两处都修。

   **修复SQL**：基于 ai_score_total 自动换算：
   ```sql
   UPDATE cleaned_intelligence 
   SET value_level = CASE 
       WHEN ai_score_total >= 80 THEN 5
       WHEN ai_score_total >= 60 THEN 4
       WHEN ai_score_total >= 40 THEN 3
       WHEN ai_score_total >= 20 THEN 2
       ELSE 1
   END
   WHERE value_level IS NULL OR value_level = 0 OR value_level = 'pending';
   ```

   **修复代码**（在她日记+记忆写入函数中）：
   ```python
   vl = int(item.get("value_level", 0)) if item.get("value_level") else 0
   stars = "⭐" * vl
   ```

   **验证**：
   ```sql
   SELECT DISTINCT value_level, COUNT(*) FROM cleaned_intelligence GROUP BY value_level ORDER BY value_level;
   -- 预期：只有 1,2,3,4,5（无 0，无 'pending'）
   ```

   详见 `references/score-backlog-pipeline-run-20260530.md`。

### 10. **🔴 cron提示词陷阱（2026-05-31更新）**：

当前cron任务prompt为：
```
处理cleaned_intelligence中未评分的积压数据。工作目录~/.hermes/，运行 python3 scripts/hermes_intelligence_pipeline.py --mode score 来批量处理AI评分队列。每次处理200条。
```

**现状更新（2026-05-31）：** `--mode score` 现在**确实存在**并正常工作。pipeline的score模式能正确处理cleaned_intelligence的积压。但存在两个问题：

1. **只查cleaned_intelligence，忽略archive_cleaned** — 评分积压还可能存在于`archive_cleaned`表中（2026-05-31实测发现223条+1条脏数据）
2. **脏数据清理** — `archive_cleaned`表中可能包含`id=NULL`的脏数据（来源为douyin等短内容平台，content仅42字符），需要手动DELETE

**建议cron prompt更新为：**
```
处理intelligence.db中未评分的积压数据。先pipeline --mode score（cleaned_intelligence），再手动处理archive_cleaned和history_archive。两项均为0则[SILENT]。
```

额外事项：检查并清理 scripts/ai_batch_to_score.json 和 scripts/next_ai_batch.json 这类陈旧中间文件——如果其ID不在cleaned_intelligence中，说明是上游管道残留，应删除。

### 11. **🔴 history_archive评分盲区（2026-06-02新发现）**：

history_archive表（25557条归档数据）可能含有未评分积压，而pipeline --mode score和所有现有评分脚本（score_backlog_200.py等）都**只查cleaned_intelligence**。2026-06-02发现5504条history_archive未评分数据。

**schema区别**：history_archive无content字段、无ai_scored_at和ai_score_reasoning字段。summary字段全为空。仅`id, title, source, platform`可用于评分。

**处理方法**：不能复用calc_item_scores（需要content）。必须写基于title+source+platform的内联规则评分（见本章节`history_archive手动评分方法`）。

**评分特征**：结果偏低是正常的。实测5504条均分~33，90% < 40。因为只有标题没有正文，靠标题判断难以给高分。

**建议**：cron prompt增加三表检查逻辑——先cleaned_intelligence、再archive_cleaned、再history_archive。


## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
