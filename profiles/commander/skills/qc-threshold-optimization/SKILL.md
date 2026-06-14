---
name: qc-threshold-optimization
description: QC评分阈值优化知识。当前QC评分72.4低于80阈值，记录趋势分析和阈值调整建议
category: operations
tags: [operations, qc, quality, threshold, optimization]
---

# qc-threshold-optimization

## QC评分现状 (2026-05-08)

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

- **最新QC评分**: 72.4/100 (低于80阈值)
- **趋势**: 持续上升中 (60.5→72.4 over May 6→May 8, +11.9分)
- **趋势判定**: STABLE-IMPROVING (连续3个周期系统健康评分: 76→82→83)
- **代码质量**: 64.7（中文标点问题）
- **最近审计**: 2026-05-07 health_audit评分85/100, 但QC子系统保持warning

## 阈值调整建议

### 长期目标阈值
| 指标 | 当前值 | 目标阈值 | 优先级 |
|---|---|---|---|
| QC总分 | 72.4 | ≥80 | HIGH |
| 代码质量 | 64.7 | ≥75 | MEDIUM |
| 采集覆盖率 | 85%+ | ≥90% | MEDIUM |

### 执行动作
1. **检查中文标点问题**: agents_company/目录下的Python文件可能存在中文冒号/分号
   ```bash
   grep -rn '[\u201c\u201d\u300a\u300b\uff1a\uff1b]' /home/administrator/.hermes/agents_company/*.py
   ```
2. **生成最新QC报告**:
   ```bash
   python3 /home/administrator/.hermes/scripts/quality_check.py --full
   ```

### 自动修复QC
若QC评分连续3次低于70，触发自动修复流程：
1. 扫描agents_company/actor文件的中文标点
2. 使用patch工具替换中文标点为英文标点
3. 重新运行QC并对比分数

### 已知问题
- actors/*.py 文件较简单（14行模板代码），但实际逻辑在scripts/目录
- 主代码库质量影响评分的最大因素是agents_company/目录下的中文标点问题

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
