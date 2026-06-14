# IMDF Sprint 3-5 商用化实施参考 (2026-06-12)

## Sprint 3: AI预标注 + 管道监控

### AI预标注 (prelabel_router.py)
- POST /api/prelabel — 3种task_type: detection/classification/tagging
- 调用DeepSeek API -> NanobotAdapter.chat()
- 返回JSON解析: 处理markdown代码块包裹、前导后缀字符
- 前端BBox叠加: SVG bbox-overlay矩形+标签文字+置信度
- prompt模板驱动: 根据task_type构造不同prompt

### 管道监控 (monitor_routes.py)
- /api/monitor/pipeline — 队列深度/运行中任务数/成功率
- /api/monitor/history?minutes=60 — 时间窗口趋势点
- 前端15秒自动刷新

## Sprint 4: 数据浏览器 + 运营看板

### 数据浏览器 (data_browser_routes.py)
- /api/datasets?page=&size=&search=&sort= — 分页数据集列表
- /api/datasets/{id}/preview — 单条数据预览
- 87条mock数据集自动生成
- AG Grid风格: 表头排序/分页器/搜索框/模态框预览

### 运营看板 (ops_dashboard_routes.py)
- /api/ops/overview — 日活/生产量/交付量/平均质量分
- /api/ops/trend?period=7d|30d — 折线图数据
- 前端: 4个Metric卡片(蓝/绿/橙/紫)+Canvas原生折线图

## Sprint 5: 节点化工作流引擎

### 三层节点架构
- 维度节点(dimension): text/image/video/audio/3d/inspiration
- 能力节点(capability): llm/comfyui/sd/seedance/ppt/script
- 功能节点(function): crop/resize/frame_extract/background_remove/merge/loop/upload
- 48节点注册在nodes/registry.py(NodeRegistry单例)

### DAG引擎 (nodes/engine.py)
- build_dag() — 从画布状态构建DAG
- validate() — Kahn拓扑排序+循环检测+类型检查
- execute() — 拓扑序依次执行+port binding数据路由
- execute_parallel() — 独立分支并行化

### 模板系统 (nodes/templates.py)
- 6个预置模板: t2i_basic/video_pipeline/ppt_auto/ai_prelabel/img_upscale/empty
- JSON Schema校验模板合法性

### API路由
- POST /api/workflow/validate — DAG校验
- POST /api/workflow/execute — DAG执行
- GET /api/workflow/templates — 模板列表
- GET /api/workflow/nodes — 节点类型列表
