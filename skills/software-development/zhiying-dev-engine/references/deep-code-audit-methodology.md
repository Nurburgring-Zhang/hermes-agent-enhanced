# 极端深度代码审核方法

## 为什么要有这个文件

2026-06-11，格林主人在IMDF项目审核中反复纠正"审核不够深"、"代码审核不带运行测试"、"双审是形式主义"。

纪律: 代码审核必须有可运行证据支持的结论，不是"看起来没问题"。

## 审核的7层深度

### 第1层: 基础检查
- 语法检查: `python3 -c "import py_compile; py_compile.compile('file.py', doraise=True)"`
- 所有文件: `find . -name "*.py" -exec python3 -c "import py_compile; py_compile.compile('{}', doraise=True)" \;`

### 第2层: 模块导入测试
- 每个模块必须实际导入: `from engines.xxx import YYY; print('PASS')`
- 检查是否有循环依赖
- 检查是否有模块级的崩溃（比如模块初始化就抛异常）

### 第3层: 函数调用测试
- 每个公开函数/方法必须实际调用验证
- 检查参数签名是否匹配
- 检查返回值类型是否正确
- 检查异常路径是否被处理

### 第4层: HTTP级端到端测试
- 启动Web应用 → curl POST/GET每个端点
- 验证: HTTP状态码 + JSON响应中的success字段 + data字段结构
- 前端: 验证core HTML功能关键字（拖拽/连线/执行/保存/加载）

### 第5层: 安全漏洞扫描
- grep `run_until_complete` —— 在async路由中调用会崩溃
- grep `eval(` / `exec(` —— 代码注入风险
- grep 路径穿越 —— `os.path.join` + `..` 检查
- grep `_assert_inside` —— 确保路径穿越防护正确实现
- grep 硬编码路径 `/mnt/` `D:\\` `/home/`

### 第6层: 降级实现检测
- 搜索: `placeholder`、`TODO`、`FIXME`、`mock`、`临时`、`假装`、`假的`
- 检查每个POST/GET端点是否返回占位数据而不是真实引擎调用
- 检查前端JS的execNode()函数: 每个case是否调用了真实API还是只addLog

### 第7层: 跨文件链路追踪
- 前端node点击执行 → 前端哪个case → 调用哪个API路由 → 路由调哪个引擎 → 引擎产生什么产出
- 每个步骤都要实际验证: grep函数存在 → curl端点返回 → python import引擎成功

## 审核报告模板

```
=== [模块名] 逐行审核 ===
行XXX: [bug类型] — [描述]
级别: 高/中/低
修复: 已修复/待修复/不需要

...

总结:
  ✅ 语法通过
  ✅ 模块导入通过
  ⚠️ 发现X个问题（Y高/Z中）
  已知降级: ...
```

## 防御性审计陷阱

1. **不要相信子Agent的结论** — 子Agent说"上传成功"不代表真的上传了。必须curl验证
2. **审核必须运行测试** — 泛读代码不叫审核。审核 = 读代码 + 跑代码
3. **大文件不能"快速扫"** — 500行以上的文件分段逐行看
4. **看到"看起来没问题"时要怀疑** — 这就是bug藏身的地方
5. **双审是铁律** — 任何工具调用前做pre_review，调用后做post_review
