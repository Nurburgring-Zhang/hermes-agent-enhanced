# ai_score_backfill.py 故障根因与分析

## 故障模式

`ai_score_backfill.py`（位于 `~/.hermes/scripts/`）是一个独立评分脚本，与 `hermes_ai_scoring.py` 不同。
通过 cron `*/4h` 运行，每次评6条（3批，每批2条）。

### 典型日志模式（故障中）

```
[16:00:17]   ❌ API重试3次均失败: HTTP Error 400: Bad Request
[16:00:17]   ⚠️ AI返回格式异常: []
[16:00:18] ✅ 评分回填完成: 共0条真正AI评分
```

### 根因

脚本第87行硬编码了OpenRouter格式的model名，但95-98行会路由到不同的API端点：

```python
# 第86-91行 — 在路由前构造
payload = json.dumps({
    "model": "deepseek/deepseek-chat",  # ❌ OpenRouter格式, 带斜杠
    ...
}).encode()

# 第95-98行 — 路由逻辑
deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
if deepseek_key:
    api_url = "https://api.deepseek.com/v1/chat/completions"  # ✅ DeepSeek
    effective_key = deepseek_key
    effective_model = "deepseek-chat"  # ✅ 正确model名
else:
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    effective_key = api_key
    effective_model = "openrouter/auto"
```

payload在路由前就已构建（第86行），使用了 `"deepseek/deepseek-chat"`。当路由走DeepSeek时，payload中的model名没有更新。DeepSeek API不接受 `deepseek/deepseek-chat`，返回400。

而第120行虽然从API响应解析了结果，但没有用上 `effective_model`——payload里的model已被固定。

### 修复方案

将payload构建移到路由之后，或修改第87行的model名：

```python
# 方案A：payload在路由后构建
if deepseek_key:
    api_url = "https://api.deepseek.com/v1/chat/completions"
    effective_key = deepseek_key
    model_name = "deepseek-chat"
else:
    api_url = "https://openrouter.ai/api/v1/chat/completions"
    effective_key = api_key
    model_name = "openrouter/auto"

payload = json.dumps({
    "model": model_name,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3,
    "max_tokens": 1000
}).encode()
```

### 快速手动回填命令

当需要手动回填评分绕过cron时：

```python
cd ~/.hermes && python3 -c "
import sqlite3, json, os, re, urllib.request
from datetime import datetime
from pathlib import Path

# 加载.env
HERMES = Path.home() / '.hermes'
env_path = HERMES / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip()
            if v and v != '***' and k not in os.environ:
                os.environ[k] = v

ds_key = os.environ.get('DEEPSEEK_API_KEY', '')

# 取待评分数据
conn = sqlite3.connect(str(HERMES / 'intelligence.db'))
rows = conn.execute('''SELECT id, title, content FROM cleaned_intelligence 
WHERE ai_scored_at IS NULL AND tags IS NOT NULL AND tags != '' AND tags != 'General'
AND LENGTH(COALESCE(content,'')) >= 30 AND title IS NOT NULL AND title != ''
ORDER BY id DESC LIMIT 2''').fetchall()

items_desc = ''
for r in rows:
    title = (r[1] or '')[:60]
    content = (r[2] or '')[:200]
    items_desc += f'id={r[0]} title={title}|content={content}\n'

prompt = f'严格JSON数组评分(不要markdown)。对以下情报六维评分:\n\n{items_desc}\n每条输出: {{\"id\":N,\"scarcity\":0-30,\"impact\":0-30,\"tech_depth\":0-20,\"timeliness\":0-10,\"preference\":0-10,\"credibility\":0-10,\"summary\":\"一句话\"}}\n只输出JSON数组。'

payload = json.dumps({
    'model': 'deepseek-chat',  # 注意：不带斜杠！
    'messages': [{'role': 'user', 'content': prompt}],
    'temperature': 0.3, 'max_tokens': 1000
}).encode()

req = urllib.request.Request(
    'https://api.deepseek.com/v1/chat/completions',
    data=payload,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {ds_key}'}
)
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
scores = json.loads(re.sub(r'^```(?:json)?s*', '', result['choices'][0]['message']['content'].strip()).rstrip('`'))

# 保存
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for s in scores:
    total = sum([s.get('scarcity',0), s.get('impact',0), s.get('tech_depth',0),
                 s.get('timeliness',0), s.get('preference',0), s.get('credibility',0)])
    total = min(total, 100)
    conn.execute('''UPDATE cleaned_intelligence SET
        ai_score_scarcity=?, ai_score_impact=?, ai_score_tech_depth=?,
        ai_score_timeliness=?, ai_score_preference=?, ai_score_credibility=?,
        ai_score_total=?, importance_score=?, ai_scored_at=?
    WHERE id=?''', (s['scarcity'], s['impact'], s['tech_depth'], s['timeliness'],
                    s['preference'], s['credibility'], total, round(total/10,2), now, s['id']))

conn.commit(); conn.close()
print(f'✅ 保存{len(scores)}条')
"
```

## 判断AI评分是否中断

```python
import sqlite3
conn = sqlite3.connect('/home/administrator/.hermes/intelligence.db')
c = conn.cursor()
c.execute('SELECT MAX(ai_scored_at) FROM cleaned_intelligence')
print(f'最后评分时间: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_scored_at IS NULL AND LENGTH(COALESCE(content,\"\")) >= 30')
print(f'待评分: {c.fetchone()[0]}条')
conn.close()
```

如果最后评分时间是2天前，且待评分>0条，说明评分中断了。
