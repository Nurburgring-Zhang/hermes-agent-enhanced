# 跨会话中断恢复实战记录（2026-05-27）

## 背景
`self_enhance_1779861005` 任务在上一轮对话被切断时中断。
当前轮醒来后自动恢复并完成4个上下文脚本的部署+审核+测试。

## 实战恢复链

### Step 1: 读 wake_guide.json
```json
{
  "interrupted_task": {
    "task_id": "self_enhance_1779861005",
    "next_action": "continue_closed_loop",
    "detail": "链完整: 3521条通过"
  },
  "ai_scoring_pending": 21027,
  "push_today": 108,
  "gear_health": "healthy",
  "actions_required": [
    "🔄 恢复中断任务: self_enhance_1779861005 → continue_closed_loop",
    "⭐ AI评分: 21027条待评分"
  ]
}
```

### Step 2: 读 gear_checkpoint.json
```json
{
  "task_id": "self_enhance_1779861005",
  "round": 1005,
  "step": "audit_chain",
  "detail": "链完整: 3521条通过",
  "next_action": "continue_closed_loop",
  "status": "running"
}
```

### Step 3: 确认cron状态
检查 `crontab -l` 确认上下文脚本是否已部署。
未部署？→ 直接加到crontab。
已部署但无日志？→ `tail -3 logs/xxx.log` 验证。

### Step 4: 推断实际需要做什么
根据 detail "链完整: 3521条通过" + next_action "continue_closed_loop"：
- 上次在做 self_enhance 增强循环
- "链完整"是指齿轮链或上下文链验证通过
- next_action 是继续闭环
- 但上次还有"补全能力+多轮测试"的用户要求未完成
- 所以实际恢复时：先部署cron → 再做测试

## 关键教训
1. **wake_guide.json 只显示中断任务，不显示完整上下文** — 需要通过 gear_checkpoint 的 step + detail 联想任务内容
2. **被中断的不一定是主任务** — wake_guide 可能显示的是后台循环任务（self_enhance_circle_loop），而实际需要恢复的是用户要求的"补全能力"的需求
3. **规则2要求不等用户指令** — 但复杂情况下可能需要根据 detail 和 next_action 判断优先级
4. **所有部署的cron脚本必须验证日志输出** — 即使crontab添加成功，也要等一轮（~1分钟）后看日志才能确认正常运行
