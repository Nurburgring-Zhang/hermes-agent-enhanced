---
name: hermes-intelligence-system-v4
description: Hermes全平台智能情报采集推送系统v4 — 采集器架构、已知bug、修复记录、IP封锁问题
category: intelligence
version: 2026-04-22
trigger: 维护/增强Hermes情报系统时加载
---

# Hermes 情报采集系统 v4 — 完整实现

## 触发条件
维护/增强Hermes全平台智能情报采集推送系统时加载。

## 系统架构

### 核心文件
- 采集器：`/home/administrator/.hermes/scripts/hermes_collector_v4.py`（53,840字节）
- 账号源：`/home/administrator/.hermes/workspace/workspace/enhanced_account_sources.yaml`（18,121字节，100+账号源）
- 数据库：`/home/administrator/.hermes/intelligence.db`（SQLite）
- 数据库表名：**`raw_intelligence`**（不是articles！这是个bug！）
- 推送：PushPlus微信推送

### 数据库结构（raw_intelligence表）
```sql
id INTEGER PRIMARY KEY,
title TEXT,
url TEXT,
source TEXT,           -- 平台名：bilibili/zhihu/weibo/36kr/ithome等
author TEXT,
content TEXT,
summary TEXT,
tags TEXT,
created_at TIMESTAMP,
url_hash TEXT UNIQUE,  -- 用于去重
title_hash TEXT,       -- 用于去重
hot_score REAL
```

### 已知问题
1. **v4采集器数据库表名错误**：代码中使用`articles`表，实际表名是`raw_intelligence`，导致写入失败
2. **数据中心IP封锁**：WSL IP被微信/小红书/知乎/百度等中国平台封锁
3. **不平衡问题**：bilibili占14,273条(85%)，需要平衡采集

## 已验证可用的平台采集

| 平台 | 状态 | 采集方式 | 条/次 |
|------|------|----------|-------|
| bilibili | ✅ 正常 | API | 20条 |
| 知乎 | ✅ 正常 | API | 15条 |
| 微博热搜 | ✅ 已修复 | API | 20条 |
| 36kr | ✅ 已修复 | RSS | 15条 |
| 今日头条 | ✅ 已修复 | JSON API | 20条 |
| github | ✅ 正常 | API | 27条 |
| Dev.to | ✅ 正常 | API | - |
| iThome | ✅ 正常 | RSS | - |
| OSCHINA | ✅ 正常 | RSS | - |

## IP封锁平台（需要Proxy或替代方案）

| 平台 | 状态 | 尝试过的方案 |
|------|------|-------------|
| 微信公众号 | ❌ CAPTCHA | 搜狗入口CAPTCHA无法自动过 |
| 小红书 | ❌ IP风险 | 300012错误码 |
| 知乎热榜 | ❌ 空白页 | 需登录+JS渲染 |
| 百度 | ❌ 验证码 | Slider验证码 |
| RSSHub | ❌ 超时 | 网络不可达 |
| Reddit | ❌ 超时 | 网络不可达 |
| Hacker News | ❌ 超时 | 网络不可达 |

## 采集命令

```bash
cd /home/administrator/.hermes
# 全量采集
python3 hermes_collector_v4.py --source all

# 单平台采集
python3 hermes_collector_v4.py --source bilibili
python3 hermes_collector_v4.py --source zhihu
python3 hermes_collector_v4.py --source weibo
python3 hermes_collector_v4.py --source toutiao
python3 hermes_collector_v4.py --source 36kr

# 查看可用平台
python3 hermes_collector_v4.py --list
```

## 修复记录（2026-04-22）

### 36kr修复
- 端点：`https://36kr.com/api/search/articles?query=AI&per_page=20`
- 解析：JSON → `data.items[].title/content/template_info`

### 今日头条修复
- 端点：`https://toutiao.com/T9859071504384000512/`（热榜页）
- 解析：正则提取`window.__INITIAL_STATE__`中的JSON数据

### 微博热搜修复
- 端点：`https://weibo.com/ajax/side/hotSearch`
- 解析：JSON → `data.hotgov.trends`

### v4采集器bug（未修复）
```python
# 错误代码（约第230行）：
cursor.execute("INSERT OR IGNORE INTO articles ...")

# 应该是：
cursor.execute("INSERT OR IGNORE INTO raw_intelligence ...")
```

## 海外平台扩展（待验证可用）

```python
# TechCrunch
"techcrunch": {
    "name": "TechCrunch",
    "type": "news",
    "urls": ["https://techcrunch.com/"],
    "hot_topics": ["https://techcrunity.com/category/artificial-intelligence/"],
    "method": "browser",
    "priority": "high"
}

# Wired
"wired": {
    "name": "Wired",
    "type": "news",
    "urls": ["https://www.wired.com/"],
    "hot_topics": ["https://www.wired.com/category/business/"],
    "method": "browser",
    "priority": "high"
}

# Ars Technica
"ars": {
    "name": "Ars Technica",
    "type": "news",
    "urls": ["https://arstechnica.com/"],
    "hot_topics": ["https://arstechnica.com/ai/"],
    "method": "browser",
    "priority": "medium"
}
```

## SOUL.md v2.2 关键设定

- 版本：2.2（全面智能化自主执行强化版）
- 核心哲学：遇到任何问题自动触发全能力扫描→Multi-Agent→子Agent集群→汇总输出
- 禁用：降级实现、模拟实现、偷工减料
- 质量>速度：即使耗时也必须保证完整性
- 推送：70%中文+30%英文

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
