---
name: wechat-mp-collector
description: 微信公众号文章采集MCP服务器 — 通过微信公众平台搜索接口获取公众号文章，支持全量/增量爬取、文章内容转Markdown、SQLite去重存储
version: 0.1.0
category: hermes
---

# 微信公众号采集器 (wechat-mp-mcp)

## 安装位置

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

- 源码: `~/.hermes/scripts/collectors/wechat-mp-mcp/`
- pip包: `wechat-mp-mcp` (已安装到Hermes venv)

## 使用方式
1. **首次使用**: 需要微信公众号扫码登录
   ```bash
   # 激活venv后运行:
   python3 -m wechat_mp_mcp.login
   ```
2. **搜索公众号+获取文章列表**:
   ```python
   from wechat_mp_mcp.client import WeChatClient
   from wechat_mp_mcp.storage import Storage
   storage = Storage()
   client = WeChatClient(storage=storage)
   articles = client.search_account("公众号名称")
   ```

## 集成到Hermes
已集成到 `hermes_ultimate_collector.py` 的 `collect_wechat_mp()` 函数。
从omni_loop调用: `python3 scripts/hermes_ultimate_collector.py --wechat`

## 限制
- 需要扫码登录（登录态有效期约4天）
- 每日API调用上限约200次
- 腾讯随时可能更改接口

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
