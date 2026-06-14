---
name: fix-push-old-articles
title: "修复推送旧文章问题"
description: "修复v12推送混入旧文章的完整方案-采集层+推送层+数据库+定时维护"
triggers: ["推送出现旧文章", "2017年文章被推送", "published_at未过滤", "v12推送混入旧内容"]
---

# 推送旧文章修复方案

## 问题描述

## 触发条件
- 用户提及Hermes系统状态、配置、诊断时
- 需要检查或修复Hermes自身功能时
- 执行系统升级、能力激活、模块检查时

搜狗微信采集器采集到2017-2020年旧文章，v12推送脚本没有检验`published_at`字段，导致旧文章混入推送。

## 修复步骤

### 1. 数据库清洗（立即执行）
```bash
python3 ~/.hermes/scripts/clean_old_intelligence.py
```

### 2. 采集层修复（root cause）
文件：`~/.hermes/collector/weixin_account_collector.py`

`_extract_sogou_item()`解析完published_at后立即检查跳过>7天文章。

### 3. 推送层修复
文件：`~/.hermes/scripts/hermes_v12_push.py`
- 新增`is_recent_published()`检查7天时效
- 所有SQL加published_at字段+importance_score>=0过滤

### 4. 定时维护
crontab: `0 */6 * * * cd ~/.hermes && python3 scripts/clean_old_intelligence.py >> logs/clean_old_intelligence.log 2>&1`

## cron排期
格林主人要求 **0 8,12,18,0 * * ***（每天8/12/18/0点整准时推送）

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
