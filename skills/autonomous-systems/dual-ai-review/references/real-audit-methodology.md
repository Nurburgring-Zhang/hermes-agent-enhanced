# 真实审核方法（2026-06-10 实战纠正）

## 为什么表面审核无效

表面审核 = 读代码 + 写一段"看起来没问题"的文字。
2026-06-10 会话中，同一个代码库在三次审核中暴露出不同的问题：

| 审核轮次 | 方法 | 发现的问题 | 漏掉的 |
|---------|------|-----------|-------|
| 第1轮 | 扫代码结构 | 0个 | 17个POST缺Body, 44个算子无实现 |
| 第2轮 | 静态AST分析 | 3个低严重性 | 16个端点返回静态JSON |
| 第3轮 | 逐行读+实际运行 | 8个(含高严重性) | — |

根因：**读代码只能发现拼写错误，不能发现运行时错误。**

## 真实审核的5步流程

### Step 1: 模块加载验证
```bash
python3 -c "from api.module import MainClass; print('PASS')"
```
如果导入失败，直接报bug，不用继续审了。

### Step 2: 方法签名逐行检查
对每个函数/方法：
- 检查参数数量是否与调用方一致（跨文件追踪）
- 检查参数类型是否匹配
- 检查POST接口是否有`Body()`绑定
- 检查是否有真正的引擎调用，而不是返回静态JSON

具体检查清单（2026-06-10 实战）：
```
# 每个POST端点都要检查两行:
grep -n "@router.post\|@app.post" file.py  # 1. 这个端点存在
grep -n "Body(" file.py                     # 2. 有Body()绑定
# 如果数量不等 → bug
```

### Step 3: 实际运行验证
对每个函数执行一次真实调用：
```bash
# 直接调Python
python3 -c "
from engines.X import Y
y = Y()
result = y.some_method(param='test')
print('PASS' if result else 'FAIL')
"

# HTTP端点验证
curl -s -X POST http://localhost:8765/api/some/endpoint \
  -H 'Content-Type: application/json' \
  -d '{"test":"data"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('success') else 'FAIL')"
```

### Step 4: 跨文件链路追踪
检查调用链是否完整：
```
HTTP层 (routes_*.py) → 导入引擎类 → 调用引擎方法 → 返回真实数据
```
如果链路中断（路由返回静态JSON、引擎方法没被调用），就是降级实现。

#### 跨文件链路追踪模板
```
1. 找到路由定义 @xxx_router.post("/xxx")
2. 找到路由函数的实现
3. 检查函数体内是否导入了引擎类并调用了方法
4. 如果没有 → 静态JSON（高严重性bug）
5. 如果有 → 检查参数签名是否与引擎方法一致
```

### Step 5: 审核报告
审核者必须说清楚：
1. 我**运行了什么**（不能只说"我看了"）
2. 每个检查点的结果
3. 通过了哪些测试，失败了哪些
4. 失败的根因是什么

### 现场检查
```bash
# 运行时验证命令
curl -s -X POST http://localhost:8765/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"audit_test","password":"test123","role":"admin"}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('OK' if 'username' in d else 'FAIL')"

curl -s -X POST http://localhost:8765/api/crowd/workers \
  -H 'Content-Type: application/json' \
  -d '{"name":"test","skills":["a"]}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('OK' if d.get('success') else 'FAIL')"
```

## 严重性分级

| 级别 | 定义 | 例子 |
|------|------|------|
| 高(致命) | 功能完全不存在/不工作 | 16个端点全返回静态JSON, 44个算子无实现 |
| 中 | 功能存在但有错误 | cube法线错误, concat_file检测不可靠 |
| 低 | 功能正确但可优化 | 类型提示不匹配, 代码重复 |

## 审核通过标准
- 所有高严重性bug已修复
- 中严重性bug修复或有明确的acknowledge
- HTTP端点返回非静态数据
- 引擎方法有真实的逻辑实现（不仅仅是return data）
