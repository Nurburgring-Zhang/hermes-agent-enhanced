# 极端逐行代码审核协议（2026-06-10 IMDF实战）

## 核心原则

审核不是搜索关键词或跑测试——是逐行读代码，检查每一行的正确性。

## 逐行审核检查清单

### 1. 导入检查
- 所有`import`语句是否真正需要
- 相对导入（`from ..xxx`）是否可能在非包上下文中崩溃
- 模块级的`try/except import`是否捕获了正确的异常

### 2. 函数签名检查
- 参数数量和名称是否与调用方一致
- 返回类型注解是否与实际return语句匹配
- `async def`的函数体内是否真的用了`await`

### 3. 枚举/常量检查
- 枚举值字符串是否与外部使用一致（如DB存字符串，枚举名用.value）
- 不同模块间的常量ID是否一致（operators_lib vs workflow_engine）

### 4. HTTP路由检查（重点！）
- 每个`@router.post()`/`@app.post()`的`data: Dict = Body(...)`参数——没有Body()时POST请求JSON不会被解析，返回422
- 每个路由的return语句——是不是返回静态JSON而不是真正调用引擎
- 前端JS中`case'xxx'`——有没有真实API调用，还是只有`addLog`

### 5. 伪实现检查（高优先级）
搜索模式：
- `return {"success": True, "data": {...}}` — 静态返回，未调用引擎
- `pass` 作为函数体
- `raise NotImplementedError`
- `TODO`/`FIXME` 注释
- `# 模拟`/`# mock` 注释
- 算子只有注册没有run逻辑
- switch case只有日志没有API调用

### 6. 前端JS检查
- 重复的case标签——JS取最后一个匹配的，前面的不会执行（dead code）
- `addLog`后面有没有真正的`await _cv_api(...)`调用
- HTML中的`onclick`/`onchange`事件是否有对应的JS函数

### 7. 路径安全检查
- `_resolve_local_file`或类似函数是否做了路径穿越防护（`resolved.startswith(normpath(directory))`）
- 文件上传是否检查文件大小

### 8. Python代码质量检查
- `"concat_file" in dir()` — 不可靠的变量存在检测
- `str.replace(".parquet", ".jsonl")` — 不安全的路径替换
- 正则中的`\\n` vs `\n` — 字面反斜杠+n vs 换行符
- `asyncio.create_task()` 在模块初始化时是否没有事件循环

## IMDF审核实战发现的34个bug分类

### 高严重性（16个）
1. routes_extended.py: 16/16 POST端点返回静态JSON，不调用引擎
2. operators_lib.py: 44个算子只有注册没有实现（所有调用返回原数据）
3. canvas_web.js: case'comfyui'只有日志没有真实API调用

### 中严重性（12个）
4. scene_exporter.py: cube法线全指向同一方向（光照错误）
5. scene_exporter.py: empty glTF有无效的primitives列表
6. video_composer.py: `"concat_file" in dir()` 不可靠
7. video_engine.py: 正则`\\n`是字面反斜杠+n不是换行
8. video_engine.py: `from ..api.nanobot_adapter`相对导入会崩溃
9. video_engine.py: 空video_paths列表直接ffmpeg拼接
10. dataset_manager.py: 版本按字符串排序(v1,v10,v2)
11. dataset_manager.py: parquet fallback用.replace不安全
12. crowd_platform.py: assign_task空技能列表筛掉所有worker
13. requirement_engine.py: created_by参数被忽略，从未赋值给Requirement
14. oss_triple_bucket.py: contains比较时value没有转小写
15. zhiying_dev_engine.py: 步骤完整性检查缺失（可跳过Step2到Step3）

### 低严重性（6个）
16. eval_engine.py: run_eval返回类型注解不匹配
17. canvas_web.js: 重复case'image'(dead code)
18. ppt_engine.py: BANNED_FONTS和模板字体冲突
19. ppt_engine.py: 所有slide_type渲染完全相同
20. zhiying_dev_engine.py: step5_dev只检查step4不检查step3
21. canvas_web.py: /api/comfyui/workflows 用POST而不是GET

## 审核执行流程

每轮审核分4个Phase:

**Phase 1: Python语法检查**
```
python3 -c "import py_compile; py_compile.compile('$file', doraise=True)" 
```
对所有.py文件执行，确保至少语法正确。

**Phase 2: 引擎模块真实加载测试**
```
python3 -c "from engines.xxx import MainClass; print('PASS')"
```
验证每个引擎可以被导入，模块级代码（单例、注册表）能正常执行。

**Phase 3: 函数级真实调用测试**
对每个引擎的主要方法传真实参数调用，验证返回值和行为正确。不是"不报错就行"，是检查返回值是否合理。用try/except包裹每个测试，一个失败不影响其他。

**Phase 4: HTTP端到端测试**
启动Web服务，对每个API端点发送真实HTTP请求验证：
- POST端点验证Body()绑定是否生效
- 验证返回的JSON包含真实数据而非静态模板
- 验证路径prefix是否正确（如auth_router prefix="/auth"）
