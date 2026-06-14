# 深度逐行代码审查清单

## 审查前准备
1. 确认系统正在运行（`curl http://localhost:8001/`）
2. 确认核心API可访问（`curl http://localhost:8001/api/v2/xxx`）
3. 对整个项目做全量文件盘点——知道有哪些文件、各自多少行，再决定审查范围
4. 识别审计模式：如果是大项目（>50个文件），必须使用并行子Agent分模块审计

## 项目全量盘点（必做第一步）

在开始审查前，先知道要审什么。不要遗漏任何文件。

```bash
# 文件总数 + 线数
find . -name "*.py" -not -path "*/__pycache__/*" | wc -l
find . -name "*.py" -not -path "*/__pycache__/*" -exec wc -l {} + 2>/dev/null | sort -rn | head -40

# 核心目录扫描
echo "=== 根目录py文件 ===" && ls *.py 2>/dev/null
echo "=== core/ ===" && ls backend/core/*.py 2>/dev/null
echo "=== routes/ ===" && ls backend/routes/*.py 2>/dev/null | grep -v __pycache__
echo "=== agent/ ===" && ls backend/agent/*.py 2>/dev/null | grep -v __pycache__
echo "=== integrations/ ===" && find backend/integrations -name "*.py" -type f 2>/dev/null | sort
```

### 致命陷阱：隐含代码目录可能被忽略
项目中可能存在 `integrations/`、`extended_skills_pkg/`、`omni_gen_studio/` 等子目录，其中包含数千行代码。必须用 `find . -name "*.py"` 全量扫描，不能只检查根目录。

## 大规模代码库审计方法论（~50,000行以上）

### 强制三阶段审计协议

**第一阶段：文件结构盘点 + 模块级扫描（不可跳过）**

```python
# 1. 全量文件列表
import subprocess, json
result = subprocess.run(['find', '.', '-name', '*.py', '-not', '-path', '*/__pycache__/*'], 
                       capture_output=True, text=True)
all_files = [f for f in result.stdout.strip().split('\n') if f]

# 2. 按大小分组
sizes = {}
for f in all_files:
    lines = int(subprocess.run(['wc', '-l', f], capture_output=True, text=True).stdout.split()[0])
    sizes[lines] = f
large = {k: v for k, v in sorted(sizes.items(), reverse=True) if k > 500}
print(f"大文件({len(large)}个): {sum(large.keys())} 行")

# 3. 模块级扫描——找假实现
for pat in ['mock', 'fake', 'simulat', 'placeholder', 'random.uniform', 'pass', 'TODO']:
    result = subprocess.run(['grep', '-rn', pat, '--include=*.py', '-l'], capture_output=True, text=True)
    print(f"[{pat}] 影响 {len(result.stdout.strip().split(chr(10)))} 个文件")
```

**第二阶段：并行子Agent逐行审查（使用不同模型做双审）**

安排3-5个子Agent并行，每个负责一个模块（约3000-8000行），每个子Agent用不同模型：

```python
tasks = [
    {"goal": f"极端逐行审查 {module_A}", "context": "所有文件路径...", "model": "deepseek-chat"},
    {"goal": f"极端逐行审查 {module_B}", "context": "...", "model": "gemini-2.5-flash"},
    {"goal": f"极端逐行审查 {module_C}", "context": "...", "model": "deepseek-chat"},
]
# 使用 batch 模式并行执行
delegate_task(tasks=tasks, ...)
```

**第三阶段：P0结论独立验证 + 浏览器实际操作验证**

每个子Agent报告的P0级别问题，必须由主Agent独立验证后再写入最终报告。

**子Agent审计报告的质量检查：**
1. 子Agent说"xxx不存在" → 主Agent `grep -n 'xxx' file.py` 证伪
2. 子Agent说"yyy是随机数" → 主Agent `grep -n 'random.' file.py` 证实
3. 子Agent说"zzz导致崩溃" → 主Agent `python3 -c "from module import class"` 测试
4. 子Agent说"前端API不存在" → 主Agent `browser_console` 验证
5. 如果子Agent的结论和另一个子Agent的结论矛盾 → 以直接验证为准

### 致命陷阱：子Agent遗漏"天然不可见"的问题类别

某些问题类别子Agent天然倾向于忽略，主Agent必须在审计checklist中单独检查：

1. **`async with ClientSession()` 退出session后继续使用** — 子Agent难以发现。必须手动检查 `async with session:` 后面的缩进是否退出了 `async with` 块
2. **`asyncio.run()` 在已有事件循环中调用** — 代码检查不出来。必须检查所有 `asyncio.run()` 是否在已有事件循环的环境中（如FastAPI lifespan）被调用
3. **`eval()` 安全性** — 在不安全的代码路径中
4. **dataclass 被当作 dict 索引** — `obj["key"]` 而非 `obj.key`
5. **`List[SomeType].items()`** — 在list上调用了dict的`.items()`
6. **缩进错误导致代码属于不同类** — 代码虽然语法正确但被错误地放在前一个类中

**对策：** 这6个模式必须作为主Agent阶段的硬编码检查项，不能委托给子Agent。

### 审计过程中的硬编码检查项（主Agent执行，不可委托）

每次调试时，以下检查必须由主Agent直接执行（不做子Agent审查）：

```python
# 1. 全量文件盘点——不做这个就没法知道审了多少漏了多少
find . -name "*.py" -not -path "*/__pycache__/*" -not -path "*/.git/*" | wc -l

# 2. 模块级mock检测——快速找出哪些文件是假实现
grep -rn 'random.uniform\|random.random\|random.randint' --include="*.py" . | grep -v __pycache_ | grep -v '.minimax'

# 3. ClientSession关闭后使用检测——async with缩进问题
grep -n 'async with aiohttp.ClientSession()' --include="*.py" . | head -20
# 然后手动检查每个匹配后面是否有在async with块外的session使用

# 4. asyncio.run()在已有循环中检测
grep -n 'asyncio.run(' --include="*.py" . | grep -v test_ | grep -v '.minimax'

# 5. dataclass当作dict检测
grep -n '\[.agent_id\]\|\[.name\]\|\[.expert_id\]' --include="*.py" . | grep -v test_

# 6. 函数名缺失检测 — "注册了但未实现"模式
# 检查functions/等目录下是否有大量只定义不执行的函数
```

## 并行审计组织策略

### 文件分配规则

| 文件大小 | 每个子Agent负责 | 审完方式 |
|----------|---------------|---------|
| <200行 | 10-20个文件 | 主Agent直接扫描 |
| 200-1000行 | 5-8个文件 | 子Agent逐行 |
| 1000-3000行 | 3-5个文件 | 子Agent逐行 |
| >3000行 | 1-2个文件 | 子Agent逐行（需超时保护） |

### 子Agent计时和超时处理（2026-06-11实战经验）

- 3000-5000行的文件每个子Agent需要约2-3分钟审完
- 8000-10000行的文件每个子Agent需要约5-10分钟审完
- 超级大文件（server.py 9000行）需要设置 `timeout=300` 以上
- 子Agent超时的处理：如果超时了但已经产生了大量 `read_file` 调用，说明文件被读完了但总结阶段超时。这时可以：
  1. 从子Agent的 `tool_trace` 中提取 `read_file` 的 `args_bytes` —— 确认文件被完整读取
  2. 手动 `read_file` 确认关键部分
  3. 子Agent的输出部分可用（如果有partial output）
- **batch模式**：用 `tasks` 数组启动多个子Agent并行，最大3个并发

### 子Agent审计报告的质量要求（强制）

每个子Agent的审计目标中必须包含以下强制检查项：

```python
审查目标中必须包含：
"特别注意：检查以下6个模式，发现了必须标注P0：
1. async with ClientSession()关闭后继续使用
2. asyncio.run()在已有事件循环中
3. eval()使用
4. dataclass被当做dict索引
5. List.items()调用
6. 缩进错误导致代码属于前一个类"
```

## 逐文件审查清单（每个文件执行）

### 1. 文件级检查
- [ ] 文件是否有文件级docstring
- [ ] import是否冗余（有未使用的import）
- [ ] 类/函数的docstring是否存在
- [ ] 文件实际功能是否与文件名和注释一致（"AI图像生成"但实际是随机椭圆 = 假实现）

### 2. 方法签名检查
- [ ] 所有 public 方法的参数是否与调用方一致
- [ ] `_get_*()` 惰性导入函数是否使用单例模式（全局变量缓存）
- [ ] `*Manager.__init__` 中 `super().__init__()` 的调用位置是否正确（不能覆盖已有初始化）
- [ ] async方法中是否有真正的await（标记为async但内部全部同步操作 = 虚async）

### 3. 枚举/常量检查
- [ ] Enum值在跨模块使用时是否一致
- [ ] DB存储的枚举值是 `value`（字符串）还是枚举对象本身
- [ ] `_load_from_db` 中是否有对应类型转换

### 4. 持久化检查
- [ ] 每次状态变更后是否调用 `_save()`
- [ ] `_db_fields` 是否和模型的字段完全对应
- [ ] `_db_key_field` 是否设置正确（默认"id"，但StatsManager的是"user_id"）
- [ ] `_save()` 前是否有 `_ensure_table()` 确保表存在
- [ ] 多表管理器（如GovernanceManager管理3个实体）每个实体的持久化是否独立
- [ ] **数据库碎片化检测**：有多少个SQLite数据库文件？表结构是否重叠？用 `find . -name "*.db" -type f` 确认

### 5. 前端交叉检查
- [ ] 所有前端 `get('path')` / `post('path', ...)` 对应的后端路由存在
- [ ] 前后端传输参数方式一致（body vs query string）
- [ ] 全局作用域变量名检查（CDN模式下 `ElMessage` = `ElementPlus.ElMessage`，`ElMessageBox` = `ElementPlus.ElMessageBox`，不能直接用裸名）
- [ ] JS库加载方式正确（Vue用`vue.global.prod.js`，ElementPlus UMD用`element-plus`或`element-plus.umd.js`）
- [ ] `post()` 函数有 `r.ok` 检查

### 5b. 浏览器真实加载验证（P0级，不可跳过）
- [ ] 使用 `browser_navigate` 在真实浏览器中加载前端页面
- [ ] 检查 `browser_console` 获取JS错误（`console.error` + 未捕获异常）
- [ ] 验证Vue app已挂载（`document.querySelector('#app').__vue_app__ ? 'mounted' : 'no'`）
- [ ] 验证ElementPlus已加载（`typeof ElementPlus !== 'undefined'`）
- [ ] 关键交互动作：点击每个按钮、触发每个dialog/prompt，确认弹窗正常出现
- [ ] CDN资源优先下载到本地 `backend/static/lib/` 目录 — 避免浏览器CDN超时或不可达
- [ ] 原生JS弹窗检查：Vue Composition API + `prompt()` 在WSL浏览器环境中被静默阻止，必须全部替换为 `ElMessageBox.prompt()`
- [ ] 跨文件路由冲突检查：不同 routes/*.py 文件是否有相同路径注册
- [ ] 子Agent审计P0结论独立验证：对每个P0级别断言用 grep/curl 独立验证后再写入最终报告
- [ ] 数据库碎片化检查：项目中是否有多套独立SQLite数据库？用 `find . -name "*.db"` 检查
- [ ] Electron前端检查：是否有 `window.electronAPI` 或 `onclick="xxx()"` 全局函数只存在于Electron preload中？
- [ ] 全局函数存在性检查：`browser_console` 中检查 `typeof startGeneration === 'function'`
- [ ] 枚举反序列化验证：用 `python3 -c` 实际跑一遍 `_load_from_db` 验证字符串→枚举转换不崩溃
- [ ] 子Agent单例模式验证：检查所有 `_get_*()` 惰性导入函数，确认使用全局缓存变量而非每次新建实例
- [ ] 跨模块算子ID一致性：验证 operators_lib 和 workflow_engine 的算子ID完全一致

### 6. Pydantic类型检查
- [ ] 从DB加载的数据是否有枚举/BaseModel类型转换
- [ ] `Task(status="pending")` 字符串→枚举转换在Pydantic中是否工作
- [ ] Pydantic serializer warnings是否被忽略

### 7. 跨模块调用链完整性检查
- [ ] server.py 中是否存在引用 `agent/` 模块的导入？如果没有，agent/~10,000行代码可能是空中楼阁
- [ ] agent/ 模块内部的 AgentLoopEngine 和 react_engine.py 的 AgentLoopEngine 是否冲突/重复？
- [ ] functions/ 目录下的文件是否只有注册没有执行逻辑？
- [ ] enterprise_api.py 中的 AIGC生成/爬虫/QC评分是否真实调用了外部API还是用random模拟？

### 8. 三类常见"壳"模式检测
- **虚假AI调用**：`random.uniform()` 替代真正的AI评分、`random.randint()` 替代爬虫结果数量
- **虚假生成**：写入文本 `"Generated image placeholder"` 替代真实图片生成
- **虚假注册**：在functions/或skills/目录中注册了大量函数/技能但handler=None或内部只有`pass`

### 9. 缩进/结构问题检测
- **代码属于前一个类**：子类方法的代码因为缩进错误属于父类（注意方法之间的缩进一致性）
- **asyncio.run()误用**：在已有事件循环中调用会崩溃
- **async with退出后继续使用session**：检查每个`async with aiohttp.ClientSession() as session:`后面的代码缩进

## 审计分级定义

| 级别 | 定义 | 判定标准 |
|------|------|---------|
| 致命 | 功能完全不可用 | CDN加载失败、路由不存在、数据不持久、前端不渲染、状态赋值逻辑错误、ClientSession关闭后使用、asyncio.run()误用 |
| 严重 | 功能异常 | 参数校验缺失抛500、搜索效率极差、中文无法搜索、多标签只选第一个、评分用随机数替代AI |
| 一般 | 代码质量 | 重复import、注释错误、类型注解语义不准确、桩函数、测试代码与生产代码混在一起 |

## 修复后的全量回归验证流程

修复完成后，必须重新执行以下验证（不可跳过）：

```python
# 1. 模块导入验证
find . -name "server.py" -exec python3 -c "compile(open('{}').read(), 'server.py', 'exec')" \;

# 2. API端点验证
for endpoint in ['/', '/zhiying', '/studio', '/health', '/api/v2/operators']:
    r = requests.get(f'http://localhost:8001{endpoint}')
    assert r.status_code == 200, f"{endpoint} returned {r.status_code}"

# 3. 浏览器验证（关键交互）
# 对每个前端页面执行：首页加载→菜单切换→按钮点击→弹窗交互→确认创建

# 4. 数据持久化验证
# 创建→重启服务→读取，确认数据未丢失

# 5. 测试运行验证
pytest tests/ -x -q --timeout=30 2>&1 | tail -10
```

## 审计报告输出规范

最终报告必须包含：
1. **已审核总行数和文件数**（精确统计）
2. **按严重度分级的问题汇总**（P0/P1/P2）
3. **每个文件的问题密度**（问题数/行数）
4. **TOP 10 致命问题**（必须包含每个问题的文件和行号）
5. **真实可用的功能列表**（已验证的）
6. **不可用的功能列表**（假实现/模拟/未集成）
7. **最后的诚实评估**：全项目功能真实度百分比
