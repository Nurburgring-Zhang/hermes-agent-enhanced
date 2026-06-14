# 真实 Harness Audit 方法论

## 诊断方法

### 并行扫描模式
使用 `delegate_task` 一次性派遣子 Agent 扫描所有模块，返回结构化报告。不要逐个顺序查。

```python
delegate_task(
    goal="Scan ALL of these systems and report real execution status...",
    toolsets=["terminal", "file"]
)
```

### 审计的 12 个检查点

| # | 检查点 | 验证方式 |
|---|--------|---------|
| 1 | Gateway | `journalctl`, `systemctl status`, `ps aux` 三路验证 |
| 2 | Cron | `crontab -l` + `hermes cron list` 双重确认 |
| 3 | Systemd | `systemctl --user list-units --type=service` |
| 4 | Key Scripts | 检查 logs/ 目录下各脚本的最近时间戳 |
| 5 | Memory | `hermes memory status`, 检查 wake_injector 进程 |
| 6 | Gear | 8个G组件的日志时间戳（应都在最近15分钟内） |
| 7 | WebUI | 检查 webui 进程 + HTTP 响应 |
| 8 | Collection | `intelligence.db` 文件大小 + 最后修改时间 |
| 9 | Push | `hermes cron list` 推送条目 + 上次执行时间 |
| 10 | Video | 检查 video_cron_jobs 进程 + comfy 是否安装 |
| 11 | Self-Evolution | self_evolution.log 最近时间戳 |
| 12 | Memory/Process | `ps aux --sort=-%mem` 看顶消耗进程 |

### 状态标记
- ✅ **运行中** — 进程活着 + 日志在最近周期内
- ❌ **FAILED** — 无进程 + 无日志 + systemd 在重启循环
- ⚠️ **部分** — 有手动进程但 systemd 挂了，或有日志但无进程

## 真实审计输出示例
见 `references/system-health-scan-example.md`
