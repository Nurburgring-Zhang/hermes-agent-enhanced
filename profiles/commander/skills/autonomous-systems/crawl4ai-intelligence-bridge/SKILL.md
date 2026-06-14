---
name: crawl4ai-intelligence-bridge
description: Crawl4AI 网页爬虫引擎全面集成到Hermes情报采集管道 — 专为LLM设计的开源爬虫，比同类方案快6倍，完全免费。将任意网页转成干净Markdown，增强情报采集能力。
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags:
  - crawl4ai
  - web-scraping
  - intelligence-collection
  - markdown
  - llm-ready
triggers:
  - "Crawl4AI"
  - "智能爬虫"
  - "网页转Markdown"
  - "深度爬取"
  - "反爬"
  - "LLM友好爬虫"
---

# Crawl4AI Intelligence Bridge

## 核心理念

基于 Unclecode 开源 Crawl4AI（GitHub: unclecode/crawl4ai）：
- 专为LLM设计的网页爬虫
- 把网页变成长模型"读起来最舒服"的Markdown格式
- 比同类方案快6倍
- 完全免费，不设任何门槛

## 核心能力

| 能力 | 描述 |
|------|------|
| LLM就绪Markdown | 输出干净Markdown，保留语义结构 |
| 智能适应 | 自动分析页面结构，无需手动CSS选择器 |
| 三级反爬 | User-Agent轮换→IP切换→动态代理池 |
| 深度爬取 | 多级页面逐层深入，保持登录态 |
| 结构化提取 | CSS选择器+XPath精准定位 |
| 崩溃恢复 | resume_state从中断点接续 |

## 集成到Hermes情报采集

### 采集策略

```
Hermes 采集管道 (现有)
    │
    ├── API采集 (bilibili/zhihu/github...)
    ├── RSS采集 (36kr/ithome/dev.to...)
    ├── 浏览器采集 (今日头条...)
    └── 新增: Crawl4AI采集 ← 补充所有无API/无RSS的源
         ├── 单页Markdown (新闻/博客)
         ├── 深度爬取 (竞品全站)
         └── 结构化提取 (特定数据)
```

### 替代封锁源

| 封锁源 | Crawl4AI方案 |
|--------|-------------|
| 微信公众号 | User-Agent轮换+请求伪装 |
| 小红书 | 自动切换代理+会话保持 |
| 知乎热榜 | 浏览器指纹模拟 |
| 百度 | 自动重试+cookie保持 |

### 降级链路

```python
async def smart_collect(url):
    result = await try_existing_collector(url)
    if result.get("status") == "failed":
        result = await crawl4ai_collect(url)
    return result
```

## 验证清单

- [ ] crawl4ai 已安装
- [ ] single page test pass
- [ ] deep crawl test pass
- [ ] markdown output clean
- [ ] degradation fallback works
