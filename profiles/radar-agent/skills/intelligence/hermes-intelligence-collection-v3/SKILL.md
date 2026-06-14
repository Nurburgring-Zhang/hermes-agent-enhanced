---
name: hermes-intelligence-collection-v3
description: Hermes全平台智能情报系统 v3.6 - 采集状态、推送修复、已知问题
version: 4.0
updated: 2026-05-24
---

# Hermes 全平台智能情报系统 v3.5

## 系统架构

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时


### 核心文件
- `hermes_ai_push_manager.py` — 推送管理器（已全面重构）
- `unified_collector_v5.py` (1,401行) — 当前活跃的统一采集器（替代了hermes_unified_collector.py）
- `hermes_unified_collector.py` (769行) — 备选采集器
- `master_pipeline.py` — 完整的采集→清洗→推送管线定义
- `guardian.py` — cycle模式是实际执行采集的cron入口（每2小时）
- `omni_loop.py` — 增量采集入口（每30分钟，调用 unified_collector_v5.py --parallel）
- `intelligence.db` (44.7MB, ~18,942条raw记录, ~27,240条clean记录)

### 数据库结构
```
weibo_items: id, platform, title, url, author, published_at, cleaned_at, content, summary, tags, language
```

## 推送系统关键修复 (v3.4-v3.5)

### 1. get_recent_items() — 跨午夜查询
- 问题: `DATE(cleaned_at)=today` 在00:00后查不到00:00前的数据
- 修复: `WHERE cleaned_at >= (now - 24 hours)`
- 附加: `WHERE (published_at >= (now - hours) OR published_at IS NULL)` 确保NULL记录也被包含

### 2. stratified_sampling() — 70/30采样
- 问题: 公式 `min(len(zh_pool)*ratio, total)` 导致中英文比例反转
- 修复:
```
zh_count = min(len(zh_pool), int(total * 0.7))
en_count = min(len(en_pool), int(total * 0.3))
```
确保先取中文70%，再补英文30%，严格按比例上限

### 3. cleanup_old_data() — 数据保留
- 问题: 每日删除昨天数据导致跨午夜数据丢失
- 修复: `DELETE WHERE cleaned_at < (now - 7 days)` — 保留7天数据

### 4. ai_value_judgment() — 多层评分
- 平台基础分: GitHub+50, Dev.to+35, HackerNews+40, 知乎/36kr/juejin+30等
- 语言加分: Python/TypeScript/Rust/Go +50, AI/LLM/Agent +30
- 内容深度: 段落>5 +10, 代码块 +20, 技术词密度>15% +30, 列表>3项 +10
- 时间衰减: 1-3天 -5, 3-7天 -15, >7天 -25
- 噪音过滤: 学习/面试/转行 -10, 低信息量 -5
- 最终: ⭐5(>80), ⭐4(60-80), ⭐3(40-60), ⭐2(20-40), ⭐1(<20)

## 平台采集状态

### 直连RSS/API（正常工作）
| 平台 | 方法 | URL/端点 | 数量/次 |
| IT之家 | RSS直连 | www.ithome.com/rss/ | ~20 |
| 开源中国 | RSS直连 | www.oschina.net/news/rss | ~50 |
| 博客园 | Atom直连 | feed.cnblogs.com/blog/sitehome/rss | ~20 |
| 少数派 | RSS直连 | sspai.com/rss | ~10 |
| 36kr | API直连 | 36kr.com/api/newsflash | ~60 |
| 知乎 | API直连 | api.zhihu.com/topstory/hot-lists/total | ~30 |
| bilibili | API直连 | api.bilibili.com/x/web-interface/ranking | ~30 |

### 不可用
| 平台 | 原因 |
| 虎嗅 | 阿里云WAF封锁 |
| CSDN | API返回521 WAF拦截 |
| RSSHub公共服务 | 网络不可达 |
| 海外(Reddit/X/YouTube/Telegram) | 境外网络不可达，已静默17天 |
| 抖音 | 网络/反爬，已静默18天 |
| 小红书 | 全部4个采集器变体失效 |

### 需认证/Cookie
| 平台 | 方案 |
| 小红书 | rnote.dev商业API / Jamailar/RedBox |
| 微信公众号 | lbbniu/wechat_official_account |

## 推送配置
- 时间: 08:00 / 12:00 / 18:00 / 00:00
- 目标比例: 70%中文 + 30%英文
- 每次条数: 30条（21中文 + 9英文）
- 推送服务: PushPlus
- 最近推送成功ID: 9cb6b8d3b6a441b69b6dd825016fe6b1

## 待办事项
1. [ ] 修复 guardian.py cycle 全量采集超时（退出码124）— 根本原因：unified_collector_v5.py 全量模式在120s跑不完
2. [ ] 集成 lbbniu/wechat_official_account 到Hermes
3. [ ] 小红书采集：测试 rnote.dev 或 Jamailar/RedBox
4. [ ] 虎嗅：RSSHub自部署或浏览器自动化
5. [ ] CSDN：浏览器自动化绕过521
6. [ ] 英文池：当前30.4%略超目标，需增加中文平台覆盖
7. [ ] 修复海外采集（Reddit/X/YouTube/TikTok/Telegram全部"Network is unreachable"）
8. [ ] 抖音采集恢复
9. [ ] 修复采集内容深度（当前74%文章<100字符，平均仅132字符）
10. [ ] 微信公众号采集恢复(需要先解搜狗验证码, 然后启用 wechat_agent_collector.py)
11. [ ] 海外源桥接(代理/镜像/RSSHub自部署)
12. [ ] 偏好关键词权重库更新到 active_memory.db
13. [ ] 推送按格林主人方向加权排序(不是简单总分)

## 关键URL
- lbbniu/wechat_official_account: github.com/lbbniu/wechat_official_account
- RedBox/Jamailar: github.com/Jamailer/RedBox
- rnote.dev: rnote.dev（商业API）
- RSSHub自部署: github.com/DIYgod/RSSHub

## 已知Bug
1. ~~浏览器delegate_task: 系统级bug~~ - 实为并发限制，max_concurrent_children=3，每次最多3个并行任务
2. 虎嗅: 阿里云WAF完全封锁，RSSHub/浏览器均无法访问
3. ~~终端curl: 60秒超时~~ - GitHub Trending浏览器超时，用GitHub API替代

## 🔴 严重已修复：推送系统中断48小时（2026-05-25 ~ 2026-05-27）

**故障链**: AI评分cron用错model名(deepseek/deepseek-chat→deepseek-chat) → 所有新数据无AI评分 → v12推送SQL条件 ai_score>=15 全部过滤 → 连续3天无推送

**修复（2026-05-27）**:
1. `ai_score_backfill.py` model名修复
2. 推送SQL加importance_score/pref降级条件
3. TARGET_COUNT 50→25（避PushPlus 2万字限制）
4. URL & 转义
5. 推送重试+降级+记录去重
6. 所有23,188条数据100%已评分

**当前推送状态**: ✅ 工作（19-22条/次）
**推送cron**: 8/12/18/0点，`guardian.py push`

## 严重已知问题 (2026-05-24审计)

## ✅ 已修复 (2026-05-24)

### 采集层黑名单拦截 (is_collect_filtered)
- **改动**: `unified_collector_v5.py` 的 `is_collect_filtered()` 从只拦截 severity>=4(156条) 改为拦截 severity>=3(**334条**)
- **效果**: 所有 severity>=3 的黑名单关键词(clickbait标题党/家庭纠纷/萌宠/游戏/八卦/低俗内容等)在写入 raw_intelligence 前就被拦截
- **采集层过滤范围**: 334条关键词, 覆盖 spam/clickbait/low_quality 三大类

### extract_tags 扩展为19方向覆盖格林主人偏好
- **改动**: `unified_collector_v5.py` 的 `extract_tags()` 从8个方向扩展为19个方向
- **新增标签**: Mobile_PC, EV, Auto, Sports_Fight, Military_Intl, Politics, Beauty_Photo, Dev_OpenSource, Robot, Space, Security, Game, Science, History_Culture, Photo_Art, Movie_Video, Music, Travel_Food, Hot, Platform
- **AI关键词扩展**: 从15个扩到60+ (覆盖智谱/月之暗面/百川/Sora/RLHF/DPO/GRPO等)
- **全量回标**: 12,494条 General 数据中 4,695条被重新归类, 分类率从33%提升到74%

### AI评分修复
- **API key**: 注入 DEEPSEEK_API_KEY 到 .env 和 config.yaml
- **bug修复**: `hermes_ai_scoring.py` 修复 `date` 未import的 NameError
- **cron**: 每15分钟后台评分30条(batch_size=3), 累计3,329条待评分

### 微信公众号采集
- 搜狗微信被CAPTCHA封锁(浏览器+HTTP均无法绕过)
- mp.weixin.qq.com 文章直连可用
- 已创建 `wechat_agent_collector.py` (agent-browser方案, 需解验证码后可用)
- 已创建 `wechat_content_enhancer.py` (增强已有文章内容, 不需新搜索)

### 新采集源评估(大部分失败)
测试结果: 机器之心(RSS返回HTML非标准格式), 极客公园/PingWest/数字尾巴/V2EX(RSS失效/网络不可达)
结论: 国内RSS已基本消亡, 新源拓展依赖API或浏览器自动化

### 🔴 guardian.py cycle 全量采集连续超时
- **症状**: 每2小时的 `cycle` 在全量采集阶段连续返回退出码124 (timeout)
- **频率**: 每天4-6次完全失败
- **证据**: `~/.hermes/logs/cron_cycle.log` 中4次重复 "重试3/2: 全量采集 返回124 → ❌ 失败"
- **影响**: 虽然 `omni_loop.py` 的增量采集仍在运行，但全量检查已完全失效

### 🔴 海外采集死亡 (18天)
- **症状**: Reddit 8个子版块全部 "Network is unreachable" (Errno 101)
- **证据**: `collector_overseas_20260503.log` 中60+次错误
- **受影响**: Reddit, X/Twitter, YouTube, Telegram, TikTok

### 🟡 内容深度严重不足
- 74% 记录的 `content` 字段 < 100 字符
- 平均内容长度仅132字符
- 多为标题+首段摘要，缺少完整文章内容

### 🟡 20个静默源
包括 douyin (18天), GitHub Trending (18天), 博客园 (17天), huxiu (13天), kuaishou (10天) 等

### ✅ 已修复 (2026-05-07)
- PushPlus token 截断问题 (a8f152...ab7f)
- 三个推送脚本的 `get_pushplus_token()` 语法错误
- omni_loop.py 升级到 v12 HTML推送模板

## 浏览器采集各平台JS提取（实测2026-04-21）

| 平台 | URL | JS选择器 | 过滤 |
|------|-----|---------|------|
| 36氪 | https://36kr.com/newsflashes | `a[href*="36kr.com/newsflashes/"]` | 无需 |
| IT之家 | https://www.ithome.com/ | `a[href*="ithome.com/0/"]` | 无需 |
| 掘金 | https://juejin.cn/ | `a[href*="/post/"]` | URL补全`https://juejin.cn`前缀 |
| 思否 | https://segmentfault.com/news | `h3 a, .news-item a[href*="/a/"]` | URL补全`https://segmentfault.com`前缀 |
| 腾讯云 | https://cloud.tencent.com/developer/articles | `a[href*="/developer/article/"]` | URL补全`https://cloud.tencent.com`前缀 |
| DEV.to | https://dev.to/t/programming | `a[href*="dev.to/"]` | 过滤`/t/`, `/new/`, `/enter` |
| Lobsters | https://lobste.rs/ | `.story a[href*="://"]` | 过滤archive.org/Ghostarchive |
| GitHub Trending | — | **不要用浏览器，会超时** | **用GitHub API替代** |

## GitHub Trending API替代方案

```python
import urllib.request, json
url = "https://api.github.com/search/repositories?q=stars:>1&sort=stars&order=desc&per_page=15"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
response = urllib.request.urlopen(req, timeout=15)
data = json.loads(response.read().decode('utf-8'))
for item in data.get('items', [])[:15]:
    print(f"{item['full_name']}|{item['html_url']}")
```

## 推送数据库实测表结构 (2026-04-21)

```
cleaned_intelligence: id, title, content, url, source, platform, author, category, importance_score, value_level, value_reasons, is_ai_related, language, chinese_ratio, is_processed, published_at, collected_at, cleaned_at, agent, personal_match_score, source_type
push_records: id, cleaned_id, title, content, url, source, platform, push_level, push_channel, push_status, push_response, opened, created_at
```

**注意**: 推送后记录到push_records用created_at字段，时间戳格式`datetime.now().strftime('%Y-%m-%d %H:%M:%S')`

## 70/30推送质量检查（实测正常）

推送条件：中文池≥21条 AND 英文池≥9条 → 执行推送
- 中文池(今日value_level≥3, language='zh'): 168条 ✅
- 英文池(今日value_level≥3, language!='zh'): 141条 ✅
- 比例: 21中文(70%) + 9英文(30%) = 30条

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
