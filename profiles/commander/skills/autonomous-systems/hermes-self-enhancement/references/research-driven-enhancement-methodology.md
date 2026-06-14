# 研究驱动型增强计划 — 2026-06-01 调研成果

## 方向A: Agent长程任务执行方法论

### 1. Anthropic Extended Thinking
- **机制**: 模型在回答前输出"thinking"块展示推理过程，延长内部推理时间
- **可借鉴**: 复杂任务前先输出思考过程(非对外输出，作为内部规划)
- **Hermes融合**: 可在agent/monitor.py中实现"pre-task thinking"阶段
- **价值**: 8/10

### 2. MetaGPT 多Agent文档驱动
- **机制**: 角色分离(PM→架构师→工程师→QA) + 文档驱动(需求→设计→方案→代码)
- **可借鉴**: Hermes 130员工+390专家可构建"软件工程SOPs"模板流水线
- **核心**: 前一个Agent的输出作为后一个Agent的上下文
- **价值**: 9/10

### 3. LangGraph StateGraph检查点
- **机制**: 有向图节点=步骤，每节点后保存完整状态快照
- **可借鉴**: 长任务每步保存检查点，支持中断恢复+状态回放
- **Hermes**: agent/reflector.py的MonitorEngine已实现检查点间隔检测
- **价值**: 9/10

### 4. Stanford小镇 生成式Agent记忆架构
- **机制**: 三循环(观察→反思→规划) + 记忆金字塔(事件→近期→反思→规划)
- **可借鉴**: Hermes Hy-Memory可直接映射：memory_semantic(语义)=反思,L2场景=规划
- **价值**: 10/10

### 5. Voyager 自主技能发现
- **机制**: 自动检测能力边界→生成刚好超出能力的课程→学习→入库→组合
- **可借鉴**: Hermes Skill库(188个)可增加能力边界扫描+自动推荐新Skill
- **价值**: 7/10

### 6. Reflexion (Shinn 2023)
- **机制**: Actor(执行)→Evaluator(评估)→Reflector(反思)三角循环+长期记忆
- **可借鉴**: 失败任务自动做根因分析→生成改进策略→存入经验池→未来自动检索
- **Hermes**: agent/reflector.py已实现ReflectorEngine
- **价值**: 8/10

---

## 方向B: 软件工程任务全流程方法论

### 1. Amazon 6页纸 + Tenets
- **来源**: Amazon内部文档文化(Jeff Bezos)
- **6页纸**: ①背景问题→②解决方案→③实施计划→④成功标准→⑤风险回滚→⑥附录
- **Tenets**: 任务开始前写下不可妥协的决策原则(如"用户体验>开发速度")
- **Hermes**: 复杂任务前强制产出6页纸式分析报告

### 2. Amazon STL (Single-Threaded Leader)
- **机制**: 每个关键项目1个负责人，100%投入不做其他事务
- **借鉴**: 每个重要长任务指定1个"主Agent"(STL)，有完整决策权

### 3. Google Design Doc + ADR
- **机制**: Context→Goals→Non-goals→Design→Alternatives→Trade-offs
- **ADR**: 记录每个架构决策的理由，形成决策历史

### 4. 微软代码审查 <200行/次
- **机制**: 每次审查限制200行以内，超过后效率显著下降
- **借鉴**: Agent代码生成后自动分段，每段≤200行

### 5. 华为IPD TR1-TR6门禁
- **机制**: TR1需求→TR2方案→TR3模块→TR4原型→TR5集成→TR6量产
- **每个TR门禁有明确的退出标准(Exit Criteria)**
- **Hermes**: 任务执行对应TR门禁(见增强计划P2部分)

### 6. Google Testing Trophy
- **机制**: 静态分析(最大)→单元测试→集成测试→端到端测试(最少)
- **借鉴**: Agent代码任务自动执行分层测试

### 7. Definition of Done (DoD)
- **标准DoD**: 代码已审查/测试通过/文档已更新/无已知Bug/性能达标
- **Hermes**: 每类任务有标准DoD清单，完成后自动检查

### 8. Toyota Kaizen 持续改善
- **机制**: 每天改1%而非大变革 + 5 Whys根本原因分析
- **Hermes**: 对应每日03:00自进化引擎的微进化(D4)

### 9. ISO 9001 PDCA
- **Plan-Do-Check-Act闭环**, 每个循环产出是下个循环的输入
- **Hermes**: 长任务直接映射PDCA

---

## 方向C: 自我进化与元认知方法论

### 1. Reflexion三角循环 (已在上方A6详述)
- **关键扩展**: 失败后生成结构化反思格式 → `{任务, 失败观察, 根因, 改进策略}`
- **Hermes融合**: 复盘<60分时触发Reflexion式深度反思(agent/reflector.py)

### 2. Voyager自动课程 (已在上方A5详述)

### 3. OpenClaw三轮反思
- **第一轮**: 执行反馈 — 为什么代码/任务失败？
- **第二轮**: 语义理解 — 代码/输出是否真正解决了问题？
- **第三轮**: 元认知 — 我为什么会犯这个错误？通用教训是什么？

### 4. Google Agent自动调优 (参数自适应+AB测试)
- **动态阈值**: 根据近期数据分布自动调整(如复盘阈值45/60/75/85滑动窗口)
- **A/B测试**: 同时运行A(当前)B(新配置)，自动保留优胜

### 5. 三层认知架构 (执行层/监控层/反思层)
- **执行层**: 直接与环境交互，快速/低开销
- **监控层**: 实时检测异常(重复失败/循环/超时/质量下降)
- **反思层**: 任务结束/瓶颈时深度分析，输出改进方案
- **Hermes**: agent/monitor.py (监控) + agent/reflector.py (反思) 已实现

### 6. GEPA遗传变异
- **5种变异**: 加点/删点/替换/参数调优/交叉重组
- **选择**: 适应度(成功率+效率+通用性+鲁棒性) + 锦标赛选择
- **Hermes**: 每日自进化引擎可对低分Skill做遗传变异操作

### 7. 经验引擎 (Experience Engine)
- **流程**: 执行轨迹→提取经验模板→验证→固化Skill
- **关键技术**: 轨迹抽象化(L居提取通用步骤) + 参数化(硬编码→占位符)
- **Hermes**: 每次任务后自动提取经验片段，验证后升级为正式Skill

### 8. 机器遗忘 (AutoClean)
- **检测**: 错误经验(连续失败)/过时经验(3月未用)/冗余经验(功能重复)
- **策略**: 软删除(标记)+归档(冷存储)+合并(通用版本)
- **Hermes**: 每周清理Hy-Memory和Skill库

### 9. 持续微进化
- **原则**: 每次只改1个参数/Skill的1步/1条规则
- **回滚**: 变更导致下降立即回滚
- **累积**: 每天1%改进，100天=2.7倍

---

## 来源清单 (12个有效来源)
1. https://arxiv.org/abs/2303.11366 — Reflexion (Shinn 2023)
2. https://arxiv.org/abs/2305.16291 — Voyager (Wang 2023)
3. https://github.com/geekan/MetaGPT — 多Agent文档驱动开发
4. https://langchain-ai.github.io/langgraph/ — LangGraph StateGraph
5. https://arxiv.org/abs/2304.03442 — Stanford小镇生成式Agent
6. https://www.amazon.jobs/content/en/our-workplace/leadership-principles — Amazon Leadership
7. https://www.industrialempathy.com/posts/design-doc/ — Google Design Doc
8. https://docs.microsoft.com/en-us/azure/devops/learn/best-practices/code-reviews — Microsoft CR
9. https://www.scrum.org/resources/definition-done — Scrum DoD
10. https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/ — Kaizen
11. https://www.iso.org/standard/62085.html — ISO 9001 PDCA
12. https://www.anthropic.com/research — Anthropic Extended Thinking
