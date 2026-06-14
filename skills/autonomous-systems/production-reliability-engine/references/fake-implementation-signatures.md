# 假装实现检测签名库 (2026-06-10)

## 后端反模式签名

### 1. 静态JSON路由
```python
# ❌ 危险的签名 — 不调用任何引擎
return {"success": True, "data": {"status": "approved", **data}}
```
grep检查: `grep -n "return.*success.*True.*data.*data" routes_extended.py`
期望: 返回的数据应该来自引擎调用，不是简单的 `**data` 回显。

### 2. 只有元信息没有逻辑的算子
```python
Operator(id="filter.null_filter", name="空值过滤", parameters={...})
# ❌ run()的默认实现是 return data
```
检查: Operator类的run()方法是否只用了`return data`。
期望: 至少关键算子有真实 `if self.id ==` 分支。

### 3. HTTP路由有Body()但没有引擎调用
```python
@router.post("/workers")
def create_worker(data: Dict[str, Any] = Body(...)):
    # ❌ 没有 from engines.X import Y; Y().method()
    return {"success": True, "data": {"worker_id": "new_worker", **data}}
```
检查: `grep -B3 "return.*data.*data" routes_extended.py` 看有没有引擎调用。
期望: POST路由的第一行应该import引擎。

## 前端反模式签名

### 1. alert/prompt代替真实API调用
```html
<button onclick="alert('功能说明')">创建</button>
```
grep检查: HTML中alert的出现次数应为0。
期望: 没有任何元素用alert作为交互响应。

### 2. 只有样式没有事件绑定的交互元素
CSS有拖拽样式但JS中没有ondragstart/dragover/drop监听器。
期望: 拖拽/点击/输入/提交全部有JS事件绑定。

### 3. execNode中有"已提交"但没调API
```javascript
case'comfyui':addLog('ok','→ 已提交');break;
// ❌ 没有调用 fetch 或 _cv_api
```
期望: 所有节点类型在execNode中都有真实API调用。

## 跨文件链路追踪检查清单

| 前端元素 | JS函数 | API端点 | 引擎方法 |
|---------|--------|---------|---------|
| createRequirement()按钮 | createRequirement() | POST /api/requirements/create | RequirementEngine |
| 执行全部按钮 | execWF() | 遍历execNode | 按类型调用引擎 |
| drag/drop创建节点 | createNode() | POST /canvas/element | CanvasState |
| ▶执行按钮 | execNode(id) | 按节点类型 | 各引擎run() |

每行都必须完整可追踪，不能有任何一环是"已提交"或占位符。
