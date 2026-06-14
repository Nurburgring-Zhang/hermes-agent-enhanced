---
name: agent-company-mcp-bridge
description: >-
  130名员工独立MCP工具路由桥 — 为Hermes Agents Company每一位员工建立基于部门(department)+
  岗位(role)+工具集(tools.yaml)的独立工具路由(MCP桥接层)，按12个部门分发独立工具集。
  不创建完整子Agent，提供设计文档和路由框架。
version: 1.0
created: 2026-05-08
author: Hermes Agent
dependencies:
  - hermes
  - agents-company-orchestration
source: /home/administrator/.hermes/agents_company/employees/
---

# Agent Company MCP Bridge — 130员工独立工具路由

## 概述

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


Agent Company MCP Bridge 为 Hermes Agents Company 的 130 名员工 (12个部门) 建立
**基于部门+岗位的独立工具集路由系统**。每位员工根据其部门特征、tools.yaml中的工具定义、
岗位职责和能力水平获得经过筛选的 MCP 工具路由。

```
Pipeline / User Request
         │
         ▼
┌──────────────────────────────────────┐
│   Agent Company MCP Bridge           │
│   (部门路由分发层 — 不创建子Agent)    │
└──┬───┬───┬───┬───┬───┬───┬───┬───┬──┘
   │   │   │   │   │   │   │   │   │
   ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
 01   02   03   04   05   06   07   08   09...
市   设   产   研   项   开   支   工   质
场   计   品   发   目   发   持   程   量
    (各部门员工独立工具路由)
```

## 核心架构

### 1. 12部门 → MCP工具路由映射

每个部门根据其职责特征，分配不同的 MCP 工具集:

| 部门ID | 部门名 | 人数 | 核心工具 | 独有工具 | 权重工具 |
|--------|--------|------|---------|---------|---------|
| 01 | 市场营销 | 5 | web_search, data_analysis | text_processing, planning | creative |
| 02 | 设计 | 8 | creative, vision | image_gen, file_operations | web_search |
| 03 | 产品 | 4 | web_search, data_analysis | planning, text_processing | skills |
| 04 | 研发 | 6 | terminal, code_review | data_analysis, git | web_search |
| 05 | 项目管理 | 5 | planning, text_processing | session_search, skills | web_search |
| 06 | 开发 | 30 | terminal, code_review | git, skills | web_search, todo |
| 07 | 技术支持 | 20 | web_search, terminal | skills, session_search | text_processing |
| 08 | 工程架构 | 23 | terminal, code_review | skills, planning | web_search |
| 09 | 质量测试 | 8 | terminal, code_review | data_analysis | skills |
| 10 | 媒体内容 | 7 | text_processing, creative | vision, web_search | data_analysis |
| 11 | 支持行政 | 6 | text_processing, planning | skills, session_search | web_search |
| 12 | 销售 | 8 | web_search, data_analysis | text_processing, planning | skills |

### 2. 员工级别 → 工具访问范围

每位员工在 gateway_registry.json 中有 `tool_scope` 字段，定义其可访问的工具白名单:

```json
{
  "emp_01_marketing_01": {
    "tool_scope": ["web_search", "browser", "data_analysis", "text_processing"],
    "skills": ["渠道拓展", "市场调研", "需求分析", "内容营销", "团队管理"],
    "department": "市场营销部",
    "role": "市场总监"
  }
}
```

Bridge 在此基础上进一步细化，根据 department 和 role 增加**领域特定工具**:

| 部门 | tool_scope基础 | bridge增强 |
|------|---------------|-----------|
| 市场营销 | web_search, browser, data_analysis, text_processing | +planning, +creative |
| 设计 | creative, vision, text_processing | +image_gen, +file_operations |
| 产品 | web_search, browser, data_analysis | +planning, +skills |
| 研发 | terminal, code_review, data_analysis | +git, +todo |
| 项目管理 | planning, text_processing, session_search | +skills |
| 开发 | terminal, code_review, data_analysis, git | +skills, +todo |
| 技术支持 | web_search, terminal, text_processing | +skills, +session_search |
| 工程架构 | terminal, code_review, planning | +skills, +data_analysis |
| 质量测试 | terminal, code_review, data_analysis | +skills |
| 媒体内容 | text_processing, creative, web_search | +vision, +data_analysis |
| 支持行政 | text_processing, planning, skills | +session_search |
| 销售 | web_search, data_analysis, text_processing | +planning, +skills |

### 3. 岗位角色 → 工具路由微调

同一部门内不同角色有**工具路由微调**。例如市场营销部:

| 员工 | 角色 | 核心工具增强 |
|------|------|-------------|
| emp_01_marketing_01 | 傅浩轩 — 市场总监 | data_analysis(1.5x), planning(1.3x) |
| emp_01_marketing_02 | 雷思颖 — 品牌经理 | creative(1.5x), text_processing(1.3x) |
| emp_01_marketing_03 | 陶乐怡 — 内容运营 | creative(1.5x), text_processing(1.4x) |
| emp_01_marketing_04 | 徐立成 — 数据运营 | data_analysis(1.5x), web_search(1.2x) |
| emp_01_marketing_05 | 朱煜城 — 渠道经理 | web_search(1.4x), planning(1.3x) |

### 4. 员工独立工具 (tools.yaml → MCP映射)

每位员工的 tools.yaml 中定义了特定领域的专属工具名，Bridge 将其映射到 Hermes MCP 工具:

**示例: 傅浩轩 (emp_01_marketing_01)**

| tools.yaml定义 | MCP映射 | 作用域 |
|---------------|---------|-------|
| python_data_analysis | data_analysis | [pandas/numpy/scipy] |
| tableau_dashboard | vision | [dashboard/visualization] |
| cross_department_survey | text_processing | [结构化问卷/访谈] |
| strategic_modeling_toolkit | planning | [PESTEL/五力/BCG矩阵] |
| market_report_writer | text_processing | [market_report] |
| decision_support_oracle | skills | [expert consultation] |

**示例: 设计师 (emp_02_design_01)**

| tools.yaml定义 | MCP映射 | 作用域 |
|---------------|---------|-------|
| Figma | creative | [design_collaboration] |
| Notion | text_processing | [design_doc] |
| Maze | data_analysis | [user_testing] |
| Principle | creative | [prototype_animation] |
| Linear | planning | [task_management] |
| Abstract | git | [version_control] |

## 路由规则文件

### `/home/administrator/.hermes/skills/agent-company-mcp-bridge/bridge_rules.yaml`

由以下脚本生成，扫描130个employee目录并建立部门+角色路由映射。

### 自动生成脚本

**位置:** `/home/administrator/.hermes/skills/agent-company-mcp-bridge/scripts/generate_employee_bridge.py`

该脚本:
1. 遍历 `/home/administrator/.hermes/agents_company/employees/` 下 130 个目录
2. 解析每个 `identity.yaml` (获取 department, role, personality, mbti)
3. 解析每个 `tools.yaml` (获取领域专属工具清单)
4. 查 `gateway_registry.json` 确认每个员工的 tool_scope 和 agent_sub_process 配置
5. 查 `agent_tools_index.json` 确认每个员工的 MCP 工具可访问性
6. 生成部门→工具映射 + 角色→工具微调规则
7. 输出到 `bridge_rules.yaml`

## 路由执行流程

```
1. Pipeline / 用户请求 → Agent Company MCP Bridge
2. Bridge 解析请求，识别目标部门或员工ID
3. 如果是部门请求 → 按部门规则分配该部门所有员工的公共工具集
4. 如果是具体员工请求 → 加载该员工的 tools.yaml + identity.yaml
5. 根据 department→MCP 映射计算基础工具集
6. 根据 role 微调工具权重
7. 根据 tools.yaml 中的独有工具名映射到 MCP 工具+作用域
8. 返回: {
     employee_id, tools_available, tool_scopes,
     priority_scores, department_context
   }
9. 调用者按路由结果执行工具调用
```

## 路由示例

### 示例1: 请求市场分析报告 (emp_01_marketing_01 - 傅浩轩)

```
请求: "生成一份新能源汽车行业竞争格局分析"

路由决策:
  目标员工: emp_01_marketing_01 (傅浩轩 - 市场总监)
  部门: 市场营销部
  岗位角色: 市场总监 → data_analysis(1.5x), planning(1.3x)
  个人工具 (tools.yaml):
    - python_data_analysis → data_analysis(scope: pandas/numpy)
    - strategic_modeling_toolkit → planning(scope: PESTEL/五力/BCG矩阵)
    - market_report_writer → text_processing(scope: market_report)
  部门基础工具: web_search + data_analysis + text_processing + planning
  最终路由(按优先级):
    1. web_search (scope: 新能源汽车/竞争格局)
    2. data_analysis (scope: pandas/numpy) — 1.5x
    3. planning (scope: 五力模型/BCG矩阵) — 1.3x
    4. text_processing (scope: market_report)
```

### 示例2: 请求UI设计 (emp_02_design_01 - 设计师)

```
请求: "设计一个用户管理后台的UI界面"

路由决策:
  目标员工: emp_02_design_01 (设计师)
  部门: 设计部
  个人工具: Figma → creative, Maze → data_analysis
  最终路由:
    1. creative (scope: figma/prototype) — 1.5x
    2. vision (scope: design_review)
    3. web_search (scope: design_patterns)
    4. data_analysis (scope: user_testing)
```

## 使用方式

### 通过Hermes Agent调用

```python
from agent_company_mcp_bridge import CompanyMCPBridge

bridge = CompanyMCPBridge()
result = bridge.route_by_employee(
    employee_id="emp_01_marketing_01",
    request="帮我做一个Q2市场分析"
)
# result.tools = 路由后的独立工具集
# result.priority_scores = 工具优先级

# 或按部门路由
result = bridge.route_by_department(
    department="设计",
    request="需要设计一个新功能页面"
)
```

### 通过CLI查询路由

```bash
# 查看某员工工具路由
hermes bridge employee-tools --employee emp_01_marketing_01

# 查看某部门工具路由
hermes bridge dept-tools --department "市场营销部"

# 查看全景
hermes bridge dept-map
```

## 关键集成点

### 与agents-company-orchestration集成

原有的 `unified_gateway.py` 中，每个Agent有 `tool_scope` 列表，但缺乏**工具优先级和
领域特定作用域**。本Bridge通过以下方式增强:

1. **工具优先级** — 基于岗位角色的权重系数，排序工具使用顺序
2. **工具作用域** — 细化每个工具的使用范围(如 `web_search(scope: 新能源汽车)`)
3. **个人独有工具映射** — 将 tools.yaml 中的领域专用名称映射到标准 MCP 工具
4. **性格适配** — 员工的 personality 影响工具权重

### 与agent_tools_index.json集成

`agent_tools_index.json` 定义了每个员工可访问的 MCP 工具白名单(如 `web_search`, `terminal`)。
Bridge 在此基础上增加:
- 部门级别的工具增强
- 角色级别的工具微调
- 性格级别的工具权重

## 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| SKILL.md | 本文件 | 设计文档和路由框架 |
| bridge_rules.yaml | skills/agent-company-mcp-bridge/ | 自动生成的路由规则 |
| scripts/generate_employee_bridge.py | skills/agent-company-mcp-bridge/scripts/ | 路由生成脚本 |
| references/dept_mcp_mapping.yaml | skills/agent-company-mcp-bridge/references/ | 部门→MCP工具映射表 |
| references/role_tool_tuning.yaml | skills/agent-company-mcp-bridge/references/ | 角色→工具微调映射表 |

## 关键技术指标

| 指标 | 值 |
|------|-----|
| 员工总数 | 130 |
| 部门数 | 12 |
| 基础MCP工具类型 | 15 (web_search, browser, data_analysis, text_processing, vision, image_gen, creative, planning, session_search, terminal, file_operations, code_review, skills, todo, git) |
| 部门级路由规则 | 12 组 |
| 角色级微调规则 | 130 条（每位员工一条） |
| tools.yaml→MCP映射 | 每位员工 4-6 个专属工具映射 |
| 路由延迟 | < 5ms (因无子Agent创建) |

## 设计原则

1. **轻量路由** — 不创建子Agent进程，仅做工具集分发和优先级排序
2. **基于真实配置** — 完全基于 `/home/administrator/.hermes/agents_company/employees/` 的 YAML 配置和 gateway_registry.json
3. **部门+角色双层路由** — 先按部门分配基础工具，再按角色微调权重
4. **个人工具映射** — 每位员工的 tools.yaml 专属工具自动映射到 MCP 标准工具
5. **自动发现** — 扫描员工目录自动生成路由规则
6. **零侵入** — 不修改现有 gateway_registry.json / agent_tools_index.json / mcp_tools_layer.py

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
