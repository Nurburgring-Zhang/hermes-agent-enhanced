---
name: hermes
description: Hermes系统 — Hermes 代理的系统诊断、升级、Profile隔离、Skills压缩和自动运行配置等自我管理技能
category: hermes
---

# Hermes (Hermes 系统)

此分类包含 Hermes 代理系统自身的维护和管理技能，涵盖系统诊断、升级、Profile 创建、Skills 压缩和自动运行搭建。

## 触发条件
- 用户提及 Hermes 系统状态、配置、诊断时
- 需要检查或修复 Hermes 自身功能时
- 执行系统升级、能力激活、模块检查时
- 需要处理情报评分积压或检查评分健康度时
- 需要创建新 Profile 隔离不同任务时
- 需要压缩 Skills 按 Profile 分流时

## 子技能

### hermes-system-diagnostic
Hermes 代理系统性全面诊断与自检流程。

### hermes-profile-isolation
创建按任务隔离的 Hermes Profile。每个 Profile 获得独立 config、SOUL.md、skills 目录和工具集。
- 创建: `hermes profile create <name> --clone`
- 设置 SOUL.md 定义职责边界
- 用 `skills.external_dirs` 指向仅包含所需 skills 的目录
- 用 `disabled_toolsets` 限制不必要的工具

### hermes-skills-compression
将常驻 Skills 压缩到每个 Profile 10 个以内。通过 `skills.external_dirs` 配置独立 skills 目录，只链接当前 Profile 需要的 skill。未分配的 skills 保留在原目录不删除。

### hermes-upgrade-auto-run
WSL2 中 Hermes 升级及全能力自动运行系统搭建。

### intelligence-scoring-ops
智慧评分管道操作指南。

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
