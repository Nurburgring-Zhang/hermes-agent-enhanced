# Dynamic Workflows ↔ 生产可靠性引擎桥接

## 对接点

### 1. G6 验证 — workflow完成时触发生产验证

`workflows/gear_integration.py` 的 `run_validator()` 在 workflow 完成时自动调用：
- 验证完整性：所有阶段是否完成
- 验证正确性：结果是否经验证
- 验证一致性：各阶段输出是否对齐
- 验证质量：是否符合执行标准

调用位置：`runtime.py` finally块（workflow完成后，复盘之前）
调用方式：`await gear_integration.run_validator(workflow_name, phase_results)`

### 2. 生产监控 — workflow写入production_monitor.json

```python
gear_integration.notify_production_loop(workflow_id, status, phase_name, error)
```

在以下时机自动写入：
- workflow启动时 → `notify_production_loop(wf.id, "running", first_phase_name)`
- workflow完成时 → `notify_production_loop(wf.id, status.value, error=error)`

### 3. daemon.py — 守护进程作为G8增强

`workflows/daemon.py` 每5分钟执行一次，写入 `reports/production_monitor.json`：
```json
{
  "source": "workflow_daemon",
  "type": "heartbeat",
  "ts": "...",
  "modules_healthy": 16,
  "modules_total": 16,
  "pending_workflows": 0,
  "running_workflows": 0
}
```

### 4. 降级检测配合

production-reliability-engine 的 `DegradationPreventer` 可在 workflow 的异常阶段被调用。
当前未自动对接——降级检测仍然只适用于对话级任务，尚未注入到 workflow 的 phase 执行中。
需扩展：在 `scheduler.py` 的每个 task 执行前/后插入 DegradationPreventer 检查。

## 当前状态

| 对接点 | 状态 | 位置 |
|--------|------|------|
| G6验证 | ✅ 已对接 | gear_integration.py run_validator() |
| 生产监控 | ✅ 已对接 | gear_integration.py notify_production_loop() |
| daemon健康心跳 | ✅ 已对接 | daemon.py → production_monitor.json |
| 降级检测注入workflow | 🔴 待对接 | scheduler.py |
| CriticAgent审核workflow | 🔴 待对接 | runtime.py完成后 |
