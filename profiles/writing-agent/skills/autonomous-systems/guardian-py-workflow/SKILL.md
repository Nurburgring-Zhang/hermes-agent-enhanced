---
name: guardian-py-workflow
title: "Guardian.py 主调度器架构文档"
description: "完整文档化 guardian.py 三模式调度系统 — cycle/heal/push。包含cron配置、心跳机制、已知Bug(AR-029)映射、与各技能的关联关系。"
domain: autonomous-systems
priority: medium
triggers:
  - "guardian.py故障排查"
  - "系统调度架构查询"
  - "guardian代码修改"
  - "cron调度频率调整"
  - "心跳检查机制修改"
  - "AR-029修复"
  - "守护神工作流"
version: "1.0"
created: "2026-05-08"
---

# Guardian.py 主调度器架构文档

## 概述

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


`guardian.py` 是Hermes系统的核心调度器，位于 `~/.hermes/scripts/guardian.py` (543行, ~21KB)。它通过3种模式实现全自动运行：

| 模式 | 调用方 | 频率 | 日均调用 |
|------|--------|------|---------|
| **cycle** | guardian.sh cycle | 每2小时 | ~12次/天 |
| **heal** | guardian.sh heal + reviver_guardian.sh | 每5-15分钟 | ~96-200次/天 |
| **push** | guardian.sh push | 每日4次(08/12/18/00) | 4次/天 |

## 三模式详解

### 1. cycle 模式 (采集闭环)
- **调用**: `guardian.sh cycle`
- **cron**: `0 */2 * * *`
- **功能**: 执行完整情报采集闭环
- **关键脚本**: `unified_collector_v5.py`, `cleaning_pipeline_v2.py`, `ai_scoring.py`

### 2. heal 模式 (自愈检查)
- **调用**: `guardian.sh heal` + `reviver_guardian.sh`
- **cron**: `*/15 * * * *` (guardian.sh) + `*/5 * * * *` (reviver_guardian.sh)
- **功能**: 
  - 检查所有关键进程是否存活
  - 检查omni_loop心跳 (check_omni_loop_heartbeat, 第260-295行)
  - 检查磁盘空间
  - 自动清理cron锁定文件
  - 自动重启死亡进程

### 3. push 模式 (推送执行)
- **调用**: `guardian.sh push`
- **cron**: `0 8,12,18,0 * * *`
- **功能**: 执行v12 AI评分推送
- **关键文件**: `hermes_v12_push.py`, `v8_final_push.py`, `push_candidates_latest.json`
- **夜间饥饿**: 00:00-08:00时段推送阈值需降低

## Cron配置

```cron
# === 守护神 5分钟心跳 ===
*/5 * * * * cd /home/administrator/.hermes && bash scripts/reviver_guardian.sh >> logs/reviver_guardian.log 2>&1

# === 守护神 15分钟自愈检查 ===
*/15 * * * * cd /home/administrator/.hermes && bash scripts/guardian.sh heal >> /dev/null 2>&1

# === 全能循环 30分钟 ===
*/30 * * * * cd /home/administrator/.hermes && timeout 600 python3 scripts/omni_loop.py >> logs/omni_loop.log 2>&1

# === 采集循环 2小时 ===
0 */2 * * * cd /home/administrator/.hermes && bash scripts/guardian.sh cycle >> /dev/null 2>&1

# === 推送 每日4次 ===
0 8,12,18,0 * * * cd /home/administrator/.hermes && bash scripts/guardian.sh push >> /dev/null 2>&1
```

## 心跳文件体系

| 文件 | 路径 | 更新者 | 用途 |
|------|------|--------|------|
| 权威心跳 | `~/.hermes/omni_heartbeat.txt` | omni_loop.py | 主心跳，每循环更新 |
| 旧心跳(CRON) | `~/.hermes/cron/omni_heartbeat.txt` | 历史遗留 | 已停止更新，应删除 |
| 旧运行记录 | `~/.hermes/cron/omni_last_run.txt` | 历史遗留 | 已停止更新，应删除 |
| guardian心跳 | `~/.hermes/cron/guardian_last.txt` | guardian.sh heal | heal每次运行更新 |
| eternal心跳 | `~/.hermes/cron/eternal_heartbeat.txt` | eternal_loop.py | 永恒循环心跳 |

## 已知Bug: AR-029 (P0-CRITICAL)

### 问题描述
guardian.py `check_omni_loop_heartbeat()` 函数(第260-295行)使用**最旧**心跳文件判断omni_loop存活状态，而非**最新**心跳文件，导致虚假重启。

### 根源分析
```python
# guardian.py 第278行 — 错误逻辑
if age_minutes > max_age:
    max_age = age_minutes          # 找最旧的(max_age=最大分钟数)
    newest_path = hb_path          # ❌ 变量名newest_path实际存储最旧路径

# 第289行 — 在旧心跳文件存在时必然触发
if max_age > 120:                  # 用了最旧文件的时间
    return _restart_omni_loop()    # 虚假重启
```

`heartbeat_paths`包含：
1. `~/.hermes/omni_heartbeat.txt` — 正常更新 (权威心跳)
2. `~/.hermes/cron/omni_heartbeat.txt` — 停止于2026-05-06T19:30
3. `~/.hermes/cron/omni_last_run.txt` — 停止于2026-05-06T19:30

因为第2和第3个文件停滞了41+小时，`max_age`被设为~2500分钟，远超120分钟阈值，**每次heal都虚假重启**。

### 影响
- **~279次/天虚假重启** (连续7周期未修复)
- **~46.5h/天 CPU浪费**
- **累计超过300h CPU浪费** (截至2026-05-08 13:00)
- guardian.log已达9000+行

### 修复方案

**方案A (推荐): 修改取最小age**
```python
# 将第278-280行改为：
if age_minutes < min_age or newest_path is None:
    min_age = age_minutes
    newest_path = hb_path
```
并在第289行使用 `min_age` 代替 `max_age`。

**方案B (快速): 仅检查权威心跳文件**
```python
# 修改heartbeat_paths为只包含权威心跳
heartbeat_paths = [HERMES / "omni_heartbeat.txt"]  # 去掉cron/下的旧文件
```

**方案C (应急): 删除旧文件**
```bash
rm /home/administrator/.hermes/cron/omni_heartbeat.txt
rm /home/administrator/.hermes/cron/omni_last_run.txt
```
这会立即消除虚假重启，但未修复根因。

### 修复后验证
- [ ] `omni_recover.log` 停止5分钟级别增长
- [ ] guardian.py正常检查心跳无虚假重启
- [ ] 每天真实重启记录 ≤ 实际omni崩溃次数

## 技能映射

| guardian.py模式 | 对应技能 | 关系 |
|----------------|---------|------|
| cycle模式 | `guardian-cycle-workflow` (S-001) | cycle子流程 |
| heal模式 | `guardian-heal-workflow` (S-002) | heal子流程 |
| push模式 | `guardian-push-workflow` (S-003) | push子流程 |
| omni健康 | `omni-health-monitor` (S-012) | omni_loop健康监控 |
| 心跳检查(第260行) | `context-guardian-recovery` | 上下文守卫心跳机制 |
| 长期任务 | `long-task-guardian` | 深度DB检查+任务恢复 |

## 常见问题排查

| 问题 | 可能原因 | 对策 |
|------|---------|------|
| heal频繁误重启 | AR-029未修复 | 检查cron/下旧心跳文件，修复第278行 |
| cycle模式采集失败 | 采集器崩溃/IP封锁 | 检查各平台日志，运行platform test |
| push模式无候选 | 夜间饥饿/阈值过高 | 22:00-08:00阈值降至1条 |
| guardian.py无法连接DB | gateway进程锁 | 等待后重试，使用timeout=60 |
| 日志增长过快 | AR-029虚假重启 | 先修复AR-029，然后轮转日志 |
| 进程死锁 | 多个guardian.py实例 | 检查并kill多余进程 |

## Verification Checklist

- [ ] guardian.py三模式均正常运行
- [ ] cron配置与本文档一致
- [ ] AR-029已修复且omni_recover.log停止异常增长
- [ ] 各子技能(S-001/S-002/S-003/S-012)效度>0.90
- [ ] 旧心跳文件(cron/omni_heartbeat.txt等)已清理
- [ ] 新的心跳文件体系正常工作

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
