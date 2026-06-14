---
name: hermes-pushplus-troubleshooting
description: Hermes PushPlus 推送故障排查与直接 API 调用方案
trigger: PushPlus server validation error during hermes_push_manager.py or hermes_v12_push.py execution
tags: [operations, pushplus, troubleshooting, hermes-intelligence, v12-push]
---

# Hermes PushPlus 推送故障排查与直接调用

## 问题描述

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

## 推送质量优化策略（2026-05-31实施）

v12推送系统实现了三层优化策略，确保持续推送高质量内容：

### 1. 时效性硬过滤（候选排名后、去重前）

```python
# push_v12() Step 4.5 — 发布时间>14天且AI<80丢弃
# 无published_at的数据只保留AI评分>=50或24小时内刚采集的
if not pub_str:
    if ai_score < 50 and collected > 24h:
        discard()
elif days_old > 14 and ai_score < 80:
    discard()
```

### 2. 时间衰减评分

评分公式乘以时间衰减因子：
```python
time_decay = 1.0
if days_old > 14:
    time_decay = max(0.1, 1.0 - (days_old - 7) * 0.05)
elif not pub_str:
    time_decay = 0.7  # 无时间降权30%
total = (ai_score * 0.4 + ...) * time_decay
```

### 3. 72小时去重窗口

已推送排除从6小时扩展到72小时：
```python
cutoff = (datetime.now() - timedelta(hours=72)).isoformat()
```

---

## ⚠️ 已知问题
1. **v12推送（当前主推送）**: `guardian.py push` 调用 `hermes_v12_push.py --push` → 返回 `❌ 推送失败: 服务端验证错误`
2. **旧推送（hermes_push_manager.py）**: `❌ [GitHub-Go] aquascurity / trivy - 服务端验证错误`

**典型症状**：
```
[12:00:04] 📤 推送微信(HTML模板)...
[12:00:04] ❌ 推送失败: 服务端验证错误
```
cron_push.log 中连续多轮出现此错误。

## 🔴 关键诊断步骤（按顺序执行）

### 1. 确定故障时间范围
```bash
cd ~/.hermes
grep -E "推送成功|推送失败|服务端验证|返回码 1" logs/cron_push.log | tail -30
```
看最近几轮：✅ 成功还是 ❌ 失败？连续几轮失败？

### 2. 验证推送是否实际写入数据库
```bash
cd ~/.hermes && python3 -c "
import sqlite3; db=sqlite3.connect('intelligence.db'); c=db.cursor()
c.execute('SELECT COUNT(*) FROM push_records WHERE date(created_at)=date(\"now\",\"localtime\")')
print(f'今日推送总数: {c.fetchone()[0]}条')
c.execute('SELECT DISTINCT date(created_at) as d FROM push_records ORDER BY d DESC LIMIT 7')
print('最近7天有推送的日期:', [r[0] for r in c.fetchall()])
db.close()
"
```

### 3. 检查数据库推送记录与实际日志是否一致
```bash
cd ~/.hermes && python3 -c "
import sqlite3; db=sqlite3.connect('intelligence.db'); c=db.cursor()
c.execute('SELECT push_time, COUNT(*) FROM push_records GROUP BY push_time ORDER BY push_time DESC LIMIT 10')
print('最近10轮推送(数据库):')
for r in c.fetchall(): print(f'  {r[0]}: {r[1]}条')
db.close()
"
```

### 4. 直接测试 PushPlus API 连通性
```python
import urllib.request, json, os, yaml
# 从 config.yaml 读取 token
with open('/home/administrator/.hermes/config.yaml') as f:
    config = yaml.safe_load(f)
TOKEN = config.get('pushplus', {}).get('token', '')

data = {
    "token": TOKEN,
    "title": "🔧 PushPlus 连通性测试",
    "content": "Test from Hermes at " + __import__('datetime').datetime.now().strftime("%H:%M:%S"),
    "channel": "wechat",
    "template": "html"
}
req = urllib.request.Request(
    "https://www.pushplus.plus/send",
    data=json.dumps(data).encode(),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=15) as resp:
    result = json.loads(resp.read().decode())
    print(f"PushPlus respond: {result}")
```

---

## 场景1: v12推送连续失败（当前主推送系统）

### 调用链路
```
cron (0 8,12,18,0) → guardian.py push → subprocess hermes_v12_push.py --push → PushPlus API
                         ↑
omni_loop.py (每30min) ──┤ (也调用 guardia.py push, 频率过高导致重复推送排除)
```

### 已知故障案例: 2026-05-25 18:00 ~ 2026-05-27 12:00 (42小时中断)

**根因**: PushPlus 服务端验证波动（非token过期，因为之后未换token恢复正常）

**症状链条**:
1. `hermes_v12_push.py` 正确生成候选（300条）→ 偏好评分 → 垃圾过滤 → 去重
2. 最终生成18-46条高质量推送候选项
3. 调用 PushPlus API 时返回 `❌ 推送失败: 服务端验证错误`
4. `guardian.py` 收到返回码 1，输出 `⚠️ v12推送返回码 1`
5. **在同一 cron_push.log 中**：v12失败但 v9 推送(hermes_push_manager)可能成功 → 数据库有推送记录但微信未收到
6. 用户完全收不到推送消息

**修复**: 无需操作，PushPlus 服务端自行恢复。但42小时空白期意味着：
- 数据库推送记录: 5/26 = 0条 (完全空窗)
- 恢复后: v12正常运行，候选300条→最终18条成功推送

**预防措施**:
1. 监控 `cron_push.log` 中连续3轮以上 `服务端验证错误`
2. 自动切换为 markdown 模板重试（HTML模板可能触发某些防火墙规则）
3. 或自动换备用token（如果有）

### 诊断命令
```bash
# 查看推送日志中的失败模式
cd ~/.hermes && grep -c "❌ 推送失败" logs/cron_push.log
grep -c "✅ 推送成功" logs/cron_push.log
grep "推送失败" logs/cron_push.log | tail -10
```

### v12 运行正常时预期输出
```
候选池: 300条, 12个平台
偏好过滤(0分): 300 → 300条
垃圾过滤: 300 → 300条
已推送排除: 300 → 179条  (已推送的标题排除)
去重: 179 → 179条
中文优先: 163中 + 16英 → 25条
多样性后: 6个平台, 18条
✅ 最终: 18条, 6个平台
```

### v12 推送逻辑关键点
| 阶段 | 说明 | 常见问题 |
|------|------|----------|
| `push_v12()` | 加载6h内已推送记录(按title) | 如果所有候选标题都在这6h内推过 → 0条 |
| `get_candidates_balanced()` | 取最近72h有标签的300条 | tags为空或General时被降级 |
| `score_quality()` | AI评分×0.4 + 方向标签×0.25 + 关键词×0.25 + 偏好分×0.1 | 未评分的候选方向分只有30%权重 |
| `enforce_diversity()` | 每平台上限25% | 平台很少时多样性后条数也少 |
| `record_pushed()` | 写入 push_records, 24h title去重 | 同一标题重复推会被跳过 |

---

## 场景2: hermes_push_manager.py 失败（旧系统，v12之前的推送）

运行 `hermes_push_manager.py --all` 时，部分推送失败并显示"服务端验证错误"，但直接调用 PushPlus API 实际可以成功。

**症状**：
```
❌ [GitHub-Go] aquascurity / trivy - 服务端验证错误
```

## 根本原因（通用）

PushPlus 服务端存在间歇性验证波动：
- 请求频率限制（免费版有每日限额）
- token 缓存/服务端负载
- HTML模板在某些IP段被拦截
- `hermes_push_manager.py` 的错误处理会将任何非 200 响应都标记为"服务端验证错误"

## 应急方案：直接 API 调用

```python
import sqlite3, urllib.request, json
from datetime import datetime, timedelta

DB_PATH = "/home/administrator/.hermes/intelligence.db"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
# 从 config.yaml 获取 PUSHPLUS_TOKEN
import yaml
with open('/home/administrator/.hermes/config.yaml') as f:
    config = yaml.safe_load(f)
PUSHPLUS_TOKEN = config.get('pushplus', {}).get('token', '')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
since = (datetime.now() - timedelta(hours=48)).isoformat()

c.execute("""
    SELECT title, url, source, value_level, importance_score, content, 
           is_ai_related, personal_match_score, value_reasons, language
    FROM cleaned_intelligence 
    WHERE cleaned_at >= ? AND value_level >= 4
    ORDER BY value_level DESC, importance_score DESC
    LIMIT 10
""", (since,))
items = [dict(r) for r in c.fetchall()]
conn.close()

def build_link(title, url):
    return f"[{title}]({url})" if url and url.startswith("http") else title

def value_tag(item):
    tags = []
    if item.get('is_ai_related'): tags.append("🤖AI")
    if item.get('personal_match_score', 0) >= 15: tags.append("⭐偏好")
    if item.get('value_level', 0) >= 4: tags.append("🔥高价值")
    if '开源' in item.get('value_reasons', ''): tags.append("📦开源")
    return " | ".join(tags) if tags else f"等级{item.get('value_level', 1)}"

gh_items = [x for x in items if 'GitHub' in x.get('source', '')]
if gh_items:
    lines = ["# 🚨 GitHub 热门项目速递\n"]
    for i, item in enumerate(gh_items[:5], 1):
        lines.append(f"**{i}. {build_link(item['title'], item.get('url', ''))}**")
        lines.append(f"   📍 {item.get('source', '')} | {value_tag(item)}")
        lines.append("")
    
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": f"🔥 GitHub Trending ({len(gh_items)}条)",
        "content": '\n'.join(lines),
        "channel": "wechat",
        "template": "markdown"
    }
    req = urllib.request.Request(
        PUSHPLUS_URL, 
        data=json.dumps(data).encode(), 
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
        print(f"Push result: {result}")
```

## 验证推送可用性

```python
import urllib.request, json, yaml
PUSHPLUS_URL = "https://www.pushplus.plus/send"
with open('/home/administrator/.hermes/config.yaml') as f:
    config = yaml.safe_load(f)
PUSHPLUS_TOKEN = config.get('pushplus', {}).get('token', '')
data = {
    "token": PUSHPLUS_TOKEN,
    "title": "🔥 测试推送",
    "content": "<b>Test</b> from Hermes v12",
    "channel": "wechat",
    "template": "html"
}
req = urllib.request.Request(PUSHPLUS_URL, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=15) as resp:
    print(json.loads(resp.read().decode()))
```

---

## ⚠️ PushPlus API字段规范（实测有效）

**常见错误**: `"msg"` 字段 → 服务端返回 `code:999, "发送内容不能为空"`
**正确字段**: `"content"` 字段 → `code:200, "执行成功"`

**最小可用payload**:
```python
{
    "token": "YOUR_TOKEN_HERE",
    "title": "标题文字",
    "content": "内容",
    "channel": "wechat",
    "template": "html"  # html模板可点击链接, markdown纯文本
}
```

**三个必须字段**: `token`, `title`, `content` + `channel:wechat`
**协议**: `https://www.pushplus.plus/send`

**HTML vs Markdown模板的选择**:
- HTML: 微信中可点击超链接，但更容易触发防火墙/验证错误
- Markdown: 更稳定，但无超链接纯文本
- **连续失败时自动降级**: HTML → 纯文本/减少条数(25→15→8) → Markdown

---

## 巡检命令（快速自检）

```bash
cd /home/administrator/.hermes

# 1. 查看推送日志最近状态
tail -20 logs/cron_push.log

# 2. 查看今日推送统计
python3 -c "
import sqlite3; db=sqlite3.connect('intelligence.db'); c=db.cursor()
c.execute(\"SELECT COUNT(*) FROM push_records WHERE date(created_at)=date('now','localtime')\")
print(f'今日推送: {c.fetchone()[0]}条')
c.execute('SELECT source, COUNT(*) FROM push_records WHERE date(created_at)=date(\"now\",\"localtime\") GROUP BY source ORDER BY COUNT(*) DESC LIMIT 5')
print('来源分布:', c.fetchall())
db.close()
"

# 3. 查看最后推送时间
python3 -c "
import sqlite3; db=sqlite3.connect('intelligence.db'); c=db.cursor()
c.execute('SELECT MAX(created_at) FROM push_records')
print(f'最后推送时间: {c.fetchone()[0]}')
db.close()
"

# 4. 查看采集是否正常（最近活跃时间）
python3 -c "
import sqlite3; db=sqlite3.connect('intelligence.db'); c=db.cursor()
c.execute('SELECT source, MAX(collected_at) FROM raw_intelligence GROUP BY source ORDER BY MAX(collected_at) DESC LIMIT 10')
for r in c.fetchall(): print(f'{r[0]:20s}: {r[1]}')
db.close()
"

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
