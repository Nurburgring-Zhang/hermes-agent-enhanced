---
name: autonomous-systems
description: "自主系统 — 多代理公司编排、全自主公司系统、统一系统编排器等大规模自动化系统的协调技能"
category: autonomous-systems
---

# Autonomous Systems (自主系统)

此分类包含大规模自主系统的编排技能，涵盖多代理公司管道调度、全自主公司运营和统一编排器。

此分类包含以下 7 个子技能：

## 子技能

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


### agents-company-orchestration
Agents Company 编排器，调度和管理130代理12部门的完整工作流管道。

### autonomous-company-system
全自主公司系统，无需人工干预的端到端自动化企业运营。

### unified-system-orchestrator
统一系统编排器，整合多个自主系统的调度和协调。

### self-evolution-executor
自进化执行器，按优先级(P0-P3)执行具体系统修复命令，包括重启停滞管道、回收DB空间、清理输出文件。

### omni-health-monitor
OMNI全能循环健康监控，检测进程停滞(>30min)、自动重启并记录恢复历史。防止OMNI静默宕机数小时。

### task-auto-resume
长期任务自动恢复，每次Hermes醒来时自动检查未完成的长期任务并从断点恢复执行。

### gear-context-compression-v2
上下文压缩与索引-复原系统，10层防御体系，不依赖Hermes记忆的纯cron方案。含 context_packer / context_auto_assoc / cross_session_cache / surgical_context_slicer / context_index_system / context_selfcheck。参考文件见 references/。

### proactive-status-reporting
主动状态反馈系统 — 解决"对话中断无反馈"问题，系统自动推送状态到WeChat。
- status_reporter.py: cron每40分钟/每2小时推送系统状态(采集/推送/齿轮健康)
- feedback_push.py: 长任务每完成一个子阶段时调用，推送进度到WeChat
- session_init_check.py: 每次对话启动时自动检测中断任务/齿轮健康/数据库异常，有问题自动推送
- context_selfcheck.py: 14项全面自检(cron健康/文件新鲜度/预加载/索引可追溯/跨轮次缓存)

关键原则：用户不在时必须主动报告，不等用户问；每子阶段完成后调用 feedback_push；启动检测自动扫描并推送异常；状态推送每30分钟去重。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
