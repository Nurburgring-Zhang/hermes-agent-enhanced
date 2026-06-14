---
name: goal-hive-orchestrator
description: Goal Hive 蜂群协作模式 — 全面融合Generic Agent开源论文的Master + 多Worker + BBS任务账本 + 预算驱动验收机制。将Hermes从单体Agent升级为多Agent蜂群组织。
version: 1.0.0
author: Hermes Agent
domain: autonomous-systems
tags:
  - goal-hive
  - multi-agent
  - master-worker
  - bbs-task-board
  - budget-driven
  - team-organization
triggers:
  - "多Agent协作"
  - "蜂群模式"
  - "Goal Hive"
  - "任务拆解"
  - "master-worker"
  - "预算驱动"
  - "任务账本"
  - "BBS"
  - "hive master"
---

# Goal Hive 蜂群协作模式

## 核心理念

基于 Generic Agent 团队开源的 Goal Hive 模式（https://github.com/lsdefine/GenericAgent），
将"组织智能"融入 Hermes 的每项任务执行：

**组织智能 = 谁拆任务 + 谁执行 + 谁验收 + 结果放哪 + 缺口如何继续补**

Goal Hive 不是让一个 AI 更强，而是让一群 AI 学会组队干活。

## 三要素

| 角色 | 职责 | 对应物 |
|------|------|--------|
| Hive Master | 拆目标 + 派任务 + 验收成果 + 发现缺口后继续派单 | 项目经理 |
| Workers | 各自领一块活，专注做深，独立交付 | 执行者 |
| BBS 任务账本 | 公共看板沉淀任务/进度/产物，不依赖谁的记忆 | 工单系统 |

## 预算驱动核心理念

传统 Agent："做完就停" — 第一版出来就交差。
Goal Hive："向可验收交付逼近" — 预算未耗尽时 Master 继续检查缺口。

**把"做完就停"升级成"验收通过才停"。**

## 数据流

```
用户目标
    ↓
Hive Master ──拆解──→ 子任务1 ... 子任务N
    │                       ↓              ↓
    │                    Worker 1       Worker N
    │                       ↓              ↓
    │                   BBS帖#1回帖    BBS帖#N回帖
    │                       │              │
    └──────────验收──────────┴──────────────┘
        不合格→返工 | 有缺口→新任务
        预算未耗尽→继续优化 | 预算耗尽→整合交付
```

## 触发条件

任意以下场景自动激活 Goal Hive 模式，而非单Agent直接执行：

1. 任务可以拆成 3 个以上独立子任务
2. 需要多视角交叉验证（调研、写作、复核）
3. 任务周期超过30分钟，单Agent容易遗忘或跑偏
4. 需要过程留痕和可追溯的交付记录

## 不适用场景

- 5分钟能搞定的简单问答
- 高度创意性、需要统一风格的单一产出
- 任务边界模糊到无法定义验收标准
- 对延迟敏感、需要实时交互的场景

## Hive Master 三板斧

### 1. 拆 — 目标到任务的分解协议

```
输入：大目标 / 模糊需求
输出：边界清晰、可独立交付的子任务列表

每个子任务包含：
  - task_id: 唯一标识
  - title: 任务标题
  - description: 详细的要做什么
  - acceptance_criteria: 验收标准（可测试）
  - assigned_to: Worker角色/ID
  - dependencies: 依赖哪些任务完成才能开始
  - estimated_budget: 预估所需token/步数
  - deliverable: 交付物类型（文件/数据/分析报告/代码）
```

### 2. 派 — 任务到BBS的发布协议

每个子任务发到BBS（公共任务账本），作为独立帖子：
- 每个Worker独立领任务
- 结果独立回帖
- 进度一目了然

BBS不是群聊（群聊信息流式的会丢失），BBS是**公共任务账本**——每个任务是一个帖子，每次交付是一个回帖。

### 3. 验 — 三层验收标准

验收不是凭感觉打分，而是回到任务定义：

| 验收层 | 检查项 | 通过条件 |
|--------|--------|---------|
| L1 完整性 | 文件是否生成？内容是否覆盖要求？ | 所有交付物存在且非空 |
| L2 正确性 | 事实是否需要降调？逻辑是否自洽？ | 无事实错误/逻辑矛盾 |
| L3 可用性 | 是否能直接进入下一步？ | 接棒者无需额外追问 |

## Hermes 原生 BBS 实现

```python
# BBS 本质是一个结构化JSON文件（替代群聊）
# 存储于 ~/.hermes/reports/hive_bbs.json

BBS结构:
{
  "hive_id": "hive_20260605_001",
  "goal": "原文目标描述",
  "master": "Hermes",
  "created_at": "ISO时间",
  "budget": {
    "max_rounds": 5,
    "max_tokens": 50000,
    "remaining": 50000
  },
  "tasks": [
    {
      "task_id": "T001",
      "title": "调研竞品A",
      "status": "in_progress",  # pending/in_progress/completed/needs_rework
      "acceptance_criteria": "列出3个竞品的核心功能差异",
      "worker": "Worker_Research",
      "post": {
        "submitted_at": "ISO",
        "deliverable": "/path/to/output.json",
        "summary": "竞品A核心发现..."
      },
      "review": {
        "reviewed_at": "ISO",
        "passed": true,
        "comments": "补充一个数据来源标注",
        "rework_rounds": 0
      }
    },
    {
      "task_id": "T002",
      ...
    }
  ],
  "deficits": [
    # 验收后发现缺口 → 新任务加入队列
    {"deficit_id": "D001", "description": "...", "new_task_id": "T00N"}
  ]
}
```

## 预算机制

### 预算消耗追踪

每次 Worker 交付 + Master 验收算 1 个"预算单位"。
```
budget.remaining -= 1 per round
当 remaining <= 0 → 强制整合交付
当 remaining > 0 但所有任务 passed → Master 检查是否有缺口
  有缺口→新增任务，消耗预算继续
  无缺口→提前交付
```

### 默认预算配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_rounds | 5 | 最大迭代验收轮次 |
| max_tokens | 50000 | 总Token预算 |
| min_improvement | 0.02 | 每轮最少改进量（收敛检测） |
| convergence_window | 3 | 连续N轮无改进则停止 |

## Hermes 集成点

### 1. 与现有delegate_task系统的融合

Goal Hive 不是替代 delegate_task，而是**在delegate_task之上加一层组织协议**：

```python
# 传统用法（单体）
result = delegate_task(goal="完成X")

# Goal Hive 用法（组织）
hive = GoalHive("完成X")
hive.decompose()      # 拆
hive.assign_to_bbs()  # 派到BBS
hive.execute_all()    # Worker并行执行(delegate_task)
hive.review_all()     # Master逐份验收
hive.fill_deficits()  # 发现缺口继续派
hive.deliver()        # 整合交付
```

### 2. 与Agent Company 130人团队的融合

Agent Company 的每位员工天然是 Goal Hive 的 Worker：
- 市场部员工 → 分析Worker
- 设计部员工 → 设计Worker
- 研发部员工 → 技术Worker
- PMO员工 → 规划Worker

Master 根据任务需求选择员工角色。

### 3. 与 Master Loop 9步流水线的融合

Goal Hive 不是替代 9步流水线，而是**包装流水线的组织层**：
- 9步流水线的每一对（采集→评分、分析→设计...）可以用 Goal Hive 的子模式运行
- Master Loop 本身就是一个"Hive Master"在调度9个子Agent

### 4. 与 Production Reliability Engine 的融合

PRE 的 DegradationPreventer 直接作为 Goal Hive 的验收防线：
- 当 Worker 交付含降级关键词时 → 验收不通过 + 记入 deficits
- CriticAgent 审计可作为 Master 验收的第三方验证

## 完整执行流程

```python
class GoalHive:
    """Goal Hive 蜂群协作主引擎"""

    def __init__(self, goal: str, context: str = ""):
        self.goal = goal
        self.context = context
        self.bbs = self._init_bbs()
        self.budget = {"max_rounds": 5, "remaining": 5}
        self.deficits = []

    def run(self) -> dict:
        """全流程：拆→派→并行执行→逐验收→补缺口→交付"""
        # Phase 1: 拆解目标
        tasks = self._decompose()

        # Phase 2: 派到BBS
        self._post_to_bbs(tasks)

        # Phase 3: 预算循环
        while self.budget["remaining"] > 0:
            # 3a: 获取待执行任务
            pending = [t for t in self.bbs["tasks"]
                       if t["status"] in ("pending", "needs_rework")]

            if not pending:
                # 3b: Master检查缺口
                deficits = self._check_deficits()
                if deficits:
                    self.deficits.extend(deficits)
                    new_tasks = self._create_deficit_tasks(deficits)
                    self._post_to_bbs(new_tasks)
                    continue
                else:
                    break  # 所有完成，无缺口 → 提前交付

            # 3c: 并行执行（使用delegate_task）
            for task in pending:
                result = delegate_task(
                    goal=f"完成任务 {task['task_id']}: {task['title']}",
                    context=f"""
                    任务描述: {task['description']}
                    验收标准: {task['acceptance_criteria']}
                    交付物: {task['deliverable']}
                    """
                )
                task["status"] = "completed"
                task["post"]["deliverable"] = result
                task["post"]["submitted_at"] = datetime.now().isoformat()

            # 3d: Master逐份验收
            for task in [t for t in self.bbs["tasks"]
                         if t["status"] == "completed"]:
                review = self._review(task)
                task["review"] = review
                if not review["passed"]:
                    task["status"] = "needs_rework"

            self.budget["remaining"] -= 1

        # Phase 4: 整合交付
        return self._integrate()
```

## 关键设计决策

### 为什么用BBS不用群聊
群聊是流式的——消息刷过去就找不到。BBS是**公共任务账本**——每个任务是一个帖子，每次交付是一个回帖，进度一目了然。BBS可以替换为 GitHub Issues、Linear、数据库队列或任何任务系统。关键不是 BBS 的形态，而是"公共任务账本"这个角色。

### 为什么需要预算驱动
传统 Agent 的问题是"做完就停"——第一版出来就交差，哪怕明显还有改进空间。预算机制把"做完就停"升级成"向可验收交付逼近"。

### 为什么Master不能自己做
Master 只关心三件事：交付了吗？合格吗？还有缺口吗？
Master 不亲自执行，亲自执行的 Master 和单体 Agent 没有区别。

## 验证清单

- [ ] Hive Master能正确拆解目标为边界清晰的子任务
- [ ] 每个子任务有明确的验收标准
- [ ] BBS任务账本能记录全部任务状态
- [ ] Worker并行执行独立交付
- [ ] Master逐份验收，不合格自动返工
- [ ] 有缺口时Master自动创建新任务
- [ ] 预算未耗尽时不默认交差
- [ ] 预算耗尽时强制整合交付
- [ ] 产出可追溯（谁做了什么什么时候）
- [ ] 无缺口时提前交付（不浪费预算）

## 陷阱

- **Master 也是 AI** — 它可能把任务拆太细（20+个子任务失去管理意义）或太粗（等于没拆）。限制：最多12个 Worker 同时运行。
- **Worker 可能跑偏** — 独立 Worker 可能做出与协作上下文不匹配的结果。Master 验收时必须检查"是否与其他 Worker 的交付一致"。
- **预算驱动不是无脑消耗** — 如果收敛检测连续3轮无改进，应该提前停止。min_improvement=0.02 是合理的收敛阈值。
- **BBS 文件不能太大** — 超过100KB的BBS文件本身会成为上下文负担。定期归档已完成任务到 hive_bbs_archive.json。
- **Goal Hive有组织税** — 不是免费午餐。Worker 越多，调度成本、上下文成本和结果不一致的风险也越高。当任务不值得拆时，不要开蜂巢。

## 回滚方案

### 快速回滚
1. 删除本skill：`skill_manage(action='delete', name='goal-hive-orchestrator')`
2. 恢复原有的单体 delegate_task 模式

### 数据安全
- BBS文件备份在 `~/.hermes/reports/hive_archive/`
- 所有配置在 `~/.hermes/config/goal_hive_config.json`
