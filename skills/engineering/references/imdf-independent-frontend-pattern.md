# IMDF独立前端开发模式

## 背景
FastAPI项目将HTML/CSS/JS内联在Python `r"""..."""` 字符串中，被子Agent多次注入破坏后，前端不再工作。

## 根因
1. 子Agent的sed/patch操作直接在Python文件行号修改 → HTML字符串内部的缩进/括号被破坏
2. 多个子Agent先后注入代码 → `//`注释出现在JS对象字面量内、多余的`}`导致括号不匹配
3. JS语法错误导致整个`<script>`块跳过 → 所有函数未定义

## 修复模式

### 检测方法
```bash
# 检查浏览器中函数是否存在
browser_console(expression='typeof switchTab')  # → "undefined"

# 检查HTML中JS语法
curl -s http://host:port/ | python3 -c "
import sys
h = sys.stdin.read()
s = h.find('<script>')
e = h.find('</script>')
js = h[s:e]
try:
    compile(js, 'test', 'exec')
    print('JS OK')
except SyntaxError as e:
    print(f'SyntaxError: {e.msg} at line {e.lineno}')
"
```

### 修复步骤
1. 创建独立前端文件（frontend/index.html + CSS + JS）
2. 在FastAPI中配置StaticFiles
3. 根路由改为返回独立HTML文件
4. 备选路由保留内联HTML

### FastAPI配置代码
```python
from fastapi.staticfiles import StaticFiles

# 在app定义后挂载
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

# 根路由
@app.get("/")
async def root():
    import os
    frontend_index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_index):
        with open(frontend_index, "r") as f:
            return f.read()
    return HTML_TEMPLATE  # fallback

# 备用画布路由
@app.get("/canvas")
async def canvas_page():
    return HTML_TEMPLATE
```

## 数据API真实优先/mock fallback模式

### 模式
```python
def get_data_api():
    # 1. 优先SQLite真实数据
    real_data = query_sqlite()
    if real_data:
        return real_data
    
    # 2. fallback到mock（仅开发阶段，mock数量≤5）
    return generate_mock_data(total=5)
```

### 运营数据同样处理
```python
def get_ops_overview():
    # 1. StatsCollector真实数据
    report = StatsCollector().get_daily_report()
    if report and report.get("daily_active_users"):
        return {"source": "real", ...}
    
    # 2. SQLite fallback
    counts = query_sqlite_counts()
    if counts.get("imported_data", 0) > 0:
        return {"source": "sqlite", ...}
    
    # 3. mock fallback
    return {"source": "mock", ...}
```
