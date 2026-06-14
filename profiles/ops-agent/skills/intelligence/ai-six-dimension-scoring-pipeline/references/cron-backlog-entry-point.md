# Cron积压评分入口路由模式

## 场景：cron收到"处理cleaned_intelligence中未评分的积压数据"

这是最常见的cron评分请求，但容易走弯路（如错误调用 `hermes_intelligence_pipeline.py --mode score`）。

## 正确路由

### 第0步：诊断数据库状态

```bash
cd ~/.hermes && python3 -c "
import sqlite3
db = sqlite3.connect('intelligence.db')
cur = db.execute('PRAGMA table_info(cleaned_intelligence)')
cols = [c[1] for c in cur.fetchall()]

# 检查表结构中有哪些评分相关字段
score_cols = [c for c in cols if 'ai_score' in c.lower() or 'score' in c.lower()]
print(f'评分字段: {score_cols}')

# 多维检查
checklist = [
    ('total IS NULL', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL'),
    ('total = 0', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0'),
    ('reasoning LIKE 规则评分', \"SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_score_reasoning LIKE '%规则评分%'\"),
    ('reasoning LIKE 规则引擎', \"SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_score_reasoning LIKE '%规则引擎%'\"),
    ('scored_at IS NULL', 'SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0 AND ai_scored_at IS NULL'),
]
for label, sql in checklist:
    try:
        cnt = db.execute(sql).fetchone()[0]
        print(f'{label}: {cnt}')
    except Exception as e:
        print(f'{label}: ERROR {e}')

# 总结
total = db.execute('SELECT COUNT(*) FROM cleaned_intelligence').fetchone()[0]
scored = db.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total > 0').fetchone()[0]
print(f'总{total}条, 已评分{scored}({100*scored/total:.1f}%)')
db.close()
"
```

### 第1步：按数据库状态选工具

| 诊断结果 | 工具 | 理由 |
|---------|------|------|
| `ai_score_total IS NULL` 少量 (<20) | `delegate_task` AI评分 | 少量条目直接子代理评分，质量最高 |
| `ai_score_total IS NULL` 大量 (>100) | `score_backlog_200.py` 先跑 | 快速规则评分填平 |
| `ai_score_total = 0` (实际已规则评分但0分) | `delegate_task` AI评分+零内容归档 | 0分通常是短内容/旅行游记，用AI理解确认 |
| `reasoning LIKE '%规则%'` (规则评分积压) | `ai_sixdim_scorer.py` | 专门处理此场景，内容感知升级 |
| 混合状态 | `score_backlog_200.py` 先清 + `delegate_task` 精评 | 两步走 |

### 第2步：执行

**快速清尾（推荐首选）**：
```bash
cd ~/.hermes && python3 scripts/score_backlog_200.py
```

`score_backlog_200.py` 的特点：
- 基于 `batch2_ai_scorer.py` 的规则引擎
- 一次处理200条，~0.05秒完成
- 过滤条件：`content IS NOT NULL AND content != ''`（不含纯空内容）
- 如果未评分数据是旧已评0分内容（如旅行游记），部分会被跳过

**AI真实评分（少量深度评分）**：
通过 `delegate_task` 子代理做六维AI理解评分。完整工作流：
1. 从DB读取未评分条目的完整内容
2. 构建评分prompt（含六维标准 + 格林主人偏好）
3. 子代理逐条评分（含reasoning字段）
4. 直接UPDATE写回cleaned_intelligence

示例命令（内联）：
```bash
cd ~/.hermes && python3 << 'INLINE'
import sqlite3, json
from datetime import datetime

DB = "intelligence.db"
conn = sqlite3.connect(DB)

# 找出需要AI评分的条目
items = conn.execute("""
    SELECT id, title, content, source, platform, author, tags, category
    FROM cleaned_intelligence
    WHERE (ai_score_total IS NULL OR ai_score_total = 0)
      AND LENGTH(COALESCE(content,'')) > 50
    ORDER BY id LIMIT 20
""").fetchall()

# → 实际评分用delegate_task子代理做
# → 评分结果以六维数组+reasoning JSON格式写回
INLINE
```

**零内容条目处理**：
对于content为空的条目(纯标题)，直接赋低分：
```python
# 零内容条目 = 统一低分（2-3分，已过时的旅行/生活类内容）
import sqlite3, json
conn = sqlite3.connect('intelligence.db')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# 每条按来源+标题做简单规则评分
conn.execute("""UPDATE cleaned_intelligence SET
    ai_score_scarcity=1, ai_score_impact=0, ai_score_tech_depth=0,
    ai_score_timeliness=0, ai_score_preference=0, ai_score_credibility=1,
    ai_score_total=2, importance_score=0.2,
    ai_score_reasoning=?, ai_scored_at=?
WHERE (ai_score_total IS NULL OR ai_score_total=0) AND (content IS NULL OR content='')""",
    (json.dumps({"summary":"纯标题条目,低分自动评分"}, ensure_ascii=False), now))
conn.commit()
```

### 零内容条目（28字符微博垃圾数据）

**场景**：1条积压（标题 "iPhone18Pro樱桃色"，内容仅 "Label:新 Score:276065"，来源 weibo）

**诊断结果**：`ai_score_total IS NULL/0 = 1条`，content仅28字符，纯微博热点标签

**处理**：`score_backlog_200.py` 正确处理了该条目 → 34分（规则引擎合理给低分，因为标题含"iPhone"但有溢价，不含技术关键词）

**结果**：全部16046条 scored_at 有值，积压清理完毕

**要点**：
- score_backlog_200.py 的过滤条件是 `(ai_score_total IS NULL OR ai_score_total = 0) AND (ai_score_reasoning IS NULL OR ai_score_reasonING = '')` — **不限制 content 长度**
- 即使 content=28字符，规则引擎仍能基于标题+来源给出合理分数（34分偏低，正确）
- 这在 cron 自检报告中表现为 `SCORE_BACKLOG_RESULT:1`，`SCORE_AVG:34.0`
- 这种尾部1-5条垃圾数据不需要人工干预，规则引擎处理即可

## 2026-05-30 实测案例

### 场景：零内容知乎问答的最后1条积压

**诊断结果：** `cleaned_intelligence` 中 `ai_score_total = 0` 的条目仅1条
- ID=805500, title=你家乡美食都有什么？, source=zhihu, content=Click:0 Score:0 (15字符)
- ai_score_reasoning 为空的全新未评分条目

**尝试的路径（都失败）：**
1. `hermes_ai_scoring.py --full` → KeyError: id 崩溃（故障14）
2. `hermes_ai_scoring.py --batch 200` → 返回 0 条待评分（content=15字符被静默过滤）
3. `ai_sixdim_scorer.py` → 不处理（只处理已有规则评分的条目）

**最终处理：手动 SQL UPDATE 赋低分：**
```python
# 六维评分：scarcity=2, impact=0, tech_depth=0, timeliness=5, preference=1, credibility=3, total=11
# 结果：cleaned_intelligence 共16088条，全部已评分，积压清零
```

### 场景（10:05）：5条多来源零内容批量清尾

**诊断结果：** `cleaned_intelligence` 中 `ai_score_total IS NULL` 的条目共5条
- ID=806077, title=台特战部队格斗表演, source=baidu, content=Baidu Hot Search (17字符)
- ID=806081, title=雷军称被何小鹏李斌骗了, source=zhihu, content=Click:0 Score:0 (15字符)
- ID=806082, title=为何汽车外形越来越大, source=zhihu, content=Click:0 Score:0 (15字符)
- ID=806083, title=上交所发布重要公告, source=baidu, content=Baidu Hot Search (17字符)
- ID=806086, title=黄仁勋谈华为新突破, source=weibo, content=Label:新 Score:195464 (20字符)

**尝试的路径（都失败）：**
1. `hermes_intelligence_pipeline.py --mode score` → ❌ 无此模式（只有 all/route/index/generate/stats）
2. `score_backlog_200_v2.py` → ✅ 运行成功但匹配 **0 条**（其WHERE条件 `'%AI内容评分%'` 已过时，与新条目不重叠）
3. 两个脚本都无法自动处理这5条

**最终处理：内联Python规则引擎评分** — 复用 `score_backlog_200_v2.py` 的 `score_item()` 函数逻辑直接 UPDATE：
```python
# 评分逻辑：六维规则引擎（scarcity=10-18, impact=8-16, tech_depth=4-6, 
#            timeliness=5, preference=5-9, credibility=4-7）
# 来源加权: baidu=4, zhihu=7, weibo=4
# 结果: ID=806077→40分, 806081→39分, 806082→40分, 806083→46分, 806086→46分
# cleaned_intelligence 共15046条，全部已评分，积压清零
```

**关键教训（2026-05-30 10:05新增）：**
- 零内容条目有两种来源类型：热榜标签内容（Baidu Hot Search / Label:Score）和问答空内容（Click:0 Score:0），但处理方式相同
- 本次5条积压与上次1条积压的模式完全一致：全部 content<30字符、全部评分脚本无法处理
- **rule of thumb**：当 `ai_score_total IS NULL` 少于10条时，直接内联Python手动评分比尝试任何评分脚本都快（<1秒）
- 来源加权很重要：同为零内容，知乎来源得7分（可信），百度/微博得4分

**关键教训：**
- 最后1-5条零内容条目不能被任何评分脚本自动处理，必须手动 SQL
- 零内容条目评分参考：知乎空问答=11分，微博空标签=13分，科技纯标题=17分
- 不要改评分脚本去适配零内容条目，直接 SQL UPDATE 低分走人

## 2026-05-29 实测案例

### 场景：6条积压评分
- **诊断**：6条 `ai_score_total IS NULL OR = 0`，其中5条是纯旅行游记（已规则评分得0分），1条是新内容
- **步骤1**：`score_backlog_200.py` → 处理了1条（新内容，得40分）
- **步骤2**：`delegate_task` AI评分 → 处理5条旅行游记，每条AI理解评分2-3分
- **结果**：clean_intelligence 15828条全部评分，0积压
- **验证**：`SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0` → 0

## 2026-05-30 实测案例：全量已评分但value_level缺失

### 场景：cron要求"处理未评分的积压数据"

**诊断结果：**
```
全新未评分(ai_scored_at IS NULL): 0
规则评分可升级: 0
从只有summary无维度: 0
有内容但未评分: 0
value_level=0: 9                  ← 仅有此问题
```

所有15,335条 `ai_scored_at` 已有值、`ai_score_total` 已覆盖。不是评分积压，是**metadata映射缺失**。

**处理路径（调用hermes_intelligence_pipeline.py --mode score前先想想）：**

1. ❌ `pipeline --mode score` → 不存在（死胡同）
2. ❌ `hermes_ai_scoring.py --batch 200` → 0条（全部已评分）
3. ❌ `ai_sixdim_scorer.py` → No entries found（没有规则评分格式）
4. ✅ **`value_level_backfill.py`** → 全量重新映射value_level

**执行结果**（2026-05-30 21:34）：
```
修复前: 0:9, 1:2766, 2:10418, 3:1242, 4:627, 5:273
修复后: 0:11, 1:2737, 2:10511, 3:1168, 4:634, 5:274
管道可用: 中价值以上(>=3级): 2076条, 高价值(>=4): 908条
```

**关键教训：** value_level=0从9条变成11条不是错误，是阈值校正（score<20应归入level 0，之前错分到level 1的2条被纠正）。11条全部是score 4-17的垃圾数据，正常状态。

**判定规则（2026-05-30固化）：**
- `ai_scored_at IS NULL = 0` 且 `ai_score_total 100%覆盖` → **已评分，不需要跑评分**
- 如果 `value_level=0` 的条目含score>20的数据 → `value_level_backfill.py` 修复
- 如果 `value_level=0` 的条目全是score<20的垃圾 → 正常状态，返回 SILENT
- `value_level_backfill.py` 只在评分100%完成但 `value_level` 错乱的场景使用
- **不要在看到 `value_level=0` 时自动认为需要评分** — 先查 `ai_scored_at IS NULL` 才是真实未评分

## 关键陷阱

1. **`--mode score` 不存在**：`hermes_intelligence_pipeline.py` 不支持 score 模式（只有 all/route/index/generate/stats）。不要走到这个死胡同。
2. **`score_backlog_200.py` 限制**：它跳过纯空内容的条目。跑完后要检查是否还有剩余。
3. **已评0分的旧数据**：0分不一定等于未评分。如果 `ai_scored_at` 有值但总分0，是已评低分而不是积压。
4. **`hermes_ai_scoring.py` 无参数 vs `--batch` 的 content-length 差异**：
   - 无参数模式内容过滤条件：`LENGTH(COALESCE(content,'')) > 50` — content ≤ 50 字符的条目被**静默跳过**，不会报错
   - `--batch N` 模式内容过滤条件：`LENGTH(content) >= 0` — 接受所有长度
   - 如果 `--dry-run` 显示 N 条但实际评分只处理了 M 条(M < N)，差值是 content 1-50 字符的条目在无参数模式下被静默忽略了。改用 `--batch N` 或单独处理这些短内容。
5. **数据库路径误差**：`score_backlog_200.py` 内部硬编码了 `/home/administrator/.hermes/data/intelligence.db`，而实际 DB 在 `/home/administrator/.hermes/intelligence.db`（已修正为该路径）。如果出现 `no such table` 错误，先检查DB路径。
6. **少量条目用delegate_task比规则引擎更准确**：5条AI评分 vs 规则引擎评分的区别在于旅行游记类内容（AI会准确识别为低相关性，规则引擎可能误判为中等分）。
7. **最后1-5条卡在零内容条目时的处理**（2026-05-30固化）：当 `ai_score_total = 0` 只剩1-5条时，这些条目通常 content=0-15字符（如知乎空问答 Click:0 Score:0）。此时评分脚本全都会失败或静默跳过：
   - `--full` → KeyError 崩溃
   - `--batch N` → 0条返回（content<50被过滤）
   - `ai_sixdim_scorer.py` → 不处理
   - `score_backlog_200_v2.py` → 匹配0条（WHERE条件过时）
   - 正确做法：直接 SQL UPDATE 赋予统一低分（39-46分，基于来源+标题的规则引擎评分）+ 标记已评分。不要改评分脚本去适配零内容条目。

8. **pipeline --mode score 是死胡同**（2026-05-30 10:05确认）：这已经是第二次 cron 直接用 `pipeline --mode score` 执行失败。这个命令**不存在**。每次遇到此种请求，先确认 pipeline 参数再动手。如果目标只是评分积压数据，直接用 `score_backlog_200.py` 或内联Python。

9. **零内容条目的来源加权规则**（2026-05-30确认）：zhihu 来源的零内容条目即使只有标题，基础可信度也较高（7分），baidu 热榜和 weibo 热点来源的基础可信度低（4分）。评分时不用统一赋低分，做基本来源+标题关键词判断即可给出合理分。
