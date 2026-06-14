# Nanobot Factory 2026-06-12 — 三AI互审+节点系统+批量队列案例

## 三AI互审模式（行业对标评估+节点体系拆解+商用级差距）

### 3个AI角色分工
| AI角色 | 任务 | 输出 |
|--------|------|------|
| **监督AI-A（行业对标）** | 搜索竞品(Label Studio/CVAT/HF Datasets/FiftyOne/ComfyUI/Scale AI/Clarifai) | 12项差距矩阵+P0-P3分级 |
| **监督AI-B（功能拆解）** | 设计节点体系，对标ComfyUI节点系统 | 60+可组合节点设计 + 3个典型工作流 |
| **监督AI-C（商用级）** | 检查代码质量、架构健康度、安全 | 25节点真实性验证+全链路98 tests |

### 执行流程
1. 执行AI启动3个子Agent并行（角色不同、互不干扰）
2. 监督AI-A仅搜索（toolsets=["web"]）
3. 监督AI-B仅读代码+分析（toolsets=["terminal","file"]）
4. 监督AI-C仅读代码+验证（toolsets=["terminal","file"]）
5. 执行AI收集3份报告后做交叉验证

### 行业差距分析模板
对标来源：Label Studio, CVAT, HuggingFace Datasets, FiftyOne, ComfyUI, Scale AI, Clarifai, Ultralytics Hub
输出格式：功能维度|我们|行业最佳|差距|对标来源
优先级：P0(核心差距)→P3(规模化差距)

### 三AI互审验收报告格式
| 模块 | 分数 | 结论 |
|------|------|------|
| nodes/节点系统 | 99/100 | 25节点全部真实实现 |
| task_queue | 98/100 | 优先级+指数退避+并发控制完整 |
| quality API | 95/100 | 从AssetManager真实读取 |

## 节点系统设计摘要
- 类别: source/filter/label/score/select/export/generate/quality/control (9类)
- 统一接口: `async def execute(self, inputs, params) -> Dict[str, Any]`
- 节点定义: NodeDefinition(id/name/category/inputs/outputs/params)
- WorkflowEngine: DAG拓扑排序(Kahn算法)+逐层并行执行
- 工作流模板: 数据清洗/AIGC生成/全自动数据生产

## 批量任务队列摘要
- 优先级排序(1-10, 1最高)
- 指数退避重试(3s→10s→30s)
- 并发控制(max_concurrent=2)
- 7种状态: PENDING/QUEUED/RUNNING/COMPLETED/FAILED/RETRYING/CANCELLED
- 手动重试+取消+状态查询

## Pipeline状态机摘要
- 8个阶段: RAW_IMPORT→FILTERING→ANNOTATION→AI_GENERATION→QUALITY_CHECK→DATASET_BUILD→EXPORT→COMPLETED
- 状态: PENDING/RUNNING/COMPLETED/FAILED/PAUSED
- 进度自动计算+错误记录+重置

## server.py架构债务警示
- server.py 9526行巨型单体（270+端点）
- 需要拆分为独立路由模块(api/generate_routes.py等)
- 两套并行工作流系统(nodes/ 和 core/workflow_engine.py)
