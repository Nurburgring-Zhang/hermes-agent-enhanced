# 穿透式验证方法论

## 核心原则

"在跑"不等于"在工作"。每一项能力都要验证三件套：
1. **进程/服务存在** — 确认配置和二进制存在
2. **有近期实际输出** — 日志时间戳在24h内、数据库有时间记录、API返回实际数据
3. **功能可真实执行** — 手动触发一次，验证返回值

## 自检清单模板

对任何声称"已启用"的能力，按此清单检查：

```
□ [进程存在] 确认 PID / systemd status / cron条目文件 / 二进制路径
□ [近期输出] 最近日志时间 < 24h；如有DB检查最新记录时间戳
□ [功能测试] 手动执行一次（执行脚本、curl API、看返回值）
```

## 常见陷阱

| 声称状态 | 实际可能 | 穿透验证方法 |
|---------|---------|-------------|
| "WebUI在运行" | pid文件指向另一个进程 | 确认PID对应的cmdline |
| "cron任务正常" | 脚本不存在或已改名 | 手动执行脚本看exit code |
| "WeChat已连接" | gateway在auto-restart循环 | 看日志中是否有实际inbound/outbound |
| "视频引擎已激活" | 脚本存在但从未被cron调度 | 检查crontab条目+日志文件 |
| "所有scripts在运行" | 只有部分有cron条目 | 逐脚本检查crontab |

## 示例：完整的一次穿透验证流程

```
# Step 1: 查进程
systemctl --user status hermes-gateway.service | grep "Active:"

# Step 2: 查日志
journalctl --user -u hermes-gateway.service --no-pager -n 10 | grep "weixin.*connect\|inbound\|outbound"

# Step 3: 查消息（手动触发验证）
# 从微信发一条消息，看gateway.log是否出现inbound记录
```
