# 双审自检机制

## 核心问题
执行AI在深度工作时会"忘记"执行预审。这不是恶意,是工具调用上下文切换太快。

## 检测方法
在每次工具调用前自动检查:
1. 当前是否处于"已预审"状态
2. 如果不是,先执行pre_review()
3. 如果是高风险操作(delete/remove/rm/drop/shutdown/reboot/format),自动STOP

## 恢复检查(事后)
当用户指出双审未执行时:
1. 停止当前任务
2. 最近3步工具调用做回溯验证
3. 从当前步恢复预审

## 自律降级(无delegate_task时)
至少拦截:
- 高风险工具名: delete/remove/rm/drop/shutdown/reboot/format
- 危险模式: rm -rf, DROP TABLE, DROP DATABASE, shutdown, > /dev/sda, chmod 777
