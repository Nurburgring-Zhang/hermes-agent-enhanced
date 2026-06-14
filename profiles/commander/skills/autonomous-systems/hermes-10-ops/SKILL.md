---
name: hermes-10-ops
description: Sharbel 10个让Hermes从对话工具变成7x24可用助手的关键操作全面部署。Mission Control / Notion监控 / Cron / Slash Goal / 子Agent团队 / Telegram工作区 / Kanban看板 / Skills即SOP / Webhooks / 按工种分Agent
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags:
  - sharbel-10-ops
  - mission-control
  - cron
  - goal-mode
  - kanban
  - skills-as-sop
  - webhooks
  - agent-specialization
triggers:
  - "10个操作"
  - "Sharbel"
  - "任务控制中心"
  - "Mission Control"
  - "Slash Goal"
  - "看板"
  - "Skills即SOP"
  - "Webhook事件驱动"
  - "按工种分Agent"
---

# Hermes 10 Operations — Sharbel 实战方法论

## 核心理念

Sharbel 的 10 个操作总结为一个原则：让 Hermes 从"你喊一声它回一句"变成"24小时不睡觉的AI助手"。

10个操作不是独立的功能，而是一套**让Agent自动运转的系统设计**。

## 操作1: Mission Control 任务控制中心

### 原则
不要等工作埋在聊天记录里。要看到什么在跑、什么在等、什么被堵住了。

### Hermes实现
**无需外部面板**，Hermes 内生就有全部能力：

```
# 1a. 查看任务状态
cat ~/.hermes/reports/wake_guide.json          # 当前中断/待办任务
python3 ~/.hermes/scripts/gear_task_driver.py status  # 棘轮队列
python3 ~/.hermes/production_loop/engine.py status     # 生产级状态

# 1b. 查看所有运行中的进程
python3 -c "
import json, os
hermes_home = os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes'))
reports = os.listdir(f'{hermes_home}/reports/')
for r in sorted(reports, key=lambda x: os.path.getmtime(f'{hermes_home}/reports/{x}'), reverse=True)[:10]:
    size = os.path.getsize(f'{hermes_home}/reports/{r}')
    mtime = os.path.getmtime(f'{hermes_home}/reports/{r}')
    from datetime import datetime
    print(f'  {datetime.fromtimestamp(mtime).strftime(\"%m-%d %H:%M\")} {r} ({size/1024:.1f}KB)')
"
```

### 每天醒来必做
```bash
# Mission Control 面板 (一句话)
python3 ~/.hermes/scripts/mission_control_dashboard.py
```
（此脚本由安装时自动创建）

## 操作2: 监控Notion/系统变化

### 原则
当你的工作流中某一处状态发生改变时，Hermes应该知道下一步要做什么。

### Hermes实现
利用已有的 cron + search_files + memory 体系：

```python
# 每5分钟检查工作流状态变化的范例
def check_workflow_changes():
    # 检查数据库采集量
    # 检查文件/配置是否有新更改
    # 检查cron执行状态
    # 发现变化 → 自动执行下一步
```

**关键文件检测**：
- `cronjob(action='list')` — 查看所有定时任务状态
- `reports/gear_checkpoint.json` — 齿轮进度变化
- `intelligence.db` — 采集数据量变化

## 操作3: Cron定时任务（Sharbel最推荐的一个操作）

### 原则
有用的信息在你开口之前就到了。这是让Hermes变成24小时助理最快的方式。

### Hermes现有Cron体系（23个活跃任务）

| 频率 | 任务类型 | 示例 |
|------|---------|------|
| 每1分钟 | 齿轮系统 | G1-G7齿轮互审 + wake_guide更新 |
| 每3小时 | 情报采集 | 常规采集(8路并行) |
| 每6小时 | 重点采集 | 全量采集(14路并行) |
| 每天03:00 | 自进化 | 技能进化/记忆压缩/能力进化 |
| 每6小时 | SkillOpt验证 | 自验证监控 |
| 每30分钟 | 推送管道 | AI评分+推送 |

### Sharbel建议补充的Cron（已实现或可启用）

```
每天早上 - "今天AI圈有什么值得报道的事"              → 每日简报
每几小时 - 扫一遍X平台找值得引用的帖子                  → 社交监控
每天     - 检查竞品有没有异常火爆的视频                  → 竞品监控
每周     - 审计选题库，哪些卡在流程里没推进               → 流程审计
```
这些通过 `hermes-fast-pipeline` + `hermes-push-v3` + 现有cron任务已覆盖。

## 操作4: Slash Goal /goal 持续执行模式

### 原则
普通提示词只回答一次。/goal命令让Hermes朝着一个目标持续推进。

### Hermes实现

```python
# Slash Goal 模板 (Sharbel模式)
goal = """
目标: [明确的结果]
信息源: [VidIQ/YouTube竞品/Nova记忆/历史表现]
约束: [避开重复角度/避开XX套路]
交付物: [标题/钩子/Demo清单/素材清单]
"""
```

**Hermes原生等价物**：
- `production-reliability-engine` 的 LoopState 全局目标锚定
- `task-auto-resume` 的长期任务自动恢复
- `goal-hive-orchestrator` 的蜂群目标拆解

### Sharbel技巧：让Hermes自己写goal命令
```python
# 把这句话发给Hermes：
"我想用持续执行模式但不想写个模糊的目标。你只问必要的问题来确认我的需求，
 然后把我的回答转成最适合的目标指令。"
```

## 操作5: 子Agent研究团队

### 原则
一个Agent给你一个答案，三个子Agent给你一整个团队。

### Hermes实现
利用 `delegate_task` 实现并行研究团队：

```python
# 并行3个子Agent研究
results = delegate_task(tasks=[
    {
        "goal": "分析信号数据",
        "toolsets": ["terminal", "file"]
    },
    {
        "goal": "分析竞品内容和字幕",
        "toolsets": ["web", "search"]
    },
    {
        "goal": "分析历史表现和记忆",
        "toolsets": ["file", "search"]
    }
])
# 三个并行跑完，汇总成一个建议
```

**更高级的用法**：结合 Goal Hive 模式，Master 拆解后派给多个 Worker 并行执行，然后验收。

## 操作6: Telegram话题分组当工作区

### 原则
每个话题维持独立的上下文，不同工作区跑不同的工作流。

### Hermes实现
Hermes Agents Company 的130名员工天然按部门分组：
- 市场部 → 情报分析工作区
- 设计部 → 产品设计工作区
- 研发部 → 技术实现工作区
- PMO部 → 项目管理工作区
- 三省六部 → 自进化工作区

每个部门有独立的 skill 集、工具集和上下文。

## 操作7: 看板（Kanban）

### 原则
看板是让Agent的工作不再消失在聊天记录里的办法。

### Hermes实现
**Hermes已有三重看板体系**：

| 看板 | 位置 | 用途 |
|------|------|------|
| BBS任务账本 | `reports/hive_bbs.json` | Goal Hive 蜂群任务看板 |
| 棘轮队列 | `reports/gear_task_queue.json` | 齿轮系统任务队列 |
| 任务跟踪器 | `task_tracker.json` | 长期任务完成状态 |

### 看板查看命令
```bash
# 当前所有活跃任务一目了然
python3 ~/.hermes/scripts/kanban_dashboard.py
```

## 操作8: Skills即SOP

### 原则
任何要解释两遍的工作流，就该变成skills。

### Hermes实现
**Hermes有343个skills**，构建在完整的 skills 编排引擎之上。

### Sharbel的规则
1. 任何要解释两遍的工作流 → 变成skill
2. 不能只靠AI自动生成 → 你要帮它做成你想要的样子
3. 每个skill应该有：
   - 明确的触发条件
   - 编号步骤（精确到命令）
   - 陷阱和失败模式
   - 验证checklist

### Hermes已有强化
- `skillopt_trainer.py` — Skill质量验证门
- `hermes-skill-evolver` — 证据驱动进化
- `hermes-self-evolve-cluster` — 每天03:00自动进化

## 操作9: Webhooks事件驱动

### 原则
Cron是因为时间流动。Webhook是因为世界变了。

### Hermes实现
Webhook不是必须的外部服务——Hermes有等价的内生事件驱动：

```bash
# 检测事件 → 自动响应
cronjob(action='create', schedule='*/5 * * * *',  # 每5分钟检查
        prompt='检查是否有新的事件需要处理...')

# 或者使用notify_on_complete
terminal(background=True, notify_on_complete=True,
         command='long_running_task')
```

**但Webhook的精确性无法替代** — 外部事件触发比轮询更及时、更省资源。
推荐安装 `webhook` 服务（或用现有 cron 模拟）：

```bash
# 如果未来需要Webhook服务
# 安装: sudo apt install webhook
# 配置: ~/.hermes/config/webhooks.yaml
```

## 操作10: 按工种分Agent（最关键的）

### 原则
不要让一个Agent干所有事。

### Hermes实现
**Hermes已有明确的工种分化**：

| Agent/角色 | 模型 | 权限范围 | Skill集 |
|-----------|------|---------|---------|
| Hermes主Agent | 最强推理模型 | 全系统权限 | 343个skills |
| 情报采集Worker | 轻量模型 | 网络+文件 | 采集skils |
| 评分Worker | 中型模型 | 文件只读 | 六维评分 |
| 审计Worker | 严格模型 | 文件只读 | 交叉审核 |
| 三省六部 | 本地LLM | 隔离上下文 | 自进化 |

### Sharbel分配建议
```
Nova (最强推理模型) → YouTube权限 + 视频产出技能
Sage (中型模型) → X平台监控 + 分析能力
编程Agent → 仓库+GitHub权限
行政Agent → 日历+邮件权限 + 审批
```

### Hermes等价分配
```yaml
worker_types:
  research:       # 调研Worker — web_search + read_file
    toolsets: [web, file]
    max_iterations: 40
  analysis:       # 分析Worker — read_file + write_file
    toolsets: [file]
    max_iterations: 15
  implementation: # 实现Worker — terminal + file
    toolsets: [terminal, file]
  audit:          # 审计Worker — read_file only
    toolsets: [file]
    readonly: true
```

## 验证清单

- [ ] Mission Control — 醒来能一眼看到所有任务状态
- [ ] 文件变化监控 — 自动检测关键文件变化
- [ ] Cron — 每天自动推送简报
- [ ] Slash Goal — 支持持续执行模式
- [ ] 子Agent — 并行研究团队可调度
- [ ] 工作区 — 不同任务独立上下文
- [ ] 看板 — 任务状态可视
- [ ] Skills即SOP — 重复流程自动skill化
- [ ] Webhooks — 事件驱动响应
- [ ] 工种分工 — 不同Agent不同权限和模型

## 相关技能

- `goal-hive-orchestrator` — 蜂群组织，含BBS任务账本
- `production-reliability-engine` — 生产级可靠性，含全局状态
- `task-auto-resume` — 任务自动恢复
- `hermes-self-evolve-cluster` — 自进化集群
- `unified-system-orchestrator` — 多进程编排
