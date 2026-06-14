# 评分回退链 & 数据库路径注意点

## DB路径二义性：`data/cleaned_intelligence.db` 是软链

`~/.hermes/data/cleaned_intelligence.db` → **指向** `~/.hermes/intelligence.db`

所以以下两个路径操作的是**同一个数据库**：
- `~/.hermes/intelligence.db`（主DB）
- `~/.hermes/data/cleaned_intelligence.db`（软链）

不要在 `data/cleaned_intelligence.db` 上写独立评分逻辑——它是 `intelligence.db` 的别名，
所有 `cleaned_intelligence` 表的操作都读写同一份数据。

验证方法：
```bash
readlink -f ~/.hermes/data/cleaned_intelligence.db
# → /home/administrator/.hermes/intelligence.db
```

## 评分回退链（API不可用时的兜底顺序）

cron 环境通常无可用 API key，按此顺序自动回退：

### 第1层：真正AI评分（有API key时）
```bash
cd ~/.hermes && python3 scripts/ai_scoring_daemon.py --backfill 200
# → 有API key则5条8秒，无API key则TASK_NO_API
```

### 第2层：`ai_sixdim_scorer.py`（本地内容感知/无API依赖）
```bash
cd ~/.hermes && python3 scripts/ai_sixdim_scorer.py
```
**⚠️ 条件陷阱**：此脚本只匹配 `ai_score_reasoning LIKE '%规则评分%'` 的条目。
新条目（`ai_score_reasoning` 为其他值或 NULL）不会被此脚本捕获。

### 第3层：手动规则评分（兜底）
当1和2都返回0条时，检查 `ai_score_total IS NULL OR ai_score_total = 0`：
```python
import sqlite3, json
conn = sqlite3.connect('/home/administrator/.hermes/intelligence.db')
cur = conn.cursor()
cur.execute("""
    SELECT id, title, content, source, platform, published_at
    FROM cleaned_intelligence
    WHERE (ai_score_total IS NULL OR ai_score_total = 0)
      AND (ai_scored_at IS NULL)
""")
```

短内容条目（<100字符）的评分方法：使用 `ai_sixdim_scorer.py` 的评分逻辑手动赋分，
或用 `ai_scoring_v2.py` 的规则引擎暴力评分（不需要API key，0.1秒/批）。

## 常见"已评分但计数异常"场景

| 现象 | 原因 | 处理 |
|------|------|------|
| 显示3条ai_score_total=0但实际全是短内容 | 新进入cleaned的短内容未被AI评分捕获 | 手动规则评分 |
| ai_sixdim_scorer.py返回"No entries" | 新条目ai_score_reasoning不是"%规则评分%" | 用ai_scoring_v2.py或手动评分 |
| ai_scoring_daemon返回TASK_NO_API | DEEPSEEK_API_KEY未配置或无网络 | 走第2层或第3层 |
| data/cleaned_intelligence.db有1393条但intelligence.db有29275条 | 软链指向的时间快照不同——用`readlink -f`确认 | 始终用intelligence.db路径 |
