---
name: xiaohongshu-collector
description: 小红书内容采集器 — 基于Playwright headless SSR DOM提取采集小红书笔记/文章（无需登录，无需API）
version: 2.0.0
category: hermes
---

# 小红书采集器 v2

## 核心发现

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

小红书API全部封死：
- `api/sns/web/v1/search/notes` POST → 500 (jarvis-gateway-default)
- `edith.xiaohongshu.com/api/...` → 404
- `api/sns/web/v1/homefeed` → 500
- `__INITIAL_STATE__` 内嵌SSR数据含有`undefined`而非`null`（JSON解析需替换）

## 唯一有效方案：Playwright headless SSR提取

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN"
    )
    page = context.new_page()
    page.goto("https://www.xiaohongshu.com/explore", timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)  # 等JS渲染

    notes = page.evaluate("""
        () => {
            const items = document.querySelectorAll('.note-item');
            return Array.from(items).slice(0, 30).map(item => {
                const link = item.querySelector('a');
                const img = item.querySelector('img');
                const titleEl = item.querySelector('.title, .note-title, [class*=title]');
                const authorEl = item.querySelector('.author, .name, [class*=author]');
                const likeEl = item.querySelector('.like, .count, [class*=like]');
                const href = link ? link.href : '';
                const match = href.match(/explore\\/([a-f0-9]+)/);
                return {
                    href, img: img ? img.src : '',
                    title: titleEl ? titleEl.textContent.trim() : '',
                    author: authorEl ? authorEl.textContent.trim() : '',
                    like: likeEl ? likeEl.textContent.trim() : '0',
                    noteId: match ? match[1] : '',
                };
            });
        }
    """)
```

## 要点
- 探索页(explore)有效，搜索页(search_result)是CSR空壳（搜索页提取不到数据）
- 每次稳定20-23条标题+作者+点赞+封面图
- 无需要登录/扫码/API key
- headless模式即可（不需要显示器）
- 注意`undefined → null`替换如果JSON提取

## 文件
- 最新采集器: `~/.hermes/scripts/xhs_collector_v4.py` (215行)
- 旧采集器(已废弃): `~/.hermes/scripts/collector_xhs_enhanced.py` (909行, API端点全挂)
- cron: 每3小时 `5 */3 * * *`

## 限制
- 搜索页无法采集（CSR渲染，需要JS执行但Playwright也拿不到数据）
- 每次只能拿到热门笔记，无法指定关键词（除非做第二次搜索）
- 每笔记只有公开信息（标题/作者/点赞/封面），无评论/正文

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
