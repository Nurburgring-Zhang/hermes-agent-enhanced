---
description: "运维 — PushPlus 推送故障排查与直接 API 调用方案等运维技能"
category: operations
---

# Operations (运维)

此分类包含系统运维相关的技能。

此分类包含以下 1 个子技能：

## 子技能

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### hermes-pushplus-troubleshooting
Hermes PushPlus 推送故障排查与直接 API 调用方案，处理 hermes_push_manager.py 执行时的服务器验证错误。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
