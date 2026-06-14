# task_monitor.py — 每10分钟任务自动监控器参考

## 位置
`~/.hermes/scripts/task_monitor.py`

## 工作原理
每10分钟由 cronjob system 触发 (`*/10 * * * *`):

### 三重中断检测
1. **wake_guide.json** — 检查 interrupted_task 字段
2. **gear_checkpoint.json** — 检查 status=running
3. **recovery_pack.json** — 检查 status=running/interrupted

### 发现中断后的恢复流程
1. 同步三份文件的 task_id 和 status — 确保一致性
2. 写入 `.resume_instruction.txt` — 供醒来读取
3. 调用 `gear_enforcer.py` — 触发Phase7自动恢复
4. 调用 `gear_task_driver.py cron` — 推动棘轮续跑
5. 调用 `wake_guide.py` — 重新生成醒来指南
6. 检查 gear_enforcer 心跳 — 30分钟无心跳尝试重启

### 输出
- `~/.hermes/reports/task_monitor_report.json` — 每次运行后的报告
- `~/.hermes/logs/task_monitor.log` — 运行日志

## 相关修复 (2026-05-23)
- gear_enforcer.py Phase7: 从"仅检测"改为"自动恢复"
- gear_context_compressor.py: 修复compress_round传空字符串bug
- gear_master.py: 增加wake_guide读环和双重保险恢复
- SOUL.md §八: 新增7条永久任务执行规则
