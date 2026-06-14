# IMDF 独立前端迁移模式（2026-06-13/15 实战总结）

## 背景
IMDF项目原始前端是43833字符的内联HTML_TEMPLATE（Python r"""...""" 字符串），被多个子Agent的sed/patch注入破坏后全部JS不执行。迁移到独立前端文件后解决了所有问题。

## 迁移步骤

### 1. 创建独立文件结构
```
frontend/
├── index.html          # 主应用入口(单页应用)
├── css/
│   └── main.css        # 深色工业主题样式(24KB)
└── js/
    ├── lib/
    │   └── api.js      # API调用封装(apiGet/apiPost/$
    ├── pages/
    │   ├── dashboard.js    # 首页
    │   ├── datasets.js     # 数据集管理
    │   ├── annotate.js     # 标注工具
    │   ├── canvas.js       # 工作流画布
    │   ├── business.js     # 任务/团队/交付/审核/统计/设置
    │   ├── data-browser-grid.js    # 数据浏览器
    │   ├── lifecycle-pipeline.js   # 生命周期流水线
    │   ├── personal-workspace.js   # 个人工作台
    │   ├── template-pipeline.js    # 模板化流水线
    │   ├── media-production.js     # 图片/视频生产
    │   ├── llm-training-pipeline.js # LLM训练管线
    │   ├── pipeline.js    # 数据处理管线
    │   ├── zhiying.js     # 智影数据工厂
    │   ├── image-editor.js    # 图片标注工具
    │   ├── eval-review.js     # 评测审核
    │   └── data-collection.js # 数据采集
    └── app.js           # 导航路由+应用初始化
```

### 2. FastAPI StaticFiles配置
```python
# canvas_web.py 中添加:
from fastapi.staticfiles import StaticFiles
import os
_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(_frontend_dir):
    app.mount("/css", StaticFiles(directory=os.path.join(_frontend_dir, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(_frontend_dir, "js")), name="js")

# 根路由改为返回独立前端:
@app.get("/", response_class=HTMLResponse)
async def root():
    frontend_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "index.html")
    if os.path.exists(frontend_index):
        with open(frontend_index, "r", encoding="utf-8") as f:
            return f.read()
    return HTML_TEMPLATE  # 备选

# 保留旧入口作为备选:
@app.get("/canvas", response_class=HTMLResponse)
async def canvas_page():
    return HTML_TEMPLATE
```

### 3. 导航路由模式（app.js）
```javascript
const PAGE_RENDERERS = {
  dashboard: renderDashboard,
  datasets: renderDatasets,
  annotate: renderAnnotate,
  workflow: renderWorkflow,
  // ... 所有页面
};

// 关键：动态查找而非缓存引用
function navigate(page) {
  let renderer = PAGE_RENDERERS[page];
  if (typeof renderer !== 'function') {
    renderer = window['render' + page.charAt(0).toUpperCase() + page.slice(1)];
  }
  if (typeof renderer === 'function') {
    renderer();
  }
}
```

### 4. 关键教训
- **不要用sed修改HTML_TEMPLATE** — Python行号≠HTML字符串内位置，会破坏括号匹配
- **检查花括号配对** — `js.count('{') == js.count('}')` 必须成立
- **对象字面量内禁止//注释** — 必须用 `/* ... */`
- **PAGE_RENDERERS动态查找** — 后续加载的JS覆盖全局函数时缓存不会更新
- **每个新页面需要4步注册**：创建JS文件→index.html添加`<script>`→app.js添加PAGE_RENDERERS→index.html添加导航菜单项

## 结果
- 从4个tab按钮（经常坏）→ 21个导航菜单项（稳定）
- 从43833字符单文件 → 16个独立JS文件（303KB, 6569行）
- 子Agent可以安全地单独修改一个页面JS文件而不影响其他页面
