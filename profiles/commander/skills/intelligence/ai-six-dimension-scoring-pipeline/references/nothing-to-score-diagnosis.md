# "Nothing to Score" 诊断手册 — 当评分引擎返回0条时

## 场景

你被调度执行评分任务（手动或cron），但 `ai_scoring_v2.py` 或 `hermes_ai_scoring.py` 输出 "未评分总量: 0" 或 "0条已评分"。

### 首先要回答的问题：真的无积压了吗？

## 诊断步骤

### 步骤1：确认 cleaned_intelligence 的评分状态

```bash
cd ~/.hermes
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
c = conn.cursor()

# 真正未评分（关键：ai_scored_at IS NULL，不是 ai_score_total=0）
c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_scored_at IS NULL')
null_scored = c.fetchone()[0]

# ai_score_total=0 但有评分时间（评了0分，非未评分）
c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0 AND ai_scored_at IS NOT NULL')
zero_rated = c.fetchone()[0]

# 总行数
c.execute('SELECT COUNT(*) FROM cleaned_intelligence')
total = c.fetchone()[0]

print(f'cleaned_intelligence 总数: {total}')
print(f'真正未评分 (ai_scored_at IS NULL): {null_scored}')
print(f'评了0分 (ai_score_total=0但有评分时间): {zero_rated}')
print(f'已评分: {total - null_scored}')
conn.close()
"
```

**判定原则：** `ai_score_total=0` 不等于是"评了0分"。SQLite默认值就是0。只有 `ai_scored_at IS NULL` 才是真正未评分。详见主skill的故障4。

### 步骤2：检查 data pipeline 是否在正常流动

评分引擎只对 cleaned_intelligence 操作。如果 cleaned_intelligence 都是已评分，但 raw_intelligence 有大量积压，说明数据在**清洗阶段**（raw→cleaned）被卡住了，不是评分的问题：

```bash
cd ~/.hermes
python3 -c "
import sqlite3
conn = sqlite3.connect('intelligence.db')
c = conn.cursor()

# raw_intelligence 中未进入 cleaned 的
c.execute('''
  SELECT COUNT(*) FROM raw_intelligence r 
  LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id 
  WHERE c.id IS NULL
''')
pend = c.fetchone()[0]
print(f'raw_intelligence 待清洗: {pend}')

# 按日期分布
c.execute('''
  SELECT DATE(r.collected_at), COUNT(*) FROM raw_intelligence r 
  LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id 
  WHERE c.id IS NULL
  GROUP BY DATE(r.collected_at)
  ORDER BY DATE(r.collected_at) DESC
  LIMIT 5
''')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}条')

# 最近 cleaned 时间
c.execute('SELECT MAX(cleaned_at) FROM cleaned_intelligence')
print(f'最近一次清洗时间: {c.fetchone()[0]}')
conn.close()
"
```

**判定：** 如果待清洗 > 0 且最近清洗时间久远 → 清洗管道挂了。需要运行 `unified_cleaning_pipeline.py` 或检查其cron。

### 步骤3：检查是否有两条不同的数据库

Hermes 维护了多个 intelligence.db：

| 路径 | 用途 | 当前状态 |
|------|------|---------|
| `~/.hermes/intelligence.db` | **主库** — 完整schema (ai_score_*字段) | 主要关注 |
| `~/.hermes/data/cleaned_intelligence.db` | 旧库 — 旧schema (ai_score单一字段) | 1393条，全部已评分 |
| `~/.hermes/data/intelligence.db` | 旧库 — 同主库 | 29008条，全部已评分 |

最新的收集清洗都走主库 `~/.hermes/intelligence.db`。旧库数据通常已归档或无新增。

### 步骤4：检查任务描述与实际脚本是否匹配

常见的模式不匹配问题：

| 任务描述 | 实际脚本 | 差异 |
|---------|---------|------|
| `pipeline.py --mode score` | pipeline 支持 `all/route/index/generate/stats` | ❌ 无 `--mode score` |
| "处理未评分积压" | 实际评分在清洗管道 `unified_cleaning_pipeline.py` 中自动完成 | 清洗=评分，无需分开执行 |
| `ai_scoring_v2.py` | 规则评分，查询 `ai_score_total=0 OR NULL` | ✅ 正确 |
| `hermes_ai_scoring.py` | DeepSeek API真实评分，查询 `ai_scored_at IS NULL` | ✅ 正确 |

当任务描述说 `--mode score` 但脚本不支持时，运行 `--mode all` 或 `--mode stats` 来获取管道状态。

### 步骤5：最终确认 — 是否有任何数据库有未评分数据？

```bash
cd ~/.hermes
for db in intelligence.db data/intelligence.db data/cleaned_intelligence.db; do
    [ -f "$db" ] || { echo "$db: 不存在"; continue; }
    python3 -c "
import sqlite3
conn = sqlite3.connect('$db')
c = conn.cursor()
tables = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
for tbl in tables:
    try:
        c.execute(f'SELECT COUNT(*) FROM {tbl} WHERE \"ai_score_total\" IS NULL OR \"ai_score_total\" = 0')
        n = c.fetchone()[0]
        print(f'$db.{tbl}: {n}条未评分')
    except:
        try:
            c.execute(f'SELECT COUNT(*) FROM {tbl} WHERE \"ai_score\" IS NULL OR \"ai_score\" = 0')
            n = c.fetchone()[0]
            print(f'$db.{tbl}: {n}条未评分(旧schema)')
        except:
            pass
conn.close()
"
done
```

## 常见结论及下一步

| 诊断结果 | 含义 | 下一步 |
|---------|------|-------|
| cleaned_intelligence 0未评分 | ✅ 评分管道健康，无积压 | 报告[SILENT]或输出状态 |
| cleaned 0未评分 + raw 大量待清洗 | ⚠️ 清洗管道积压 | 运行 `unified_cleaning_pipeline.py` |
| cleaned 大量未评分 + ai_scored_at IS NULL | ❌ 评分引擎故障 | 检查API key、脚本错误、cron健康 |
| ai_score_total=0 + ai_scored_at IS NOT NULL | ✅ 这些是真正"评了0分"的被过滤项 | 通常不需要处理，除非想重新评分 |
| 任务用`--mode score`但脚本不支持 | ⚠️ 描述过时 | 用 `--mode all` 或 `--mode stats` 替代，或改用 `hermes_ai_scoring.py --batch` |
| archive_cleaned 有数十万零分 | ✅ 正常（归档表不参与评分） | 不处理 |

## 本会话示例（2026-05-28）

```
任务: "处理cleaned_intelligence中未评分的积压数据。运行 --mode score"
结果: cleaned_intelligence 29008条，0未评分
      raw_intelligence 15201条待清洗
结论: 评分管道健康，清洗管道有积压
      --mode score 不存在于 pipeline 脚本（只有all/route/index/generate/stats）
输出: 报告无未评分数据 + 附带发现清洗管道积压
```

这个诊断流程用于 cron 任务的"空跑"场景，避免每次返回空结果时重复做同样的事。
