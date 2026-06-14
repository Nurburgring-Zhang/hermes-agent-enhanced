# 自我强化系统 — 部署验证检查清单

## V3.0 模块健康命令

```bash
# IFC信息保真核心
cd ~/.hermes/evolution_v3 && python3 information_fidelity_core.py health
# 七通道记忆引擎
python3 seven_channel_memory.py health
# DPW任务引擎
python3 task_engine.py health
# V3完整主循环
python3 self_enhancement_v3_loop.py full
# V3全系统集成测试(47项)
python3 full_system_test_v3.py
```

## 状态确认命令(旧版保留)

```bash
# 齿轮系统健康
cd ~/.hermes && python3 scripts/gear_master.py status
# 三记忆引擎健康
python3 scripts/memory_orchestrator_v3.py health
# LCM DAG完整性
python3 scripts/lcm_dag_engine.py verify
# 审计链完整性
python3 scripts/audit_logger.py verify
# 上下文管理器状态
python3 scripts/context_manager.py status
# 漂移检测日志
python3 scripts/meta_thinker.py status
```

## cron检查
```bash
crontab -l | grep -E 'gear_enforcer|self_enhance.*v3'
```
期望: gear_enforcer(* * * * *), V3-SAR(0 */6 * * *)

## 日志文件
```
~/.hermes/logs/self_enhance_v3.log      # gear_enforcer v3日志
~/.hermes/reports/self_enhance_report.json # V3运行报告
~/.hermes/evolution_v3/                   # V3模块目录
```
