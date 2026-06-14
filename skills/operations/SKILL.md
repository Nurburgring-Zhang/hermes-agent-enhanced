---
name: operations
description: 运维 — 系统健康检查、systemd服务修复、网关故障排查、推送系统诊断等Hermes Agent运维技能
category: operations
---

# Operations (运维)

此分类包含系统运维相关的技能。

## 子技能

### hermes-systemd-service-repair
修复 Hermes 的 systemd 用户服务（gateway/eternal/webui 等）启动失败的问题。详细排查步骤见 references/systemd-service-repair.md。

### 穿透式验证方法论
"在跑不等于在工作"——对每一项能力做三件套验证(进程+日志+手动触发)。见 references/penetration-testing-checklist.md。

### hermes-pushplus-troubleshooting
Hermes PushPlus 推送故障排查与直接 API 调用方案，处理 hermes_push_manager.py 执行时的服务器验证错误。

### 休眠管线激活
发现代码存在的自动化管线未被调度时的激活流程（验证引擎→检查历史→手动执行→加cron→加健康检查）。详细步骤见 references/dormant-pipeline-activation.md。

## 触发条件
- 用户提及部署、安装、配置服务时
- 需要调试系统环境或依赖时
- 执行系统运维操作时

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
