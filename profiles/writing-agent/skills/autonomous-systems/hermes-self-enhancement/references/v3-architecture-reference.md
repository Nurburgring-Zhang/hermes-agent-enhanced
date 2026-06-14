# V3.0 自我强化系统参考 — 2026-05-20构建

## 来源文档(5份深度研究)

源自D:盘的5份OI/IFC/Mnemosyne文档:
1. `# Open Intelligence (OI) 项目极端详细开发文档（融合增强.md` (~108K字) 
2. `jicheng# Open Intelligence (OI) 项目国内生态开发文档.md` (~54K字)
3. `Hermes_Agent_OpenHuman_自我强化技术解决方案_Windows版.docx`
4. `面向 Hermes Agent与 OpenHuman 等系统的自我强化增强计划.md`
5. `Mnemosyne与任务的全域持久能力提升优化方案.md`
6. `hermes agent自我强化与长期记忆技术解决方案.docx`

## V3模块目录结构

```
~/.hermes/evolution_v3/
  __init__.py                           — 模块描述与架构图
  information_fidelity_core.py          — IFC信息保真核心(589行)
  seven_channel_memory.py               — 七通道记忆引擎(648行)
  task_engine.py                        — DPW双规划器任务引擎(999行)
  self_enhancement_v3_loop.py           — V3自我强化主循环(580行)
  full_system_test_v3.py                — 全系统集成测试(47项)
```

## 核心架构映射

### IFC信息保真核心 → 对应OI§1.2/自我强化v2.0§1.2

| OI概念 | evolution_v3实现 | 文件 |
|--------|-----------------|------|
| 无损压缩管道-路径A(R3Mem可逆) | ReversibleCompression类: zlib层级压缩+哈希校验 | ifc.py |
| 无损压缩管道-路径B(SimpleMem语义) | SemanticCompression类: gzip+结构化元数据 | ifc.py |
| 无损压缩管道-路径C(Delta差分) | DeltaCompression类: zlib+基线哈希 | ifc.py |
| 三路径交叉验证(相似度>0.95) | compress_all_paths(): 解压结果哈希对比 | ifc.py |
| AES-256-GCM加密(DPAPI密钥保护) | encrypt()/decrypt(): cryptography AESGCM | ifc.py |
| 保真度监控(阈值0.95) | record_fidelity_check(): 哈希一致性+日志 | ifc.py |
| 信息论约束 I(Ot;I0)>=theta | health_report(): fidelity_rate统计 | ifc.py |

### 七通道记忆引擎 → 对应OI§15-17/Mnemosyne§5.4

| OI通道 | evolution_v3实现 | 特性 |
|--------|-----------------|------|
| 语义向量通道(LanceDB/candle) | SemanticChannel: n-gram哈希特征向量+余弦相似度 | 128维特征向量 |
| 实体图谱通道(Neo4j/Cypher) | 未实现(依赖Neo4j外部服务) | 需要Neo4j |
| 时间线通道(PostgreSQL/窗口函数) | TimelineChannel: SQLite时序查询+recency评分 | 30天衰减 |
| 关键词/全文通道(Tantivy/BM25) | KeywordChannel: SQLite FTS5 BM25 | unicode61分词 |
| 扩散激活通道(petgraph) | 未实现(依赖petgraph图算法) | 需要petgraph |
| 整合记忆通道(加权仲裁器) | MemoryArbiter: 信号vs噪音过滤+加权融合+去重 | 阈值0.15 |
| Hopfield联想通道(nalgebra) | 未实现(依赖nalgebra线性代数) | 需要nalgebra |
| CLAUDE.md层次化配置 | 未实现(采用Hermes原生SOUL.md体系) | |

关键设计决策:
- 语义通道使用128维n-gram特征向量替代真实ONNX嵌入(零外部依赖)
- BM25 FTS5检索对中文支持有限(基于tokenize=unicode61)
- 仲裁器通过channel_weights.json持久化历史准确率
- 预过滤层借鉴claude-mem"信号vs噪音"策略

### DPW任务引擎 → 对应OI§20-25

| OI组件 | evolution_v3实现 | 特性 |
|--------|-----------------|------|
| 双规划器+见证者 | SystematicPlanner + IntuitivePlanner + Witness | A(BFS) vs B(DFS) |
| 三级纠偏 | apply_correction(): 轻度(引导)/中度(回退)/重度(重置) | 经验库持久化 |
| Task V2七工具 | task_create/list/get/update/stop/claim/output | 文件+SQLite双写 |
| KDN关键决策节点 | 见Witness.detect_drift() | 中文trigram+英文word |
| 依赖管理(blockedBy/blocks) | TaskStore.clear_dependency() | PostgreSQL触发器模拟 |
| 子Agent独立上下文 | 未实现(需要Hermesdelegate_task) | |
| 关联图谱(Neo4j+GNN) | 未实现(依赖Neo4j外部服务) | |

关键设计决策:
- 漂移检测使用中文三字词组+英文word重叠(不使用sentence-transformers)
- 阈值: OK<0.25, mild<0.5, moderate<0.7, severe>=0.7
- 进度接近完成时(>80%)漂移分数乘0.7降低误报
- SEEVERE纠偏触发失败案例注入correction_library.json

### V3自我强化主循环 → 对应OI§36-38/Mnemosyne§8.1

| OI系统 | evolution_v3实现 | 频率 |
|--------|-----------------|------|
| 日级循环(记忆健康+纠偏+安全+AutoDream) | SelfEnhancementLoopV3.run_complete_loop() | 每1分钟(gear_enforcer v3) |
| 周级循环(Sleeptime+任务关联) | 同上(自动在2-5点执行) | 每小时 |
| 月级循环(SAR报告+催化回路) | 同上(+自进化) | 每6小时(独立cron) |
| 催化回路R1(记忆->任务) | step6_task_association() | 每次循环 |
| 催化回路R2(安全->记忆) | step3_security_update() | 每次循环 |
| 催化回路R3(记忆->Skills) | 未实现(需要Skill系统) | |
| 催化回路R4(Hooks->自适应) | step8_catalyst_loops() | 每次SAR |
| SAR三交叉自检 | step7_sar_report() | 每6h |

SAR评分公式:
- 记忆健康 = min(100, total_entries * 0.1)
- 执行可靠性 = witness.consistent_rate
- 安全态势 = IFC.fidelity_rate
- 综合 = avg(三维)
- 等级: S>=90, A>=75, B>=60, C>=40, D<40

## 集成测试结果

```
47/47 全部通过:
  组1 IFC信息保真核心: 8/8 (压缩率31.93x, AES加密, 30KB大文本)
  组2 七通道记忆引擎: 6/6 (语义命中top1, 关键词命中top1)
  组3 DPW任务引擎: 14/12 (任务CRUD+漂移+纠偏+DPW+依赖+并发)
  组4 V3自我强化循环: 8/8 (记忆+纠偏+安全+AutoDream+SAR+催化)
  组5 gear_enforcer集成: 5/5 (模块可导入)
  组6 可靠性测试: 8/8 (空数据+大文本+并发+多次更新)
```

## 已知限制与后续工作

| 限制 | 影响 | 解决方案 |
|------|------|----------|
| 语义向量使用n-gram hash而非真实ONNX模型 | 中文检索精度有限 | 安装candle+ONNX模型后替换_embed |
| 缺少Neo4j依赖(图谱/扩散/Hopfield通道) | 3/7通道未激活 | 安装Neo4j或使用内存图替换 |
| 缺少delegate_task依赖(子Agent) | 子Agent隔离未实现 | 使用Hermes原生delegate_task |
| Drift检测使用trigram而非嵌入 | 长文本差异检测不敏感 | 中英混合场景下精度受限 |
| 无Skill系统集成(R3催化) | 记忆->Skill闭环未实现 | 对接existing skills/目录 |
| Task V2缺少PostgreSQL后端 | 依赖SQLite单文件 | 安装PostgreSQL后切换 |
