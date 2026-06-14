---
name: weixin-gateway-failure-playbook
description: "Weixin Gateway 推送失败诊断与修复手册 — iLink sendmessage error: ret=-2 和 Timeout context manager 错误的系统性排查方案"
category: operations
tags: [operations, weixin, gateway, push, troubleshooting]
triggers:
  - "Weixin send failed"
  - "iLink sendmessage error"
  - "Timeout context manager should be used inside a task"
  - "推送失败"
  - "wechat gateway error"
version: "1.0"
created: "2026-05-08"
---

# Weixin Gateway 推送失败诊断与修复手册

## 问题概述

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Hermes Gateway 的 Weixin 推送通道出现持续性失败。有两种主要错误模式：

### 错误模式1: iLink sendmessage error: ret=-2
**症状**: `[Weixin] send failed to=o9cq80-G: iLink sendmessage error: ret=-2 errcode=None errmsg=unknown error`
**原因**: Weixin iLink 协议级别错误，通常表示：
- 微信官方平台链路抖动/限流
- 推送内容触发了内容安全审查
- 微信连接池超时或断开
- 消息体过大或格式异常

### 错误模式2: Timeout context manager
**症状**: `[Weixin] send failed to=o9cq80-G: Timeout context manager should be used inside a task`
**原因**: 异步上下文管理问题 — 尝试在事件循环之外使用异步超时上下文管理器。

### 错误模式3: poll error — DNS解析失败
**症状**: `[Weixin] poll error (2/3): Cannot connect to host ilinkai.weixin.qq.com:443 ssl:default [Temporary failure in name resolution]`
**原因**: 临时性 DNS 解析失败

## 快速诊断

```bash
# 1. 检查今日Weixin错误总数
grep -c "Weixin.*send failed" ~/.hermes/logs/errors.log

# 2. 检查Weixin服务器可达性
python3 -c "
import urllib.request, ssl
try:
    ctx = ssl.create_default_context()
    req = urllib.request.Request('https://ilinkai.weixin.qq.com/')
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    print(f'Weixin server reachable: HTTP {resp.status}')
except Exception as e:
    print(f'Weixin server unreachable: {e}')
"

# 3. 检查gateway代码中的weixin适配器
find ~/.hermes -path \"*gateway*\" -name \"*.py\" 2>/dev/null | head -5
```

## 修复方案

### 方案A: 纯文本降级 (已有支持)

系统已尝试 `plain-text fallback`:
```
[Weixin] send failed → trying plain-text fallback → Fallback send also failed
```
这表明问题不在消息格式，而是链路本身。修改 `plain_text_fallback` 为使用 **PushPlus** 作为二级降级通道。

PushPlus 降级方法（从已有脚本获取token）：
```python
import urllib.request, json, os

def pushplus_fallback(title, content):
    # 从 hermes_push_manager.py 提取 PUSHPLUS_TOKEN
    token = None
    with open(os.path.expanduser('~/.hermes/scripts/hermes_push_manager.py')) as f:
        for line in f:
            if 'PUSHPLUS_TOKEN' in line and '=' in line:
                token = line.split('=')[1].strip().strip('"').strip("'")
                break
    if not token:
        print("Cannot find PUSHPLUS_TOKEN")
        return
    
    data = {
        "token": token,
        "title": title,
        "content": content,
        "channel": "wechat",
        "template": "markdown"
    }
    req = urllib.request.Request(
        "https://www.pushplus.plus/send",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())
```

### 方案B: 异步上下文修复 (针对模式2)

如果 `Timeout context manager` 错误持续出现：
```python
# 在 weixin.py 中查找问题模式
# 将:
#   async with asyncio.timeout(30): ...
# 改为:
#   try:
#       await asyncio.wait_for(coro, timeout=30)
#   except asyncio.TimeoutError:
#       ...
```

### 方案C: 连接池重置

```bash
# 找到gateway进程PID
ps aux | grep "[g]ateway" | awk '{print $2}'
# 然后重启: kill -HUP <PID> 或重启服务
```

## 监控与告警

```bash
# 监控Weixin失败率趋势
python3 -c "
count = 0
with open('/home/administrator/.hermes/logs/errors.log') as f:
    for line in f:
        if 'Weixin.*send failed' in line:
            count += 1
print(f'Weixin失败累计: {count}')
if count > 2000:
    print('CRITICAL: 累计失败超2000次')
elif count > 1000:
    print('WARNING: 累计失败超1000次')
elif count > 500:
    print('ALERT: 累计失败超500次')
"
```

## 当前状态 (2026-05-08)
- 错误占比: ~9.6% of total errors in errors.log
- 趋势: 主要集中在 10:00-10:07 时间段密集爆发，之后趋于平稳
- 建议: 低优先级 (不影响核心采集/评分/推送)，可在下次维护窗口修复
- 深层定位: `find ~/.hermes -path '*/gateway/*' -name 'weixin*' -o -path '*/platforms/*' -name 'weixin*' 2>/dev/null`

## 陷阱与注意事项
1. 不要尝试无限制重试 — 3次重试后依然失败，重试10次不会有帮助
2. iLink ret=-2 是Weixin内部协议错误码，不是网络错误 — 不要误判为DNS/网络问题
3. PushPlus 降级需要独立 token — 从已有脚本提取
4. 重启gateway会中断所有正在进行的推送 — 在低峰期操作
5. 错误集中在10:00-10:07时段的爆发模式，提示可能有按小时的Weixin限流策略

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
