# 三层认知架构增强 (2026-06-01)

## 架构概览

在G1齿轮循环中注入三层架构，实现**执行层→监控层→反思层**分离：

```
Gear Enforcer 每1分钟循环
  │
  ├─ Phase 0/8: 监控层评估 (MonitorEngine)
  │   ├─ 进度监控 — 当前步数 vs 预算
  │   ├─ 错误率监控 — 连续失败检测 (阈值: 3次/阶段 或 30%)
  │   ├─ 时间预算预警 — >120分钟触发CHECKPOINT
  │   ├─ 退化检测 — 性能下降>20%
  │   └─ 循环检测 — 连续5步无进展→RECOVER
  │   │ 输出信号: CONTINUE / CHECKPOINT / REFLECT / RECOVER / ABORT
  │
  ├─ Phase 0b: 反思层 (ReflectorEngine)
  │   └─ 当监控层信号=REFLECT/RECOVER时自动触发
  │      ├─ R1 执行复盘: 错误分类(syntax/logic/environment/resource)
  │      ├─ R2 策略复盘: 工具效率/执行顺序/资源使用评分
  │      └─ R3 元认知复盘: 模式库匹配+历史趋势+系统性改进建议
  │
  └─ 正常V3循环继续 (Phase 1-7)
```

## 关键部署文件

| 组件 | 路径 | 功能 |
|------|------|------|
| MonitorEngine | `agent/monitor.py` | 5维度监控引擎, MonitorSignal枚举(CONTINUE/CHECKPOINT/REFLECT/RECOVER/ABORT) |
| ReflectorEngine | `agent/reflector.py` | 三轮反思引擎, 含pattern_db错误模式库 |
| ModelRouter | `agent/model_router.py` | 三梯队模型路由(E0=flash/E1=chat/E2=pro) |
| ProgressTracker | `tools/progress_tool.py` | 进度反馈工具(步骤/里程碑/阶段/ETA) |
| gear_enforcer.py | `scripts/gear_enforcer.py` | 注入Phase 0/8监控层调用 |

## 模型路由策略

| 梯队 | 模型 | 复杂度上限 | 适用任务 |
|:----:|------|:----------:|----------|
| E0 (value) | deepseek-v4-flash | ≤0.3 | 简单检索/状态查询/单步操作 |
| E1 (balanced) | deepseek-chat | ≤0.7 | 常规开发/修复/分析 (当前默认) |
| E2 (performance) | deepseek-v4-pro | >0.7 | 复杂推理/长链/高精度要求 |

可用task_type辅助: query/status→E0, fix/research/push→E1, develop/review/evolve→E2

## 进度反馈协议

- 长任务每轮结束后: `progress_report("step", "当前步骤描述")`
- 关键节点: `progress_report("milestone", "节点名称")`
- 阶段切换: `progress_report("phase", "阶段名称")`
- 状态查询: `progress_report("status", "")` → 返回可读摘要
- 完整报告: `progress_report("report", "")` → 返回可推送完整报告
- 持久化: `progress_report("persist", "")` → 写入 `reports/progress_{task_id}.json`

## P1-P3增强模块

### P1: 全局规划与长程任务
| 文件 | 功能 |
|------|------|
| `scripts/checkpoint_recorder.py` | 每5步结构化检查点+中断恢复+task_current同步 |
| `scripts/layered_planner.py` | L1目标层→L2策略层→L3执行层递进规划 |
| `skills/hermes/six-page-plan/SKILL.md` | Amazon式任务前分析模板 |

### P2: 质量把控与审核
| 文件 | 功能 |
|------|------|
| `scripts/tr_gate.py` | IPD TR1-TR6六道质量门禁 |
| `scripts/dod_checklist.py` | 4类任务强制DoD清单 |
| `scripts/hermes_retrospect.py` (已修改) | 三轮复盘强化(执行/策略/元认知) |

### P3: 自我进化与能力增强
| 文件 | 功能 |
|------|------|
| `scripts/reflexion_engine.py` | 复盘<60自动触发Actor→Evaluator→Reflector三角循环 |
| `scripts/gepa_variator.py` | 5种遗传变异(加/删/替/参数/交叉)+A/B测试队列 |
| `scripts/experience_extractor.py` | 轨迹→模板→参数化→验证→入库自动经验提炼 |
| `scripts/auto_cleaner.py` | 错误/过时/重复三种检测+软删除 |

## 验证方法

```bash
# 监控层测试
python3 agent/monitor.py test

# 反思层测试
python3 agent/reflector.py test

# 模型路由测试
python3 agent/model_router.py test

# 进度工具测试
python3 tools/progress_tool.py

# 全链路测试
python3 scripts/test_all_enhancements.py
```
