---
name: collection-quality-prescreen
description: 采集时质量预筛 — 在insert_raw_item()阶段直接过滤低质数据，不让垃圾进库
category: intelligence
tags: [collection, quality, filtering, prescreen, intelligence]
---

# 采集质量预筛方法论

## 核心原则

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时


**在采集入口处就过滤垃圾，不让任何低质数据进入 raw_intelligence 表。**
不要等清洗/AI评分阶段再过滤——那时候垃圾已经占用了DB空间和计算资源。

## 预筛规则

```
insert_raw_item(item)  → 分为4道筛：

第0道: 格林主人偏好过滤（2026-05-27新增）
  从 collector_preferences.json 读取兴趣配置：
  - 先检查 discard 方向（股票/基金/房产/娱乐八卦/养生/星座等）→ 命中直接丢弃
  - 再检查 P0/P1/P2 兴趣方向 → 命中任一即放行并标记层级
  - 全没命中 → 丢弃（不让格林主人不感兴趣的内容进库）
  
第1道: 黑名单关键词拦截
  命中 spam_filter_keywords(severity>=3)  → 直接丢弃

第2道: 内容有效长度检测
  blog类来源(CSDN/博客园/掘金/segmentfault/devto/oschina):
    内容有效字符 < 150 → 丢弃（低质摘要）
  
  非短内容来源:
    内容有效字符 < 80 → 丢弃
  
  短内容来源例外:
    weibo, baidu, toutiao, tieba, solidot, hackernews, 
    reddit, sina_tech, zhihu, 36kr, bilibili
    → 天然短摘要，放行

第3道: 碎片垃圾检测
  标题有效字符 < 6 且 内容有效字符 < 100 → 丢弃

第4道(CSDN专有): 主动获取全文
  摘要 < 200字时，自动请求文章URL获取完整正文
  → 提高blog内容质量，避免只存几十字摘要

有效字符 = 去除空白/HTML标签/标点符号后的纯中文+英文字符
```

## 在代码中的实现

### insert_raw_item() 质量预筛（unified_collector_v5.py）

```python
# ===== 内容质量预筛 =====
clean_content = re.sub(r'[\s\r\n\t<>/\[\]{}()=+#@$%^&*|\\;:\'"~`]+', '', content).strip()
clean_title = re.sub(r'[\s\r\n\t<>/\[\]{}()=+#@$%^&*|\\;:\'"~`]+', '', title).strip()
content_info_len = len(clean_content)
title_info_len = len(clean_title)

short_content_ok_sources = {'weibo', 'baidu', 'toutiao', 'tieba', 'solidot', 
                             'hackernews', 'reddit', 'sina_tech',
                             'zhihu', '36kr', 'bilibili', 'bilibili_tech',
                             'baidu_hot', 'weibo_hot', 'weibo_search'}

is_short_ok = platform in short_content_ok_sources or source in short_content_ok_sources

if content_info_len < 80 and not is_short_ok:
    return False  # 丢弃
if content_info_len < 150 and ('blog' in source.lower() or 
    platform in ('csdn', 'cnblogs', 'juejin', 'segmentfault', 'devto', 'oschina')):
    return False  # 低质blog摘要丢弃
if title_info_len < 6 and content_info_len < 100:
    return False  # 碎片垃圾丢弃
```

### CSDN采集器v2 主动获取全文

```python
if len(content) < 200:
    # 摘要太短 -> 抓取文章页获取全文
    article_html = fetch(url, timeout=10)
    if article_html:
        full_content, full_author = extract_full_content(article_html)
        if len(full_content) > len(content):
            content = full_content
```

### 低分数据自动清理（lowscore_cleaner.py）

```python
# 每4小时cron自动清理cleaned_intelligence中的低分数据
# ai_score_total < 20 的数据:
#   1. 归档到 archive_cleaned 表
#   2. 从 cleaned_intelligence 删除
#   3. raw_intelligence 中3天前未清洗的孤立数据也删除
# 也集成到 unified_cleaning_pipeline.py 的末尾自动执行
```

## 适用场景

- 任何需要采集网页/API/RSS数据的系统
- CSDN、博客园、掘金等blog来源（搜索API只返回摘要）
- 微博/百度热搜等短内容来源（不需要长内容）
- 采集数据量>1000条/天的系统

## 关键陷阱

- **"有效字符"不是原始长度** — 要去除HTML标签、空格、标点符号后再算
- **短内容来源和白名单** — 不要一刀切，微博热搜天然只有标题，不能按文章标准要求
- **质量预筛只影响未来数据** — 已有堆积的垃圾数据需要额外清理步骤
- **CSDN搜索API的description字段就是短的** — 不是采集器的问题，是搜索API本来就只返回摘要
- **不要把"清洗时过滤"和"采集时过滤"混为一谈** — 清洗过滤太晚，数据已入库
- **source_type=match的数据必须绕过所有过滤** — match类型从已有数据库记录中按关键词匹配偏好方向，content为空、title可能不命中偏好关键词。如果走is_user_interest()会被丢弃。修复：match分支必须在insert_raw_item()最前面处理，进入任何过滤之前就拦截并更新category_tags后直接return。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
