# 自动调优参数调整规则 v1.0

基于复盘数据、Cron状态和关键词分布的确定性调优规则。

## 参数1: retrospect_threshold (复盘触发Skill进化阈值)

### 规则
```
if avg_score > 70:
    threshold = min(75.0, 60.0 + 5)   # 高质量 → 提高阈值
elif avg_score < 50:
    threshold = max(45.0, 60.0 - 5)   # 低质量 → 降低阈值
else:
    threshold = 60.0                   # 稳定
```

### 示例
- 平均分72.1(B良好) → 阈值=65.0（更挑剔，只触发真正需要改进的）
- 平均分41.7(D需改进) → 阈值=55.0（更敏感，多触发Skill改进）
- 平均分67.8(稳定) → 阈值=60.0（不变）

## 参数2: quality_wall_check_interval (质量墙检查间隔)

### 规则
```
if avg_score > 75:
    interval = 5    # 质量高 → 少检查（节省精力）
elif avg_score < 55:
    interval = 2    # 质量低 → 多检查（提高把控）
else:
    interval = 3    # 默认（每3步）
```

### 示例
- 平均分82(A级) → 间隔=5步（已经做得好，不必频繁检查）
- 平均分48(F级) → 间隔=2步（必须频繁纠正方向）
- 平均分67(B级) → 间隔=3步（标准节奏）

## 参数3: cron_push_frequency (每日推送次数)

### 规则
```
if cron_ok_ratio < 70:
    frequency = max(2, push_freq - 1)  # 成功率低 → 降频
elif cron_ok_ratio > 95:
    frequency = min(6, push_freq + 1)  # 成功率高 → 加频
else:
    frequency = 4                        # 默认4次(0/8/14/20)
```

### 示例
- OK率62%(11次失败/17次) → 降频至3次（减少不可靠推送）
- OK率100%(全部成功) → 加频至5次（试试更多推送点）
- OK率87%(7/8正常) → 保持4次

## 参数4: skillopt_threshold (SkillOpt验证门阈值)

### 规则
```
if avg_score > 72:
    threshold = min(0.88, 0.80 + 0.03)  # 质量高 → 提高门槛
elif avg_score < 55:
    threshold = max(0.70, 0.80 - 0.05)  # 质量低 → 降低门槛
else:
    threshold = 0.80                     # 默认
```

### 示例
- 平均分72.1(B级) → 阈值=0.83（稍微提高要求）
- 平均分41.7(D级) → 阈值=0.75（降低门槛，鼓励改进）
- 平均分67.8(B级) → 阈值=0.80（标准要求）

## 参数5: max_task_steps_before_checkpoint (检查点步数阈值)

### 规则
```
if total_retros > 10 and avg_score > 65:
    checkpoint = min(15, 10 + 2)  # 有经验+质量好 → 减少检查
elif total_retros > 10 and avg_score < 55:
    checkpoint = max(5, 10 - 3)   # 有经验+质量差 → 增加检查
else:
    checkpoint = 10                # 默认（数据不足，保持谨慎）
```

### 示例
- 15条复盘+平均分72 → 检查点=12步（经验充足，少中断）
- 15条复盘+平均分48 → 检查点=7步（需要更频繁检查）
- 4条复盘(数据不足) → 检查点=10步（保持默认）

## A/B测试对比参数

默认A/B测试创建规则：

| 参数字段 | Variant A | Variant B | 时长 |
|---------|-----------|-----------|------|
| retrospect_threshold | 55.0（更低） | 65.0（更高） | 48h |
| quality_wall_check_interval | 2（更频繁） | 5（更宽松） | 48h |
| cron_push_frequency | 3（更少） | 5（更多） | 72h |
| skillopt_threshold | 0.75（宽松） | 0.85（严格） | 48h |
| max_task_steps_before_checkpoint | 7（更频繁） | 15（更宽松） | 48h |

评估指标：A/B测试期间的平均复盘评分。更高的一方获胜。
