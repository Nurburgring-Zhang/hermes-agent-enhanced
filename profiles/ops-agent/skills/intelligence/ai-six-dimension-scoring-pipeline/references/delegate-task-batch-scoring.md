# Delegate-Task Batch AI Scoring

当需要**真正的AI内容理解评分**（而非规则关键词匹配）处理大量积压数据时使用。

## 适用场景

- cleaned_intelligence 有数百条未评分数据（内容>50字符）
- 需要比规则评分更准确的六维评分
- 数据价值高（技术/行业/开源内容为主）
- 不急于几秒钟内完成（预算约1-3分钟/25条）

## 工作流

### 1. 检查积压量

```bash
cd ~/.hermes
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('intelligence.db')
unscored = conn.execute("""
    SELECT COUNT(*) FROM cleaned_intelligence 
    WHERE (ai_score_total IS NULL OR ai_score_total = 0 OR ai_score_total = -1
           OR ai_score_reasoning IS NULL OR ai_score_reasoning = '' 
           OR ai_score_reasoning LIKE '%规则评分%')
    AND title IS NOT NULL AND title != ''
    AND LENGTH(COALESCE(content,'')) > 50
""").fetchone()[0]
print(f"待评分(内容合格): {unscored}")
conn.close()
PYEOF
```

### 2. 提取待评分数据并分片

```bash
python3 << 'PYEOF'
import sqlite3, json
conn = sqlite3.connect('intelligence.db')
rows = conn.execute("""
    SELECT id, title, COALESCE(content,'') as content, platform, source,
           author, tags, category, published_at, url,
           COALESCE(ai_score_total, 0) as ai_score_total
    FROM cleaned_intelligence
    WHERE (
        ai_score_total IS NULL OR ai_score_total = 0 OR ai_score_total = -1
        OR ai_score_reasoning IS NULL OR ai_score_reasoning = '' 
        OR ai_score_reasoning LIKE '%规则评分%'
    )
    AND title IS NOT NULL AND title != ''
    AND LENGTH(COALESCE(content,'')) > 50
    ORDER BY importance_score DESC, cleaned_at DESC
""").fetchall()
cols = ['id','title','content','platform','source','author','tags','category','published_at','url','ai_score_total']
items = [dict(zip(cols, r)) for r in rows]
conn.close()

batch_size = 25
batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
for idx, batch in enumerate(batches):
    with open(f"/tmp/score_batch_{idx}.json", "w") as f:
        json.dump(batch, f, ensure_ascii=False)
    print(f"Batch {idx}: {len(batch)} items, IDs {batch[0]['id']}-{batch[-1]['id']}")
print(f"\nTotal: {len(batches)} batches")
PYEOF
```

### 3. 用 delegate_task 批量评分

每次并行发送最多 3 个 delegate_task（每批25条）。评分任务的任务描述：

```
读取 /tmp/score_batch_N.json，对每条进行六维评分后写回 SQLite 数据库 
/home/administrator/.hermes/intelligence.db。

六维评分标准(满分100):
- scarcity(稀缺性) 0-30: 独家首发25-30, 深度分析15-24, 转载5-14, 普通0-4
- impact(影响力) 0-30: 行业变革25-30, 公司战略15-24, 产品更新5-14, 一般0-4
- tech_depth(技术深度) 0-20: 具体技术细节15-20, 有分析8-14, 普通信息0-7
- timeliness(时效性) 0-10: 24h内9-10, 48h内7-8, 一周内4-6, 更早0-3
- preference(偏好匹配) 0-10: 核心兴趣9-10, 部分匹配5-8, 不相关0-4
- credibility(可信度) 0-10: 官方一手9-10, 知名媒体7-8, 普通4-6, 不明0-3

格林主人偏好: AI/LLM/大模型, IT/开发/开源(Rust/TS/Python), 消费电子/芯片, 
新能源汽车, 军事/国际, 开发者生态。讨厌低俗新闻和标题党。

每条执行:
UPDATE cleaned_intelligence SET 
  ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
  ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
  ai_score_total=?, importance_score=?, ai_score_reasoning=?, ai_scored_at=?
WHERE id=?

importance_score = total/10.0
ai_score_reasoning = JSON {"scarcity_reason":"..","impact_reason":"..","tech_depth_reason":"..",
"timeliness_reason":"..","preference_reason":"..","credibility_reason":"..","summary":".."}
```

**重要**：每个 delegate_task 的 context 中必须包含完整的维度定义和格林主人偏好，否则子代理会自行发挥。

### 4. 验证结果

```bash
python3 << 'PYEOF'
import sqlite3, json
conn = sqlite3.connect('intelligence.db')
unscored = conn.execute("""
    SELECT COUNT(*) FROM cleaned_intelligence 
    WHERE (ai_score_total IS NULL OR ai_score_total = 0 OR ai_score_total = -1)
    AND LENGTH(COALESCE(content,'')) > 50
""").fetchone()[0]
total = conn.execute('SELECT COUNT(*) FROM cleaned_intelligence').fetchone()[0]
new_scores = conn.execute("""
    SELECT COUNT(*) FROM cleaned_intelligence 
    WHERE ai_scored_at LIKE '2026-05-28%'
""").fetchone()[0]
print(f"总条目: {total}")
print(f"剩余未评分(内容>50c): {unscored}")
print(f"本次评分条数: {new_scores}")
conn.close()
PYEOF
```

## 性能基准（2026-05-28实测）

### 并行模式（通过文件分片+多delegate_task）

| 指标 | 值 |
|------|-----|
| 每批大小 | 25条 |
| 每批耗时 | 70-170秒 |
| 并行度 | 3个delegate_task |
| 处理200条总耗时 | ~18分钟 |
| 评分方式 | 真正的AI内容理解（非规则匹配） |
| 失败率 | 0%（全部25批无失败） |

### 串行模式（通过real_ai_scorer.py循环处理，cron会话可用）

**适用场景**: 在单次cron会话中逐批处理20条，不预先生成分片文件，而是每轮调用 `real_ai_scorer.py` 读取下一批。

| 指标 | 值 |
|------|-----|
| 每批大小 | 20条 |
| 每批耗时 | 82-145秒 |
| 4批总耗时 | ~6.9分钟 |
| 4批处理量 | 80条 |
| 失败率 | 0%（4批全部成功） |
| 数据源 | `real_ai_scorer.py` → `_ai_scoring_prompt.json` |

**工作流**:
```bash
# 轮次1
cd ~/.hermes && python3 scripts/real_ai_scorer.py
# → _ai_scoring_prompt.json (20条)
# → delegate_task with context=读取prompt + 评分 + 写库

# 轮次2-4（重复，每个子任务用不同时间戳保存）
# 时间戳顺序：T23:06:00, T23:08:00, T23:10:00, T23:13:00
```

**注意**: 每批的 `ai_scored_at` 时间戳必须不同，以便追踪和验证。在数据库验证时按 `WHERE ai_scored_at LIKE '2026-05-28T23%'` 分组统计。

### Cron串行多批 vs 并行分片对比

| 方面 | 串行(real_ai_scorer) | 并行(文件分片) |
|------|---------------------|---------------|
| 数据分片 | 自动生成，无需手动 | 手动SQL导出分片 |
| 适合场景 | cron单次会话5-20批 | 大量积压快速清 |
| 每批token消耗 | ~130-220K input | ~100-150K input |
| 断言 | 每批重新连接数据库 | 各子任务独立写库 |
| 陷阱 | 子任务context必须包含完整六维标准 | 分片文件要放/tmp不干扰 |

## 与规则评分对比

| 方面 | 规则评分 (ai_scoring_v2.py) | 委托评分 (delegate_task) |
|------|--------------------------|------------------------|
| 速度 | 200条/0.3秒 | 25条/70-170秒 |
| 准确性 | 关键词匹配，中等 | AI内容理解，高 |
| 成本 | 无 | consumes model tokens |
| 适用 | 大量积压快速清 | 高价值数据精评 |
| 工具依赖 | 无 | delegate_task可用 |

## 陷阱

- **数据分片文件放 /tmp/**: 确保 cron 环境能写入 /tmp，不要放 ~/.hermes 目录下避免干扰
- **delegate_task toolsets**: 必须包含 `["terminal","file"]`，子代理需要读JSON文件+连SQLite
- **子代理context**: 维度定义必须完整写入任务 context，不要在 goal 里写评分标准（子代理不读goal的详细内容）
- **新数据进入**: 评分过程中采集器可能持续写入新数据，最后一轮要检查并处理新进的几条
