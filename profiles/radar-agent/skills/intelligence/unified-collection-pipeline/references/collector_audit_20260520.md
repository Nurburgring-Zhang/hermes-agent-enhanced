# 采集系统深度审计报告 — 2026-05-20

## 核心数据

- 数据库: `~/.hermes/intelligence.db` (44.7MB)
- `raw_intelligence`: 18,942条
- `cleaned_intelligence`: 27,240条
- `push_records`: 3,192条
- 数据时间跨度: 2026-05-01 ~ 2026-05-20 (20天)
- 今日采集(24h): 3,916条
- 最近7天: 14,045条 (日均~2,007条)
- 总独立数据源数: 20+

## 平台状态快照

### ✅ 活跃采集 (24h内)
| 平台 | 24h量 | 采集器源文件 |
|------|-------|-------------|
| weibo | 929条 | unified_collector_v5.py |
| sina_tech | 710条 | unified_collector_v5.py |
| arxiv | 1,241条 | unified_collector_v5.py |
| ithome | 295条 | unified_collector_v5.py |
| toutiao | 260条 | toutiao_browser_collector.py/v4 |
| baidu | 230条 | unified_collector_v5.py |
| zhihu | 208条 | unified_collector_v5.py |
| bilibili | 95条 | unified_collector_v5.py |
| hackernews | 86条 | RSS采集 |
| oschina | 55条 | RSS |
| techmeme/tmtpost | 42条 | RSS |
| freebuf | 30条 | RSS |
| sogou_wechat | 25条 | unified_collector_v5.py |
| 36kr | 17条 | RSS |
| GitHub | 2条 | hermes_unified_collector.py |

### ❌ 静默/死亡 (7天+无数据)
| 平台 | 静默天数 | 最后采集 | 原因 |
|------|---------|----------|------|
| douyin | 18天 | 2026-05-02 | 网络/反爬 |
| overseas (Reddit/X) | 17天 | 2026-05-03 | Network is unreachable |
| 博客园 | 17天 | 2026-05-03 | N/A |
| B站-全站 | 19天 | 2026-05-01 | 被替换为bilibili_tech |
| GitHub Trending | 18天 | 2026-05-02 | 浏览器超时，API替代未就绪 |
| huxiu | 13天 | 2026-05-07 | 阿里云WAF封锁 |
| kuaishou | 10天 | 2026-05-10 | 每天仅1条热搜 |
| toutiao_tech/finance/... | 18-19天 | 2026-05-01/02 | 子频道采集被废弃 |

## 内容质量评估

- **平均内容长度: 132字符** ⚠️ 极短
- **内容<100字符**: 13,985条 (73.8%) — 大多数仅为标题+摘要片段
- **内容100-500字符**: 1,935条 (10.2%)
- **内容500-2000字符**: 2,950条 (15.6%)
- **内容2000+字符**: 仅29条 (0.15%)
- **空内容**: 43条 (0.23%)
- **重复标题**: 18组共160条 (0.85%)

## 关键日志错误统计

| 日志 | 错误数 | 主要错误 |
|------|--------|---------|
| collector_overseas_20260501 | 60 | Network is unreachable (Reddit) |
| collector_kuaishou_20260519 | 27 | 403/429 |
| collector_kuaishou_20260520 | 10 | 403/429 |
| collector_kuaishou_20260513 | 13 | 403 |
| cron_cycle.log | 连续4次 | 全量采集退出码124 (timeout) |

## Cron中采集的间接入口

crontab中无显式采集cron，采集通过以下间接触发:
1. `guardian.py cycle` - 每2小时，调用 unified_collector_v5.py --collect，但全量模式4次连续超时
2. `omni_loop.py` - 每30分钟，调用 unified_collector_v5.py --collect --parallel 2，正常产出

## 采集器清单（~/.hermes/scripts/）

共28个采集相关脚本，核心入口集中在:
- `unified_collector_v5.py` (1,401行) — 主采集器，包含24+采集函数
- `hermes_unified_collector.py` (769行) — 备选采集器，15+采集函数  
- `master_pipeline.py` — 完整管线定义，但未被cron直接调用
- 无 `collectors/` 目录，无 `agents_company/collectors/` 目录

## 历史退化脉络

参考 `~/.hermes/reports/degradation_analysis_20260507.json`:
- 采集峰值: 7,794条/天 (4月底)
- 5月初断崖下跌至 ~613条/天
- 降幅: 91%
- 原因: 抖音/小红书/海外/微信采集大面积死亡 + 全量采集超时
