---
description: "DevOps — npm MCP 服务器配置、Python 项目依赖安装、Webhook 订阅管理等基础设施与运维技能"
category: devops
---

# DevOps (DevOps)

此分类包含基础设施和开发运维相关的技能，涵盖包管理、MCP 服务器配置和事件驱动的 Webhook 订阅管理。

此分类包含以下 3 个子技能：

## 子技能

## 触发条件
- 用户提及部署、安装、配置服务时
- 需要调试系统环境或依赖时
- 执行系统运维操作时


### npm-mcp-server-setup
安装和配置基于 npm 的 MCP 服务器，处理 npm 安装超时或静默失败问题，支持手动提取包和后台重试。

### python-project-setup-with-uv
使用 uv 包管理器安装和配置 Python 项目，处理不完整的依赖声明和兼容性问题。

### webhook-subscriptions
创建和管理 Webhook 订阅，用于事件驱动的代理激活或直接推送通知（零 LLM 成本）。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
