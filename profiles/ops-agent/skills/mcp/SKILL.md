---
description: "MCP协议 — 模型上下文协议工具，通过 mcporter 和原生 MCP 客户端连接和管理外部 MCP 服务器"
category: mcp
---

# MCP (MCP 协议)

此分类包含模型上下文协议（Model Context Protocol）相关的技能，用于连接、管理和调用外部 MCP 服务器的工具。

此分类包含以下 2 个子技能：

## 子技能

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### mcporter
使用 mcporter CLI 列出、配置、认证和调用 MCP 服务器/工具，支持 HTTP 和 stdio 传输方式。

### native-mcp
Hermes 内置的 MCP 客户端，连接外部 MCP 服务器并发现其工具，自动注册为原生 Hermes Agent 工具，支持 stdio 和 HTTP 传输、自动重连和安全过滤。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
