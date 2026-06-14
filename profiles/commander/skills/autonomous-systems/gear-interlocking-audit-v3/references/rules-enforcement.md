# 7条规则全对话生效 — gear-interlocking-audit-v3 补充参考

## 生效保证

7条永久执行规则已在以下层面与齿轮系统集成，确保所有对话生效：

### 齿轮系统层面的7规则强制

| 规则 | 齿轮组件 | cron频率 | 机制 |
|:----:|----------|:--------:|------|
| 规则1 回顾预判 | task_monitor rule1_review_check() | 每10分钟 | 全局预判+回顾检查 |
| 规则2 中断续跑 | gear_enforcer Phase7 + task_monitor | 每1分钟+每10分钟 | 3文件同步+wake_guide+恢复指令 |
| 规则3 阶段复盘 | task_monitor `rule2_interrupt_recovery` | 每10分钟 | 恢复后自动记录actions |
| 规则4 全局复盘 | gear_complete() + G0签章 | 任务完成时 | 清断点+注册中心签章 |
| 规则5 健康测试 | task_monitor rule5_gear_health_check() | 每10分钟 | 齿轮心跳+多工况测试 |
| 规则6 相互督促 | task_monitor cross_gear_verify() | 每10分钟 | G1→G2→G4→G5→G6→G7→G8链式验证 |
| 规则7 真实激活 | gear_enforcer ability_activation + task_monitor rule7 | 每1分钟+每10分钟 | 文件完整+语法正确+真实激活 |

### 验证
```bash
python3 ~/.hermes/scripts/verify_rules.py
# → 9/9 全部通过
```
