---
name: intelligence
description: "情报系统 — 多平台数据采集、情报收集管线、RSS订阅调试、端点发现和统一信息处理的情报工作流。包含48个注册采集器的完整管理体系。"
category: intelligence
---

# Intelligence (情报系统)

## 采集器架构

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时


所有采集器注册在 `unified_collector_v5.py` 的 `COLLECTORS` 字典中。
每个条目: `'name': (function, priority, timeout_seconds)`

- **priority**: 1-10，越高越优先执行（排序用，不影响存活）
- **timeout**: 采集器线程超时（秒），30s全局线程超时在 `collect_platform` 中

## 采集器类型

1. **RSS采集器** — `collect_xxx_rss()`，通过 `fetch()` + `parse_rss()` 解析
2. **API采集器** — `collect_xxx()`，直接调用平台API，JSON解析
3. **HTML爬取** — `collect_xxx()`，正则解析HTML页面
4. **自采集器** — 独立脚本，自己负责入库（如 csdn_blog_collector），需要 `wrap_xxx()` 包装
5. **Match采集器** — 从已有数据中按关键词匹配，标记偏好方向标签

## 扩增平台的最佳实践

### 新增平台步骤
1. 检查RSS可用性（国内网络限制——境外RSS可能不通）
2. 写 `collect_xxx()` 函数
3. 注册到 `COLLECTORS`
4. 测试单平台: `--platform xxx`
5. 全量测试: `--collect`

### 国内网络限制应对
- **境外RSS不可用** → 用match采集器从已有数据中按关键词匹配
- **百度搜索受限** → 直接数据库LIKE匹配
- **替代方案**: 用微博/头条/CSDN/Sina等国内源的关键词搜索结果替代

### 关于match类型采集器
match类型使用 `source_type='match'`，走特殊入库路径：
- 不经过偏好过滤（数据本身就是按偏好匹配出来的）
- 不插入新记录，而是更新已有记录的 `category_tags`
- 使用 `url` 匹配（不是 `url_hash`——因为hash算法有MD5和SHA256混用问题）
- 自动去重：检查每个tag部分是否已存在

## 已知BUG与修复

详见 `references/collector_pitfalls.md`。

## 标签系统

`extract_tags()` 函数负责给每条数据打方向标签。格林主人偏好分三层：
- **P0核心**: AI/LLM/手机/芯片/新能源/军事/机器人/安全
- **P1高兴趣**: 格斗/摄影/NBA/电影/音乐/游戏/科学/太空
- **P2一般**: 旅游/美食/历史/时尚

偏好配置在 `reports/collector_preferences.json`。

## 子技能

此分类包含以下子技能：
- hermes-intelligence-collection-v3
- hermes-intelligence-system-v4
- hermes-intelligence-v5-debug
- multi-platform-collection-debugging
- platform-endpoint-discovery
- rss-feed-debugging-playbook
- unified-collection-pipeline

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
