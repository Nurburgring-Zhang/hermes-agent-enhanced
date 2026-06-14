2026-06-10 实战: 从"概念设计(v1.x)"到"代码层注入(v2.0)"

## 背景
双AI互审v1是一个概念设计：规则写得很好（预审/实时验证/干预/双审/不可绕过），
但没有代码路径实际触发它。检查逻辑依赖执行AI"主动提交"，执行AI会忘记/跳过。

## 解决
v2.0把双AI互审从"概念规则"改为"代码层强制注入"：
1. 新建 workflows/dual_review.py — 真正的异步执行引擎
2. 写入 executor.execute_task() — 每个delegate_task前(pre_review)+后(post_review)
3. 写入 mandatory_engine.py — 每分钟验证注入状态

## 关键代码
```python
# executor.py 注入点
# 执行前:
pre_review = await dual_review(task_name, task_goal, task_context, stage="planning")
# 执行后:
post_review = await dual_review(task_name, task_goal, task_context, stage="review")
```

## 验证方法
mandatory_engine每分钟检查:
1. executor.py中有无"dual_review"字符串
2. executor.py中有无"pre_review"变量
3. runtime.py中有无"_run_adversarial_validation"或"dual_review"
4. logs/dual_review/目录是否存在

## 三路冗余
- executor.py: 每个delegate_task前后（最频繁）
- runtime.py: workflow phase完成时（最长链）
- unified_engine.py: 7步流程（最完整）

## 关键教训
"能导入 ≠ 能运行"。代码注入到正确位置还不够——要验证这条路径是否真的有人走。
mandatory_engine不检查"能不能import"，它检查"代码是否injected到正确文件+正确位置"。
