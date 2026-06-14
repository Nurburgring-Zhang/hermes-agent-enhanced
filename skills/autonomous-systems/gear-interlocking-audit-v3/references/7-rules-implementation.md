# 7条任务执行规则 — 固化实现参考

格林主人2026-05-23永久固化。已写入 `SOUL.md §八`。

## 实现映射

| 规则 | task_monitor实现 | gear_enforcer实现 | 执行位置 |
|------|-----------------|-------------------|---------|
| 1. 回顾+全局预判 | rule1_review_check() | 无(由Hermes在对话中执行) | SOUL.md §八规则1 |
| 2. 超限拆解+中断续跑 | check_interrupted_tasks()+recover_task() | Phase7自动恢复 | task_monitor每10min + gear_enforcer每分钟 |
| 3. 每阶段复盘 | recover_task()中记录复盘 | 中断恢复后写resume_instruction | 对话中Hermes执行 |
| 4. 完整后全局复盘 | 报告写入task_monitor_report.json | recovery_pack同步 | 对话中Hermes执行 |
| 5. 真实实现+联网+严苛测试 | rule5_gear_health_check() 多工况测试 | Phase8语法验证 | 对话中Hermes执行 |
| 6. 完善→审核→测试循环 | rule6_full_ability_scan() 全能力扫描 | 每1分钟语法验证 | 对话中Hermes+自动化 |
| 7. 禁降级 | rule7_activate_all() 真实激活验证 | Phase8文件完整性 | 对话中Hermes+自动化 |

## 3个修复的关键bug

### Bug 1: compress_round ""
**文件**: `gear_context_compressor.py` 第354行
**症状**: 永远不触发压缩 → checkpoint永远不更新 → 新旧task_id矛盾
**修复**: 改为读取 `current_context.txt` 或 `task_current.json`

### Bug 2: Phase7 仅检测不恢复
**文件**: `gear_enforcer.py` 第442行
**症状**: 检测到中断任务但只写日志
**修复**: 自动同步3份文件 + 调用wake_guide + 写入恢复指令 + 触发meta_thinker

### Bug 3: 文件一致性断裂
**文件**: `gear_enforcer.py` `get_active_task()`
**症状**: gear_checkpoint显示running但task_current显示completed → recovery_pack矛盾
**修复**: 三重冗余检测 + 以gear_checkpoint为准同步
