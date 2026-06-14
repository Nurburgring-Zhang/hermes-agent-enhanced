---
name: expert-system-mcp-bridge
description: >-
  390名专家独立MCP工具路由桥 — 为Hermes Expert System每一位专家建立基于domain+department的
  独立工具集路由(MCP桥接层)，根据expert_XXX/identity.yaml + tools.yaml自动分配工具权限。
  不创建完整子Agent，仅提供设计文档和路由框架。
version: 1.0
created: 2026-05-08
author: Hermes Agent
dependencies:
  - hermes
  - expert-system
source: /home/administrator/.hermes/agents_company/experts/
---

# Expert System MCP Bridge — 390专家独立工具路由

## 概述

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


Expert System MCP Bridge 是一个**轻量路由层**，为 Hermes Expert System 的 390 位专家建立
**独立工具集(MCP Tools)路由**。每个专家根据其领域(domain)、工具集(tools.yaml)和
性格基因自动获得经过筛选的工具权限，由路由桥统一分发。

```
Hermes Agent/User Request
         │
         ▼
┌─────────────────────────────────────┐
│   Expert System MCP Bridge          │
│   (路由分发层 — 不创建子Agent)       │
└──────────┬──────────────────────────┘
           │
    ┌──────┼────────┬────────┬────────┐
    ▼      ▼        ▼        ▼        ▼
expert_001 expert_002 ... expert_389 expert_390
  │          │                  │          │
  │工具路由   │工具路由           │工具路由    │工具路由
  ▼          ▼                  ▼          ▼
[PyTorch]  [Transformers]     [GIS]      [科技史]
[W&B]      [BERT/GPT]         [遥感]      [档案/文献]
[arXiv]    [NLP工具链]         [空间分析]   [跨文化比较]
```

## 核心架构

### 1. 路由决策引擎

对390个专家目录进行扫描，为每位专家生成一个**工具路由规则**:

```python
# bridge_rules.yaml 自动生成格式
expert_001:        # 深度学习架构师 — 鲁思慧
  domain: AI与机器学习
  personality: 深度思考者
  tools:
    read_write: ["PyTorch/JAX/HuggingFace", "Weights & Biases / MLflow", "Slurm/Kubernetes集群"]
    read_only:  ["arXiv / PapersWithCode"]
    mcp_mapped:  # 映射到Hermes原生MCP工具
      - tool: web_search
        scope: [arxiv, paperswithcode, huggingface]
      - tool: terminal
        scope: [python, pytorch, jax]
      - tool: code_review
        scope: [ml_model, training_pipeline]
    
expert_141:       # SRE实践专家 — 杜雨泽
  domain: DevOps与SRE
  personality: 连接者
  tools:
    read_write: ["Prometheus/Grafana", "ELK Stack", "PagerDuty/OpsGenie"]
    read_only:  ["SLO仪表盘", "故障库"]
    mcp_mapped:
      - tool: web_search
        scope: [sre_patterns, incident_response]
      - tool: terminal
        scope: [shell, kubectl, promql]
      - tool: data_analysis
        scope: [sli_analysis, error_budget]
```

### 2. 30域 → MCP工具映射规则

| 域 | 通用工具路由 | 独有MCP工具 |
|----|-------------|------------|
| AI与机器学习(30人) | web_search(arxiv/paper) + terminal(python/pytorch) | code_review, data_analysis |
| 软件工程(20人) | terminal(git/build) + code_review | git, todo |
| 通信与网络(15人) | web_search + terminal(network) | vision(diagram) |
| 质量与测试(15人) | web_search + code_review | terminal(test) |
| 安全与隐私(15人) | web_search(cve) + terminal(security) | code_review, file_operations |
| 云计算与基础设施(15人) | web_search + terminal(cloud) | skills |
| DevOps与SRE(15人) | terminal(shell/promql) + web_search | code_review |
| 前端与用户体验(15人) | web_search + creative | vision, skills |
| 产品与商业(15人) | web_search + data_analysis | planning |
| 数据与存储(15人) | terminal + data_analysis | file_operations |
| 管理与沟通(15人) | web_search + planning | text_processing |
| 移动与IoT(15人) | terminal + web_search | code_review |
| 艺术与设计(10人) | creative + vision | image_gen |
| 内容与创意(10人) | text_processing + creative | session_search |
| 能源与环保(10人) | web_search + data_analysis | terminal |
| 经济与金融(10人) | data_analysis + web_search | terminal |
| 生物与医学(10人) | web_search(pubmed) + data_analysis | terminal |
| 物理与材料(10人) | web_search + data_analysis | terminal |
| 法律与伦理(10人) | web_search + text_processing | session_search |
| 汽车与交通(10人) | web_search + data_analysis | terminal |
| 机器人与自动化(10人) | terminal + web_search | code_review |
| 教育与培训(10人) | text_processing + planning | creative |
| 心理学与认知(10人) | web_search + data_analysis | text_processing |
| 地理与空间(10人) | web_search + data_analysis | vision |
| 哲学与人文(10人) | web_search + text_processing | session_search |
| 区块链与Web3(10人) | web_search + terminal | code_review |
| 供应链与物流(10人) | web_search + data_analysis | planning |
| 数学与理论(15人) | data_analysis + terminal | text_processing |
| 行业垂直(15人) | web_search + data_analysis | planning |
| AI Advanced(15人) | web_search + terminal | code_review, skills |
| 语言与翻译(15人) | web_search + text_processing | creative |
| 心理学与认知(10人) | web_search + data_analysis | text_processing |

### 3. 性格基因 → 工具偏好权重

15种性格基因对工具有不同**优先级权重**:

| 性格 | 首选工具 | 次选工具 | 权重系数 |
|------|---------|---------|---------|
| 连接者 | session_search | web_search | 1.3x |
| 质疑者 | code_review | web_search | 1.2x |
| 执行力爆表 | terminal | todo | 1.5x |
| 极致审美 | creative | vision | 1.4x |
| 共情高手 | text_processing | planning | 1.2x |
| 沟通大师 | text_processing | session_search | 1.3x |
| 细节强迫症 | code_review | data_analysis | 1.4x |
| 深度思考者 | data_analysis | planning | 1.3x |
| 实战派 | terminal | todo | 1.4x |
| 战略视野强 | planning | data_analysis | 1.3x |
| 稳重可靠 | planning | todo | 1.2x |
| 创新狂人 | creative | web_search | 1.4x |
| 系统思考者 | data_analysis | planning | 1.3x |
| 速度型选手 | terminal | todo | 1.5x |
| 完美主义者 | code_review | creative | 1.3x |

### 4. 路由执行流程

```
1. 用户/Agent请求 → Expert System MCP Bridge
2. Bridge解析请求中的domain关键词或明确expert_id
3. 加载对应expert_XXX/identity.yaml + tools.yaml
4. 根据domain映射规则 + 性格权重计算工具优先级
5. 返回: {tools_available, tool_scopes, routing_rules, priority_scores}
6. 调用者按优先级使用路由结果执行工具调用
```

## 路由规则文件

### `/home/administrator/.hermes/skills/expert-system-mcp-bridge/bridge_rules.yaml`

由以下脚本生成，扫描390个expert目录并建立路由映射:

```bash
# 生成命令 (放置于cron或按需执行)
cd /home/administrator/.hermes/agents_company
python3 generate_expert_bridge_rules.py
```

### 自动生成脚本 (参考)

**位置:** `/home/administrator/.hermes/skills/expert-system-mcp-bridge/scripts/generate_expert_bridge.py`

该脚本:
1. 遍历 `/home/administrator/.hermes/agents_company/experts/` 下 390 个目录
2. 解析每个 `identity.yaml` (获取 personality, domain, level)
3. 解析每个 `tools.yaml` (获取工具路由列表)
4. 查 `agent_tools_index.json` 确认该专家的 Hermes MCP 工具可访问性
5. 结合 domain→MCP 映射表和性格权重表，生成完整路由规则
6. 输出到 `bridge_rules.yaml`

## 路由示例

### 示例1: 请求深度架构咨询 (expert_001 - 鲁思慧)

```
请求: "帮我设计一个视觉Transformer架构"

路由决策:
  目标专家: expert_001 (深度学习架构师)
  域映射: AI_ML → web_search(arxiv/paper) + terminal(python/pytorch) + code_review
  性格偏好: 深度思考者 → data_analysis + planning (1.3x)
  最终工具集(按优先级):
    1. web_search (scope: arxiv/paperswithcode) — 论文调研
    2. terminal (scope: python/pytorch) — 原型实现
    3. data_analysis — 实验分析
    4. code_review — 代码审查
```

### 示例2: 请求Web3合约审计 (expert_351 - 安昱辰)

```
请求: "审计这个Solidity智能合约"

路由决策:
  目标专家: expert_351 (智能合约专家)
  域映射: Blockchain_Web3 → web_search + terminal + code_review
  性格偏好: 深度思考者 → data_analysis + planning (1.3x)
  最终工具集:
    1. code_review — 合约代码审查
    2. terminal (scope: solidity/forge) — 编译测试
    3. web_search — 安全事件查询
    4. data_analysis — gas成本分析
```

## 使用方式

### 通过Hermes Agent调用

```python
from expert_system_mcp_bridge import ExpertMCPBridge

bridge = ExpertMCPBridge()
# 自动路由到合适的专家，并带上它的工具集
result = bridge.route(
    request="请分析这个深度学习模型的可解释性",
    expert_id="expert_016"  # 彭哲瀚 — AI可解释性专家
)
# result.tools = 经过路由过滤的独立工具集
# result.priority_scores = 工具优先级排序
```

### 通过CLI查询路由

```bash
# 查看某个专家的工具路由
hermes bridge expert-tools --expert expert_001

# 查看某个域的工具路由
hermes bridge domain-tools --domain "AI与机器学习"
```

## 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| SKILL.md | 本文件 | 设计文档和路由框架 |
| bridge_rules.yaml | skills/expert-system-mcp-bridge/ | 自动生成的路由规则 |
| scripts/generate_expert_bridge.py | skills/expert-system-mcp-bridge/scripts/ | 路由生成脚本 |
| references/domain_mcp_mapping.yaml | skills/expert-system-mcp-bridge/references/ | 域→MCP工具映射表 |
| references/personality_tool_weights.yaml | skills/expert-system-mcp-bridge/references/ | 性格→工具权重表 |

## 关键设计原则

1. **轻量路由，不创建子Agent** — 仅做工具集分发，不实例化完整子Agent进程
2. **基于真实配置** — 完全基于 `/home/administrator/.hermes/agents_company/experts/expert_XXX/` 的 YAML 配置
3. **自动发现** — 扫描专家目录自动生成路由规则，新专家加入无须手动配置
4. **性格感知** — 不同性格基因影响工具优先级，使专家工作风格更真实
5. **域感知** — 30个域各有不同的 MCP 工具组合
6. **可扩展** — 添加新专家或新工具时只须更新配置，不需要改路由代码

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
