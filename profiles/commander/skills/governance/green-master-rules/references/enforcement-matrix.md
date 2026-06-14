# 7条规则全对话生效 — 9层强制机制参考

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    7条永久执行规则                             │
│  (SOUL.md §八 + AGENTS.md + CLAUDE.md + .cursorrules)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  层1: SOUL.md §八 (核心灵魂文件)                               │
│  层2: AGENTS.md (Claude/Cursor/Windsurf/Cline全兼容)          │
│  层3: CLAUDE.md (Claude Code专用)                              │
│  层4: .cursorrules (Cursor IDE)                                │
│  层5: memory (每次对话自动注入)                                │
│  层6: wake_init.sh in .bashrc (每次终端启动)                   │
│  层7: task_monitor.py 每10分钟 (7规则自检+能力扫描)            │
│  层8: gear_enforcer.py 每1分钟 (全能力监督+链式验证)           │
│  层9: ability_activator.py 每1小时 (全能力语法验证+激活)       │
│  层🔴: 反幻觉铁律 (2026-06-01上线, 最高优先级)                   │
│    ├─ SOUL.md 永久禁令§0                                          │
│    ├─ 24个context_sections章节                                    │
│    ├─ 16个核心脚本docstring                                       │
│    ├─ auto_engine self_evolution_engine.py                        │
│    └─ memory永久固化                                              │
│                                                                │
├─────────────────────────────────────────────────────────────────┤
│                    验证器: verify_rules.py                      │
│        输出: reports/rules_verification_report.json            │
└─────────────────────────────────────────────────────────────────┘
```

## 各层文件位置

| 层 | 文件 | 创建日期 |
|:-:|------|----------|
| 1 | `~/.hermes/SOUL.md` | 原有，2026-05-23更新v3.3 |
| 2 | `~/.hermes/AGENTS.md` | 2026-05-24 新创建 |
| 3 | `~/.hermes/CLAUDE.md` | 2026-05-24 新创建 |
| 4 | `~/.hermes/.cursorrules` | 2026-05-24 新创建 |
| 5 | memory条目 `【7条永久执行规则】` | 2026-05-24 更新 |
| 6 | `~/.hermes/scripts/wake_init.sh` + `~/.bashrc` | 2026-05-24 新创建 |
| 7 | `~/.hermes/scripts/task_monitor.py` v2.0 | 2026-05-24 重写 |
| 8 | `~/.hermes/scripts/gear_enforcer.py` v3.0 | 2026-05-24 增强 |
| 9 | `~/.hermes/scripts/ability_activator.py` | 2026-05-24 新创建 |
| 验证 | `~/.hermes/scripts/verify_rules.py` | 2026-05-24 新创建 |

## 验证命令

```bash
# 一键验证所有规则已生效
python3 ~/.hermes/scripts/verify_rules.py

# 检查输出
cat ~/.hermes/reports/rules_verification_report.json
```

输出应显示 `✅ 全部通过 — 7条规则在所有层面生效` 且 9/9 项检查全部 ✅。

## 全能力统计

```bash
# 全能力激活扫描
python3 ~/.hermes/scripts/ability_activator.py

# 任务监控（含7规则自检）
python3 ~/.hermes/scripts/task_monitor.py

# 齿轮健康
python3 ~/.hermes/scripts/gear_master.py status
```

## 故障排查

如果 verify_rules.py 报某项未通过：

| 问题 | 修复 |
|------|------|
| SOUL.md 关键词不匹配 | 检查 `grep -n "七条\|规则[1-7]\|严禁降级" ~/.hermes/SOUL.md` |
| AGENTS.md/CLAUDE.md 缺失 | 重新创建 |
| task_monitor.py 缺少7规则 | 确保包含 rule1_review_check() ~ rule7_activate_all() |
| gear_enforcer.py 缺少 ability_activation | 确保 Phase8/Phase9 包含全能力监督 |
| cron缺失 | 检查 `crontab -l | grep gear_master` 和 `cronjob list task-monitor` |
| memory过期 | 用 memory tool 检查 `【7条永久执行规则】` 条目是否存在 |
