# 分层增强计划模板（P0-P3）

用于"大规模系统增强"类任务。将改进项按紧迫性和实施顺序分层。

## 分层原则

| 层级 | 时间范围 | 实施内容 | 测试要求 |
|------|---------|---------|---------|
| **P0** | 本轮对话 | 基础架构层增强（监控/路由/反馈） | 每模块单独测试 |
| **P1** | 本周 | 核心流程强化（规划/检查点/分层） | 集成测试 |
| **P2** | 下周 | 质量体系（门禁/清单/复盘） | 全链路测试 |
| **P3** | 后续 | 高级进化（Reflexion/GEPA/经验/清理） | 长期运行验证 |

## P0项检查清单

- [ ] 能独立于其他模块运行吗？
- [ ] 是否注入现有齿轮/cron系统？
- [ ] 是否修改了核心执行循环？如果没有，是否足够？
- [ ] 与现有模块会冲突吗？
- [ ] 有独立测试脚本验证吗？
- [ ] 是否需要备份现有文件？

## 增强计划文档结构

```markdown
### P0-N: 名称

**背景：** 为什么需要改（引用调研来源）
**实现路径：**
| 文件 | 改动 |
|------|------|
| path/to/file.py | 具体改动 |

**验证方法：**
- 命令或测试

**优先级：** P0 | **估算：** 2h
```

## 本对话实战清单

2026-06-01 全系统底层增强已完成：

| 分层 | 模块 | 文件路径 |
|------|------|---------|
| P0 | 监控层引擎 | `agent/monitor.py` |
| P0 | 反思层引擎 | `agent/reflector.py` |
| P0 | 模型路由 | `agent/model_router.py` |
| P0 | 进度工具 | `tools/progress_tool.py` |
| P1 | 6页纸Skill | `skills/hermes/six-page-plan/SKILL.md` |
| P1 | 检查点 | `scripts/checkpoint_recorder.py` |
| P1 | 分层规划 | `scripts/layered_planner.py` |
| P2 | TR门禁 | `scripts/tr_gate.py` |
| P2 | DoD清单 | `scripts/dod_checklist.py` |
| P2 | 三轮复盘 | `scripts/hermes_retrospect.py`(修改) |
| P3 | Reflexion | `scripts/reflexion_engine.py` |
| P3 | GEPA变异 | `scripts/gepa_variator.py` |
| P3 | 经验引擎 | `scripts/experience_extractor.py` |
| P3 | AutoClean | `scripts/auto_cleaner.py` |
| 测试 | 全链路 | `scripts/test_all_enhancements.py` |
| 齿轮 | 集成监控 | `scripts/gear_enforcer.py`(修改) |
