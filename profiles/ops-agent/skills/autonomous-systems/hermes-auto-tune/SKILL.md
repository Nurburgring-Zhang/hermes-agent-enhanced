---
name: hermes-auto-tune
description: 自动调优系统 — 参数自适应(5项核心参数)+A/B测试+动态阈值。基于复盘平均评分/Cron成功率/关键词分布自动调整系统参数。规则引擎驱动，零LLM成本。集成到自进化集群模块8，每天03:00自动运行。
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags: [auto-tune, parameter-adaptation, ab-testing, dynamic-thresholds, self-optimization]
triggers:
  - "自动调优"
  - "auto tune"
  - "参数自适应"
  - "A/B测试"
  - "动态阈值"
  - "系统调优"
  - "参数调整"
  - "tune parameters"
  - "hermes_auto_tune"
  - "自进化集群模块8"
  - "模块8"
---

# Hermes 自动调优系统

## Overview

自动调优系统，基于复盘平均评分、Cron成功率、关键词分布自动调整5项核心参数。所有调优决策基于规则引擎，零LLM成本。集成到自进化集群模块8，每天03:00自动运行。

**底层能力声明**: 系统参数自动适应运行数据。调优是底层能力，所有参数全面覆盖，完全自动执行。规则已固化到AGENTS.md（格林主人最高指令 2026-05-31固化）。

## 可调优参数

| 参数 | 默认值 | 范围 | 调优逻辑 |
|------|--------|------|----------|
| `retrospect_threshold` | 60.0 | 30-80 | 平均评分>70→上调至75，<50→下调至45 |
| `quality_wall_check_interval` | 3步 | 1-10 | 评分>75→放宽至5步，<55→收紧至2步 |
| `cron_push_frequency` | 4次/天 | 2-6 | Cron成功率<70%→降频 |
| `skillopt_threshold` | 0.80 | 0.60-0.95 | 评分>72→上调至0.88，<55→下调至0.70 |
| `max_task_steps_before_checkpoint` | 10步 | 5-20 | 更多任务数据→更精确检查点 |

## 工具命令

```bash
# 分析当前系统参数状态（含复盘/Cron/关键词分布）
python3 scripts/hermes_auto_tune.py analyze

# 执行参数调优（分析+调整+保存）
python3 scripts/hermes_auto_tune.py tune

# 创建或评估A/B测试
python3 scripts/hermes_auto_tune.py ab-test

# 输出当前调优参数
python3 scripts/hermes_auto_tune.py report
```

## 架构

```python
scripts/hermes_auto_tune.py
├── SystemAnalyzer         # 模块1: 分析器
│   ├── analyze_retrospects()  — 复盘记录 → 平均分/低分比例/趋势
│   ├── analyze_keywords()     — 关键词权重 → 分布/重平衡需求
│   ├── analyze_cron()         — Cron状态 → 成功率/暂停数
│   └── analyze_all()          — 综合分析
├── AutoTuner              # 模块2: 调优执行器
│   ├── compute_adjustments()  — 规则引擎调优决策
│   ├── apply_adjustments()    — 约束后保存
│   └── load_saved_params()    — 读取已保存参数
└── ABTestRunner           # 模块3: A/B测试框架
    ├── create_test()          — 创建参数对比实验
    └── evaluate_test()        — 48小时后评估效果
```

## 调优决策引擎（规则引擎，零LLM）

所有调优决策基于确定性规则，不使用LLM：

```python
# 示例：复盘阈值调整
def compute_retrospect_threshold(avg_score):
    if avg_score > 70:
        return min(75.0, 60.0 + 5)   # 质量高→提高阈值
    elif avg_score < 50:
        return max(45.0, 60.0 - 5)   # 质量低→降低阈值
    return 60.0                       # 不变
```

## A/B测试框架

```python
runner = ABTestRunner()

# 创建测试：比较两种复盘阈值
test = runner.create_test(
    param_name="retrospect_threshold",
    variant_a=55.0,       # 对照组
    variant_b=65.0,       # 实验组
    duration_hours=48     # 48小时后评估
)

# 评估测试结果
result = runner.evaluate_test(test["id"])
if result and result["winner"]:
    # 应用赢家参数
    apply_adjustments({test["param"]: result[f"variant_{result['winner']}"]})
```

## 关联技能

- `task-retrospect` — 复盘数据是调优决策的主要输入源
- `hermes-skill-evolver` — Skill进化引擎的输出可作为参数调优的反馈信号
- `production-reliability-engine` — Cron状态是调优决策的输入之一
- `self-evolution-executor` — 自进化执行器在P3步骤中可运行调优

## 实战陷阱（2026-05-30发现）

### 1. 数据量小时保持默认
当复盘记录<5条时，调优系统不建议调整任何参数。平均分67.8(4条) → 保持默认值。需要足够数据量才能做出有意义的调整。

### 2. A/B测试的duration选择
默认48小时足够采集到稳定的效果数据。太短(<24h)会被短期波动干扰，太长(>72h)会延缓改进速度。

### 3. 参数约束避免极端值
每个可调优参数都有硬性范围约束(min/max)。调优输出总是被约束在范围内，避免极端值导致系统异常。

## 数据存储

- 当前参数: `reports/auto_tune/current_params.json`
- 调优报告: `reports/auto_tune/tune_<timestamp>.json`
- A/B测试记录: `reports/auto_tune/ab_tests.json`
- 当前参数详解: `references/current-parameters.md` (含决策逻辑和A/B测试用法)

## 回滚方案

重置所有参数为默认值：
```bash
rm ~/.hermes/reports/auto_tune/current_params.json
# 下次运行时自动使用默认值
```
