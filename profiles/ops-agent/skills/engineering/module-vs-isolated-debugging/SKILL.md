---
name: module-vs-isolated-debugging
description: 模块调用返回0但单独测试正常 — Python调试方法论，处理导入模块状态污染和连接池问题
category: engineering
version: 2026-04-23
trigger: Python模块函数在模块上下文返回0/None/空但单独测试正常时的调试
---

# 模块上下文 vs 隔离测试 — Python调试方法论

## 触发条件
Python模块中定义的函数通过`from module import fn; fn()`调用返回异常结果（0/None/空列表），但单独复制代码测试完全正常。

## 典型症状

```python
# 模块定义
def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": UA})) as r:
        return r.read()

def collect_solidot():
    raw = fetch("https://www.solidot.org/index.rss")
    items = parse_rss(raw)
    return items

# 问题
from mymodule import collect_solidot
collect_solidot()  # 返回 [] — 但单独测试正常
```

## 诊断流程

### Step 1: 隔离测试底层
```python
# 直接复制底层逻辑测试，不走模块
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ua = "Mozilla/5.0..."
req = Request("https://www.solidot.org/index.rss", headers={"User-Agent": ua})
with urlopen(req, timeout=10) as r:
    raw = r.read().decode()
# 如果这里返回正确数据，问题在模块封装层
```

### Step 2: Monkey-patch追踪
```python
import mymodule as mod

original = mod.fetch
def debug_fetch(url, **kwargs):
    result = original(url, **kwargs)
    print(f"fetch({url[:50]}): {len(result)} bytes, status={result!r[:20]}")
    return result
mod.fetch = debug_fetch

# 现在运行
mymodule.collect_solidot()  # 观察哪步返回空
```

### Step 3: 检查模块状态
```python
# 模块可能有初始化状态污染
import mymodule
print(dir(mymodule))  # 查看模块级变量
print(mymodule.__dict__)  # 完整状态

# 检查是否有类实例状态
if hasattr(mymodule, 'session'):
    print(mymodule.session)  # 可能是复用连接导致问题
```

## 根因类型

### 1. 连接池/会话状态
模块在顶层创建了`requests.Session()`或`http.client.HTTPSConnection`，复用时连接失效。
**解决**：在函数内部创建新连接，或传入`session=None`参数。

### 2. 全局状态覆盖
模块顶层修改了全局变量，后续调用使用旧状态。
**解决**：在函数开始打印所有全局状态。

### 3. 导入顺序问题
模块A依赖模块B，导入顺序导致B未初始化完成。
**解决**：`import module; module.init()`显式初始化。

### 4. 多线程竞态
模块使用了共享可变状态，多线程并发时产生竞态。
**解决**：添加锁，或在线程局部存储中运行。

## 通用解决方案模板

```python
def collect_platform_safe(url, parse_fn, max_retries=2):
    """安全采集模板：隔离连接+重试"""
    from urllib.request import Request, urlopen
    import time
    
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0"
    
    for attempt in range(max_retries):
        try:
            # 每次都创建新的请求，不复用任何连接状态
            req = Request(url, headers={"User-Agent": ua})
            with urlopen(req, timeout=15) as resp:
                raw = resp.read().decode('utf-8', errors='replace')
            
            if len(raw) > 100:
                return parse_fn(raw)
        except Exception as e:
            if attempt == max_retries - 1:
                return []
            time.sleep(1)
    return []
```

## Hermes中的应用

**文件**：`/home/administrator/.hermes/scripts/unified_collector_v5.py`

**问题**：模块内`fetch`在循环中对某些域名返回0字节。

**原因**：模块顶层可能维护了连接状态，某些平台在连接复用时返回空。

**已验证解决方案**：在采集器函数内部直接用`urllib`创建新连接，不依赖模块的`fetch`。

## 验证步骤

修复后必须验证：
```python
# 1. 模块调用
from unified_collector_v5 import collect_solidot
items1 = collect_solidot()

# 2. 连续调用（测试状态稳定性）
items2 = collect_solidot()
items3 = collect_solidot()

# 3. 全部应为非零
assert len(items1) > 0, "Module call failed"
assert len(items2) > 0, "Second call failed"
assert len(items3) > 0, "Third call failed"
print("All OK")
```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
