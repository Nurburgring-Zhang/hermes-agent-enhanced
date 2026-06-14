---
name: long-task-guardian
description: HERMES 长期任务守护神 — 三路冗余守护(数据库检查/Cron管道/自动重启+恢复)，15分钟循环检查
category: autonomous-systems
tags: [guardian, long-task, auto-restart, monitoring, pipeline]
---

# long-task-guardian

由Hermes自进化引擎于 2026-05-01 05:00 自动生成。
最后更新: 2026-05-08 01:30 (手动填充完整文档)

## 源文件

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

- 主脚本: `/home/administrator/.hermes/scripts/long_task_guardian.py` (302行, ~10KB)
- 检查点文件: `~/.hermes/task_checkpoint.json`
- 心跳目录: `~/.hermes/heartbeat/`
- 日志: `~/.hermes/logs/guardian.log`

## 功能概述

三路冗余守护：
1. **数据库检查** — 验证6个核心SQLite数据库的完整性+表数量+大小
2. **Cron管道检查** — 读取pipeline_runs.sqlite的表状态+最后更新时间
3. **任务恢复** — 通过checkpoint文件追踪agent-company/expert-system/intelligence-collection任务状态

## CLI 使用方法

```bash
# 主模式: 全面检查+恢复 (推荐用于cron)
python3 ~/.hermes/scripts/long_task_guardian.py

# 守护模式: 持续监控（每5分钟循环，用于delegate_task）
python3 ~/.hermes/scripts/long_task_guardian.py --watch
```

## 被监控的管道列表

| 管道ID | 名称 | Cron时间 | 恢复命令 |
|--------|------|----------|----------|
| agent-company-pipeline | Agent Company 流水线 | 05:00 | `run_pipeline_hermes.py` |
| expert-system | 专家系统 | 06:00 | `multi_agent_engine.py --mode expert` |
| intelligence-collection | 情报采集 | 每4小时 | 由cron自动处理 |

## 数据流

```
long_task_guardian.py
    ↓
Step 1: verify_db_integrity()  → 检查6个DB: employees/experts/pipeline/departments/gateway
    ↓
Step 2: check_all_cron_jobs()  → 读取 pipeline_runs.sqlite 表状态
    ↓
Step 3: auto_restart_dead_tasks() → 更新 checkpoint 文件
    ↓
Step 4: create_status_report() → 生成完整Markdown报告
    ↓
Step 5: 写入 ~/.hermes/heartbeat/guardian_last.txt
```

## 检查的数据库

| 数据库 | 路径 |
|--------|------|
| employees.sqlite | agents_company/data/employees.sqlite |
| experts.sqlite | agents_company/data/experts.sqlite |
| pipeline_runs.sqlite | agents_company/data/pipeline_runs.sqlite |
| automation_control.sqlite | agents_company/data/automation_control.sqlite |
| departments.sqlite | agents_company/data/departments.sqlite |
| gateway.db | agents_company/gateway.db |

## 由 `--watch` 模式管理的文件

- 心跳: `~/.hermes/heartbeat/guardian_XXXX.txt` (保留最近12份)
- 日志: `~/.hermes/logs/guardian.log`

## 与 guardian.py 的关系

| 特性 | long-task-guardian | guardian.py |
|------|--------------------|-------------|
| 调用 | 每15分钟(cron) 或 --watch持续 | heal: */15, cycle: 5 */2, push: 8/14/20/22 |
| 聚焦 | 深度DB检查 + 任务恢复 | 轻量采集清洗推送调度 |
| 输出 | 完整Markdown报告 | 日志行 |
| 数据库 | 6个Agent Company DB | state.db/intelligence.db |
| 任务恢复 | 跟踪3个长期管道 | 无 |

两者互补而非重叠：guardian.py 做cron调度，long_task_guardian 做深度检查。

## 常见问题排查

### checkpoint文件损坏
```bash
# 删除后重新生成
rm ~/.hermes/task_checkpoint.json
python3 long_task_guardian.py  # 自动创建新checkpoint
```

### pipeline_runs.sqlite 不存在
不影响守护器运行 — 仅跳过表查询阶段。

### 守护模式日志太多
watch模式每5分钟写一个文件到heartbeat/，保留最近12份自动清理。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
