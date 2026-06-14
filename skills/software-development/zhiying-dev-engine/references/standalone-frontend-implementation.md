# 独立前端实现方案（替代内联HTML_TEMPLATE）

## 背景

IMDF项目原始前端存储在 `api/canvas_web.py` 的 `HTML_TEMPLATE = r"""..."""` 字符串中（约43833字符/864行）。多轮子Agent注入导致：
1. JS花括号不匹配
2. 对象字面量内的非法`//`注释
3. script块整体被浏览器丢弃
4. 侧边栏不渲染，用户只看到空白画布

## 解决方案：独立前端文件

### 目录结构
```
frontend/
├── index.html         # 主入口（不受sed/patch影响）
├── css/
│   └── main.css       # 深色工业主题（CSS变量驱动）
├── js/
│   ├── lib/
│   │   └── api.js     # api()/apiGet()/apiPost()全局封装
│   ├── pages/
│   │   ├── dashboard.js  # 首页渲染
│   │   ├── datasets.js   # 数据集管理(Phase2)
│   │   ├── annotate.js   # 标注工具(Phase2)
│   │   └── workflow.js   # 工作流画布(Phase2)
│   └── app.js         # 导航路由+PAGE_RENDERERS+状态栏
```

### FastAPI配置

```python
from fastapi.staticfiles import StaticFiles

# 在app = FastAPI() 之后
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

# 根路由
@app.get("/", response_class=HTMLResponse)
async def root():
    idx = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(idx):
        return open(idx).read()
    return HTML_TEMPLATE  # 备选

# 保留旧画布备选
@app.get("/canvas", response_class=HTMLResponse)
async def canvas_page():
    return HTML_TEMPLATE
```

### SPA路由（JavScript端）

使用`PAGE_RENDERERS`对象实现简单路由：

```javascript
const PAGE_RENDERERS = {
  dashboard: renderDashboard,
  datasets: renderDatasets,
  annotate: renderAnnotate,
  workflow: renderWorkflow,
  // ... 其他页面
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

### 首页默认视图（格林主人要求的直接呈现）

```
┌─ 今日生产量 ─┐  ┌─ 待审核任务 ─┐  ┌─ 在线人数 ─┐  ┌─ 系统状态 ─┐
│   1,234 条   │  │    56 项    │  │   12 人   │  │  🟢 正常   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘

[📁 上传数据] [🖌️ 开始标注] [🚀 执行工作流] [📊 查看看板]
[📋 创建任务] [👥 邀请成员] [📦 交付数据] [📈 统计分析]

┌─ 最近任务 ──────────────────┐  ┌─ 快速标注 ────────┐
│ 商品图片标注  67% 进行中 ▶   │  │ 🖼️ 拖拽图片到此处  │
│ 车辆检测     100% 审核中 ▶   │  │ 或点击上传        │
│ 医疗影像     0%  待分配 ▶   │  └──────────────────┘
│ LLM数据      100% 已完成 ▶   │
└─────────────────────────────┘
```

## 关键经验

### 1. 前端独立于Python代码
- 不再塞进 `r"""..."""` 字符串
- 修改前端不需要重启Python服务（热更新）
- 不会被sed/patch误伤

### 2. 保留备选入口
- `/canvas` 路由返回旧的HTML_TEMPLATE
- 独立前端出问题时用户还能用画布

### 3. JS加载顺序
```html
<script src="/js/lib/api.js"></script>      <!-- 1. 基础API -->
<script src="/js/pages/dashboard.js"></script> <!-- 2. 页面渲染器 -->
<script src="/js/app.js"></script>            <!-- 3. 初始化+路由 -->
```
- `DOMContentLoaded`中调用`navigate('dashboard')`
- 所有渲染器函数必须在app.js之前加载

### 4. 状态栏自动刷新
```javascript
document.addEventListener('DOMContentLoaded', () => {
  navigate('dashboard');
  refreshStatusBar();
  setInterval(refreshStatusBar, 30000);
});
```

### 5. Common Pitfalls

| 陷阱 | 现象 | 原因 | 解决 |
|------|------|------|------|
| 导航切换无反应 | JS不执行 | 渲染器函数未定义(undefined in PAGE_RENDERERS) | 确认所有renderXxx函数已定义 |
| 指标卡不显示 | 首页白板 | api.js未加载或dashboard.js未加载 | 检查script标签顺序 |
| 404 on JS/CSS | 控制台报错 | StaticFiles挂载路径不对 | 检查app.mount路径是否与frontend/目录一致 |
| 旧页面缓存 | 修改前端后浏览器还是旧版 | 浏览器缓存 | 加`?t=timestamp`或清除缓存 |
