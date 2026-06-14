# WSL浏览器前端加载与交互修复模式

## 问题背景

在WSL环境下运行FastAPI后端 + Vue3前端时，浏览器加载过程有三个独立的问题需要分别处理：

## 问题1: CDN加载超时/不可达

**现象：** `browser_navigate` 超时（30s timeout），页面标题显示正确但snapshot为空或只有静态元素。

**根因：** WSL的浏览器通过Windows网络栈访问，unpkg.com等CDN在国内可能DNS解析慢、被阻断、或返回302重定向后浏览器等待资源超时。

**修复模式：**
```
1. curl -sL --max-time 30 -o backend/static/lib/vue.global.prod.js https://unpkg.com/vue@3/dist/vue.global.prod.js
2. curl -sL --max-time 30 -o backend/static/lib/element-plus.umd.js https://unpkg.com/element-plus
3. curl -sL --max-time 30 -o backend/static/lib/element-plus.css https://unpkg.com/element-plus/dist/index.css
4. 修改HTML中的script/link src: 从CDN URL改为 /static/lib/xxx
5. 在server.py中挂载静态文件: app.mount("/static", StaticFiles(directory="backend/static"), name="static")
```

**验证：** `curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/static/lib/vue.global.prod.js` → 200

## 问题2: 原生JS弹窗在Vue Composition API中被浏览器阻止

**现象：** 点击按钮无反应（没有弹窗），但无js console error。反复点击无变化。

**根因：** Chrome安全策略在异步回调（async function/Vue reactive）中调用 `prompt()` 时静默阻止。Vue `@click` → async await → then链中的prompt被认定为"非用户直接触发"。

**修复模式：**
```javascript
// ❌ 浏览器阻止
async function createReq() {
  const name = prompt('输入需求描述：');
  if (!name) return;
}

// ✅ 正常工作
const ElMessageBox = ElementPlus.ElMessageBox;  // 必须在全局定义
async function createReq() {
  try {
    const { value } = await ElMessageBox.prompt('输入需求描述：', '标题', {
      confirmButtonText: '确定', cancelButtonText: '取消'
    });
    if (!value) return;
    // ... do work
    ElMessage.success('创建成功');
  } catch(e) { /* cancelled - do nothing */ }
}
```

**需要替换的所有模式（6类）：**
1. `const name = prompt('xxx'); if(!name) return;` → `ElMessageBox.prompt`
2. `alert('xxx')` → `ElMessage.success/info/warning/error`
3. `ElMessageBox.prompt` 的 import 方式：CDN模式下必须在script顶层定义：
   `const ElMessage = ElementPlus.ElMessage; const ElMessageBox = ElementPlus.ElMessageBox;`

## 问题3: 浏览器中ElementPlus全局变量作用域

**现象：** `ReferenceError: ElMessage is not defined`

**根因：** CDN加载的ElementPlus UMD包注册为 `window.ElementPlus` 对象。`ElMessage`、`ElMessageBox` 等不是顶层全局变量，必须从 `ElementPlus.xxx` 解构。

**修复模式：**
在 `<script>` 标签开头（Vue app创建之前）定义：
```javascript
const ElMessage = ElementPlus.ElMessage;
const ElMessageBox = ElementPlus.ElMessageBox;
```

**验证：** `browser_console` 执行 `typeof ElMessage !== 'undefined' && typeof ElMessageBox !== 'undefined'` → true

## 浏览器调试三明治协议

每次前端验证必须执行以下3步：

1. **加载验证：**
   ```
   browser_navigate(url)
   browser_console → expression: document.title + ' | ' + (document.querySelector('#app').__vue_app__ ? 'mounted' : 'no')
   ```

2. **交互验证（每个功能页）：**
   ```
   browser_click(button_ref)  → 点击需要交互的按钮
   browser_snapshot()          → 检查是否有dialog/alert出现
   browser_console()           → 检查是否有JS错误
   ```

3. **获取真实错误：**
   当页面看起来"无反应"时：
   ```
   browser_console(clear=true)              → 清空历史
   browser_click(button_ref)                → 重新触发
   browser_console()                        → 检查真实错误
   browser_console(expression='typeof ElMessage !== "undefined"')  → 检查变量存在
   ```
