---
name: hermes-intelligence-v5-debug
description: Hermes v5采集器调试方法论与平台连通性实测结果 - 2026-04-23重大调试成果
category: intelligence
version: 2026-04-23
trigger: 调试hermes情报采集系统平台连通性问题时加载
---

# Hermes v5 采集器调试方法论

## 触发条件
调试Hermes情报采集系统平台连通性、采集器返回0数据、RSS解析失败问题时加载。

## 核心调试方法

### 问题：采集器通过模块调用返回0，但单独测试正常

**症状**：`collect_solidot()`返回0条，但`parse_rss(fetch(url))`返回20条

**根因**：模块内`fetch`函数在某些平台循环调用时返回0字节（可能是连接池/状态问题）

**诊断步骤**：
```python
# Step 1: 直接测试底层
from unified_collector_v5 import fetch, parse_rss
raw = fetch("https://www.solidot.org/index.rss")  # 应该返回 >1000 bytes
items = parse_rss(raw)  # 应该返回 >0 items

# Step 2: 如果底层正常，问题在采集器包装
from unified_collector_v5 import collect_solidot
items = collect_solidot()  # 如果返回0，说明采集器内部问题

# Step 3: 用monkey-patch追踪
original_fetch = mod.fetch
def debug_fetch(url, headers=None, data=None, timeout=10):
    result = original_fetch(url, headers, data, timeout)
    print(f"  fetch({url[:60]}): {len(result)} bytes")
    return result
mod.fetch = debug_fetch
```

**解决方案**：在采集器内部直接使用urllib，不依赖模块的fetch：
```python
def collect_solidot_fixed():
    from urllib.request import Request, urlopen
    import xml.etree.ElementTree as ET, re, html
    
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0"
    req = Request("https://www.solidot.org/index.rss", headers={"User-Agent": ua})
    with urlopen(req, timeout=10) as r:
        raw = r.read().decode('utf-8', errors='replace')
    
    # 解析逻辑...
```

## 平台连通性实测 (2026-04-23 WSL环境)

### ✅ 终端直接可采集
| 平台 | 端点 | 备注 |
|------|------|------|
| 微博热搜 | `weibo.com/ajax/side/hotSearch` | 52条/次 |
| Bilibili | `api.bilibili.com/x/web-interface/ranking/v2` | 100条/次 |
| 知乎热榜 | `zhihu.com/api/v4/creators/rank/hot` | 19条/次 |
| 36kr | `36kr.com/api/newsflash` | 30条/次 |
| IT之家 | `ithome.com/rss/` | 60条/次 |
| OSChina | `oschina.net/news/rss` | 50条/次 |
| 今日头条 | `toutiao.com/api/pc/feed` | 8-20条/次 |
| 百度热搜 | `top.baidu.com/board?tab=realtime` | 30条，正则`"word"` |
| GitHub Trending | `api.github.com/search/repositories` | 20条/次 |
| Dev.to | `dev.to/api/articles?top=10` | 30条/次 |
| 搜狗微信 | `weixin.sogou.com/weixin?type=2&query=` | 每关键词1-5条 |
| Solidot | `solidot.org/index.rss` | 20条，需`.//item` |
| 知乎问答 | `zhihu.com/api/v4/creators/rank/hot` | 30条 |

### ❌ 网络封锁（需浏览器/Camofox）
| 平台 | 原因 | 降级方案 |
|------|------|----------|
| 微信公众号 | 需微信登录 | Sogou搜索（部分可用） |
| 小红书 | IP风控+反爬 | Camofox浏览器 |
| 抖音 | API需登录 | Camofox浏览器 |
| 知乎（完整） | 登录墙/403 | Sogou搜索降级 |
| Reddit | 网络封锁 | `old.reddit.com`已测试返回0 |
| HuggingFace | 网络封锁 | API返回0 |

### ⚠️ 需要调试
| 平台 | 问题 | 状态 |
|------|------|------|
| Cnblogs | Atom命名空间 | parse_rss已修复，需验证 |
| iFanr | XML实体`&#8211;` | parse_rss已修复HTML unescape |
| TMTPost | XML实体`&#8211;` | parse_rss已修复 |
| Juejin | 可能需要JS渲染 | 需Camofox或找API |
| HackerNews | 单线程慢22s | 已改为ThreadPoolExecutor并行 |

## RSS解析关键修复

### 1. XML实体问题（ifanr/tmtpost）
```python
import html, re
clean = re.sub(r'<!\[CDATA\[|\]\]>','',xml_text)
clean = re.sub(r'&#[0-9]+;', lambda m: html.unescape(m.group()), clean)
clean = re.sub(r'&#[xX][0-9a-fA-F]+;', lambda m: html.unescape(m.group()), clean)
root = ET.fromstring(clean)
```

### 2. Atom命名空间（cnblogs）
```python
# 尝试多种方式
all_items = channel.findall('.//item')
if not all_items:
    all_items = channel.findall('.//{http://www.w3.org/2005/Atom}entry')
if not all_items:
    all_items = channel.findall('.//entry')
```

### 3. CDATA处理
```python
clean = re.sub(r'<!\[CDATA\[|\]\]>','',xml_text)
```

## 平台特定发现

- **Reddit**：必须用`old.reddit.com`，`www.reddit.com`返回0
- **Bilibili**：PC User-Agent返回100条，iPhone UA返回0
- **Baidu**：页面包含`"word":"标题"`模式，用正则提取
- **Sogou微信**：必须`type=2`（文章搜索），`type=1`是账号搜索

## 采集文件位置
- v5采集器：`/home/administrator/.hermes/scripts/unified_collector_v5.py`
- v4采集器：`/home/administrator/.hermes/scripts/hermes_collector_v4.py`
- 清洗管道：`/home/administrator/.hermes/scripts/unified_cleaning_pipeline.py`
- 推送引擎：`/home/administrator/.hermes/scripts/unified_pusher.py`
- 总控脚本：`/home/administrator/.hermes/scripts/master_pipeline.py`

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
