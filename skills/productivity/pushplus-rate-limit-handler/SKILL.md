---
name: pushplus-rate-limit-handler
description: PushPlus微信推送频率限制诊断与处理
triggers:
  - PushPlus 推送失败
  - 服务端验证错误
  - 推送频率过快
---

# PushPlus 微信推送 - 频率限制处理

## 触发条件
使用 `hermes_push_manager.py --all` 或 `--personal` / `--daily` 推送失败，返回 `"code": 999, "msg": "服务端验证错误"` 或 `"推送频率过快"`。

## 根因
PushPlus 对同一 token 有发送频率限制：
- 同一 token 短时间内多次调用会被限流（999错误）
- 紧急推送（`--urgent`）和日常推送（`--daily`/`--personal`）共享同一 token 的频率计数器
- 间隔 2-3 小时内的多次推送会被拦截

## 症状识别
```
❌ 个人偏好推送失败: 服务端验证错误
❌ 日报推送失败: 服务端验证错误
✅ 紧急情报推送成功
```
限流时紧急推送可能成功（队列独立），而个人/日报被拦截。

## 诊断命令
```bash
cd /home/administrator/.hermes/scripts && python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/intelligence.db')
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('SELECT push_time, push_status, push_response, title FROM push_records ORDER BY id DESC LIMIT 10')
for row in c.fetchall():
    print(row)
"
```

## 解决方案

### 1. 等待冷却（自动）
PushPlus 频率限制通常在 30 分钟-1 小时后自动解除。cron 任务会在下次调度时自动重试。

### 2. 分离推送时间（推荐）
修改 cron 调度，确保 `--urgent`、`--daily`、`--personal` 错开：
- `--urgent`: 每4小时（与采集同步）
- `--daily`: 每天1次（08:00），不要与其他推送重叠
- `--personal`: 每天1次（12:00 或 18:00），与日报错开

### 3. 直接 API 调用验证
```python
import urllib.request, json

# ⚠️ 关键：必须使用 HTTP 而不是 HTTPS！
PUSHPLUS_URL = "http://www.pushplus.plus/send"
TOKEN = "your_token_here"

data = {
    "token": TOKEN,
    "title": "标题",
    "content": "内容",
    "channel": "wechat",
    "template": "markdown"
}
req = urllib.request.Request(
    PUSHPLUS_URL,
    data=json.dumps(data).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=15) as resp:
    result = json.loads(resp.read().decode())
    print(result)
```

**关键发现 (2026-04-20)**:
- HTTPS 端点 `https://www.pushplus.plus/send` → 连接错误
- HTTP 端点 `http://www.pushplus.plus/send` → 正常工作
- PushPlus 频率限制后，等待 5+ 秒再重试可能成功

## 关键代码位置
- 推送脚本: `/home/administrator/.hermes/scripts/hermes_push_manager.py`
- 数据库: `~/.hermes/intelligence.db` → `push_records` 表
- PushPlus token: 第25行 `PUSHPLUS_TOKEN`

## 验证步骤
推送后检查 `push_records` 表：
- `push_status = 'success'` 且 `push_response` 含 `200` = 成功
- `push_status = 'sent'` = 已发送（异步队列）
- `push_response` 含 `999` = 频率限制

## 预防
- 同一 cron 任务不要同时执行多个 `--all`（包含 urgent+daily+personal）
- 紧急和非紧急推送使用不同的 PushPlus token（需要多账号）
- 在脚本中加入重试冷却逻辑：失败后等待 N 秒再重试

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
