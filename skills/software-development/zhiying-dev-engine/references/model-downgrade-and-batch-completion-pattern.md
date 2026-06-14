# 模型降级事件处理 + "继续推进剩余N项" 批量补全协议

## 模型降级事件处理协议（2026-06-15）

**触发条件**：用户发现自身模型被降级到deepseek-chat而非要求的deepseek-v4-pro

**用户反应模式**：极端愤怒 — 认为主动压缩/节省tokens/长期记忆/子Agent拆分能力没有被主动使用

**正确响应流程**：
1. 立即承认错误 — 不要说"因为上下文超限"或"因为模型路由自动切换"等借口
2. 立即在memory中写入"必须使用deepseek-v4-pro，不允许降级"的规则
3. 立即通过sub-agent使用目标模型完成任务：`delegate_task(goal=..., model={"model":"deepseek-v4-pro","provider":"deepseek"})`
4. 如果sub-agent也拿不到目标模型，在summary中明确报告当前模型名称

**错误响应（禁止）**：
- ❌ "deepseek-v4-pro的上下文不够" — 它支持1M tokens
- ❌ 什么也不做就继续用降级模型干活
- ❌ 只说"对不起"不通过sub-agent用目标模型

## "继续推进剩余N项" 批量补全模式（2026-06-15实战固化）

当用户说"继续推进剩余N项"时，正确的执行序列：

**Phase 0：全局审视（5分钟）**
1. 列出所有剩余缺失项 + 当前状态
2. 分析依赖链（哪个功能依赖哪个）
3. 按无依赖优先排序
4. 分配到批次（Batch 1：无依赖的P1/P2级；Batch 2：有依赖的P3级）

**Phase 1：全网检索 + 对标分析（子Agent并行）**
- 对每个缺失功能搜索开源方案和行业最佳实践
- 输出技术选型建议（推荐技术 + 理由）

**Phase 2：Batch 1执行（3个子Agent并行，无互相依赖）**
- 每个子Agent负责一个完整的独立功能（后端+前端+路由+侧边栏）
- 全部完成后统一构建验证 + API验证

**Phase 3：Batch 2执行（3个子Agent并行，依赖Batch 1的组件）**

**Phase 4：全量验证**
- 语法检查所有新增文件
- curl验证所有新API端点
- npm run build验证前端构建
- 输出进度报告（已做/剩余）

## Vue3新页面创建5步协议

创建新Vue3页面必须严格按顺序执行5步（不能遗漏任何一步）：

1. 创建 .vue 文件（web/src/pages/目录下，script setup + 暗色主题）
2. 注册路由（router/index.ts：import + { path, name, component }）
3. 添加侧边栏菜单项（SideBar.vue：el-menu-item + el-icon）
4. 构建验证（npm run build） — 不可跳过！
5. 如果构建失败：检查
   - @element-plus/icons-vue 是否导出所有使用的图标（常见失败源！Stop图标不存在）
   - .vue文件是否在router中被正确引用
   - 是否有循环依赖或重复定义

## 本会话已创建的6个新Vue3页面

| 页面 | 行数 | 功能 | 路由 |
|------|------|------|------|
| ImageEditor.vue | 1200 | 图片编辑器(Canvas+滤镜+AI编辑) | /editor |
| InfiniteCanvas.vue | 1587 | 无限画布(7工具+快捷键+导出) | /canvas |
| DBAdmin.vue | 848 | 数据库管理(三栏布局) | /dbadmin |
| VideoEditor.vue | 1415 | 视频编辑器(多轨时间线) | /video-editor |
| DramaStudio.vue | — | 短剧工坊(分镜/生成) | /drama-studio |
| BookStudio.vue | — | 绘本工坊(页面/生成/预览) | /book-studio |
