# Vue3图片编辑器实现模式（2026-06-15实战）

## 适用场景
需要在Vue3+Element Plus项目中添加图片编辑功能（裁剪/滤镜/调整/AI编辑）

## 架构
```
ImageEditor.vue（主页面）
├── 顶部工具栏 — 打开/撤销/导出/缩放控制
├── 左侧工具栏 — 裁剪/调整/滤镜/文字/AI编辑
├── 中央画布 — ImageCanvas组件（托管Canvas元素）
└── 右侧面板 — 选中工具的参数配置
```

## ImageCanvas.vue核心实现
- 使用原生Canvas 2D Context渲染
- 图片加载：`const img = new Image(); img.src = url;`
- 拖拽平移：mousedown/mousemove/mouseup track差值
- 滚轮缩放：wheel事件调整scale + 以鼠标位置为中心平移补偿
- 选框：拖拽绘制矩形覆盖层，getSelection返回{x,y,w,h}
- 棋盘格背景：网格CanvasPattern用于透明区域显示
- 覆盖层：overlayItems数组（text/draw类型），渲染在画布上

## 右侧面板工具实现
- 裁剪：Shift+拖拽选择区域，旋转/翻转用Canvas transform
- 调整（亮度/对比度/饱和度/色温）：Canvas的getImageData → 逐像素处理 → putImageData
- 滤镜（灰度/怀旧/反转/复古等）：预置CSS filter字符串或像素矩阵变换
- 文字：在画布上fillText
- AI编辑：调用POST /api/v2/generate，轮询GET /api/v2/generate/queue/status获取结果

## API对接
```typescript
// 调用ComfyUI编辑
const resp = await fetch('http://127.0.0.1:8001/api/v2/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: prompt.value,
    model: selectedModel.value,
    image: canvasRef.getImageDataURL(), // base64
    width: 512, height: 512, steps: 20
  })
})
const data = await resp.json()
// 回调: 用data.images[0]更新画布
```

## 路由注册
```typescript
// router/index.ts
{ path: '/editor', name: 'editor', component: () => import('../pages/ImageEditor.vue') }
```

## 侧边栏菜单
```vue
<el-menu-item index="/editor">
  <el-icon><EditPen /></el-icon>
  <span>图片编辑</span>
</el-menu-item>
```
