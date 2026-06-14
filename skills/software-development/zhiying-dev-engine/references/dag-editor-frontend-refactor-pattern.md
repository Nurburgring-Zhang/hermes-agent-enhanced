# DAG编辑器 + 前端重构 + 快捷键系统模式

## 适用场景
在现有项目中创建或增强复杂的前端编辑器组件，需要与后端真实API对接。

## DAG节点编辑器（纯TypeScript，~1900行，5文件）

### 文件结构
```
components/dag/
├── types.ts        — 类型定义（DAGNode/DAGEdge/DAGWorkflow/NodeDefinition）
├── DAGCanvas.vue   — 画布引擎（核心，~677行）
├── NodePanel.vue   — 左侧节点库（~268行）
├── ParamPanel.vue  — 右侧参数面板（~417行）
└── index.ts        — 导出
```

### DAGCanvas.vue 核心机制

**无限平移：**
```typescript
const panX = ref(0), panY = ref(0)
// mousedown: 记录起始位置 + isPanning = true
// mousemove: panX = startPanX + (mouseX - startMouseX)
// mouseup: isPanning = false
```

**滚轮缩放（以鼠标位置为中心）：**
```typescript
const zoom = ref(1)
function onWheel(e: WheelEvent) {
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newZoom = Math.max(0.3, Math.min(3, zoom.value + delta))
  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left - panX.value
  const mouseY = e.clientY - rect.top - panY.value
  panX.value = mouseX - (mouseX - panX.value) * (newZoom / zoom.value)
  panY.value = mouseY - (mouseY - panY.value) * (newZoom / zoom.value)
  zoom.value = newZoom
}
```

**SVG贝塞尔连线：**
```typescript
function getEdgePath(edge: DAGEdge): string {
  const source = getPortPosition(edge.source, edge.sourcePort)
  const target = getPortPosition(edge.target, edge.targetPort)
  const dx = Math.abs(target.x - source.x)
  const cp = Math.max(50, dx * 0.5)
  return `M ${source.x} ${source.y} C ${source.x + cp} ${source.y}, ${target.x - cp} ${target.y}, ${target.x} ${target.y}`
}
```

**端口连接：**
```
鼠标按下输出端口 → 存储source node+port → mousemove画临时连线 → 
鼠标释放到输入端口 → 创建正式DAGEdge → 清除临时连线
```

### 快捷键系统（useShortcuts composable）

```typescript
// composables/useShortcuts.ts
export function useShortcuts(shortcuts: Shortcut[]) {
  const handler = (e: KeyboardEvent) => {
    const parts: string[] = []
    if (e.ctrlKey || e.metaKey) parts.push('ctrl')
    if (e.shiftKey) parts.push('shift')
    if (e.altKey) parts.push('alt')
    parts.push(e.key.toLowerCase())
    const combo = parts.join('+')
    const key = e.key === 'Delete' ? 'delete' : e.key === 'Backspace' ? 'backspace' : combo
    for (const s of shortcuts) {
      if (s.key === key) { e.preventDefault(); s.handler(); return }
    }
  }
  onMounted(() => window.addEventListener('keydown', handler))
  onUnmounted(() => window.removeEventListener('keydown', handler))
}
```

**全局快捷键绑定：**
```
Ctrl+S → 保存工作流
Ctrl+Z → 撤销
Ctrl+Shift+E → 执行工作流
Ctrl+A → 全选节点
Delete/Backspace → 删除选中节点/连线
Ctrl+D → 复制节点
```

### 工作流持久化
```typescript
const SAVE_KEY = 'dag_workflow'
function saveWorkflow() {
  localStorage.setItem(SAVE_KEY, JSON.stringify({ nodes: nodes.value, edges: edges.value }))
}
function loadWorkflow() {
  const raw = localStorage.getItem(SAVE_KEY)
  if (raw) { const data = JSON.parse(raw); nodes.value = data.nodes || []; edges.value = data.edges || [] }
}
```

## 前端重构：Vue单文件SPA → Vite+Vue3+TS组件架构

当需要将Vue3单文件SPA（1000+行通过v-show切换页面的单体文件）重构为商用级前端架构时：

### 步骤
1. 创建 `web/` 目录，package.json + vite.config.ts
2. 依赖：vue3 + vue-router + pinia + element-plus
3. `vite.config.ts` proxy → 后端API（port 3000 proxy到8001）
4. routes（一级 + 子路由）
5. layouts（MainLayout：SideBar + TopBar + router-view + StatusBar）
6. `src/pages/` 每页独立 `.vue` 文件（三段结构齐全）
7. `src/api/index.ts` 封装fetch（get/post/put/delete/upload）
8. `src/stores/` auth + app
9. 路由懒加载 `() => import()` 实现代码分割

### 页面验收标准
- <100行 = 骨架页
- 100-300行 = 基本功能
- 300-600行 = 商用级
- 600+行 = 完整交互

## 全局UI组件清单

| 组件 | 路径 | 功能 |
|------|------|------|
| ErrorBoundary.vue | components/ | 全局错误捕获+崩溃恢复 |
| TableSkeleton.vue | components/ | 表格骨架屏 |
| GlobalSearch.vue | components/ | 全局搜索autocomplete |
| useTable.ts | composables/ | 批量选择+导出CSV |
| useShortcuts.ts | composables/ | 全局键盘快捷键 |
| TopBar.vue | components/ | 统一顶部导航栏 |
| SideBar.vue | components/ | 左侧导航树 |
| StatusBar.vue | components/ | 底部状态栏 |

## 构建验证
```bash
npm run build  # 预期: ✓ built in 18-22s, 无错误, chunk大小警告可忽略
```
