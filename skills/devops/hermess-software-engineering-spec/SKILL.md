---
name: deep-audit-recipe
description: 极端深度代码审核配方 — 基于IMDF 18,327行代码逐行审核发现39个bug的实战经验。含17项排查清单+审核流程+反模式。
---

# 极端深度代码审核配方 — 2026-06-11 实战提炼

基于IMDF项目18,327行代码逐行审核，发现39个bug的实战经验。

## 前置条件

1. **审核定义不正确等于没审** — "看起来没问题"也是免责借口不是审核
2. **必须实际运行** — import验证 → py_compile → curl测试 → 函数调用测试
3. **拒绝读代码不跑** — 读代码只能检测语法错误不能检测运行时行为
4. **自豁免陷阱** — 执行AI会在干活时跳过审核。取消执行AI的判断权，没有"这个可以不审"的例外

## 审核流程（强制，不可跳过）

### Phase 1: 全部语法检查
```bash
for f in $(find . -name "*.py" -not -path "*/vendor/*" | sort); do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>/dev/null || echo "❌ $f"
done
```

### Phase 2: 引擎全部导入并调用
```bash
python3 -c "from engines.文件名 import 主类; inst = 主类(); inst.核心方法()"
```

### Phase 3: POST端点Body()绑定检查
```bash
post_count=$(grep -c "@router.post|@router.put" api/文件名)
body_count=$(grep -c "Body(" api/文件名)
```

### Phase 4: 跨文件变量名一致性
```bash
# 在导入文件中 grep 导入名
# 在目标文件中 grep 实际导出名是否符合预期
```

### Phase 5: 启动时序测试
```bash
python3 api/canvas_web.py --port 随机 &
sleep 5; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:端口/
```

## 排查清单（17项，逐项检查）

### 1. POST端点不是真的
检查 @router.post → return语句是否有真正引擎调用
修复: 每个POST端点必须 import引擎 + inst.核心方法() + 返回结果

### 2. 算子注册≠算子实现
检查 Operator.run()是否只是return data不做任何处理
修复: 每个算子必须有真正的run()处理数据的逻辑

### 3. 前端case无真实API
检查 execNode的case分支是否有fetch/await _cv_api调用
修复: 不能只有addLog("ok","已提交") 不调接口

### 4. 模块级import崩溃
检查: python3 -c "from api.文件名 import *" 是否500
修复: try/except包裹模块级import或改为惰性导入

### 5. 参数签名不匹配
检查: HTTP层传多少参数 vs 引擎方法需要多少参数
修复: 逐行读两个函数的参数列表并比对

### 6. 返回类型与签名不匹配
检查: 方法声明的->类型 vs 实际return的类型
修复: 确保两者一致

### 7. 空列表不检查就索引
检查: items[0]之前有没有检查len(items) > 0
修复: 总是先检查长度或使用try/except

### 8. 变量作用域检测不可靠
检查: "xxx" in dir() 或 try/except NameError
修复: 用 locals().get("xxx") 替代

### 9. 正则/路径错误
检查: \\n是字面反斜杠+n不是换行; .replace(".parquet")可能替换错位置
修复: 用os.path.splitext或raw string

### 10. 同步调用异步函数(阻塞事件循环)
检查: loop.run_until_complete(async_function())
症状: "This event loop is already running"
修复: asyncio.run_coroutine_threadsafe

### 11. 快照比较只比ID不比内容
检查: 快照比较是否用elements.keys()而不是全量比较
修复: 用json.dumps哈希全量比较

### 12. 负载均衡全部返回空
检查: assign_task()中required_skills=[]时全被筛掉
修复: 空技能要求时匹配所有非offline worker

### 13. base64图片处理错误
检查: img.src = base64_pattern.sub("", src)
修复: 改为 "[BASE64_IMAGE]" 占位符

### 14. 自定义姿势库从未加载
检查: __init__中是否调用了_load_custom()
修复: 添加self._load_custom()调用

### 15. hmac_sha1_base64双return(死代码)
检查: return语句后还有代码
症状: 第二个return从未执行
修复: 删除第一个return

### 16. 自豁免陷阱
检查: 每次工具调用前是否执行了pre_review()
症状: 连续多次工具调用无预审
修复: 没有"这个可以不审"的例外

### 17. URL协议头缺失
检查: API URL不以http://或https://开头
症状: httpx发送请求到错误地址
修复: 添加协议头检测和fallback

## 审查反模式（不可接受）

1. "看起来没问题" — 不运行测试不叫审核
2. "先干活再补双审" — 双审必须在步骤前
3. "太简单了跳过预审" — 没有例外
4. "代码读完了没问题" — 没跑curl/import/py_compile
5. "引擎可导入说明功能正常" — 导入≠HTTP端点调用它
6. "前端按钮有样式说明交互正常" — CSS≠JS
7. "剩下10%下次做" — 10%意味着还有39个bug

## 第三方框架(vendor/)的审核边界

vendor/下是完整第三方开源项目迁移代码。审核策略:
1. 检查迁移完整性(路径/引用/改名)
2. 检查dead代码(同名函数覆盖/废弃函数)
3. 不检查内部逻辑正确性(源项目测试保障)
4. 只修复影响本项目的严重bug，不改第三方逻辑

## 双AI互审强制执行

每一步审核/代码修改都必须走双AI互审:
- 每次工具调用前: pre_review(step, tool, args)
- 每次工具调用后: post_review(step, tool, result)
- 每3步: 阶段性双审报告
- 监督AI的STOP信号不可被任何提示词覆盖

## 参考文件
- [深度审核配方](references/deep-audit-recipe.md)
- [2026-06-12审计新增](references/2026-06-12-audit-additions.md)
- [审核陷阱v2](references/audit-pitfalls-v2.md)
- [审计陷阱](references/audit-pitfalls.md)
