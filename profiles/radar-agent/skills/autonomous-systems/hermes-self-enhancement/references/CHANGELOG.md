# 技能更新日志

## 2026-05-19

### 新增: hermes-self-enhancement
- references/comfyui-node-dev-pattern.md — PromptLibraryNode PRO (808行, 45项测试100%)
- references/final-ultra-fusion-pattern.md — FinalUltraFusion超分节点 (1119行, 79项测试100%)
- references/deep-verify-pattern.md — 深度验证体系 (301项资产+46项运行)
- 触发条件新增ComfyUI/upscale/deep_verify关键词
- 新增ComfyUI节点开发pitfall: nonlocal关键字冲突, meshgrid签名, WindowAttention分区要求

### 更新: comfyui (creative)
- references/comfyui-node-architecture-patterns.md 新增FinalUltraFusion架构章节:
  - 9种注意力机制实现细节
  - 9种放大算法参数对比 (3.3M-43.1M)
  - 算法调度器/分块处理/图像调整管道
  - 79项测试10维度全覆盖
  - 18个pitfalls (新增7个custom node开发陷阱)
- SKILL.md新增pitfalls 12-18, 更新When to Use和reference描述

## 2026-05-18

### 更新: hermes-self-enhancement (autonomous-systems)
从v1.0到v2.0:
- 补充完整的脚本清单(8个脚本, 含路径和功能描述)
- 添加漂移检测pitfall: Jaccard匹配50%准确率, 正确做法sentence-transformers或纯Python LocalSemanticEmbedding
- 添加加密层pitfall: 必须先压缩后加密(否则压缩无效)
- 添加审计日志pitfall: 必须哈希链防篡改
- 补充中文分词pitfall: 2字词碎片化问题, 需词汇表+语义联想
- 添加Phase 4压力测试详细结果
- 添加齿轮集成cron配置
- 添加完整触发条件列表
- 添加references/p4-stress-test-report.md

### 更新: gear-interlocking-audit-v3 (autonomous-systems)
从v4.0到v4.1:
- 架构图新增G8齿轮(记忆调度)
- 添加增强子系统表格(LCM DAG/三引擎/上下文/漂移检测/加密/审计)
- 更新关键文件清单(新增8个文件)
- 更新命令速查(新增G8/LCM/MetaThinker/加密/审计命令)

### 更新: task-auto-resume (autonomous-systems)
从v1.0到v2.0:
- 重新组织为三层恢复层级(L1棘轮/L2上下文漂移/L3齿轮调度)
- 添加MetaThinker+ContextEquilibria漂移恢复快速参考
- 添加关键文件清单(含新脚本)
- 添加陷阱: 漂移检测不要用Jaccard, 恢复后需验证LCM DAG完整性
