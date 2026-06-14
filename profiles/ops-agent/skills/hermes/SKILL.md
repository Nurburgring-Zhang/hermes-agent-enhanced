---
description: "Hermes系统 — Hermes 代理的系统诊断、升级和自动运行配置等自我管理技能"
category: hermes
name: hermes
---

# Hermes (Hermes 系统)

此分类包含 Hermes 代理系统自身的维护和管理技能，涵盖系统诊断、升级、评分管道运维和自动运行搭建。

## 触发条件
- 用户提及Hermes系统状态、配置、诊断时
- 需要检查或修复Hermes自身功能时
- 执行系统升级、能力激活、模块检查时
- 需要处理情报评分积压或检查评分健康度时

## 子技能

### hermes-system-diagnostic
Hermes 代理系统性全面诊断与自检流程，覆盖 Skills/Agents/Expert System/Intelligence/Memory/Workflow Handlers/Cron Jobs/auto_engine 的全系统深度诊断。

### hermes-upgrade-auto-run
WSL2 中 Hermes 升级及全能力自动运行系统搭建，包含实际 schema 验证、情报→专家→记忆管道和 cron 配置。

### intelligence-scoring-ops
智慧评分管道操作指南，包括评分积压检查、评分引擎选择、数据质量验证。

参考: `references/intelligence-scoring-ops.md`

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
