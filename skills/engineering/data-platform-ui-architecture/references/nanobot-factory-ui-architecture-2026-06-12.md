# Nanobot Factory UI架构实战案例 2026-06-12

## 背景
项目有~80个功能分布在4个页面（index/zhiying/studio/workflow）。用户要求"对标Scale AI/Labelbox"设计完整UI架构。

## 完整功能映射

| 功能 | 操作 | 页面 | 点击次数 |
|------|------|------|---------|
| 智影数据工场 | CRUD数据生产管理 | /zhiying (13页面SPA) | 1 |
| AIGC生成 | 图像/视频/3D生成 | /studio.html | 1 |
| 工作流编辑器 | 节点拖拽+参数编辑+执行 | /workflow.html | 1 |
| ML模型管理 | 模型注册、预标注、主动学习 | zhiying→🧠侧栏 | 2 |
| 多模态标注 | 视频帧提取、音频转写 | zhiying→🎬侧栏 | 2 |
| 数据集版本管理 | commit/diff/branch/merge/tag | zhiying→🗂️侧栏 | 2 |
| RBAC权限管理 | 组织/项目/用户角色管理 | zhiying→👥侧栏 | 2 |
| 质量中心 | 质量仪表盘+异常检测+分布分析 | zhiying→📊侧栏 | 2 |
| 资产管理 | 文件/素材CRUD | zhiying→🖼️侧栏 | 2 |
| 需求管理 | 数据生产需求 | zhiying→📋侧栏 | 2 |
| 任务管理 | 标注/生成任务 | zhiying→📌侧栏 | 2 |
| 系统健康检查 | API状态/metrics | /health | 1 |

所有功能1-2次点击可达。

## 三站式导航

```
/index.html (导航门户 — 8卡片)
├── /zhiying (Vue3 SPA — 13项侧边栏)
│   ├── 数据组: 仪表盘📊 资产管理🖼️ 需求管理📋 任务管理📌
│   ├── 开发组: 数据集💾 数据集版本🗂️ ML模型🧠 模型评测🧪
│   ├── 质量组: 统计看板📈 数据治理🔐 质量中心📊
│   └── 协作组: 多模态标注🎬 权限管理🔐 用户管理👥
├── /studio.html (AIGC工作室 — 暗色主题)
│   ├── 🖼️ 图片生成 ✏️ 编辑 🎬 视频 🎲 3D
│   ├── 📁 历史生成
│   └── 🔧 ComfyUI
├── /workflow.html (DAG节点编辑器)
│   ├── ➕ 添加步骤 📋 模板库(3个)
│   ├── 💾 保存/加载 localStorage
│   └── 🚀 执行 POST /api/v2/workflow/execute
└── /health /metrics /api/v2/nodes (直接API访问)
```

## 关键度量

- 首页卡片: 8个
- 智影工场侧边栏: 13项
- 导航树深度: 最多2层
- 首页→功能点击次数: 1-2次
- 所有功能是否可达: ✅
- 无路径功能: 0

## 首页门户规格

- 304行纯HTML+CSS+JS
- 暗色主题 (#0f172a)
- 8卡片2×4网格
- 顶部4个快速导航链接
- 底部API状态自动检测
- 响应式(900px/500px两个断点)

## 智影工场扩展

zhiying.html 从 781 行扩展到 992 行(+211行)，新增：
- 3个menuItems (ML模型/多模态标注/数据集版本)
- 3个完整Vue page (含Element Plus UI组件)
- 15个API调用methods
- 对应的data refs和return导出

## browser实测结果

```
首页(/) — HTTP 200, 9970bytes, 21个可交互元素
zhiying — HTTP 200, 13个menuItems全部注册
studio.html — HTTP 200, 52510bytes
workflow.html — HTTP 200, 15490bytes, 25个可选节点
health — 200
/api/v2/nodes — 25 nodes
```
