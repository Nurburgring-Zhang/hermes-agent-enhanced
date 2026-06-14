# 三AI互审互查 + 可组合节点体系方法论

> 基于2026-06-11/12 Nanobot Factory ~145,000行商用级审核实战提炼

## 一、三AI互审互查模式

### 架构

```
执行AI（主力审代码/修bug）  ← 监督AI-C 验证
    │
    ├── 监督AI-A：行业对标（delegate_task并行搜索竞品）
    │     对标对象: Label Studio/CVAT/FiftyOne/ComfyUI/HuggingFace/Scale AI/Labelbox等
    │     输出: 功能差距矩阵（P0-P3分级）
    │
    ├── 监督AI-B：节点体系设计（delegate_task分析项目现有模块）
    │     输出: 可组合节点体系设计(NODE_SYSTEM_DESIGN.md)
    │
    └── 监督AI-C：商用级差距验证（自律审核模式）
          验证: 执行AI的每个结论是否真实
```

### 触发条件
- 格林主人要求"三AI互审"时
- 需要对大型项目(>50,000行)做系统性审计时
- 需要将项目提升到商用级时

### 执行流程

1. **执行AI（主力）**: 立即开始全项目深度审核（需先load deep-audit-recipe）
2. **监督AI-A**: `delegate_task(goal="全网检索对标项目功能差距")` — 并行搜索8+竞品
3. **监督AI-B**: `delegate_task(goal="设计可组合功能节点体系")` — 输出节点分类/接口/工作流模板
4. **监督AI-C**: 在每次工具调用前执行pre_review（自律审核模式）

### 关键经验
- 三个AI必须使用**不同的模型**（普通/标准/困难三级，防止相同错误）
- 监督AI必须作为独立子Agent创建，不是同一个实例的自言自语
- 执行AI的每个"修复了"的声明必须提供 `curl测试返回数据/metrics计数对齐/代码修改diff` 三重证据

---

## 二、可组合节点体系设计方法论

### 设计原则
1. 所有节点统一接口：`(input_type, params) -> output_type`
2. 输入输出类型标准化：`image` / `image[]` / `text` / `video` / `3d_model` / `dataset` / `metadata` / `any`
3. 每个节点可被前端的 React Flow / Rete.js 渲染
4. 节点可序列化为 JSON 格式

### 节点类别（60+节点）

| 类别 | 功能 | 对标 | 数量 |
|------|------|------|------|
| Source | 数据源 | ComfyUI Loaders | 7 |
| Filter | 数据过滤 | 44 Operators | 6+ |
| Label | AI标注 | Label Studio | 7 |
| Score | 评分排序 | FiftyOne | 5 |
| Select | 筛选 | — | 5 |
| Export | 格式导出 | HuggingFace | 6 |
| Generate | AIGC生成 | ComfyUI | 7 |
| Quality | 质量评估 | FiftyOne | 3 |
| Control | 控制流 | ComfyUI | 6 |
| Output | 输出 | — | 4 |

### 节点Schema定义（JSON）
```json
{
  "node_id": "filter.blur",
  "name": "模糊检测过滤",
  "category": "filter",
  "inputs": [{"name": "images", "type": "image[]", "required": true}],
  "outputs": [{"name": "filtered_images", "type": "image[]"}],
  "params": [{"name": "threshold", "type": "float", "default": 0.5}]
}
```

### 后端实现架构
```
backend/nodes/
├── __init__.py      # NodeRegistry + WorkflowEngine + API路由
├── base.py           # NodeDefinition/BaseNode/WorkflowDefinition
├── registry.py       # 自动注册装饰器
├── filter_nodes.py   # 6个过滤节点（封装operators_lib）
├── gen_nodes.py      # 5个生成节点（封装ProviderFactory）
├── quality_nodes.py  # 2个质量评估节点
├── control_nodes.py  # 6个控制流节点
└── export_nodes.py   # 6个导出节点
```

### 典型工作流模板

1. **数据清洗**: source → filter.blur → filter.dedup → label.caption → score.aesthetic → select.top_k → export.jsonl
2. **AIGC生成**: control.batch → gen.text_to_image → gen.image_upscale → export.local
3. **全自动生产**: source.oss → filter.resolution → filter.nsfw → label.caption → label.tagging → score.aesthetic → select.top_k → export.llava

---

## 三、商用级差距分析法

### 对标维度（对标8+产品）

| 维度 | 对标产品 |
|------|---------|
| 可视化工作流 | ComfyUI |
| 自动质量评估 | FiftyOne |
| 数据集版本管理 | HuggingFace Datasets |
| 模型辅助标注 | Label Studio |
| 企业权限管理 | Scale AI |

### 差距分级
- **P0（核心差距）**: 可视化节点工作流编辑器 + 自动质量评估引擎
- **P1（竞争力差距）**: 数据集版本管理 + ML Backend + RBAC多租户
- **P2（生态差距）**: 节点插件市场 + gRPC双API + 多模态标注
- **P3（规模化差距）**: MLOps闭环 + 实时协作 + 合规认证

---

## 四、格林主人交付铁律补充（2026-06-12）

1. **发现"process叫成execute"必须纠正** — 验证函数名用`hasattr(inst, 'method_name')`而非假设
2. **每个功能模块必须确认是"真实还是壳"** — 不满足于"看起来正常"；必须提供curl/metrics/diff三重证据
3. **不满足"有几个问题"——要列全部问题的完整清单** — 每个问题附带文件:行号+代码片段+严重度
4. **审核测试后立即执行"全部修正完善优化"三步一体** — 不能只报问题不修
5. **部署不允许使用Docker等容器工具** — 只能在服务器上直接修改代码验证
