---
name: clawhub-ranking-monitor
description: ClawHub 淘金小镇排行榜监控 - 自动化追踪AI技能/插件榜单变化
trigger: clawhub排行榜、淘金小镇、AI技能市场监控
---

# ClawHub 排行榜监控系统

## 数据源

## 触发条件
- 用户提及Hermes系统状态、配置、诊断时
- 需要检查或修复Hermes自身功能时
- 执行系统升级、能力激活、模块检查时

- **ClawHub** (clawhub.ai) — AI Agent技能注册中心 (Vite/React SPA, Convex后端)
  - `sort=installs` — 最高安装量 ✅ 可用 (25 results)
  - `sort=newest` — 最新发布 ✅ 可用 (25 results)
  - `sort=featured` — 精选 ⚠️ 只有5个
  - `sort=stars` — ⛔ Broken (0 results, ClawHub bug)
  - `sort=downloads` — ⛔ Broken (0 results)
  - `sort=updated` — ⛔ Broken (0 results)
  - `sort=name` — ✅ 可用 (全部技能, 字母序)
- **AA榜单** — AI Agent排行榜 (待补充完整)

## Cron任务
- 每6小时采集一次 (`cronjob id: 6641dda559e5`)
- 数据存入 `~/.hermes/intelligence.db` (表: clawhub_rankings)
- 原始快照存 `~/.hermes/rankings/`

## 手动运行
```bash
python3 ~/.hermes/scripts/clawhub_monitor.py
```

## 查看历史数据
```bash
sqlite3 ~/.hermes/intelligence.db \
  "SELECT collected_at, source, category, name FROM clawhub_rankings ORDER BY collected_at DESC LIMIT 20;"
```

## 数据表结构
```sql
clawhub_rankings (
    id, source, category, rank, name, 
    author, installs, rating, url, collected_at
)
```

## 重要注意事项

1. **ClawHub 是 SPA (Convex + Vite/React)** — HTML抓取无法获取技能数据。必须使用浏览器渲染（Playwright）才能提取实际排名。
2. **broken sort orders**: `most-downloaded`, `most-starred`, `recently-updated` 均返回0条结果（ClawHub平台bug）。
3. **数据采集脚本**已改为 `~/.hermes/scripts/clawhub_collect_data.py`，通过浏览器工具获取真实数据后写入DB。
4. **存储逻辑**: 每次运行会INSERT OR REPLACE同排序+排名的最新数据。旧快照保留在JSON文件中。
5. **作者集中度**: steipete 占据安装量排行榜超过50%的技能。pskoett的Self-Improving Agent以426k安装量居首。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
