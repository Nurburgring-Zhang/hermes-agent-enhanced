---
description: "OpenClaw迁移 — 系统性将 OpenClaw 全功能迁移到 Hermes 的实战方法论"
category: openclaw-migration
---

# OpenClaw Migration (OpenClaw 迁移)

此分类包含将 OpenClaw 系统完整迁移到 Hermes 的方法论和工具。

此分类包含以下 1 个子技能：

## 子技能

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### openclaw-full-migration
系统性迁移 OpenClaw 全功能到 Hermes 的实战方法，基于成功迁移经验总结的完整工作流。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
