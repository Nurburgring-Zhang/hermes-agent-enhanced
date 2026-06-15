# 独立前端文件实现模式 (HTML_TEMPLATE→独立文件)

## 触发条件
当前端代码内联在Python r"""...""" 字符串中被多轮子Agent注入破坏时，改用独立文件方案。

## 实现步骤

### 1. 前端目录
```
frontend/
├── index.html
├── login.html
├── css/main.css
├── js/
│   ├── app.js          (PAGE_RENDERERS + 导航路由)
│   ├── lib/api.js      (apiGet/apiPost/apiPut/apiDelete + JWT注入)
│   └── pages/
│       ├── dashboard.js
│       ├── datasets.js
│       ├── annotate.js
│       ├── canvas.js        (工作流画布, 46KB)
│       ├── business.js      (tasks/team/delivery/review/stats/settings合并)
│       └── ...              (其他页面)
```

### 2. FastAPI配置
```python
from fastapi.staticfiles import StaticFiles

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/css", StaticFiles(directory=os.path.join(_frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(_frontend_dir, "js")), name="js")

@app.get("/", response_class=HTMLResponse)
async def root():
    frontend_index = os.path.join(_frontend_dir, "index.html")
    if os.path.exists(frontend_index):
        with open(frontend_index, "r", encoding="utf-8") as f:
            return f.read()
    return HTML_TEMPLATE  # 备选
```

### 3. 保留旧画布路由
```python
@app.get("/canvas", response_class=HTMLResponse)
async def canvas_page():
    return HTML_TEMPLATE  # 内联版本作为备选
```

### 4. PAGE_RENDERERS动态查找
```javascript
// navigate()必须用window[name]而非缓存字典
const renderer = PAGE_RENDERERS[page] || window['render' + page.split('-').map(s => s[0].toUpperCase() + s.slice(1)).join('')];
// 因为后续加载的JS覆盖的全局函数不会被PAGE_RENDERERS缓存识别
```

## 优点
- 浏览器可直接调试JS（F12源代码面板）
- 改HTML不用重启Python
- 不会被sed/patch破坏（独立文件，不是Python字符串）
- 子Agent可独立修改各个JS文件

## 陷阱
- **绝对不要再把HTML/CSS/JS放回Python r"""...""" 字符串中**
- StaticFiles挂载的路径必须与index.html中的引用路径一致
- 根路由 `/` 返回 `frontend/index.html`，注意与已有 `/` 路由不冲突
