# Vendor 代码审核方法论

从 crawl4ai 80个文件50,207行的深度审核实战提炼。

## 核心原则

**vendor目录下的第三方框架源码不需要逐行审"有没有bug"——需要审"有没有正确迁移"。**

开源项目(crawl4ai 16K+ Stars)的代码质量通常比我们自己手写的模块高。逐行审它们的内部逻辑是浪费时间。

## 审核清单

### 1. Dead code 检查
迁移时第三方代码经常有残留的旧版本函数被同名函数覆盖：
```bash
# 查找被覆盖的同名函数
grep -n "^def " vendor/*/src/*.py | sort | uniq -d
```

### 2. 类名/方法名匹配性
IMDF的引擎层(routes_extended.py)导入vendor类时经常用错名字：
```bash
# 检查routes_extended.py中导入的类名在vendor中是否存在
grep "from engines" api/routes_extended.py | sed 's/.*import //' | while read cls; do
  grep -r "class $cls" engines/ vendor/ 2>/dev/null || echo "MISSING: $cls"
done
```

### 3. 危险模式检查
第三方代码中硬编码的危险操作：
- `rm -rf` / `shutil.rmtree` / `os.remove` 在被调用的关键路径上
- 硬编码的 API key / token / secret
- 硬编码的内网IP/域名

### 4. 同步调用阻塞事件循环
第三方代码中在 `async def` 内调用了同步的 `requests.get()` / `time.sleep()`：
```bash
grep -n "requests\.\|time\.sleep(" vendor/*/src/*.py
```

### 5. Lambda闭包延迟绑定
循环中创建lambda/routes时闭包捕获了循环变量：
```python
# BAD - 所有lambda使用最后一个ext值
for ext in to_block:
    await context.route(f"**/*.{ext}", lambda route: route.abort())

# GOOD - 默认参数绑定当前值
for ext in to_block:
    await context.route(f"**/*.{ext}", lambda route, e=ext: route.abort())
```

## 实战成果

crawl4ai 80个文件50,207行审核结果:
- 发现并修复 6 个bug(全部小问题:闭包/大小写/死代码)
- 无结构性设计缺陷
- 代码质量高于IMDF自行开发的多数模块
- 结论: **vendor代码只需检查迁移完整性,无需深度审核内部逻辑**
