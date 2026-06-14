---
name: agents-company-orchestration
description: Hermes Agents Company 130人团队Multi-Agent编排架构 - 从unified_gateway.py实战提炼的完整调度模式
triggers:
  - 复杂任务需要多Agent协作
  - 需要调度130员工团队
  - 任务分解与并行执行
  - 专家系统调用
version: 1.0
created: 2026-04-24
source: unified_gateway.py实战（52494字节）
---

# Agents Company Multi-Agent Orchestration

## 核心架构

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


```
用户请求 → Unified Gateway → Task Decomposition Engine
                                    ↓
                              分解为原子任务
                                    ↓
                    ┌──────────────┼──────────────┐
                    ↓              ↓              ↓
              专项Agent子     专项Agent子     专项Agent子
              (员工角色)     (员工角色)     (员工角色)
                    ↓              ↓              ↓
                    └──────────────┼──────────────┘
                                    ↓
                         Quality Control Engine
                                    ↓
                         Business Logic Engine
                                    ↓
                            结果汇总输出
```

## 三大引擎集成

### 1. Task Decomposition Engine
```python
from task_decomposition_engine import TaskEngine
engine = TaskEngine()
task = engine.decompose("开发一个AI推荐系统")
# 返回: {plan_id, phases: [{phase_id, name, tasks: [{task_id, agent_id, skills}]}]}
```

### 2. Quality Control Engine
```python
from quality_control_engine import QualityControlEngine
qc = QualityControlEngine()
result = qc.validate_output(task_id, output, context)
# 返回: {passed, issues, suggestions}
```

### 3. Business Logic Engine
```python
from business_logic_engine import BusinessLogicEngine
bl = BusinessLogicEngine()
flow = bl.get_business_flow(request)
# 返回: {flow_id, steps: [{step_id, handler, dependencies}]}
```

## 130员工注册到Gateway

每个员工通过`AgentRegistry`注册到`UNIFIED_GATEWAY.agents`字典：
```python
gateway.agents['pm_001'] = {
    'id': 'pm_001',
    'name': '张明',
    'type': 'employee',
    'department': 'project_management',
    'personality': {...},
    'skills': [...],
    'collaboration_protocol': {...},
    'tools': [...]  # 独立Tools/MCP
}
```

每位员工都有独立的`tools`（Tools/MCP），与子Agent隔离。

## 专家系统390专家注册

```python
gateway.experts['expert_ai_nlp_001'] = {
    'id': 'expert_ai_nlp_001',
    'name': 'NLP专家',
    'domain': 'AI_NLP',
    'level': 'world_top',
    'genes': {...},
    'tools': [...],
    'collaboration_protocol': {...}
}
```

## 调度流程

```python
# unified_gateway.py核心流程
async def process_request(self, request):
    # Step 1: 任务分解
    task_plan = self.task_engine.decompose(request.user_request)
    
    # Step 2: 业务逻辑编排
    business_process = self.business_engine.start_process(request)
    
    # Step 3: 分配到正确Agent
    for phase in task_plan.phases:
        for atomic_task in phase.tasks:
            agent = self.route_to_agent(atomic_task)
            result = await agent.execute(atomic_task)
    
    # Step 4: 质量控制
    qc_result = self.qc_engine.validate_output(task_id, results)
    
    # Step 5: 汇总输出
    return self.summarize(results)
```

## 工作目录
- Gateway: `/home/administrator/.hermes/agents_company/unified_gateway.py`
- 引擎: `/home/administrator/.hermes/agents_company/task_decomposition_engine.py`
- 注册器: `/home/administrator/.hermes/agents_company/agent_registry.py`
- 业务逻辑: `/home/administrator/.hermes/agents_company/business_logic_engine.py`
- 质量控制: `/home/administrator/.hermes/agents_company/quality_control_engine.py`

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
