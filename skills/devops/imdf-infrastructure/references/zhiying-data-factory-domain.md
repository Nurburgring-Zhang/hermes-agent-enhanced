# 智影数据工场平台 — 领域知识概要

## 来源
两份文档共4966行: 功能设计文档.md(1715行) + 开发文档.txt(3251行)
已迁移到IMDF的模块见下方。

## 核心设计原则
- **AI优先 + 人工在环**: 大部分功能AI自动执行，同时支持人工审核
- **模块化封装**: 功能封装为独立算子
- **工作流可编排**: 画布拖拽组合算子
- **全生命周期追踪**: 血缘追溯
- **多租户协同**: RBAC+任务分配+看板
- **本地优先**: 不强制上传云端

## 10个AI Agent
1. 需求解析Agent — NLP拆解需求→工作流
2. 采集Agent — 定时/API/RSS自动采集
3. 清洗Agent — 多路并行+自动阈值
4. 预标注Agent — CLIP/BLIP自动打标
5. 质量评估Agent — 多维评分
6. 数据筛选Agent — 多样性/困难样本
7. 工作流编排Agent — 历史最佳实践推荐
8. 模型评测Agent — 跑推理+算指标
9. BadCase分析Agent — 聚类+根因
10. 反馈闭环Agent — 识别短板→触发采集/标注

## 已迁移到IMDF的模块
| IMDF位置 | 行数 | 对应智影章节 |
|----------|------|-------------|
| engines/operators_lib.py | ~250 | 设计第3章 + 开发第4章(44算子) |
| engines/dataset_manager.py | ~200 | 设计第9章(数据集+6格式导出) |
| engines/eval_engine.py | ~195 | 设计第1.5节 + 开发第8章(评测闭环) |
| engines/multi_tenant.py | ~180 | 设计第11章(RBAC) |
| engines/requirement_engine.py | ~200 | 设计第7章(需求管理) |
| engines/crowd_platform.py | ~193 | 设计第8章(众包) |
| engines/data_delivery.py | ~158 | 设计第10章(交付审核) |
| engines/algorithm_review.py | ~277 | 设计第10章(算法审批) |
| engines/stats_dashboard.py | ~286 | 设计第12章(统计看板) |
| engines/oss_triple_bucket.py | ~288 | 设计——(三桶+智能文件夹) |

## 未迁移(后续可做)
- 浏览器扩展采集(Chrome/Edge/Firefox)
- Tauri桌面应用
- PostgreSQL替代SQLite
- 可视化工作流编辑器(画布拖拽算子)
- 阿里云OSS三桶实际部署配置
