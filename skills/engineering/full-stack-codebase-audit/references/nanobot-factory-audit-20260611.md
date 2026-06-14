# Nanobot Factory 145,000行全项目极端深度审计实战记录

## 审计概况
- **时间**: 2026-06-10 至 2026-06-11
- **项目**: Nanobot Factory — 145,000行 Python + TypeScript/React 全栈应用
- **方法**: 13批次并行子Agent逐行审核 + 主Agent独立P0验证 + 浏览器实际操作验证
- **结果**: 285个问题（55个P0致命 / 90个P1严重 / 140个P2中等）
- **功能真实度**: 约40%真实可用, 约60%模拟/占位符/未集成

## 子Agent并行审计组织策略

### 文件到子Agent的分配方案

| 子Agent批次 | 负责模块 | 行数 | 模型 | 耗时 | 
|------------|---------|------|------|------|
| 1 | server.py (8944行) | 8,944 | deepseek-chat | 145s |
| 2 | backend/core/ 16个文件 | 3,112 | deepseek-chat | 120s |
| 3 | backend/routes/ 19个文件 | 10,100 | deepseek-chat | 144s |
| 4 | database.py (1672行) | 1,672 | deepseek-chat | 196s |
| 5 | 前端React源码 (44,033行) | 44,033 | deepseek-chat | 228s |
| 6 | aigc.py + llm_client.py | 3,247 | deepseek-chat | 187s |
| 7 | production_workbench + omni_gen | 4,822 | deepseek-chat | 207s |
| 8 | database_manager.py | 1,977 | deepseek-chat | 101s |
| 9 | diffuser/unified_gen/comfyui 3大文件 | 5,755 | deepseek-chat | 101s |
| 10 | skills/unified_exec/production_db/data_pipelines | 12,828 | deepseek-chat | 111s |
| 11 | agent/18个文件 + security + infra + functions + extended | 26,000 | deepseek-chat | 273s |
| 12 | enterprise_api/airi/annotation_enhanced/workflow_lib | 8,592 | deepseek-chat | 107s |
| 13 | 整合系统+剩余文件+数据库API+内存+监控+中控+协作 | ~5,000 | deepseek-chat | 112s 超时 |
| 14 | integrations/ 12个文件 | 8,467 | deepseek-chat | 196s |

### 关键发现：子Agent超时处理策略

**问题**: batch 13（40个小文件约5,000行）在600秒超时后中断。但子Agent已完成了44个API调用（包含36个read_file），说明文件都被完整读取了，只是在总结阶段超时。

**应对策略**:
1. 从子Agent的 `tool_trace` 提取所有 `read_file` 调用 → 确认哪些文件被完整读取
2. 对超时子Agent的任务做二次分配：拆成更小的批次（2-3个文件）
3. 或者放弃重新分配，由主Agent直接 `grep` 扫描剩余文件的关键模式

### 致命陷阱：P0结论未经独立验证

**事件**: 子Agent2审核core/目录后得出 "db_manager.assets是内存字典无持久化" 的P0结论。但主Agent直接 `grep -n 'INSERT INTO\|CREATE TABLE' database.py` 发现database.py有完整的SQLite建表和INSERT语句。database.py的assets通过 `INSERT OR REPLACE INTO assets (32 columns) VALUES (?,...,?)` 真实写入了SQLite。

**教训**: 子Agent只看了一个模块就下了P0结论。真实情况是：存在两套系统——database.py的真实验assets表和core/的PersistentManager独立SQLite。两者共存但互不相关。

**对策**: 每个P0级别断言必须由主Agent独立验证后才能写入最终报告。验证方法：
- 持久化断言 → `grep -n 'INSERT INTO\|CREATE TABLE'` 确认
- 随机数断言 → `grep -n 'random.uniform'` 确认
- 路由存在性断言 → `curl -s http://localhost:8001/xxx` 确认

## 前端浏览器验证策略（关键改革）

### 2026-06-10 之前的做法（失败）
只检查后端API返回200 + 前端HTML文件静态审查。遗漏了：
1. CDN超时/不可达导致页面空白
2. `prompt()` 在WSL浏览器中被静默阻止
3. `ElMessage` 定义在ElementPlus命名空间内但前端直接使用裸名
4. AIGC全功能界面需要Electron IPC才能工作

### 2026-06-11 的做法（成功）
对每个前端的每个功能页面执行：
1. `browser_navigate(url)` 加载页面
2. `browser_console({expression: '...'})` 检查JS错误
3. 验证关键组件： `typeof Vue !== 'undefined'`, `typeof ElementPlus !== 'undefined'`, `typeof startGeneration === 'function'`
4. 点击每个交互元素：菜单项、按钮、输入框
5. 验证弹窗/对话框能正常弹出
6. 验证后端API实际能处理前端的请求
7. **CDN本地化**: 从unpkg下载Vue/ElementPlus到 `backend/static/lib/` 避免CDN不可用

## 发现的关键缺陷模式总结

### 模式1: "空中楼阁"代码
agent/ 目录下18个文件 ~10,500行，包含完整的 AgentLoopEngine/ModelRouter/EnhancedMemorySystem 等，但 server.py 中没有任何导入这些模块的代码。这是一个完全独立的"项目内项目"。

### 模式2: "注册但不执行"代码
functions/ 目录下6个文件~2,200行，全部只有函数注册/定义，没有执行逻辑。

### 模式3: "假实现"代码
enterprise_api.py 的 AIGC生成写入文本 `"Generated image placeholder"` 替代真实图片；server.py 的评分使用 random.uniform() 替代AI模型。

### 模式4: "重叠不兼容"代码
两个 CanvasState 类（infinite_canvas_agent_engine.py 和 infinite_canvas_engine.py）；两个 memory.py（根目录和agent/）；三个独立SQLite数据库（database.py的assets、database_manager.py的nanobot_data.db、AnnotationManager的annotations.db）。

### 模式5: "缩进/IPC依赖"问题
llm_client.py 的 SeedanceClient.generate_video() 构建了payload但没有发送HTTP请求——真正的HTTP请求代码因为缩进错误被放在了DeepSeekClient类内（且位于return之后，永远不会执行）。前端 `startGeneration()` 只存在于Electron preload中，浏览器中调用报 ReferenceError。

## 重要统计数据

| 度量 | 值 |
|------|-----|
| 核心Python文件数 | ~100个 |
| 总审核行数 | ~145,000行 |
| 子Agent批次数 | 14批 |
| 总API调用 | ~450次 |
| 浏览器验证次数 | ~30次 |
| 审核总耗时 | ~5小时 |
| 致命错误 | 55个 |
| 严重错误 | 90个 |
| 中等错误 | 140个 |
