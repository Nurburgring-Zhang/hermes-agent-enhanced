---
name: omni-health-monitor
title: OMNI Loop Health Monitor & Auto-Restarter
description: "Monitor the OMNI omnibus loop process health, detect stalls (>30min), auto-restart, and track recovery history. Prevents OMNI from silently dying for hours."
domain: autonomous-systems
priority: high
triggers:
  - "check omni health"
  - "restart omni loop"
  - "omni monitor"
  - "omni静态监控"
  - "全能循环健康检查"
---

# OMNI Loop Health Monitor & Auto-Restarter

Monitor the OMNI omnibus loop (`omni_loop.py`) and restart it when stalled or dead.

## Background

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


OMNI loop runs via cron every 30 minutes (job: `全能循环-每30分钟`). This has been the stable architecture since at least 2026-05-06 — it is **not** a daemon process. The guardian.py `heal` mode (line 260, `check_omni_loop_heartbeat()`) provides secondary health monitoring via heartbeat file checks. The eternal loop (`eternal_loop.py`, running as standalone daemon) is a separate system for continuous long-running tasks.

**Architecture Note (2026-05-08)**: OMNI is intentionally cron-scheduled, not continuous. This reduces resource consumption (~600s window per run vs always-running). The guardian.py heal+reviver_guardian.sh duo provides redundancy — heal checks every 15 min, reviver_guardian.sh every 5 min.

## Step 1: Check OMNI Process Status

```bash
# Check if omni_loop.py is running
ps aux | grep omni_loop | grep -v grep

# Check last log activity
tail -5 /home/administrator/.hermes/logs/omni_loop.log

# Get last modification time
stat -c '%Y %y' /home/administrator/.hermes/logs/omni_loop.log
```

### Health Assessment Logic

| Condition | Status | Action |
|-----------|--------|--------|
| Process running AND log modified <30min ago | ✅ HEALTHY | No action needed |
| Process NOT running, log <30min ago | ⚠️ RECENT | Restart, likely just crashed |
| Process NOT running, log >30min ago | 🔴 STALLED | Restart + alert |
| Process running BUT log >30min ago | 🟡 HUNG | Kill + restart |
| No log file exists | 🆕 FRESH | First run, start OMNI |

## Step 2: Restart OMNI Loop

```bash
# Kill any stale omni process
pkill -f omni_loop.py 2>/dev/null; sleep 1

# Start fresh with timeout guard (30 min max)
cd /home/administrator/.hermes && timeout 1800 python3 scripts/omni_loop.py >> /home/administrator/.hermes/logs/omni_loop.log 2>&1 &
```

Or via cron direct invocation:
```bash
cd /home/administrator/.hermes && timeout 600 python3 scripts/omni_loop.py
```

## Step 3: Verify Restart

```bash
# Wait 10s, then verify
sleep 10
ps aux | grep omni_loop | grep -v grep
tail -3 /home/administrator/.hermes/logs/omni_loop.log
```

Expected output after restart:
```
[HH:MM:SS] 🌀 ==================================================
[HH:MM:SS] 🌀 📡 步骤1: 全平台采集
[HH:MM:SS] 🌀 ✅ 采集完成: ...
```

## Step 4: Track Recovery History

Record each recovery event in the OMNI health log:
```bash
echo "[$(date '+%Y-%m-%d %H:%M:%S')] OMNI_RESTART: reason=<REASON> previous_static_h=<HOURS>" >> /home/administrator/.hermes/logs/omni_health.log
```

## Automation Integration

### Option A: Cron-based Health Check (Recommended)

Add a cron job that runs every 15 minutes:
```
*/15 * * * * cd /home/administrator/.hermes && python3 scripts/omni_health_check.py
```

The script should:
1. Check OMNI process existence
2. Check log file last modification time
3. If stale >30min, log warning and restart
4. If dead, restart and record recovery

### Option B: Guardian Integration

Add to `guardian.py heal()` function:
```python
# OMNI health check
import subprocess, os, time
log_path = "/home/administrator/.hermes/logs/omni_loop.log"
if os.path.exists(log_path):
    mtime = os.path.getmtime(log_path)
    age_min = (time.time() - mtime) / 60
    if age_min > 30:
        log("🏥 OMNI静态>30min, 尝试重启...")
        subprocess.run(["pkill", "-f", "omni_loop.py"], capture_output=True)
        time.sleep(2)
        subprocess.Popen(["python3", "scripts/omni_loop.py"], cwd="/home/administrator/.hermes")
```

## Recovery Anatomy

From log analysis (last successful run at 2026-05-06T19:30:44):
- Full cycle takes ~1 second when all data is up-to-date
- Steps: 采集 → 清洗+匹配 → AI评分 → 需求挖掘 → Agent匹配 → 产品生成 → 推送 → 记忆更新
- Output goes to logs/omni_loop.log (76KB at last run)

## Pitfalls

1. **Don't restart too often**: If OMNI crashes within 5min of restart, investigate root cause before retrying. Max 3 restarts per hour.
2. **Don't conflict with guardian cycles**: OMNI runs its own collection. Let guardian handle the collection-only cycles.
3. **Log file ownership**: OMNI runs as `administrator` user. Ensure log dir permissions allow append.
4. **state.db lock**: Gateway (PID 984781) holds write-lock on state.db. OMNI may fail if gateway is mid-transaction. Always use timeout.
5. **No duplicate OMNI processes**: Check before starting. Two OMNI loops will duplicate work and may deadlock on DB.

## Verification Checklist

- [ ] OMNI process running (or auto-restarted)
- [ ] Log file updating every 30 min max
- [ ] Health check cron/guardian integrated
- [ ] Recovery events tracked in omni_health.log
- [ ] No duplicate OMNI processes running

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
