---
name: agent-driven-master-loop
description: 全自主9步主控循环 — 使用delegate_task调度子Agent完成情报采集→评分→分析→设计→架构→规划→推送→记忆→审计的全链路闭环
trigger: Cron定时任务或用户请求"运行全能主控循环"
---

# Hermes 全能主控循环 (Agent-Driven Master Loop)

## 触发条件
- 每天定时cron执行
- 用户显式要求"运行全能主控循环"

## 本循环实战数据 (2026-05-08)
- **采集量**: 26条 → 清洗后Top8高分 (上次)
- **最高分(本次)**: 90分 (AI攻击机器人攻破GitHub Actions) / (上次)114分 (UC Berkeley)
- **产品需求(本次)**: AI-Safe Guard (企业AI编程安全审计) + AgentOps Hub (多Agent协作编排)
- **技术架构(本次)**: Go+Python双语言 + K8s + vLLM推理 + Temporal Workflow + PostgreSQL
- **项目计划(本次)**: 4 Phase / 36周 / ¥1,235万预算
- **推送**: 30条候选 (P0:7条, P1:13条, P2:10条)
- **审计评分**: 13/15 (平均) — 全部11个文件完整，无退化
- **StructMem**: Event #5 已存储, 4个未整合事件
- **关键经验**: 统一输出路径到 agent_driven/；子Agent输出限200-300行避免截断；Step1采集超时时重试需降低搜索轮次；StructMem在父Agent直接执行

## 工作流

### 前置操作
```bash
mkdir -p /home/administrator/.hermes/outputs/agent_driven/
```

### 步骤1: 全平台信息采集
使用 `delegate_task` 调度采集Agent：
- 工具集: `["web","file","search"]`
- max_iterations: 40
- Goal: "搜索采集20条最新科技情报"
- Context: 包含输出路径、搜索源列表、JSON格式要求
- **注意**：如果首次超时（300s），重试时要求子Agent更聚焦，减少搜索次数

### 步骤2: AI清洗与评分
使用 `delegate_task` 调度评分Agent：
- 工具集: `["file","web"]`
- 读取 raw_intelligence.json
- 六维评分（稀缺性/影响力/技术深度/时效性/偏好匹配/可信度，每项1-10分）
- 总分>36为高通，筛选至少5条
- 输出 scored_intelligence.json

### 步骤2.5: 多Agent交叉审核 (AutoResearch融合)
在六维评分之后，引入AutoResearch多Agent交叉审核方法论，对评分结果和关键产出物进行双重验证，确保情报质量和代码级严谨性。

#### 2.5.1 五维度代码质量标准评分
在六维评分之上，新增五维度加权评分体系（0.0-1.0），用于评估产出物的代码/数据质量：

| 维度 | 权重 | 评估要点 |
|------|------|----------|
| 正确性 | 35% | 逻辑完整、边界处理、错误处理、类型安全 |
| 测试质量 | 25% | 覆盖完整、独立可重复、断言有效 |
| 代码质量 | 20% | 结构清晰、命名语义化、DRY原则、类型注解 |
| 安全性 | 10% | 无硬编码密钥、参数化查询、输入消毒 |
| 性能 | 10% | 算法复杂度合理、无N+1、内存使用适当 |

**综合评分公式：**
```
final_score = correctness × 0.35 + test_quality × 0.25 +
              code_quality × 0.20 + security × 0.10 + performance × 0.10
```

**评级阈值：**
- ✅ >= 0.90 优秀 — 直接进入下一阶段
- ✅ >= 0.80 良好 — 建议修复次要问题
- ⚠️ >= 0.65 合格 — 需修复后重新审核
- ❌ < 0.65 不合格 — 需大幅修改后重新审核

#### 2.5.2 双Agent角色轮换机制
使用两个独立 `delegate_task` 调用，交替担任实现者和审核者：

```yaml
角色轮换规则:
  奇数轮: Agent A 实现/修复 → Agent B 独立审核
  偶数轮: Agent B 实现/修复 → Agent A 独立审核
  核心原则: 审核者与实现者绝对隔离，不共享实现上下文
```

**Implementer Agent 模板：**
```python
delegate_task(
    goal="Implement/修复评分输出 — Round N",
    context=f"""
    ROLE: Implementer
    ROUND: {round_number}
    
    REQUIREMENTS:
    读取 scored_intelligence.json，根据审核反馈进行优化
    确保所有修复通过完整性验证
    
    PREVIOUS REVIEW FEEDBACK (round {round_number - 1}):
    [上一轮审核报告中的阻塞性和建议性问题]
    
    OUTPUT: outputs/agent_driven/cross-review/round-{round_number}/
    
    CONSTRAINTS:
    - 所有public函数必须有测试
    - 测试覆盖 >= 70%
    - 函数长度 <= 60行
    - 文件长度 <= 500行
    - 类型注解必须完整
    - I/O/网络/DB操作必须有错误处理
    - 无硬编码密钥
    """,
    toolsets=['terminal', 'file']
)
```

**Reviewer Agent 模板（独立上下文）：**
```python
delegate_task(
    goal="审核Round N产出 — 五维度评分",
    context=f"""
    ROLE: Reviewer — independent quality assessment
    ROUND: {round_number}
    
    REVIEW: outputs/agent_driven/cross-review/round-{round_number}/
    ORIGINAL REQUIREMENTS: 读取 scored_intelligence.json 优化
    
    SCORING FRAMEWORK:
    - Correctness (35%): 逻辑正确性、边界处理、错误处理
    - Test Quality (25%): 覆盖完整、断言有效、测试独立
    - Code Quality (20%): 结构、命名、DRY、类型注解
    - Security (10%): 硬编码密钥、注入、输入验证
    - Performance (10%): 算法复杂度、内存、N+1
    
    OUTPUT: outputs/agent_driven/cross-review/round-{round_number}/review-report.md
    
    CONSTRAINTS:
    - 只读访问，不修改任何代码
    - 对每个问题标注文件:行号
    - 阻塞性问题必须修复才能进入下一轮
    """,
    toolsets=['file']  # 审核者只有文件读取权限
)
```

#### 2.5.3 审核反馈驱动下一轮机制
每轮审核报告包含三类问题，驱动下一轮实现方向：

| 问题类型 | 标记 | 处理方式 |
|----------|------|----------|
| 🔴 阻塞性 | 必须修复 | 下一轮Implementer必须解决 |
| 🟡 建议性 | 推荐修复 | 实现者自主决定 |
| ✅ 通过的检查 | 无需操作 | 记录到最终报告 |

**审核报告格式：**
```yaml
## 五维度评分
- 正确性: 0.95
- 测试质量: 0.90
- 代码质量: 0.85
- 安全性: 1.00
- 性能: 0.95
- 综合评分: 0.92

## 发现的问题
### 阻塞性问题
1. [文件:行号] [问题描述]

### 建议性问题
1. [文件:行号] [改进建议]

## 审核结论
PASS / FAIL / CONDITIONAL_PASS
```

#### 2.5.4 program.md 宪法概念
在 `outputs/agent_driven/` 下生成 `cross-review-program.md`，定义审核全过程的权限边界和行为规范：

```yaml
# 交叉审核宪法
version: 1.0
scope:
  allowed_directories:
    - outputs/agent_driven/        # 工作区
  forbidden_directories:
    - /etc/
    - /proc/
    - /sys/
    - ~/.ssh/

actions:
  allowed:
    - read_file
    - write_file
    - run_tests
  forbidden:
    - modify_deployment
    - access_secrets
    - modify_program_md

reviewer_privileges:
  - read_only                 # 审核者仅读取权限
  - cannot_modify_code        # 审核者不能修改代码
  - can_output_report         # 审核者只能输出审核报告

quality:
  minimum_test_coverage: 0.7
  maximum_function_length: 60
  maximum_file_length: 500
  require_type_annotations: true
  require_error_handling: true

testing:
  framework: pytest
  required_for: [all_public_functions, error_handling, edge_cases]
  forbidden:
    - print_based_testing
    - sleep_based_testing
```

#### 2.5.5 退火重试机制
当审核评分持续偏低时，通过自适应退火策略逐步提升，避免无限循环：

```python
def should_retry(round_number, current_score, scores_history, consecutive_failures):
    """
    退火策略:
    - 每轮降低对完美分数的期望
    - 当分数持续不增长时停止
    """
    max_rounds = 5
    if round_number >= max_rounds:
        return (False, f"达到最大轮次 ({max_rounds})")
    
    if consecutive_failures >= 3:
        return (False, f"连续失败超过阈值 (3/3)")
    
    # 分数收敛检测
    if len(scores_history) >= 3:
        recent = scores_history[-3:]
        score_range = max(s[1] for s in recent) - min(s[1] for s in recent)
        if score_range < 0.05:
            return (False, f"评分已收敛 (range={score_range:.2f} < 0.05)")
    
    if current_score >= 0.90:
        return (False, f"评分 {current_score:.2f} >= 0.90，目标达成")
    
    return (True, f"评分 {current_score:.2f} < 0.90，继续迭代")
```

**退火参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_rounds` | 5 | 最大审核轮次 |
| `target_score` | 0.90 | 目标综合评分 |
| `convergence_threshold` | 0.05 | 连续三轮波动<此值则停止 |
| `consecutive_fail_limit` | 3 | 连续评分<0.65则停止 |
| `min_improvement` | 0.02 | 每轮最少改进量 |

**触发退火停止时：**
1. 产生降级报告 `outputs/agent_driven/cross-review/summary/degradation-report.md`
2. 记录所有未修复问题
3. 建议人类介入
4. 保存当前最佳版本（最高评分轮次）

**硬停止条件（连续3次评分<0.65）：**
```python
HARD_STOP:
  1. 立即停止审核循环
  2. 生成应急报告: outputs/agent_driven/cross-review/summary/emergency-stop.md
  3. 包含所有轮次评分、阻塞性问题汇总、失败根因分析
  4. 记录失败模式到下次迭代的知识库
```

#### 2.5.6 交叉审核产出物
```
outputs/agent_driven/cross-review/
├── cross-review-program.md              # 项目宪法
├── round-1/
│   ├── (优化后的文件)
│   └── review-report.md                 # 第1轮审核报告
├── round-2/
│   ├── (优化后的文件)
│   └── review-report.md
├── round-3/ ...
├── summary/
│   ├── final-report.md                  # 最终总结报告
│   ├── score-trajectory.csv             # 评分变化轨迹
│   ├── degradation-report.md            # 降级报告（如触发）
│   └── emergency-stop.md                # 应急停止报告（如触发）
└── audit-log.md                         # 完整操作审计日志
```

### 步骤3: 市场分析（运营部）
使用 `delegate_task` 调度市场分析Agent：
- 读取 scored_intelligence.json
- 识别3+市场趋势，提炼2+产品需求
- 输出 market_analysis_report.md

### 步骤4: 产品设计（设计部）
使用 `delegate_task` 调度设计Agent：
- 工具集: `["file"]`
- 读取 market_analysis_report.md 和 scored_intelligence.json
- 输出 design_spec.md（产品功能设计 + UX原则）
- **已知问题**：输出可能被截断，max_iterations设为15，要求简洁输出（3000-5000字）

### 步骤5: 技术架构（研发部）
使用 `delegate_task` 调度技术Agent：
- 工具集: `["file"]`
- 读取 design_spec.md 和 market_analysis_report.md
- 输出 tech_architecture.md（技术选型 + 架构 + 工作量评估）
- **已知问题**：同步骤4，输出简洁（2000-3000字）

### 步骤6: 项目计划（PMO部）
使用 `delegate_task` 调度项目Agent：
- 工具集: `["file"]`
- 读取 tech_architecture.md
- 输出 project_plan.md（里程碑 + 风险评估 + 资源分配）

### 步骤7: 推送候选生成
使用 `delegate_task` 调度推送Agent：
- 工具集: `["file"]`
- 读取 scored_intelligence.json
- 输出 push_candidates.json（30条，P0/P1/P2分级）

### 步骤8: StructMem深度记忆更新（4层记忆 + 事件级绑定 + 跨事件整合）

**核心变更**：由于 `StructMemMemory`（memory工具、数据库操作）在子Agent中不可用，本步骤由**父Agent直接执行**Python代码，不再使用 `delegate_task`。

#### 8.1 初始化StructMem引擎

在步骤8开始时，由父Agent执行：

```python
import sys, json, os
from datetime import datetime
sys.path.insert(0, "/home/administrator/.hermes/scripts")
from structmem_memory import StructMemMemory

mem = StructMemMemory()
session_id = f"master_loop_{datetime.now().strftime('%Y%m%d_%H%M')}"
```

#### 8.2 读取所有7个输出文件并聚合

```python
output_dir = "/home/administrator/.hermes/outputs/agent_driven/"
files_to_read = [
    "scored_intelligence.json",
    "market_analysis_report.md",
    "design_spec.md",
    "tech_architecture.md",
    "project_plan.md",
    "push_candidates.json",
    "cross-review/summary/final-report.md"
]

all_outputs = []
for fname in files_to_read:
    fpath = os.path.join(output_dir, fname)
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            all_outputs.append(f"=== {fname} ===\n{content[:2000]}")  # 截断避免超长
```

#### 8.3 StructMem事件级绑定（双视角提取 + 时序锚定存储）

对聚合的对话内容进行**双视角提取**并写入structmem_events表：

```python
conversation_text = "\n\n".join(all_outputs)

# Step 8.3a: 双视角提取 + 存储为事件单元
event_id = mem.process_turn(
    session_id=session_id,
    conversation_text=conversation_text
)
print(f"[StructMem] Event #{event_id} 已存储（session={session_id}）")
```

该调用自动触发：
- `dual_extract()` → 事实视角（action/state/tech/preference/plan）+ 关系视角（support/oppose/causal/temporal）
- `process_turn()` → 写入 `structmem_events` 表，含时间戳、session_id、去重校验
- `_check_consolidation()` → 检查是否达到整合阈值

#### 8.4 跨事件整合触发

```python
# Step 8.4a: 计算未整合事件数
count = mem.count_unintegrated()

# Step 8.4b: 每10个事件或首次运行累积触发整合
if count >= 8 or count > 0:  # 8个事件阈值（StructMem默认）
    knowledge = mem.trigger_consolidation(session_id=session_id)
    print(f"[StructMem] 跨事件整合完成，生成 {len(knowledge)} 条合成知识")
    for k in knowledge:
        print(f"  - [{k['type']}] {k['content'][:80]}")
else:
    print(f"[StructMem] 未整合事件 {count} 个，未达阈值(8)，等待累积")
```

整合产出写入 `structmem_knowledge` 表，包含：
- 时序知识（temporal）：事件的时间序列关系
- 事实聚合（fact_*）：同类型事实的统计汇总
- 因果链（causal）：从关系视角中提取的因果关系

#### 8.5 StructMem查询接口 — 供记忆Agent检索使用

在Step 8的末尾，也开放一个查询入口，允许主控循环按需检索历史记忆：

```python
# Step 8.5a: 按本次会话检索
query_result = mem.query(
    query="本轮情报采集与分析核心产出",
    limit=3,
    time_range="7d"
)

# Step 8.5b: 写入检索结果到memory_retrieval.json供后续步骤使用
retrieval_path = os.path.join(output_dir, "structmem_retrieval.json")
with open(retrieval_path, "w", encoding="utf-8") as f:
    json.dump({
        "session_id": session_id,
        "matched_knowledge": [k["content"] for k in query_result["knowledge"]],
        "related_events": [e["event"]["source_preview"][:100] for e in query_result["related_events"]],
        "event_count": query_result["total_events"],
        "knowledge_count": query_result["total_knowledge"]
    }, f, ensure_ascii=False, indent=2)
```

#### 8.6 4层记忆文件输出（兼容Hermes原有4层架构）

以StructMem的事件单元为基础，映射到4层记忆JSON文件：

```python
status = mem.status()

# L1: 操作记录 — 直接映射为事件单元原始记录
layer1 = {
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "total_events": status["total_events"],
    "events_summary": "StructMem事件级绑定已存储，通过 structmem_events 表查询"
}
with open(os.path.join(output_dir, "memory_layer1.json"), "w", encoding="utf-8") as f:
    json.dump(layer1, f, ensure_ascii=False, indent=2)

# L2: 关键事实 — 映射为StructMem的facts提取结果
extraction = mem.dual_extract(conversation_text)
layer2 = {
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "facts": extraction["facts"],
    "relations": extraction["relations"],
    "fact_count": len(extraction["facts"]),
    "relation_count": len(extraction["relations"])
}
with open(os.path.join(output_dir, "memory_layer2.json"), "w", encoding="utf-8") as f:
    json.dump(layer2, f, ensure_ascii=False, indent=2)

# L3: 工作流固化 — 映射为跨事件整合后的合成知识
knowledge_data = mem.query("本轮工作流", limit=10)
layer3 = {
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "consolidated_knowledge": [k["content"] for k in knowledge_data["knowledge"]],
    "knowledge_count": len(knowledge_data["knowledge"])
}
with open(os.path.join(output_dir, "memory_layer3.json"), "w", encoding="utf-8") as f:
    json.dump(layer3, f, ensure_ascii=False, indent=2)

# L4: 模式学习 — 映射为因果链和关系分析
causal_rels = [k for k in knowledge_data["knowledge"] if "causal" in str(k.get("knowledge_type",""))]
layer4 = {
    "timestamp": datetime.now().isoformat(),
    "session_id": session_id,
    "patterns": [k["content"] for k in knowledge_data["knowledge"]],
    "causal_relations": causal_rels,
    "session_summary": f"本轮处理事件数: {status['total_events']}, 知识条目: {status['total_knowledge']}"
}
with open(os.path.join(output_dir, "memory_layer4.json"), "w", encoding="utf-8") as f:
    json.dump(layer4, f, ensure_ascii=False, indent=2)

print(f"[StructMem] 4层记忆文件已输出到 {output_dir}")
```

### 步骤9: 质量自检
使用 `delegate_task` 调度审计Agent：
- 工具集: `["file"]`
- 验证所有16个输出文件存在且内容完整
- 输出 quality_audit_report.md
- **注意**：审计Agent运行在隔离上下文，可能无法看到主控层文件，需要在主控层额外验证

## 输出文件清单
| # | 文件 | 内容 |
|---|------|------|
| 1 | raw_intelligence.json | 20+条原始情报 |
| 2 | scored_intelligence.json | 六维评分结果 |
| 3 | cross-review/round-{N}/review-report.md | 多Agent交叉审核报告（N轮） |
| 4 | cross-review/cross-review-program.md | 交叉审核宪法 |
| 5 | cross-review/summary/final-report.md | 交叉审核最终总结报告 |
| 6 | cross-review/summary/score-trajectory.csv | 五维度评分变化轨迹 |
| 7 | market_analysis_report.md | 市场分析报告 |
| 8 | design_spec.md | 产品设计规范 |
| 9 | tech_architecture.md | 技术架构方案 |
| 10 | project_plan.md | 项目里程碑计划 |
| 11 | push_candidates.json | 30条推送候选 |
| 12 | memory_layer1.json | 操作记录（StructMem事件级绑定） |
| 13 | memory_layer2.json | 关键事实（StructMem双视角提取） |
| 14 | memory_layer3.json | 工作流固化（StructMem跨事件整合） |
| 15 | memory_layer4.json | 模式学习（StructMem因果链分析） |
| 16 | structmem_retrieval.json | StructMem历史记忆检索结果 |

## 已知陷阱
1. **子Agent输出截断**：步骤1/4/5的max_iterations可能被触达导致截断。步骤1设为40，步骤4/5设为15并要求精简。
2. **子Agent输出截断**：步骤4/5/6（设计/架构/规划）中，子Agent读取大文件后输出过长会导致max_iterations耗尽而失败。**解决方案**：对于大内容产出，让子Agent只做分析推理输出到文件，或主Agent直接使用write_file写入产出物。
3. **web_search工具可能缺失**：此环境可能无web_search工具。**替代方案**：检查现有情报数据库（/home/administrator/intelligence_report.json），如为当日数据可直接复用；或使用browser工具访问新闻API。
4. **Memory工具可能不可用**：某些环境中memory工具被禁用。**替代方案**：将关键事实写入JSON文件到outputs目录。
5. **交叉审核之审核者上下文污染**：Reviewer的delegate_task必须与Implementer隔离，不共享实现上下文。Reviewer应像第一次看到代码一样独立评审。
6. **交叉审核之角色混淆**：奇数轮A实现B审，偶数轮B实现A审。必须用两个独立的delegate_task调用，不可在同一次调用中同时实现和审核。
7. **交叉审核之评分膨胀**：审核者倾向于打高分。要求审核者明确指出每个维度的扣分项，提供文件:行号。Reviewer模板强制要求具体问题标注。
8. **交叉审核之无限循环**：评分在0.80-0.89徘徊时可能无限循环。通过退火机制的收敛检测（连续三轮波动<0.05则停止）和最大轮次保护（max_rounds=5）防止。
13. **omni_loop vs delegate_task 双轨运行**：实际生产管线（omni_loop.py）使用直接API调用（urllib → OpenRouter），而本skill描述的是delegate_task驱动的9步循环。两者不兼容——delegate_task在子Agent内无法调用外部API（无network tools）。**如果omni_loop不可用**，需确认delegate_task子Agent能否访问外部API后再设计。|
- toolsets配置：子Agent按任务类型精准配置：分析类→['file']，采集类→['web','terminal','file']（注意web_search在子Agent可能不可用，降级方案：父Agent用execute_code通过curl/API采集后再传给子Agent），代码类→['terminal','file']。
- 时间预算：全循环约20-35分钟，如有超时步骤需重试。
- **子Agent不可用父Agent工具**：memory()、skill_manage()、delegate_task()等在子Agent中不可用。需由父Agent在Step 8直接执行。
- **200行输出约束**：设计/架构/规划等产出物控制在200-300行以内，避免子Agent max_iterations耗尽。
- **数据传递**：父Agent完成采集后，子Agent通过read_file读取产出文件，而非通过context传递原始数据。
- **六维评分更新**：每维0-20分（总分0-120），高分阈值为>60分。2026-05-07实际测试21/25条>60分，阈值合适。
- **StructMem数据库隔离**：active_memory.db 位于 /home/administrator/.hermes/ 根目录，步骤8直接操作该数据库。如果StructMemMemory实例化失败（如缺少sqlite3模块），回退到纯JSON文件写入4层记忆。
- **StructMem integration状态跟踪**：8个事件阈值整合后，已整合事件标记为integrated=1。如果同一session_id后续再次运行Step 8，只有未整合事件会参与整合。为避免整合过量，每次最多处理20个未整合事件。
- **双视角提取内容质量**：StructMem的dual_extract基于正则匹配，对高度技术性的JSON/代码内容提取效果有限。建议在聚合conversation_text时保留可读的自然语言摘要，而非纯JSON转储。|

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
