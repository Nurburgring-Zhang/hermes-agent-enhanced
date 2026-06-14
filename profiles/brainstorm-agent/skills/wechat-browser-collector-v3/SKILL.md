---
name: wechat-browser-collector-v3
description: 微信公众号采集器 v3 - 多Context轮换方案 解决搜狗反爬 + 频率限制  核心策略： 1. 每个批次(5个关键词)使用全新的browser context 2. 每次请求之间随机延迟3-6秒
category: auto-generated
tags: [auto-generated, wechat-browser-collector-v3]
---

# wechat-browser-collector-v3

由Hermes自进化引擎于 2026-04-28 05:00 自动生成。

## 源文件

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

`/home/administrator/.hermes/scripts/wechat_browser_collector_v3.py`

## 使用方法
加载此skill后可直接使用其功能。

## 自动生成说明
此skill是从系统中已有的脚本自动提取而来。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
