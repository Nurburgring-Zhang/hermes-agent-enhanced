# 极端深度代码审核配方 — 2026-06-11/12 实战提炼

基于IMDF项目18,327行Python + vendor/crawl4ai 50,207行第三方代码的逐行审核实战。发现在当前所有"审核会话"中从未被发现的36个bug。

## 前置条件

1. **审核定义不正确等于没审** — "看起来没问题"是免责借口不是审核
2. **必须实际运行** — `import`验证 → `py_compile` → `curl`测试 → `python3 -c "from x import y; print(y())"` 函数调用测试
3. **拒绝读代码不跑测试** — 读代码只能检测语法错误不能检测运行时行为
4. **自豁免陷阱是最大敌人** — 执行AI会在干活时跳过审核。取消执行AI的判断权，没有"这个可以不审"的例外

## 审核流程（四阶段，强制，不可跳过）

### Phase 1: 全部语法检查
```bash
for f in $(find . -name "*.py" -not -path "*/vendor/*" | sort); do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>/dev/null && echo "  ✅ $f" || echo "  ❌ $f"
done
```

### Phase 2: 引擎全部导入并调用
```bash
python3 -c "from engines.文件名 import 主类; inst = 主类(); print(inst.核心方法())"
```
**必须跑真实调用，不是只import。** `import`成功不代表任何函数可以被调用。

### Phase 3: API端点真实测试（HTTP级）
```bash
# 启动服务
python3 api/canvas_web.py --port 8765 &
sleep 6

# 每个POST端点必须跑curl验证
curl -s -X POST http://127.0.0.1:8765/api/xxx \
  -H 'Content-Type: application/json' \
  -d '{"param":"value"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success'))"
```

### Phase 4: 前端交互验证（浏览器打开实际点击）
```bash
# 浏览器验证每个交互按钮的真实行为
# 检查execNode的case分支是否有真实API调用
grep -A5 "case'xxx'" api/canvas_web.py
```

## 20项排查清单（逐项检查）

### 1. POST端点不是真的（高严重性）
**检查:** `grep "@router.post\|@router.put" api/*.py` — 每个端点的return语句是否有真正引擎调用
**发现:** routes_extended.py 16个端点全部 `return {"success": True, "data": {**data}}` 返回静态JSON
**修复模版:**
```python
@crowd_router.post("/workers")
def create_worker(data: Dict[str, Any] = Body(...)):
    import uuid
    from engines.crowd_platform import CrowdPlatform
    cp = CrowdPlatform()
    worker_id = f"w_{uuid.uuid4().hex[:8]}"
    result = cp.register_worker(worker_id, data.get("name"), data.get("skills"))
    return {"success": True, "data": result}
```

### 2. POST端点Body()绑定缺少（高严重性）
**检查:** `post_count=$(grep -c "@router.post\|@router.put" api/xxx.py); body_count=$(grep -c "Body(" api/xxx.py); [ $body_count -lt $post_count ] && echo "❌ 缺少Body绑定"`
**发现:** 17个POST端点用`data: dict`而不是`data: Dict[str, Any] = Body(...)`
**修复:** FastAPI不会自动解析JSON body除非用`Body()`或Pydantic模型

### 3. 算子注册≠算子实现（高严重性）
**检查:** Operator类是否有默认`run()`直接`return data`不做任何处理
**发现:** 44个算子全部只有meta信息没有真正的run_func
**修复:** 每个算子必须有处理数据的真实逻辑

### 4. 前端case无真实API调用（高严重性）
**检查:** execNode的每个case分支是否有`await _cv_api()`或`fetch()`调用
**发现:** `case'comfyui'`只有`addLog('ok','→ 已提交')`不调接口; `case'llm'`调的是`/engine/plan`不是AI对话
**修复:** 每个case分支必须有真实API调用

### 5. 模块级import崩溃（高严重性）
**检查:** `python3 -c "from api.文件名 import *"` 不报错
**发现:** `auth_routes.py`的`from passlib.context import CryptContext`在bcrypt版本不兼容时整个模块崩溃
**修复:** `try/except`包裹模块级import，或改为惰性导入

### 6. 参数签名不匹配（中严重性）
**检查:** 逐行比对HTTP层传参和引擎方法签名
**发现:** crowd_platform的`register_worker(worker_id, name, skills)`需要3参数，HTTP层只传了name和skills
**修复:** 在HTTP层自动生成worker_id后传入

### 7. 返回类型与签名不匹配（中严重性）
**检查:** 方法声明的`-> Type` vs 实际`return`的对象类型
**发现:** `run_eval(self, task, test_samples) -> EvalTask`实际返回`(task, results)`元组

### 8. 跨文件变量名不一致（高严重性）
**检查:** 在导入文件中grep导入名, 在目标文件中grep实际导出名
**发现:** canvas_web.py的`from api.routes_extended import require_router`但实际导出名是`req_router`

### 9. 变量作用域检测不可靠（中严重性）
**检查:** `"xxx" in dir()`的用法
**发现:** video_composer.py用`"concat_file" in dir()`检测变量是否定义——不可靠（可能因作用域规则意外返回False）
**修复:** 用 `locals().get("concat_file")` 替代

### 10. 正则/路径/字符串处理错误（中严重性）
**检查:** 正则中`\\n`是字面反斜杠+n不是换行符; `.replace(".parquet", ".jsonl")`可能替换错误位置(如果路径中有类似字符串)
**修复:** 用 `os.path.splitext` 或 raw string; `.replace`只在已知安全时用

### 11. 同步调用异步函数阻塞事件循环（高严重性）
**检查:** `loop.run_until_complete(async_function())` 在已有事件循环的上下文中
**发现:** resource_library.py的`_resolve_source`用`loop.run_until_complete(_fetch_remote(url))` — 在FastAPI异步路由中会抛RuntimeError
**修复:** `asyncio.get_running_loop()` 存在时直接用 `await`，不存在时用 `asyncio.run()`

### 12. 快照比较只比ID不比内容（中严重性）
**检查:** 撤销/历史栈的快照比较是否只对比元素ID列表
**发现:** canvas_core.py的`HistoryManager.commit`用`sorted(e.id for e in elements)`比较——如果元素坐标变了但没增减，误判为"无变化"
**修复:** 用 `json.dumps({e.id: asdict(e) for e in elements}, sort_keys=True)` 哈希全量比较

### 13. 空技能分配导致全部筛掉（中严重性）
**检查:** `assign_task()`中`required_skills=[]`时所有worker被筛掉
**发现:** crowd_platform.py在`required_skills`为空时，`set() & set(w.skills)`永远为空
**修复:** 空技能要求时匹配所有非offline worker

### 14. 自定义资源从未加载（低严重性）
**检查:** `__init__`中是否调用了`_load_custom()`
**发现:** data_3d.py的PoseLibrary只有`_load_builtin()`没有`_load_custom()`
**修复:** 在`__init__`末尾添加`self._load_custom()`

### 15. hmac_sha1_base64双return（中严重性）
**检查:** return语句后还有代码（死代码）
**发现:** cloud_storage.py的`hmac_sha1_base64`有两个return——第一个返回bytes，第二个从未执行
**修复:** 删除第一个return

### 16. URL协议头缺失（中严重性）
**检查:** API URL不以`http://`或`https://`开头
**发现:** NANOBOT_HOST默认值是`http://127.0.0.1`，但如果用户设了`127.0.0.1`（无协议头），httpx会报错
**修复:** 添加协议头检测和补全逻辑

### 17. 自豁免陷阱（高严重性，跨会话反复出现）
**检查:** 每次工具调用前是否执行了pre_review()
**症状:** 连续多次工具调用无预审，导致bug漏过
**修复:** 没有"这个可以不审"的例外。执行AI无权自己判断"跳过预审"。

### 18. 闭包延迟绑定（中严重性）
**检查:** 循环中创建lambda/闭包是否捕获循环变量
**发现:** browser_manager.py的`context.route(f"**/*.{ext}", lambda route: route.abort())` — 所有lambda最终使用最后一个ext值
**修复:** `lambda route, e=ext: route.abort()` — 用默认参数立即绑定

### 19. Content-Disposition大小写敏感（低严重性）
**检查:** 比较HTTP头字段时是否忽略大小写
**发现:** `_is_file_download`用`'attachment' in content_disposition` — HTTP头字段不区分大小写
**修复:** `'attachment' in content_disposition.lower()`

### 20. 异步函数中同步调用LLM阻塞事件循环（高严重性）
**检查:** async def函数中是否有`perform_completion_with_backoff`（同步版）调用
**发现:** EmbeddingStrategy.map_query_semantic_space在async def中调用同步perform_completion_with_backoff
**修复:** 使用`aperform_completion_with_backoff`（异步版）+ 相应import

## 审查反模式（不可接受）

1. **"看起来没问题"** — 不运行实际测试不叫审核
2. **"先干活再补双审"** — 双审必须在步骤前执行
3. **"太简单了跳过预审"** — 没有例外，工具调用前必须pre_review
4. **"代码读完了没问题"** — 没跑 `curl`、`import`、`pip_compile` 三件套
5. **"引擎可导入说明功能正常"** — 导入成功 ≠ HTTP端点调用它返回200
6. **"前端按钮有样式说明交互正常"** — CSS按钮存在 ≠ JS点击后有实际API调用
7. **"剩下10%下次做"** — 10%意味着还有未知数量的bug。本次会话修复的36个bug，没有一个是过去任何"审核"中发现的——过去的审核全是读代码不跑测试。
8. **"vendor/第三方代码不用审"** — 虽然不审内部逻辑，但要审dead代码(同名函数覆盖/废弃函数)和迁移完整性(路径/引用改名)。vendor/crawl4ai的imdf_utils.py发现4个bug。

## 第三方框架(vendor/)的审核边界

vendor/下是完整第三方开源项目的迁移代码（如crawl4ai 80文件50,207行），以`imdf_`前缀改名的完整迁入。

审核策略:
1. **检查迁移完整性** — 路径、引用、改名是否一致
2. **检查dead代码** — 同名函数覆盖（两个normalize_url）、废弃的临时函数（normalize_url_tmp）
3. **检查危险的模式** — 如闭包延迟绑定、异步中调用同步
4. **不检查内部业务逻辑** — 源项目测试保障其正确性
5. **修复边界**: 只修复影响本项目运行的bug，不改第三方框架的内部实现逻辑
6. **vendor中发现的bug在实践中占约10%** — 本项目3,734行发现4个bug，本项目54,000+行发现36个bug
