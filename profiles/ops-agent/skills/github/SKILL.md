---
description: "GitHub工作流 — 使用 gh CLI 和 git 管理 GitHub 仓库、拉取请求、代码审查、Issue 和代码库检查等工作流"
category: github
---

# GitHub (GitHub 工作流)

此分类包含 GitHub 平台相关的工作流技能，覆盖从仓库管理、代码审查到 Issue 追踪和 PR 操作的完整开发协作流程。

此分类包含以下 6 个子技能：

## 子技能

## 触发条件
- 用户提及仓库管理、PR、Issue操作时
- 需要执行Git或GitHub工作流操作时
- 代码审查、版本发布、CI/CD配置时


### codebase-inspection
代码库检查工具，分析仓库结构、代码质量和依赖关系。

### github-auth
GitHub 身份验证配置工具，设置和管理 gh CLI 及 git 的认证信息。

### github-code-review
代码审查工作流，自动检查 Pull Request 的变更内容并提供评审意见。

### github-issues
GitHub Issues 管理工具，创建、更新和追踪 Issue。

### github-pr-workflow
Pull Request 工作流，包含 PR 创建、更新、合并和冲突处理的完整流程。

### github-repo-management
GitHub 仓库管理工具，涵盖仓库创建、配置、分支保护和权限设置。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
