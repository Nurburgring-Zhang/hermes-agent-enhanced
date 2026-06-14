# Hermes 强制自运行引擎架构（2026-06-10 固化）

## 核心问题

18个模块全部"能导入"但 runtime.run() 从未被调用。
preflight/company_matcher/SDLC/gear/复盘/进化/双AI互审全部注入到 runtime.run() 和 executor.execute_task() 中，
但没人走过这条路径。所有模块只是"活着"不是"在跑"。

## 解决方案：三路冗余注入

任意一路存活即可保证强制引擎持续运行。

| 注入路径 | 频率 | 代码位置 | 检查内容 |
|---------|------|---------|---------|
| G1齿轮强制器 | 每分钟 | scripts/gear_enforcer.py (enforce函数末尾) | 9模块注入状态+自动重启 |
| G7醒来指南 | 每分钟 | scripts/wake_guide.py (文件顶部) | 独立注入，不依赖G1 |
| daemon守护进程 | 每5分钟 | workflows/daemon.py (run_once开头) | 16模块可导入性+联合唤醒 |

## 被监控的9个模块

| 模块 | 检查方式 | 失效自愈 |
|------|---------|---------|
| preflight | runtime.py 中是否存在 "run_preflight" | 自动重新注入 |
| company_matcher | executor.py 中是否存在 "CompanyMatcher" 和 "matched_employee" | 自动重新注入 |
| SDLC | executor.py 中是否存在 "SDLCEnforcer" 或 "sdlc_enforcer" | 自动重新注入 |
| gear_integration | crontab 中是否有 gear_enforcer + 模块可导入 | 自动重注册 |
| retrospect | crontab 中是否有 hermes_retrospect + 模块可导入 | 自动激活 |
| evolution | crontab 中是否有 evolution_trigger + 模块可导入 | 自动激活 |
| daemon | crontab 中是否有 workflow_daemon + 日志文件存在 | 自动重启 |
| dual_review | executor.py 中是否存在 "dual_review" 和 "pre_review" | 自动注入 |
| unified_engine | 文件存在性 + 模块可导入 | 自动修复 |

## 失效处理流程

模块异常 → mandatory_engine_alarm.txt 立即写入 → 尝试自动重启（重新注入/修复代码）→ 重启成功→状态恢复为restored → 重启失败→持续告警

## 全链路生产测试

每天10:00和22:00 cron自动执行 full_chain_test.py，验证15步：

1. Workflow 构建（deep_research模板，3 phases）
2. G0 齿轮注册
3. Workflow Runtime 创建
4. delegate_task 配置检查
5. G1 唤醒写入
6. 生产引擎通知
7. Checkpoint + SQLite 持久化
8. 数据库读写验证
9. Agent Company 匹配（117名员工）
10. preflight 代码注入验证
11. SDLC 强制注入验证
12. 双AI互审注入验证
13. adversarial_validation 代码验证
14. mandatory_engine 全模块健康检查
15. 进化候选写入

## crontab 时间覆盖

- 每分钟: gear_enforcer + wake_guide（强制引擎自检）
- 每5分钟: daemon（全模块健康扫描+联合唤醒）
- 每15分钟: cron_activate + hermes_retrospect
- 每30分钟: evolution_trigger + gear_task_validator
- 每天10/22点: full_chain_test（全链路生产验证）
- 每天18点: workflow_daily（执行汇总日报）
- 每天03点: self_evolve_cluster（全量自进化）

## 关键教训

1. **"能导入 ≠ 能运行"** — 必须在模块构建后立即验证调用路径是否真实存在
2. **双AI互审必须在任务开始时触发** — 不是事后审查，是执行中监督
3. **三路冗余不是可选** — 任意一路失效不影响整体运行
4. **强制引擎必须独立于 Hermes 主流程** — 主进程死掉它还在跑
