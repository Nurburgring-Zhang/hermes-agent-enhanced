---
name: skills-orchestration-engine
description: 构建Skills组合/并行/链式/组队/流水线编排引擎，让343个skill像Agent Company一样可编排执行
category: autonomous-systems
tags: [orchestration, skills, workflow, DAG, parallel]
---

# Skills Orchestration Engine

创建完整的skills编排引擎，包括6大模块。

## 目录结构

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


```
~/.hermes/orchestrate/
├── __init__.py      — 统一导出
├── types.py         — 核心类型(SkillMeta, WorkflowNode, WorkflowGraph, NodeType, ChainMode)
├── discovery.py     — 技能发现与注册中心(扫描SKILL.md→skill_registry.json)
├── graph.py         — DAG图构建器(链式/并行/条件/流水线/拓扑排序/YAML)
├── executor.py      — 执行器(串行/并行/条件/团队/循环+delegate_task)
├── engine.py        — 引擎入口(run_workflow/chain/parallel)
└── composer.py      — 智能组合器(auto_compose/compose_team/dynamic)
```

## 关键步骤

### 1. types.py — 核心类型
- `SkillMeta`: name, description, category, tags, inputs/outputs, priority, compatibility, parallel_capable, chain_capable
- `WorkflowNode`: id, type(INPUT/OUTPUT/SKILL/PARALLEL/CONDITIONAL/CHAIN/TEAM/LOOP), skill_name, children/parents, condition
- `WorkflowGraph`: 支持add_node/add_edge/validate, 拓扑排序

### 2. discovery.py — 注册中心
- 扫描 ~/.hermes/skills/**/SKILL.md
- 解析YAML frontmatter + 启发式回退
- SkillRegistry类: get_skill(), get_skills_by_category(), get_skills_by_tags()
- **注意**: 内部用 `_skills` 属性

### 3. graph.py — DAG构建
- `build_chain/parallel/conditional/pipeline` 
- `validate_graph/topological_sort/merge_graphs`
- YAML持久化 (create/save_workflow_from/to_yaml)

### 4. executor.py — 执行
- SkillsExecutor: `_execute_node()` 分派6种NodeType
- PARALLEL用ThreadPoolExecutor并发
- 返回WorkflowResult + execution_plan

### 5. engine.py — 入口
- SkillsOrchestrator单例: run_workflow/chain/parallel/conditional
- recommend() 技能推荐

### 6. composer.py — 组合器
- auto_compose: 检测任务类型→自动构建工作流
- compose_team: 团队协作图

## 已知陷阱
- SkillRegistry用`_skills`属性(不是skills)
- execute_graph是SkillsExecutor方法不是模块函数
- 重复skill名时按目录深度优先
- **类别索引 vs 工作流Skill**: 顶级目录的SKILL.md（如`mlops/mlops`、`github/github`）是参考文档，不是可执行工作流。编排时应该跳过这些。检测方法：`len(rel.parts) == 2` 或父目录名==类别名。2026-05-29全量扫描发现179个未通过验证门的Skill中，158个是这种类别索引。
- **DB schema不匹配**: `memory_scene.tags`(不是`keywords`)、`memory_scene.last_activated`(不是`updated_at`)、`memory_profile.dimensions`+`summary`。每次脚本改动后运行`orchestrator.py audit`。
- **llm_bridge统一调用**: 用`scripts/llm_bridge.py`的`llm_call_json()`/`llm_call()`/`llm_simple()`，不用原始`urllib.request`。`delegate_task`在cron上下文中不可用。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
