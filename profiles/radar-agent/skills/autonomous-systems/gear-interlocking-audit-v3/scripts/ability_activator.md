# ⚡ Ability Activator — 全能力自检脚本

**位置**: `~/.hermes/scripts/ability_activator.py`
**cron**: `0 * * * *` (每1小时)

## 职责
1. 扫描全部 `scripts/*.py` (214+) — 语法验证，标记可独立运行
2. 激活全部 `evolution_v3/` (16个核心进化模块)
3. 激活全部 `agents_company/` (45+个模块含actors/handlers)
4. 检查cron覆盖，报告缺失

## 触发方式
- cron自动: 每1小时
- 手动: `cd ~/.hermes && python3 scripts/ability_activator.py`

## 输出
- `reports/ability_activation_report.json` — 完整报告
- `logs/ability_activator.log` — 运行日志

## 7规则自检 task_monitor.py v2.0
**位置**: `~/.hermes/scripts/task_monitor.py`
**cron**: `*/10 * * * *` (每10分钟)

内嵌7规则引擎:
- 规则1: rule1_review_check() — 全局预判+回顾
- 规则2/3/4: check_interrupted_tasks() — 中断恢复+复盘
- 规则5: rule5_gear_health_check() — 齿轮健康+多工况
- 规则6: rule6_full_ability_scan() — 全能力扫描
- 规则6/7: cross_gear_verify() — 链式相互验证
- 规则7: rule7_activate_all() — 真实激活验证
