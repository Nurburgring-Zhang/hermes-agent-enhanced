---
name: cross-review-autoresearch
description: >
  多Agent交叉审核Skill — 基于AutoResearch方法论的Hermes原生实现。
  两个Agent交替担任实现者和审核者，5维度加权评分，4阶段循环。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cross-review, auto-research, multi-agent, quality, code-review, iterative]
    related_skills: [subagent-driven-development, requesting-code-review, test-driven-development, github-code-review]
---

# 多Agent交叉审核 (Cross-Review AutoResearch)

## 概述

基于AutoResearch方法论的Hermes原生实现。核心思想：**两个Agent轮流担任实现者和审核者**，A写完B审，B写完A审，审核反馈驱动下一轮实现。

**核心理念：** 不对称审查 — 每个审查者审查自己未参与编写的代码，确保完全独立的审阅视角。

## 触发条件

此skill在以下场景被触发：

- 用户要求"交叉审核"、"互审"、"AutoResearch"、"cross-review"
- 需要高可靠性代码生成（生产级代码）
- 两个或多个Agent协作完成任务
- 需要5维度加权评分的质量评估
- 迭代式代码改进场景
- 处理复杂、高风险的代码变更
- 用户说"审一下"、"review each other"、"peer review"

**跳过：** 纯文档修改、简单的一行修复、用户明确说"不需要审核"的场景。

## 五维度评分标准细则

每个维度的评分范围：0.0 - 1.0（保留两位小数）

### 1. 正确性 (权重 35%)

| 分值 | 标准 |
|------|------|
| 1.0 | 代码完全正确，所有边界情况已处理，所有测试通过 |
| 0.9 | 代码正确，核心功能无误，少量非关键边界未覆盖 |
| 0.8 | 主要功能正确，有1-2个次要逻辑缺陷 |
| 0.7 | 核心功能可用但有明显逻辑漏洞 |
| 0.6 | 有严重逻辑缺陷，但整体方向正确 |
| 0.5- | 代码存在方向性错误或完全不可运行 |

**检查清单：**
- [ ] 所有函数逻辑与注释/需求一致
- [ ] 边界条件处理（空值、极值、并发）
- [ ] 错误处理完整（try/except覆盖，异常类型准确）
- [ ] 返回值和类型符合预期
- [ ] 依赖调用的假设成立
- [ ] 浮点精度问题考虑
- [ ] 时区/编码/平台差异处理

### 2. 测试质量 (权重 25%)

| 分值 | 标准 |
|------|------|
| 1.0 | 全覆盖（单元+集成+边界），测试可重复、独立 |
| 0.9 | 核心功能全面覆盖，少数边缘路径未测试 |
| 0.8 | 主要路径已覆盖但缺乏边界/异常测试 |
| 0.7 | 仅有基本冒烟测试 |
| 0.6 | 测试碎片化，覆盖率<50% |
| 0.5- | 无测试或测试不可运行 |

**检查清单：**
- [ ] 单元测试覆盖每个public函数
- [ ] 边界值测试（空、NaN、负数、超大值）
- [ ] 异常路径测试（网络错误、文件不存在、权限拒绝）
- [ ] 测试之间无共享可变状态
- [ ] 测试命名清晰（test_<function>_<scenario>）
- [ ] 使用断言而非print
- [ ] 测试独立可重复（无顺序依赖）

### 3. 代码质量 (权重 20%)

| 分值 | 标准 |
|------|------|
| 1.0 | 整洁架构，高内聚低耦合，符合语言惯用法 |
| 0.9 | 结构清晰，可读性好，少量小改进空间 |
| 0.8 | 组织良好但存在样式问题或轻微冗余 |
| 0.7 | 可理解但有明显设计缺陷 |
| 0.6 | 糟糕的结构，难以维护和扩展 |
| 0.5- | 不可维护的代码 |

**检查清单：**
- [ ] 命名语义化（变量/函数/类名自解释）
- [ ] 函数长度合理（<50行，单一职责）
- [ ] 无重复代码（DRY原则）
- [ ] 类型注解完备（Python）或类型定义清晰
- [ ] 注释：为什么 > 是什么（好代码自文档化）
- [ ] 遵循PEP8/PEP484（Python）或语言惯用风格
- [ ] 模块化设计，依赖方向清晰
- [ ] 无死代码、TODO堆积、print debug残留

### 4. 安全性 (权重 10%)

| 分值 | 标准 |
|------|------|
| 1.0 | 经过安全审计，无任何已知漏洞 |
| 0.9 | 安全意识良好，少量非关键问题 |
| 0.8 | 有基本防护但存在1个中等风险 |
| 0.7 | 存在明显安全疏漏 |
| 0.6 | 多个安全风险 |
| 0.5- | 严重安全漏洞 |

**检查清单：**
- [ ] 无硬编码密钥/密码/token
- [ ] SQL使用参数化查询（非f-string拼接）
- [ ] 输入验证和消毒（路径遍历、命令注入）
- [ ] 不使用eval/exec处理外部输入
- [ ] 不使用pickle.loads处理不可信数据
- [ ] 文件路径进行规范化（防止../攻击）
- [ ] 敏感信息不在日志中输出
- [ ] 依赖版本没有已知CVE

### 5. 性能 (权重 10%)

| 分值 | 标准 |
|------|------|
| 1.0 | 最优算法，资源使用高效 |
| 0.9 | 性能良好，有少量可优化点 |
| 0.8 | 合理但存在可预见的性能瓶颈 |
| 0.7 | 有明显低效实现 |
| 0.6 | 存在严重性能问题 |
| 0.5- | 不可接受的性能 |

**检查清单：**
- [ ] 算法复杂度合理（无O(n²)可用O(n)替代的场景）
- [ ] 无N+1查询问题
- [ ] 适当的数据结构选择（dict/list/set）
- [ ] 避免不必要的数据拷贝
- [ ] 内存使用合理（大量数据时考虑流式处理）
- [ ] I/O操作有超时和重试机制
- [ ] 缓存策略（如果需要）
- [ ] 无阻塞调用在异步路径中

### 综合评分公式

```
final_score = correctness * 0.35 + test_quality * 0.25 +
              code_quality * 0.20 + security * 0.10 + performance * 0.10
```

**评级阈值：**
- >= 0.90: ✅ 优秀 — 可直接使用
- >= 0.80: ✅ 良好 — 建议修复次要问题
- >= 0.65: ⚠️ 合格 — 需要修复问题后重新审核
- < 0.65: ❌ 不合格 — 需要大幅修改后重新审核

## 交叉审核流程

### 阶段0: 环境准备

```bash
# 1. 创建工作目录
mkdir -p outputs/cross-review/{round-1,round-2,round-3,summary}

# 2. 读取项目宪法的权限边界
# program.md 定义了项目规则（见下文program.md章节）

# 3. 获取初始代码或需求
# 读取要审核的文件
```

### 阶段1: 第一轮 — Agent A 实现 / Agent B 审核

**Step 1.1: Agent A 实现 (奇数轮)**

Agent A (implementer) 完成以下任务：
1. 读取需求/规范文档
2. 编写代码实现
3. 编写测试
4. 确保所有测试通过
5. 保存到 `outputs/cross-review/round-1/`

**Step 1.2: Agent B 审核 (独立上下文)**

Agent B (reviewer) 是 独立 的 delegate_task 调用。Reviewer 接收：
- 原始需求（非实现说明）
- 生成的代码文件和测试文件
- 不共享Agent A的实现上下文

Reviewer 输出到 `outputs/cross-review/round-1/review-report.md`，格式：

```yaml
## 五维度评分
- 正确性: 0.95
- 测试质量: 0.90
- 代码质量: 0.85
- 安全性: 1.00
- 性能: 0.95
- 综合评分: 0.92

## 发现的问题
### 阻塞性问题（必须在下一轮修复）
1. [问题描述] — 具体位置

### 建议性问题（推荐修复）
1. [问题描述] — 改进建议

## 审核结论
PASS / FAIL / CONDITIONAL_PASS
```

### 阶段2: 第二轮 — Agent B 实现 / Agent A 审核

**Step 2.1: Agent B 实现 (偶数轮)**

Agent B 的角色转换为 implementer：
1. 读取原始需求 + 上一轮的审核报告
2. 根据审核反馈修复Agent A代码中的问题
3. 或编写新的功能模块
4. 确保所有测试通过
5. 保存到 `outputs/cross-review/round-2/`

**Step 2.2: Agent A 审核 (独立上下文)**

Agent A 现在作为 reviewer：
1. 读取原始需求 + 本轮的实现
2. 进行五维度评分
3. 输出审核报告到 `outputs/cross-review/round-2/review-report.md`

**角色轮换规则：**
- 奇数轮 (1, 3, 5...): Agent A实现，Agent B审核
- 偶数轮 (2, 4, 6...): Agent B实现，Agent A审核
- 审核反馈中标记为"阻塞性"的问题必须在下一轮修复
- "建议性"问题可由实现者自行决定是否修复

### 阶段3: 迭代循环

**每轮迭代步骤：**

```
1. Implementer 读取: 原始需求 + 上一轮审核报告（第1轮无审核报告）
2. Implementer 实现: 编写/修复代码，编写测试
3. Implementer 验证: 所有测试通过
4. Implementer 提交: 保存到 outputs/cross-review/round-N/
5. Reviewer 审核: 五维度评分 + 问题列表
6. Reviewer 输出: review-report.md
7. 决策: 是否进入下一轮？
   - 综合评分 >= 0.90 且无阻塞性问题 → 阶段4
   - 综合评分 >= 0.80 且无阻塞性问题 → 可选继续
   - 综合评分 < 0.80 或存在阻塞性问题 → 必须继续下一轮
   - 连续失败 ≥ 3次 → 自动停止（见退火机制）
```

### 阶段4: 自动提交与结果归档

```bash
# 1. 生成最终总结报告
cat > outputs/cross-review/summary/final-report.md << 'EOF'
# 交叉审核最终报告

## 元信息
- 项目名称: [name]
- 审核轮次: [N]
- 起止时间: [start] → [end]

## 评分变化轨迹
| 轮次 | 正确性 | 测试 | 质量 | 安全 | 性能 | 综合 |
|------|--------|------|------|------|------|------|
| 1    | 0.XX   | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX |
| 2    | 0.XX   | 0.XX | 0.XX | 0.XX | 0.XX | 0.XX |

## 最终评分
- 综合评分: [score]
- 评级: [等级]

## 最终文件清单
- [列出所有生成的文件]

## 发现的问题摘要
- 已修复: [N]
- 待修复(非阻塞): [N]
- 待修复(阻塞): [N]

## 审核历程
- 每轮的关键发现和改进

## 结论
[通过/条件通过/不通过]
EOF

# 2. 归档所有轮次结果
# outputs/cross-review/ 作为完整的审核工件

# 3. 可选: 将最终代码复制到目标位置
```

## program.md — 项目宪法设计

项目宪法(program.md)定义了交叉审核全过程的权限边界和行为规范。建议放置在工作目录的 `cross-review-program.md`。

### 权限边界

```yaml
# 交叉审核宪法
version: 1.0
scope:
  allowed_directories:
    - outputs/cross-review/    # 审核工作区
    - src/                     # 源代码（如需修改）
    - tests/                   # 测试代码
  forbidden_directories:
    - /etc/
    - /proc/
    - /sys/
    - ~/.ssh/
    - ~/.config/important-secrets/

actions:
  allowed:
    - read_file               # 读取源文件
    - write_file              # 创建/修改代码
    - run_tests               # 运行测试套件
    - git_commit              # 提交代码
    - install_dependencies    # 安装依赖
  forbidden:
    - modify_ci_config        # 修改CI配置
    - modify_deployment       # 修改部署配置
    - access_secrets          # 访问密钥
    - network_egress          # 网络外发（除依赖下载外）
    - modify_program_md       # 修改宪法自身

reviewer_privileges:
  - read_only                 # 审核者仅拥有读取权限
  - cannot_modify_code        # 审核者不能修改代码
  - can_output_report         # 审核者只能输出审核报告
```

### 质量规范

```yaml
quality:
  minimum_test_coverage: 0.7          # 最低测试覆盖率
  maximum_function_length: 60         # 最大函数行数
  maximum_file_length: 500            # 最大文件行数
  require_type_annotations: true      # 需要类型注解（Python）
  require_docstrings: true            # 需要文档字符串
  require_error_handling: true        # 需要错误处理

  naming_conventions:
    classes: PascalCase
    functions: snake_case
    constants: UPPER_SNAKE_CASE
    private_methods: _leading_underscore

  commit_conventions:
    format: "type(scope): description"
    allowed_types:
      - feat
      - fix
      - refactor
      - test
      - docs
      - chore
```

### 测试规范

```yaml
testing:
  framework: pytest
  required_for: [all_public_functions, error_handling, edge_cases]
  forbidden:
    - print_based_testing     # 禁止基于print的测试
    - sleep_based_testing     # 禁止基于sleep的时序测试
    - skipped_tests           # 禁止跳过的测试（除非注释说明）
  
  organization:
    - tests/unit/             # 单元测试
    - tests/integration/      # 集成测试（如需要）

  naming:
    test_files: "test_<module>.py"
    test_functions: "test_<function>_<scenario>"
```

## delegate_task 调用模板

### Implementer 模板

```python
delegate_task(
    goal="Implement [module_name] with cross-review readiness",
    context=f"""
    ROLE: Implementer — write production-quality code.
    ROUND: {round_number} (odd = implement from scratch, even = improve from feedback)

    REQUIREMENTS:
    [原始需求描述]

    PREVIOUS REVIEW FEEDBACK (round {round_number - 1}):
    [上一轮审核报告中的阻塞性和建议性问题]

    OUTPUT DIRECTORY: outputs/cross-review/round-{round_number}/

    CONSTRAINTS:
    - All public functions must have tests
    - Test coverage >= 70%
    - Function length <= 60 lines
    - File length <= 500 lines
    - Type annotations required
    - Error handling required on I/O, network, DB operations
    - No hardcoded secrets

    DELIVERABLES:
    1. Source code in outputs/cross-review/round-{round_number}/
    2. Tests in outputs/cross-review/round-{round_number}/tests/
    3. All tests pass: `python -m pytest outputs/cross-review/round-{round_number}/ -q`
    
    SAVE every file to the OUTPUT DIRECTORY. Do NOT modify files outside that directory.
    """,
    toolsets=['terminal', 'file']
)
```

### Reviewer 模板

```python
delegate_task(
    goal="Cross-review [module_name] with 5-dimension scoring",
    context=f"""
    ROLE: Reviewer — independent quality assessment. 
    You did NOT write this code. You have no shared context with the implementer.
    ROUND: {round_number}

    REVIEW ME: outputs/cross-review/round-{round_number}/
    ORIGINAL REQUIREMENTS:
    [原始需求描述]

    SCORING FRAMEWORK:
    - Correctness (35%): Is the logic correct? All edge cases handled?
    - Test Quality (25%): Coverage, edge cases, independence, assertions?
    - Code Quality (20%): Structure, readability, naming, DRY, typing?
    - Security (10%): Hardcoded secrets, injection, input validation?
    - Performance (10%): Algorithm complexity, memory, N+1 queries?

    OUTPUT: outputs/cross-review/round-{round_number}/review-report.md
    FORMAT: YAML-style scoring + blocking issues + suggestions + verdict.

    CONSTRAINTS:
    - Read-only access. Do NOT modify any code.
    - Be specific about file:line for each issue.
    - Blocking issues = must fix before next round.
    - Suggestions = nice to have.
    - If score < 0.65, verdict must be FAIL.
    
    Save the review report to the OUTPUT DIRECTORY.
    """,
    toolsets=['file']  # 审核者只有文件读取权限
)
```

## 退火重试机制

当审核评分偏低时，通过针对性修复逐步提升。

### 重试策略

```python
def should_retry(round_number, current_score, scores_history, consecutive_failures):
    """
    退火策略: 
    - 每轮降低了对完美分数的期望
    - 但当分数持续不增长时，停止
    
    Args:
        round_number: 当前轮次 (1-based)
        current_score: 当前轮综合评分
        scores_history: list of (round, score) for all completed rounds
        consecutive_failures: 连续未通过轮次（score < 0.65）
    
    Returns:
        (should_continue: bool, reason: str)
    """
    # 最大轮次保护
    max_rounds = 5
    if round_number >= max_rounds:
        return (False, f"Reached max rounds ({max_rounds})")
    
    # 连续失败保护
    if consecutive_failures >= 3:
        return (False, f"Consecutive failures exceeded (3/3)")
    
    # 分数不再增长 — 退火停止
    if len(scores_history) >= 3:
        recent = scores_history[-3:]
        # 如果最后三轮分数波动小于0.05，认为已收敛
        score_range = max(s[1] for s in recent) - min(s[1] for s in recent)
        if score_range < 0.05:
            return (False, f"Score converged (range={score_range:.2f} < 0.05)")
    
    # 分数已达标
    if current_score >= 0.90:
        return (False, f"Score {current_score:.2f} >= 0.90, target achieved")
    
    # 继续迭代
    improvement = ""
    if scores_history:
        prev_score = scores_history[-1][1]
        delta = current_score - prev_score
        improvement = f" (delta={delta:+.2f})"
    
    return (True, f"Score {current_score:.2f} < 0.90, retrying{improvement}")
```

### 退火参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_rounds` | 5 | 最大审核轮次 |
| `target_score` | 0.90 | 目标综合评分 |
| `convergence_threshold` | 0.05 | 连续三轮波动小于此值则停止 |
| `consecutive_fail_limit` | 3 | 连续评分<0.65则停止 |
| `min_improvement_per_round` | 0.02 | 每轮最少改进量（低于此值视为收敛） |

### 失败降级

当触发退火停止条件时：
1. 产生降级报告 `outputs/cross-review/summary/degradation-report.md`
2. 记录所有未修复问题
3. 建议人类介入
4. 保存当前最佳版本（最高评分轮次）

## 连续失败保护

当连续3次审核未通过（综合评分 < 0.65），自动触发硬停止：

```python
HARD_STOP_PROTOCOL:
  1. 立即停止审核循环
  2. 生成应急报告: outputs/cross-review/summary/emergency-stop.md
  3. 内容包括:
     - 所有轮次的评分和审核报告
     - 所有阻塞性问题汇总
     - 失败根因分析
     - 建议的人工修复方案
  4. 锁定 outputs/cross-review/ 目录（改为只读提醒）
  5. 记录失败模式到下次迭代的知识库
```

## 输出文件清单

### 目录结构

```
outputs/cross-review/
├── cross-review-program.md           # 项目宪法（每项目一份）
├── round-1/
│   ├── src/                          # 第1轮源代码
│   │   └── [module].py / [module].js / ...
│   ├── tests/                        # 第1轮测试
│   │   └── test_[module].py / ...
│   └── review-report.md              # 第1轮审核报告
├── round-2/
│   ├── src/
│   ├── tests/
│   └── review-report.md
├── round-3/
│   ├── src/
│   ├── tests/
│   └── review-report.md
├── summary/
│   ├── final-report.md               # 最终总结报告
│   ├── score-trajectory.csv          # 评分变化轨迹
│   ├── degradation-report.md         # 降级报告（如触发）
│   └── emergency-stop.md             # 应急停止报告（如触发）
└── audit-log.md                      # 完整操作审计日志
```

### 文件命名规范

| 文件 | 命名规则 | 示例 |
|------|----------|------|
| 源代码 | `<module>.<ext>` | `user_auth.py` |
| 测试文件 | `test_<module>.<ext>` | `test_user_auth.py` |
| 审核报告 | `review-report.md` | 固定命名 |
| 每轮汇总 | 存入round-N/目录 | 版本化 |

## 已知陷阱

### 流程陷阱

1. **审核者上下文污染** — 确保reviewer的delegate_task没有共享implementer的context。审核者必须像第一次看到代码一样独立审核。
   - ✅ 正确：reviewer的delegate_task只包含原始需求和代码路径
   - ❌ 错误：reviewer的delegate_task包含implementer的思路、中间决策过程

2. **角色混淆** — 奇数轮A实现B审，偶数轮B实现A审。实现者不能同时审核自己的代码。
   - 必须用两个不同的delegate_task分别调用
   - 不要在同一次delegate_task中同时实现和审核

3. **跳过审核修复验证** — 如果reviewer发现阻塞性问题，implementer修复后，reviewer应再次审核。不能假设修复一定正确。

4. **评分膨胀** — 审核者倾向于打高分。要求审核者明确指出每个维度的扣分项，并提供文件:行号。

5. **无限循环** — 当评分在0.80-0.89之间徘徊时，可能会导致无限循环。通过退火机制的收敛检测防止。

### 代码陷阱

6. **空测试** — 审核者要注意测试是否真的做了断言，而不是只写了框架。检查 `assert` 关键字出现次数。

7. **测试依赖** — 测试之间不能共享可变状态。测试应按任意顺序运行结果一致。

8. **隐藏的硬编码** — 审核者应检查所有字符串常量，特别是类密码、API端点、IP地址的硬编码。

9. **过度工程** — 第1轮实现应该最小可行，后续轮次优化。第1轮就过度抽象会引入不必要的复杂度。

10. **修复引入新bug** — 跨轮次的修复经常引入回归。每轮实现结束后必须运行完整测试套件。

11. **conftest.py污染** — 如果使用pytest，注意conftest.py中的fixture可能会在测试之间共享状态，导致测试顺序依赖。

12. **文档与代码不一致** — 审核者应检查docstring/注释是否与代码行为一致，特别是修复后忘记更新注释的场景。

### delegate_task陷阱

13. **delegate_task超时** — 大型审核任务可能因上下文过长超时。建议：
    - 如果文件过多，分批提交审核
    - reviewer只获取必要的审核上下文

14. **delegate_task返回非JSON** — reviewer模板强制要求输出特定格式。如果返回不解析，重试并明确指示格式。

15. **文件路径不匹配** — implementer保存的文件必须和reviewer读取的路径一致。使用绝对路径或在delegate_task中明确指定工作目录。

## 实用脚本

### 计算综合评分

```python
#!/usr/bin/env python3
"""score_calculator.py — 计算五维度加权综合评分"""
import sys

WEIGHTS = {
    "correctness": 0.35,
    "test_quality": 0.25,
    "code_quality": 0.20,
    "security": 0.10,
    "performance": 0.10,
}

def calculate(scores: dict) -> float:
    if set(scores.keys()) != set(WEIGHTS.keys()):
        missing = set(WEIGHTS.keys()) - set(scores.keys())
        extra = set(scores.keys()) - set(WEIGHTS.keys())
        raise ValueError(f"Missing: {missing}, Extra: {extra}")
    
    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total, 2)

def rating(score: float) -> str:
    if score >= 0.90: return "优秀"
    if score >= 0.80: return "良好"
    if score >= 0.65: return "合格"
    return "不合格"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Parse from CLI: correctness test_quality code_quality security performance
        parts = sys.argv[1:]
        if len(parts) == 5:
            scores = dict(zip(WEIGHTS.keys(), map(float, parts)))
            score = calculate(scores)
            print(f"综合评分: {score} ({rating(score)})")
            sys.exit(0)
    
    # Interactive mode
    scores = {}
    for dim in WEIGHTS:
        while True:
            try:
                val = float(input(f"{dim} (0.0-1.0): "))
                if 0.0 <= val <= 1.0:
                    scores[dim] = val
                    break
                print("范围 0.0-1.0")
            except ValueError:
                print("请输入数字")
    
    score = calculate(scores)
    print(f"\n综合评分: {score} ({rating(score)})")
    for dim, w in WEIGHTS.items():
        contribution = scores[dim] * w
        print(f"  {dim}: {scores[dim]:.2f} × {w:.2f} = {contribution:.3f}")
```

### 评分变化轨迹生成

```python
#!/usr/bin/env python3
"""generate_trajectory.py — 从审核报告生成评分轨迹CSV"""
import glob
import re
import csv
import sys

ROUND_DIR = sys.argv[1] if len(sys.argv) > 1 else "outputs/cross-review"

def extract_scores(report_path: str) -> dict:
    with open(report_path) as f:
        content = f.read()
    
    scores = {}
    patterns = {
        "correctness": r"正确性[:\s]+([0-9.]+)",
        "test_quality": r"测试质量[:\s]+([0-9.]+)",
        "code_quality": r"代码质量[:\s]+([0-9.]+)",
        "security": r"安全性[:\s]+([0-9.]+)",
        "performance": r"性能[:\s]+([0-9.]+)",
        "composite": r"综合评分[:\s]+([0-9.]+)",
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            scores[key] = float(match.group(1))
    
    return scores

# 找到所有审核报告
reports = sorted(glob.glob(f"{ROUND_DIR}/round-*/review-report.md"))

# 提取轮次号
def round_num(path):
    m = re.search(r"round-(\d+)", path)
    return int(m.group(1)) if m else 0

reports.sort(key=round_num)

# 写入CSV
csv_path = f"{ROUND_DIR}/summary/score-trajectory.csv"
with open(csv_path, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["round", "correctness", "test_quality", "code_quality", "security", "performance", "composite"])
    
    for report_path in reports:
        rn = round_num(report_path)
        scores = extract_scores(report_path)
        writer.writerow([
            rn,
            scores.get("correctness", ""),
            scores.get("test_quality", ""),
            scores.get("code_quality", ""),
            scores.get("security", ""),
            scores.get("performance", ""),
            scores.get("composite", ""),
        ])

print(f"评分轨迹已保存: {csv_path}")
```

## 完整使用示例

### 用例：实现一个URL短链接服务

```python
# === 阶段0: 环境准备 ===
# mkdir -p outputs/cross-review/{round-1,round-2,round-3,summary}

# === 阶段1: 第一轮 — Agent A实现 / Agent B审核 ===
# Agent A (implementer)
delegate_task(
    goal="Implement URL shortener service — round 1",
    context="""
    ROLE: Implementer
    ROUND: 1
    
    REQUIREMENTS:
    - Function: shorten(url: str) -> str — 返回短码
    - Function: resolve(short_code: str) -> str — 返回原始URL
    - 短码: 7位随机字符 [a-zA-Z0-9]
    - 碰撞检测: 如果短码冲突，重新生成
    - 存储: 内存字典（后续轮次可升级为持久化）
    - 输入验证: URL必须以 http:// 或 https:// 开头
    - 错误处理: 无效URL抛ValueError，不存在的短码抛KeyError
    
    CONSTRAINTS: [按宪法要求]
    
    OUTPUT: outputs/cross-review/round-1/
    """,
    toolsets=['terminal', 'file']
)

# Agent B (reviewer)
delegate_task(
    goal="Review URL shortener implementation",
    context="""
    ROLE: Reviewer — independent review
    ROUND: 1
    
    REVIEW: outputs/cross-review/round-1/
    
    ORIGINAL REQUIREMENTS:
    - shorten(url) -> str, resolve(code) -> str
    - 7-char random codes, collision detection
    - In-memory storage, URL validation
    - Error handling
    
    OUTPUT: outputs/cross-review/round-1/review-report.md
    """,
    toolsets=['file']
)

# === 阶段2: 第二轮 — Agent B实现 / Agent A审核 ===
# Agent B (implementer) 读取审核报告，修复问题
delegate_task(
    goal="Improve URL shortener — round 2",
    context="""
    ROLE: Implementer
    ROUND: 2
    
    PREVIOUS FEEDBACK:
    [读取 outputs/cross-review/round-1/review-report.md 中的阻塞性问题]
    
    ADDITIONAL REQUIREMENTS:
    - 添加SQLite持久化存储
    - 添加自定义短码支持: shorten(url, custom_code=None)
    - 短码有效期（可选）
    
    OUTPUT: outputs/cross-review/round-2/
    """,
    toolsets=['terminal', 'file']
)

# ... 继续迭代 ...

# === 阶段4: 总结归档 ===
# 生成最终报告
# 输出到 outputs/cross-review/summary/final-report.md
```

## 与其他Skill的关系

| 相关Skill | 关系 |
|-----------|------|
| **subagent-driven-development** | 本skill更强调对称/交替审核，而subagent-driven-development是单Agent实现+双阶段审核 |
| **requesting-code-review** | 本skill提供多轮迭代的交叉审核，requesting-code-review是单次预提交验证 |
| **test-driven-development** | 本skill要求implementer在提交前遵循TDD |
| **github-code-review** | 本skill产出本地审核报告，不直接与GitHub PR交互 |

## 特别提醒

```
╔══════════════════════════════════════════════════════╗
║    交叉审核的核心力量来自角色轮换和独立上下文         ║
║                                                      ║
║    Agent A 写的代码 → Agent B 审查 (独立)            ║
║    Agent B 根据反馈修复/扩展 → Agent A 审查 (独立)   ║
║                                                      ║
║    两个人轮流开车，轮流看导航                         ║
║    谁都不会独自处理所有转弯。                         ║
╚══════════════════════════════════════════════════════╝
```

## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
