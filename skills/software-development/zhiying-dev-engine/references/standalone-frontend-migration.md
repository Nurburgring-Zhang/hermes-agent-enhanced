# IMDF 前端独立化迁移指南

## 为什么要从HTML_TEMPLATE迁移到独立前端

**问题：** IMDF的整个前端（HTML/CSS/JS）内联在 `api/canvas_web.py` 的 `HTML_TEMPLATE = r"""..."""` 字符串中（~43833字符，864行）。

**根本缺陷：**
1. 多个子Agent并行注入碎片代码 — 花括号不匹配、`//`注释侵入对象字面量、重复函数定义
2. Python编译不会发现JS语法错误 — 只有浏览器运行时报错
3. 任何对Python文件的patch都可能误伤字符串内容（行号对应Python文件而非HTML）
4. 无法做代码热更新（改HTML必须重启Python进程）
5. 无法使用浏览器DevTools做调试

**独立前端的优势：**
- 不受子Agent的sed/patch影响
- FastAPI通过StaticFiles提供静态文件服务
- 可做热更新（改完文件刷新浏览器即可）
- 浏览器DevTools可直接调试
- 前后端分离架构

---

## 迁移步骤

### Step 1: 创建前端文件结构

```
frontend/
├── index.html           # 主入口（结构+引导）
├── css/
│   └── main.css         # 所有样式（深色主题）
└── js/
    ├── lib/
    │   └── api.js       # API调用层（fetch封装）
    ├── pages/
    │   ├── dashboard.js # 首页（指标卡+快捷操作+最近任务）
    │   ├── datasets.js  # 数据集管理（表格+搜索+批量）
    │   ├── annotate.js  # 标注工具（AI预标注+BBox叠加）
    │   └── ...          # 更多业务页面
    └── app.js           # 应用初始化+导航路由
```

### Step 2: 配置FastAPI静态文件服务

在 `api/canvas_web.py` 中：

```python
from fastapi.staticfiles import StaticFiles

# app定义后立即挂载（放在所有路由注册之前）
import os
_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(_frontend_dir):
    app.mount("/css", StaticFiles(directory=os.path.join(_frontend_dir, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(_frontend_dir, "js")), name="js")
```

### Step 3: 修改根路由（优先返回独立前端）

```python
@app.get("/", response_class=HTMLResponse)
async def root():
    """返回独立前端页面(优先)或内联HTML_TEMPLATE(备选)"""
    import os
    frontend_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "index.html")
    if os.path.exists(frontend_index):
        try:
            with open(frontend_index, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return HTML_TEMPLATE

@app.get("/canvas", response_class=HTMLResponse)
async def canvas_page():
    """画布编辑器页面(备选)"""
    return HTML_TEMPLATE
```

### Step 4: SPA路由模式（无框架纯JS）

```javascript
const PAGE_RENDERERS = {
  dashboard: renderDashboard,
  datasets: renderDatasets,
  annotate: renderAnnotate,
  // ...
};

function navigate(page) {
  // 更新导航高亮
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navItem) navItem.classList.add('active');
  
  // 渲染页面
  const renderer = PAGE_RENDERERS[page];
  if (renderer) renderer();
}
```

### Step 5: 页面JS通过script标签加载

```html
<script src="/js/lib/api.js"></script>
<script src="/js/pages/dashboard.js"></script>
<script src="/js/pages/datasets.js"></script>
<script src="/js/pages/annotate.js"></script>
<script src="/js/app.js"></script>
```

---

## 业务页面实现模式

### 页面结构（以数据集管理页为例）

每个业务页面由一个 `renderXxx()` 函数驱动：

1. **设置innerHTML** → 渲染页面骨架（顶栏操作区+表格+分页）
2. **调API获取数据** → `await apiGet('/api/datasets?page=1')`
3. **动态填充DOM** → 遍历数据生成表格行
4. **事件绑定** → 搜索/分页/批量操作通过onclick属性

### 全局工具函数（在api.js中定义）

```javascript
function $(id) { return document.getElementById(id); }
function showModal(html) { /* 通用模态框 */ }
function closeModal() { /* 关闭模态框 */ }
```

---

## 已知陷阱

### 1. 函数定义位置和加载顺序

`PAGE_RENDERERS` 字典中的函数名，必须在 `app.js` 加载**之前**已经被定义。由于script标签是按顺序加载的同步标签，只要 `pages/*.js` 在 `app.js` 之前加载，就不会出现 `renderDatasets is not defined` 错误。

**规则：** 所有页面JS的script标签必须在app.js之前。

### 4. PAGE_RENDERERS 缓存陷阱（2026-06-13发现）

`PAGE_RENDERERS = { pipeline: renderPipeline }` 在加载时立即捕获当时的函数引用。如果 `pipeline.js` 在 `app.js` 之后加载，并重新定义了 `window.renderPipeline`，`PAGE_RENDERERS.pipeline` 仍指向旧引用（占位函数）。

**修复：navigate() 必须用动态查找**
```javascript
let renderer = PAGE_RENDERERS[page];
if (!renderer || typeof renderer !== 'function') {
    // fallback to window dynamic lookup
    renderer = window['render' + page.charAt(0).toUpperCase() + page.slice(1).replace(/-[a-z]/g, m=>m[1].toUpperCase())];
}
```

所有API调用必须用 `.catch()` 包装，否则一个接口挂掉会导致整个页面空白：

```javascript
const data = await apiGet('/api/something').catch(() => ({}));
```

### 3. 业务页面名称必须注册到PAGE_RENDERERS

新增一个业务页面时要做两件事：
1. 创建 `frontend/js/pages/newpage.js`，定义 `renderNewPage()`
2. 在 `frontend/js/app.js` 的 `PAGE_RENDERERS` 中添加 `newpage: renderNewPage`

---

## 验证清单

| 检查项 | 验证方法 |
|--------|---------|
| 首页200 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/` |
| CSS可访问 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/css/main.css` |
| JS可访问 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/js/app.js` |
| 导航菜单完整 | 首页HTML包含所有导航菜单项文本 |
| 画布备选保留 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/canvas` |
| API正常 | `curl -s http://localhost:8765/api/v1/health` |
| 页面切换 | 每个导航点击后content区有变化 |
