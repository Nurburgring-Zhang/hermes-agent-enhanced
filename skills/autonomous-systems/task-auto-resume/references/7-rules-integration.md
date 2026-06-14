# 7条规则脚注

**来源**: `~/hermes/SOUL.md §八` — 格林主人2026-05-23永久固化

## 与task-auto-resume的集成方式

task-auto-resume 的7步流程(S0-S7)直接对应7条规则：
- **S0(全面复盘)** = 规则1前半段(查文件/会话/记忆/状态)
- **S1(全局预判)** = 规则1后半段(规划+拆解)
- **S2-续跑** = 规则2(中断续跑+task_monitor每10分)
- **S3-阶段复盘** = 规则3
- **S4-全局复盘** = 规则4
- **S5-真实实现** = 规则5
- **S6-循环** = 规则6
- **S7-禁降级** = 规则7

## 三个关键bug

2026-05-24大规模审计发现的3个自毁性bug：

| Bug | 影响 | 修复方式 |
|-----|------|---------|
| compress_round传"" | 上下文压缩永不触发 | 改为读取current_context.txt |
| Phase7仅检测不恢复 | 中断任务永远卡死 | 改为3文件同步+wake_guide+meta_thinker |
| 文件一致性断裂 | recovery_pack数据矛盾 | 三重冗余+以gear_checkpoint为准 |

## 全能力激活器

`ability_activator.py` (每1小时)：
- 扫描214个scripts语法
- 激活16个evolution_v3模块  
- 激活45个agents_company模块
- 检查cron覆盖
- 输出到 `reports/ability_activation_report.json`
