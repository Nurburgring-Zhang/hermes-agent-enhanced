# Cron循环 vs 中断任务的区分规则

## 问题
gear_enforcer Phase7 和 wake_guide 将 V3自我强化循环（cron `* * * * *`，每1分钟）的 gear_checkpoint 误判为"中断任务"。

## 根因
齿轮系统的 pending→running→completed→delivered 四态模型不适用于高频cron循环任务。

**区别**：
- **中断任务**：长链任务（5+步骤）、用户发起的对话级任务，有明确的开始和结束
- **循环任务**：cron `* * * * *` 或 `*/X * * * *` 级别的自强化/自检/守护，每轮快速执行后由新cron覆盖，永远不会有 completed 态

## 规则
1. `task_id` 以 `self_enhance_` 开头的 → 跳过中断检测（V3自我强化循环）
2. `round` 值超过1000的 → 大概率是循环任务（非中断）
3. 未来新增任何 `* * * * *` 级别的 cron 任务，必须在其 task_id 中加入可识别的循环标记，或在注册时标记 task_type=loop

## 已修复文件
- `gear_enforcer.py` Phase7: `if tid.startswith("self_enhance_"): return`
- `wake_guide.py`: `if tid.startswith("self_enhance_"): continue`

## 验证
查看 wake_guide.json 确认 interrupted_task=null：
```bash
python3 ~/.hermes/scripts/wake_guide.py
```
期望输出：`✅ 无中断任务`
