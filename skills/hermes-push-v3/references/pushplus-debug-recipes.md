# PushPlus 推送故障排查食谱

## 问题："服务端验证错误"

### 排查步骤

1. **测试PushPlus接口是否正常**
```python
import urllib.request, json
data = json.dumps({
    'token': '<token>',
    'title': '测试',
    'content': '<div>test</div>',
    'template': 'html',
}).encode()
req = urllib.request.Request('https://www.pushplus.plus/send', data=data,
    headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
print(resp)  # 应该返回 {'code': 200, 'msg': '执行成功', 'data': '...'}
```

2. **检查返回码含义**
- `999 服务端验证错误` → 看data字段给的具体原因
  - `发送内容过大，不能超过2万字` → HTML太长，减少推送条数或降级

3. **检查HTML中是否有未转义字符**
```python
# 检查URL中的&
for i, ch in enumerate(html):
    if ch == '&' and not html[i:i+5] in ('&amp;', '&lt; ', '&gt; '):
        print(f'未转义& at pos {i}')
```
修复: `safe_url = url.replace('&', '&amp;')`

4. **检查推送候选池为空的原因**
- AI评分失败？→ 检查 `ai_score_backfill.py` 日志
- SQL条件太严？→ 检查 `get_candidates_balanced()` 的 `WHERE` 子句
- 数据真的为空？→ 直接查DB: `SELECT COUNT(*) FROM cleaned_intelligence WHERE cleaned_at > datetime('now', '-24 hours')`

## 常见故障链
```
AI评分400 → ai_score_total=0 → SQL ai_score>=15过滤所有新数据 → 候选池空 → PushPlus报验证错误(无有效内容)
                                                            ↓
                                     HTML超2万字(旧50条模式) → PushPlus报999验证错误
```

## 快速恢复命令
```bash
# 1. 测试PushPlus
python3 -c "import urllib.request,json; data=json.dumps({'token':open('~/.hermes/.env').read().split('PUSHPLUS_TOKEN=')[1].split()[0],'title':'test','content':'test','template':'html'}).encode(); req=urllib.request.Request('https://www.pushplus.plus/send',data=data,headers={'Content-Type':'application/json'}); print(json.loads(urllib.request.urlopen(req,timeout=15).read()))"

# 2. 测试推送
cd ~/.hermes && python3 scripts/hermes_v12_push.py --push

# 3. 检查候选池
cd ~/.hermes && python3 -c "
import sqlite3; c=sqlite3.connect('intelligence.db').cursor()
c.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE cleaned_at > datetime(\"now\", \"-24 hours\") AND ai_score_total > 0')
print(f'24h内有评分数据: {c.fetchone()[0]}条')
"

# 4. 回填AI评分
cd ~/.hermes/scripts && python3 ai_score_backfill.py --high-value
```
