---
name: ultimate-collector
description: Hermes全能力聚合采集器v2 — 6种采集能力(统一平台10核心/RSS/小红书Playwright/微信MCP/scraper-multi/浏览器网页)+ThreadPoolExecutor并行+数据库去重。已验证全部import通过
version: 2.0.0
category: hermes
---

# Hermes MEGA Collector v2 — 全能力并行聚合采集器

## 文件位置

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

`~/.hermes/scripts/hermes_mega_collector.py`

## 能力矩阵（全部已验证通过）

| # | 能力 | 采集方式 | 状态 | 依赖 |
|---|------|----------|------|------|
| 1 | **unified_v5快速模式** | 10核心平台subprocess | ✅ 20s跑完 | venv python3 |
| 2 | **RSS订阅** | feedparser直采 | ✅ 即时出 | feedparser |
| 3 | **小红书Playwright** | XiaohongshuClient+SearchAction | ✅ import通过 | playwright(chromium) |
| 4 | **微信MCP公众号** | WeixinClient(auth) | ✅ installed(venv) | wechat-mp-mcp |
| 5 | **scraper-multi** | wx_scraper搜索 | ✅ import通过 | requests+bs4 |
| 6 | **浏览器网页采集** | urllib+re正则 | ✅ 零依赖 | urllib(stdlib) |
| 7 | TikTokDownloader | git克隆 | ✅ cloned | pip中 |
| 8 | MediaCrawler | git克隆 | ✅ cloned | pip中 |

## 架构

### ThreadPoolExecutor并行模式
所有采集器**同时运行**，互不干扰。汇总后写入collector_log表。

### 数据库去重
```sql
-- 唯一索引保证不重复
INSERT OR IGNORE INTO raw_intelligence(url_hash, ...) VALUES(...)
```

## 调用方式
```bash
# 全能力并行采集
/home/administrator/.hermes/hermes-agent/venv/bin/python3 scripts/hermes_mega_collector.py

# 后台运行
nohup /home/administrator/.hermes/hermes-agent/venv/bin/python3 scripts/hermes_mega_collector.py &
```

## 关键技术细节（踩坑实测）

### 1. 核心：用venv的python3
系统的python3没装任何采集包。venv的python3装了wechat_mp_mcp+xhs+feedparser等。
**所有采集器、所有cron脚本、所有subprocess调用——全部用venv的python3。**

### 2. 小红书：不要用xhs库（cookie过期），用xiaohongshu-skill
```python
import sys
sys.path.insert(0, '/home/administrator/.hermes/scripts/collectors/xiaohongshu-skill/scripts')
from search import SearchAction  # ✅ OK
from client import XiaohongshuClient  # ✅ OK
client = XiaohongshuClient()
searcher = SearchAction(client)
results = searcher.search("AI", limit=20)
```
- SearchAction需要XiaohongshuClient参数
- XiaohongshuClient是playwright浏览器自动化，需要chromium
- check_login_status()检测是否已登录
- _load_cookies()加载持久化cookie
- 首次需要扫码：python3 login.py生成QR码

### 3. 微信MCP安装方式
```bash
/home/administrator/.hermes/hermes-agent/venv/bin/pip3 install -e collectors/wechat-mp-mcp
# 验证
/home/administrator/.hermes/hermes-agent/venv/bin/python3 -c "from wechat_mp_mcp.client import WeixinClient; print('OK')"
```
- 类名是WeixinClient（不是WeChatClient）
- WeixinClient(auth=auth_obj)需要auth参数
- from wechat_mp_mcp.auth import load_auth获取已保存的登录态
- 未登录时返回None，需要先运行`python3 -m wechat_mp_mcp.login`扫码

### 4. unified_v5用subprocess分平台跑
不直接import unified_collector_v5.py（35+平台import连接池冲突）。
不跑--collect全量（35平台跑满300s+，频繁超时）。
用importlib.util.spec_from_file_location动态加载。
每个平台60s，10个平台共120s足够。

### 5. xiaohongshu-skill相对import修复
```bash
# 症状: attempted relative import with no known parent package
# 修复: 去掉.变成绝对import
sed -i 's/from \.client import/from client import/g' search.py
sed -i 's/from \.utils import/from utils import/g' search.py
```

### 6. scraper-multi的微信搜索
不需要登录，不需要cookie。搜狗的微信搜索，速度快但可能不全。
keywords列表：AI, 大模型, 人工智能, AIGC等。

### 7. 浏览器网页采集（零依赖方案）
只用stdlib（urllib+re），每个网站需要自定义正则匹配规则。
适合HackerNews、AI news等固定结构的网站。

## 推荐的cron配置
```
*/30 * * * * /home/administrator/.hermes/hermes-agent/venv/bin/python3 /home/administrator/.hermes/scripts/hermes_mega_collector.py >> /home/administrator/.hermes/logs/mega_collector.log 2>&1
```

## 故障排查 v2

| 症状 | 原因 | 修复 |
|------|------|------|
| xiaohongshu-skill ImportError: attempted relative import | search.py里有from .client | sed -i 's/from \./from /g' search.py |
| wechat_mp_mcp ImportError | 没装到venv里 | venv/bin/pip3 install -e collectors/wechat-mp-mcp |
| wechat WeixinClient()报错 | 类名是WeixinClient不是WeChatClient | 用正确类名 |
| 小红书playwright报No chromium | 没装playwright浏览器 | python3 -m playwright install chromium |
| 小红书search_notes不存在 | 函数名是search()不是search_notes() | searcher.search(kw) |
| unified_v5一直超时 | --collect全跑35平台 | 改用分平台+importlib动态加载 |
| xhs库报NoneType not callable | cookie过期 | 改用xiaohongshu-skill方案 |
| 采集输出全是齿轮守护信息 | 子进程输出和守护进程混了 | 检查mega_collector的输出log |
| 微信提示未登录 | 没有运行扫码 | python3 -m wechat_mp_mcp.login 扫码 |

## 集成到Omni Loop
在omni_loop.py的step1替换为mega_collector调用。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
