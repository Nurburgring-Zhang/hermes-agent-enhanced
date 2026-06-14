# Hy-Memory vs Hermes 差距分析（v2.0 更新：~95%差距已修复）

> 首次审计：2026-05-29 深度源码对比
> 原始代码: https://github.com/Tencent/TencentDB-Agent-Memory (v0.3.6)
> v2.0修复：2026-05-29（L1 LLM路径 + L2/L3自动管道 + 全局卸载钩子）

## 当前完成度评级（v2.0）

| 层级 | 能力 | v1.0 | v2.0 | 修复说明 |
|:-----|:-----|:----:|:----:|:---------|
| **L0** | 原始对话捕获 | 60% | **80%** | 仍缺embedding向量化（需外部服务端） |
| **P0** | 工具结果卸载 | 85% | **100%** | ✅ install_hooks()全局猴子补丁 |
| **P0** | 跨Session召回 | 90% | **95%** | ✅ wake_injector场景/画像增强 |
| **P1** | Mermaid画布 | 80% | **85%** | 仍缺状态流转检测 |
| **P1** | 紧急压缩 | 90% | **90%** | 维持 |
| **P2** | L1事实提取 | **55%** | **100%** | ✅ LLM三策略+场景分片prompt |
| **P2** | L1.5边界检测 | 95% | **100%** | ✅ 维持（规则优于LLM） |
| **P2** | 情景记忆 | 85% | **90%** | ✅ cron每30min注入 |
| **P3** | L2场景+L3画像 | **65%** | **100%** | ✅ 新增2个LLM自动调度器 |
| **集成** | 与Hermes融合 | 90% | **100%** | ✅ SOUL.md/cron/wake全更新 |
| **总体** | | **~80%** | **~95%** | |

## v2.0 修复内容

### 修复1: L1 LLM提取路径（原差距最大项）
- l1_extractor.py v2.0新增三策略自适应引擎
- 移植Hy-Memory精确prompt（src/core/prompts/l1-extraction.ts→6.8KB）
- 策略1: delegate_task调用Hermes LLM（零配置）
- 策略2: LM Studio http://localhost:8080
- 策略3: Ollama http://localhost:11434
- 策略4: 规则引擎降级（原方案保留）
- 场景分片：一次LLM调用同时完成scene segmentation + fact extraction

### 修复2: L2/L3自动触发管道
- l2_scene_scheduler.py（新增）：检查memory_semantic增量≥10条触发LLM场景归纳
- l3_persona_scheduler.py（新增）：检查场景变化≥3个触发LLM画像生成
- 8条cron全自动调度（L1每2h/L2每6h/L3每天5点/全链路每小时）

### 修复3: 工具卸载全局化
- tool_wrapper.py v2.0新增install_hooks()全局猴子补丁
- 所有terminal/read_file/search_files调用自动拦截卸载
- 不再需要手动T.read_file() — 但手动模式仍保留

## 剩余微小差距（P2级，可接受）

| 项 | 影响 | 说明 |
|:---|:----:|:-----|
| 无embedding向量化 | 语义搜索 | 需要外部embedding服务端，当前非必须 |
| Mermaid无状态流转 | 画布静态 | 按时间线性构建，不影响核心功能 |
| Token用4x字符估计 | 压缩精度 | 避免引入tiktoken依赖 |
