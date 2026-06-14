# 纯Canvas 2D无限画布实现模式（2026-06-15实战）

## 适用场景
需要在Vue3项目中实现白板/无限画布功能，对标 Miro/Excalidraw

## 核心架构（~1587行单文件）
```
InfiniteCanvas.vue
├── Canvas渲染引擎
│   ├── Canvas 2D context绘制
│   ├── 无限平移（panX/panY State + transform）
│   ├── 滚轮缩放（zoom State，以鼠标位置为中心补偿）
│   └── 自适应网格背景
├── 7种工具
│   ├── Select (V) — 点击/框选/拖拽移动，射线碰撞检测
│   ├── Rect (R) — 拖拽绘制矩形
│   ├── Ellipse (O) — 拖拽绘制椭圆
│   ├── Line (L) — 拖拽绘制线条
│   ├── Text (T) — 点击创建，双击内容编辑（contenteditable overlay）
│   ├── Freehand (P) — 拖拽涂鸦
│   └── Image — 上传/拖拽/Ctrl+V粘贴图片
├── 右侧面板
│   ├── 属性编辑（X/Y/W/H/旋转/颜色/描边/透明度）
│   └── 图层列表（z-index排序）
├── 顶部工具栏
│   ├── 撤销/重做（history栈）
│   ├── Fit to screen
│   └── 导出PNG/SVG
└── 快捷键系统
    ├── V/R/O/L/T/P 切换工具
    ├── Delete/Backspace 删除选中
    ├── Ctrl+Z 撤销 / Ctrl+Shift+Z或Ctrl+Y 重做
    └── Ctrl+V 粘贴图片
```

## 数据类型
```typescript
interface CanvasElement {
  id: string
  type: 'rect' | 'ellipse' | 'line' | 'text' | 'image' | 'freehand'
  x: number; y: number; width: number; height: number
  rotation: number; fill: string; stroke: string
  strokeWidth: number; opacity: number; zIndex: number
  data: any // text内容或imageData
}
```

## 关键模式

### 碰撞检测（hit-test）
对每种type实现不同的碰撞检测：
- rect: pointInRect
- ellipse: (dx/rx)^2 + (dy/ry)^2 <= 1
- line: 点到线段距离
- text: rect hit（text的bounding box）
- freehand: 逐点距离

### 缩放居中
```typescript
function onWheel(e: WheelEvent) {
  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  const oldZoom = zoom.value
  const newZoom = clamp(oldZoom * (1 - e.deltaY * 0.001), 0.1, 10)
  // 以鼠标位置为中心补偿
  panX.value = mouseX - (mouseX - panX.value) * (newZoom / oldZoom)
  panY.value = mouseY - (mouseY - panY.value) * (newZoom / oldZoom)
  zoom.value = newZoom
}
```

### 导出SVG
对每个element type生成对应的<rect>/<ellipse>/<line>/<text>/<image>标签

### 快捷键冲突
Vue页面中要避免快捷键与浏览器默认行为冲突：
- `Ctrl+S` 需要 `e.preventDefault()`
- text编辑模式下（contenteditable）要禁用所有快捷键

## 路由注册
```typescript
{ path: '/canvas', name: 'canvas', component: () => import('../pages/InfiniteCanvas.vue') }
```

## 侧边栏菜单
```vue
<el-menu-item index="/canvas">
  <el-icon><EditPen /></el-icon>
  <template #title>无限画布</template>
</el-menu-item>
```
