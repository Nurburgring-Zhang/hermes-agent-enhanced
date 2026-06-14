# Nanobot Factory 极端深度逐行审计 —— 2026-06-10/11

## 概况
- 审计对象：`/mnt/d/minimax/nanobot-factory/nanobot-factory/`
- 总代码量：~85,326行后端Python + ~44,033行前端React/TypeScript + 前端HTML
- 审核深度：逐行审查约100,000行代码
- 子Agent使用：5轮共9个子Agent并行审查

## 核心方法论

### 架构（本次验证有效）
1. 分模块并行子Agent审查（server.py / core/ / routes/ / database.py / aigc+llm / production_workbench+omni_gen / data_pipelines）
2. 子Agent审查后必须做独立验证（grep/curl/python3 -c）
3. 不能在API层面停——必须在真实浏览器里点每个按钮
4. 最后输出完整"已知问题清单"（包括未修复的问题）

### 致命陷阱（本次新发现）
1. **跨模块算子IDA不一致** — operators_lib.py和workflow_engine.py的算子ID不同（score.quality vs score.technical_quality）
2. **路由跨文件冲突** — production.py和v2_zhiying.py共享相同路径POST /api/v2/tasks和GET /api/v2/stats/global，FastAPI静默覆盖
3. **数据库碎片化** — database.py / database_manager.py / AnnotationManager 三套独立SQLite数据库
4. **Electron前端在浏览器不可用** — `startGeneration()`函数不存在，API路径缺少前导"/"
5. **子Agent误报P0** — 声称"db_manager.assets是内存字典无持久化"，但database.py其实有SQLite INSERT。每个P0必须独立验证

## 审计结果

### 致命问题（39个P0）
- server.py: 评分是random.uniform随机数
- 44个AI标注算子43个是占位符
- llm_client.py: 缩进错误导致SeedanceClient.generate_video()不发HTTP请求
- aigc.py: 4处async with ClientSession()退出后使用→运行时崩溃
- database.py: 3个表缺失(matrix_assets/assets_fts)，2个参数顺序错误
- omni_gen.py: mock模式generate返回空images后依然调用.save()→崩溃

### 实际可用的功能（经浏览器验证）
- 智影前端7个页面全部可用（需求/资产/任务/数据集/评测/统计）
- AIGC全功能管理系统UI完整可浏览但生成功能不可用
- data_*_pipeline: 全部基于OpenCV/PIL的真实本地处理

### 不可用功能
- AIGC生成（前端startGeneration不存在）
- 44个AI算子（43个不调AI模型）
- unified_executor.py：引用server.py中不存在的函数，完全不可运行
