# 采集过滤机制调查 (2026-05-27)

## 用户的问题

"是经过过滤之后才进行采集吗？采集覆盖的全面吗？我的偏好网站、偏好方向的信息都采集到了吗？"

## 调查结果

### 过滤发生在哪个阶段？

**采集后、入库前**。流程是：

```
采集API/源网页 → 解析出标题+内容+URL → insert_raw_item()检查黑名单+质量预筛 → 入库raw_intelligence
```

`is_collect_filtered()` runs at line ~299 of `unified_collector_v5.py`:
- Loads 351 active keywords from `spam_filter_keywords` (severity ≥ 3)
- Checks title + first 500 chars of content
- Any match → `return True` → item dropped, never enters DB

This means: **API requests/bandwidth are already consumed** before filtering. Content is fetched from the source, parsed, then discarded if filtered.

### 采集覆盖了哪些平台？

38 registered collectors in `COLLECTORS` dict (line ~1444 of unified_collector_v5.py):

| Category | Platforms |
|----------|-----------|
| 综合热点 | 微博热搜/搜索, 百度, 知乎热榜/日报/故事, 贴吧, 头条 |
| 科技/开发者 | 36氪, InfoQ, 虎嗅, 钛媒体, 爱范儿, 新浪科技, CSDN, 掘金, 思否, 博客园, 腾讯云, DevTo, FreeBuf, TechMeme |
| AI专项 | arXiv(2 API endpoints), HuggingFace |
| 国际 | HackerNews, Reddit, GitHub Trending |
| 视频 | B站综合/科技, 抖音, 快手 |
| 微信 | 搜狗微信搜索 |
| 独立采集器 | 微信公众号MCP, 小红书, 抖音, CSDN |

### 偏好方向的采集问题

**采集阶段缺乏偏好增强。** 40+方向标签（AI/EV/Military等）只在采集**后**作为分类标签使用。没有偏好配置文件（JSON/YAML）在采集**前**注入偏好关键词来增强特定方向的采集密度。

目前的做法：所有平台平等采集 → 入库后标签分类 → 推送时根据TAG_TO_TIER排序。

### 黑名单关键词误杀问题

`spam_filter_keywords` 表有351个活跃关键词，其中一些误杀了合法内容：

| 关键词 | 误杀内容 | 建议处理 |
|--------|---------|---------|
| "夫妻" | 婚姻/家庭类内容 | 降级到severity=1或删除 |
| "荣耀" | 华为荣耀手机新闻 | 降级 |
| "主播" | 直播行业新闻 | 降级 |
| "性感" | 时尚/美妆/摄影内容 | 降级 |
| "泰国" | 泰国旅行/新闻 | 降级 |

## 修复建议

1. **创建偏好配置文件** (`reports/preference_directions.json`) — 列出格林主人各偏好的权重
2. **采集前增强** — 在`collect_sogou_wechat()`等函数中，按偏好权重调整关键词遍历次数
3. **黑名单审核** — 降低误杀关键词的severity
4. **补充缺失源** — 格林主人可能关注的知识星球/少数派/即刻等未覆盖源
