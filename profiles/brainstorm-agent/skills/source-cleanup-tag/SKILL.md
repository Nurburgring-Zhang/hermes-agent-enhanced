---
name: source-cleanup-tag
description: 标记、清理和归档静默数据源。检测4天以上无数据的采集源，标记为已知静默，建议移除或归档
category: operations
tags: [operations, source-management, cleanup, maintenance]
---

# source-cleanup-tag

## 用途

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

识别并处理长期（≥4天）无数据的采集源，标记为已知静默源，避免重复告警。

## 采集源静默判定标准
- **4-6天无数据**: 标记为"低活跃"，可保留但降低告警
- **7-13天无数据**: 标记为"静默"，建议检查采集器
- **14+天无数据**: 建议从活跃采集列表移除，移至archive

## 当前已知静默源（截至2026-05-08 14:00，来自intelligence.db实时查询）
⚠️ 注意: 不要将活跃源误标记为静默源。以下列表已与intelligence.db交叉验证。

### 实际静默源 (4-6天无新数据，低活跃/保留)
| 源 | 最后数据 | 数据量 | 状态 |
|---|---|---|---|
| 36kr | 2026-05-04 | 19条 | LOW — 4天无新数据 |
| douyin | 2026-05-03 | ~89(总) | SILENT — 采集器需浏览器方案重写 |
| cnblogs | 无数据 | 0条 | ARCHIVE候选 — 采集器失效 |
| juejin | 无数据 | 0条 | ARCHIVE候选 — 采集器失效 |

### 活跃但被错误列为静默的源 (⚠️ 不要标记)
以下源曾被错误标记为静默，但intelligence.db显示它们实际活跃：
| 源 | 4天数据量 | 最近时间 | 修正说明 |
|---|---|---|---|
| **ithome/IT之家** | 670条 | 2026-05-08 14:05 | **非常活跃**，不要标记为静默 |
| **oschina** | 104条 | 2026-05-08 14:00 | **活跃中**，不要标记为静默 |
| **HackerNews** | 319条 | 2026-05-08 13:55 | **活跃中**，不要标记为静默 |
| **B站(bilibili)** | 34条 | 2026-05-08 当日 | 今日有数据，活跃 |
| **sina_tech** | 233条 | 2026-05-08 当日 | **非常活跃**，间歇性工作但当前正常 |

### 7-13天无数据 (静默，检查采集器)
| 源 | 最后数据 | 数据量 | 处理建议 |
|---|---|---|---|
| sogou_wechat | 未知 | 0条(4d内) | 检查采集器 |
| toutiao_sports | 2026-05-02 | 49条(7d) | **6天静默** — 检查采集器，主toutiao源活跃(623条/7d) |
| toutiao_finance | 2026-05-02 | 26条(7d) | **6天静默** — 同上 |
| toutiao_military | 2026-05-02 | 13条(7d) | **6天静默** — 同上 |
| toutiao_world | 2026-05-02 | 17条(7d) | **6天静默** — 同上 |
| toutiao_game | 2026-05-02 | 8条(7d) | **6天静默** — 同上 |
| toutiao_tech | 2026-05-02 13:00 | 6条(7d) | **6天静默** — 同上 |
| overseas | 2026-05-03之前 | 0条(4d内) | 检查采集器 |

### 永久失效源（无需重复告警）
| 源 | 原因 | 处理 |
|---|---|---|
| kuaishou | 站点重构，HTTP 302重定向 | 需要浏览器方案重写 |
| zhihu_topstory | HTTP 401需认证 | 需要auth方案 |
| zhihu_daily | API废弃 | 已移除 |
| ifanr | RSS空数据 | 已移除 |
| itmyhome | 数据库中无此平台数据(可能是IT之家旧名称) | 已合并到ithome |

### 主动作
执行：python3 -c "
import sqlite3
conn = sqlite3.connect('/home/administrator/.hermes/intelligence.db')
c = conn.cursor()
from datetime import datetime, timedelta
# 标记静默源
cutoff_4d = (datetime.now() - timedelta(days=4)).isoformat()
cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()
c.execute(\"SELECT source, MAX(collected_at), COUNT(*) FROM raw_intelligence WHERE source != '' GROUP BY source HAVING MAX(collected_at) < ? ORDER BY MAX(collected_at)\", (cutoff_4d,))
rows = c.fetchall()
print(f'Silent sources (>4 days): {len(rows)}')
for r in rows:
    days_silent = (datetime.now() - datetime.fromisoformat(r[1].replace('T',' '))).days if r[1] else 99
    status = 'ARCHIVE' if days_silent >= 14 else 'SILENT' if days_silent >= 7 else 'LOW'
    print(f'  [{status}] {r[0]}: {days_silent}d silent, {r[2]} items')
"

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
