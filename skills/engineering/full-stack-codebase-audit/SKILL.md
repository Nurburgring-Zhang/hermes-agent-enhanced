---
name: full-stack-codebase-audit
description: >-
  全栈代码库审计与修复工作流 — 从代码扫描、问题分级(P0-P3)、优先级排序、
  到系统性修复执行与回归验证的端到端流程。适用于新接手项目质量评估、
  大版本重构前基线扫描、用户要求"以真实软件工程方法全流程分析审核测试"等场景。
version: 2.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [code-audit, quality-gates, full-stack, testing, refactoring, cleanup, deep-line-by-line]
    related_skills:
      - deep-code-architecture-analysis
      - systematic-debugging
      - test-driven-development
      - multimodal-data-production
      - requesting-code-review
      - infinite-canvas-engine
      - diagnose
---

# 全栈代码库审计与修复工作流

## 概述

本Skill定义了一套可重复执行的14维全栈审计流程，从问题发现→优先级排序→系统性修复→回归验证→模块化重构，适用于：

- 新接手项目质量基线扫描
- 用户要求"以真实软件工程的完整方法进行全流程分析、审核、测试"
- 大版本重构前的问题清单收集
- 代码质量门禁的自检

## 14维审计维度

| # | 维度 | 覆盖范围 |
|---|------|---------|
| 1 | 项目文件结构 | 目录布局合理性、备份残留、测试目录缺失 |
| 2 | 依赖分析 | package.json/requirements.txt/pyproject.toml同步性、版本策略、多余polyfill |
| 3 | 代码风格 | TypeScript strict模式、ESLint、Python loguru/basicConfig重复、注释中英混排 |
| 4 | 死代码检测 | 未使用的函数/类/import、残留备份文件、一次性测试脚本 |
| 5 | 重复逻辑检测 | 类型枚举重复、CRUD模式重复、数据模型前后端重复 |
| 6 | 安全审计 | 路径穿越、API Key泄露、WebSocket无认证、CORS、输入验证缺失 |
| 7 | API设计一致性 | RESTful规范违背、错误格式不统一、版本前缀缺失、snake_case vs camelCase |
| 8 | 测试覆盖分析 | 测试框架/目录是否存在、测试案例数量、前端/后端/集成测试覆盖 |
| 9 | 构建配置审计 | vite.config.ts、tsconfig.json、build sourcemap、proxy配置 |
| 10 | 空异常捕获 | bare `except:` 模式统计及修复 |
| 11 | 类型注解缺失 | mypy配置检查、缺失的返回类型/参数类型 |
| 12 | 长文件/函数检测 | 单文件行数超标、单函数行数超标、React组件过大 |
| 13 | 配置硬编码 | 字体路径、API URL、端口号、模型名称、OCR语言代码 |
| 14 | 错误处理模式 | HTTPException泄露敏感信息、WebSocket无恢复、async Task KeyError、降级无声 |

## 严重级别定义

| 级别 | 标签 | 定义 | 响应时间 |
|------|------|------|---------|
| **P0** | 灾难性 | 功能完全不可用、数据安全风险、无测试覆盖 | 立即修复 |
| **P1** | 严重 | 单文件超5000行、大量bare except、非RESTful DELETE | 本轮修复 |
| **P2** | 一般 | strict模式关闭、依赖不同步、安全漏洞、配置硬编码 | 高优修复 |
| **P3** | 建议 | 备份残留、polyfill多余、中英混排 | 可选清理 |

## 执行流程

### Step 1: 全景扫描（delegate_task）

并行扫描所有文件，收集原始数据：

```bash
# 文件统计
find . -name "*.py" -not -path "*/node_modules/*" -not -path "*/venv/*" | wc -l
find . -name "*.ts" -o -name "*.tsx" | grep -v node_modules | wc -l
wc -l $(find . -name "*.py" -not -path "*/node_modules/*") | sort -rn | head -20

# 依赖清单
cat requirements.txt 2>/dev/null || cat pyproject.toml 2>/dev/null
cat package.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('deps:',len(d.get('dependencies',{}))); print('devDeps:',len(d.get('devDependencies',{})))"
```

### Step 2: 14维深度审计（delegate_task 3-4个并行）

每个维度由独立子Agent执行，返回结构化的问题清单（文件:行号:级别:描述:建议）。

**关键审计模式：**

```python
# bare except检测
rg -n '^\s*except\s*:' --type py | grep -vP 'except\s+(Exception|ImportError|KeyError|...)'

# 超过N行的文件
find . -name "*.py" -not -path "*/node_modules/*" | xargs wc -l | sort -rn | awk '$1 > 500'

# 死import检测（用vulture或手工）
vulture . --min-confidence 60

# TypeScript strict模式
python3 -c "import json; c=json.load(open('tsconfig.json')); print('strict:', c['compilerOptions'].get('strict','MISSING'))"
```

### Step 3: 优先级排序 + 修复计划

按 P0→P1→P2→P3 排序：
- P0: 立即修复
- P1: 本轮内完成
- P2: 高优先级（单次会话可完成5-10项）
- P3: 备注不执行（或批量清理）

**工时估算经验值：**
```
P0 测试体系建立      ~200个测试/2-4小时
P1 bare except修复   ~50处/1-2小时
P1 死代码清理        ~20文件/30分钟
P2 TypeScript strict  ~8项配置/5分钟
P2 安全加固           ~5项/30分钟
P2 依赖同步           ~2文件/10分钟
P1 项目清理+模块化    ~20-30分钟
```

### Step 4: 系统性修复

按文件/按维度组织修复，避免跳来跳去：

**推荐执行顺序：**
1. 死代码+备份清理（最低风险）
2. bare except修复（批量，同一模式）
3. 测试体系建立（防止后续修复引入回归）
4. 安全加固（高风险低变更量）
5. 配置硬编码（配置化）
6. 依赖同步（元数据）
7. TypeScript strict（高风险高变更量，最后做）

**每个修复后立即运行测试验证：**
```bash
cd project && timeout 30 python3 -m pytest tests/ -v --timeout=30 -q
```

## 🔴 格林主人强制的深度审计方法论（2026-06-11 追加）

**背景（2026-06-10）：** 之前两次审计在API层面通过了所有测试，但用户发现页面功能完全无效、已有模块无法使用。根因在于审计只看接口返回，不看实际运行时表现。

**第2次强化（2026-06-11）：** 即使逐行审核了后端代码+路由，仍然遗漏了最核心的问题——浏览器实际打开页面点一下按钮，或者对子Agent的P0结论做独立验证就能发现。教训：审计的最大敌人不是不知道要查什么，而是做了假设就不验证。

**第3次强化（2026-06-11，145,000行审计实战）：** 即使并行派了14批子Agent审了全部~145,000行，仍然遗漏了：① `integrations/` 目录的8,467行代码+② `memory.py` 的变量作用域bug+③三套独立SQLite数据库碎片化。教训：没有任何捷径，必须完成全量文件盘点才能确定审计范围是否完整。

### 强制8步深度审计协议（不可跳过，每步必须执行）

**Step 0: 先验证系统是否正在运行**
```python
# 不要假设系统在跑 — 先验证
import urllib.request
try:
    r = urllib.request.urlopen('http://localhost:8001/')
    assert r.status == 200, f"首页不可达: {r.status}"
except Exception as e:
    print(f"❌ 系统未运行: {e}")
    # 启动系统后重试
```

**Step 1: 逐文件完整阅读（不是搜索关键行，是整个文件）**
```
对项目中的每一个核心模块：
  1. read_file(path) 读完整文件
  2. 逐行检查：方法签名是否一致、import是否正确、枚举值是否匹配
  3. 检查所有 `_get_*()` 惰性导入函数 — 确认使用了全局单例模式:
     ❌ def _get(): return ManagerClass()  ← 每次请求新建空实例
     ✅ _cache = None; def _get(): global _cache; if not _cache: _cache = ManagerClass(); return _cache
```

**Step 2: 交叉验证路由声明（前端API调用 vs 后端路由定义）**
```python
# 列出所有后端路由
from routes.v2_xxx import router
backend_routes = {r.path for r in router.routes}

# 列出前端所有API调用
import re
frontend = open('frontend/index.html').read()
frontend_calls = set(re.findall(r"(?:get|post)\('([^']+)'", frontend))

# 找出前端调了但后端没有的路由
missing = frontend_calls - backend_routes
assert not missing, f"前端调用了后端不存在的路由: {missing}"
```

**Step 3: 验证前端CDN/资源加载**
```python
# 检查CDN URL是否有效
cdn_urls = re.findall(r'https?://[^\'"\s)]+', frontend)
for url in cdn_urls:
    import urllib.request
    try:
        r = urllib.request.urlopen(url, timeout=5)
        assert r.status == 200, f"CDN不可用: {url}"
    except Exception as e:
        print(f"❌ CDN加载失败: {url} — {e}")
```

**Step 4: 实际HTTP请求验证（不止是模块导入通过）**
```python
# 对每个核心API端点发真实HTTP请求验证
for path, name in [('/api/v2/users','用户'), ('/api/v2/tasks','任务')]:
    r = urllib.request.urlopen('http://localhost:8001' + path)
    assert r.status == 200, f"{name} API返回 {r.status}"
    data = json.loads(r.read())
    assert data is not None, f"{name} 返回空数据"
```

**Step 5: 正反测试（不仅测正常路径，更要测异常路径）**
```python
# 创建后验证持久化
req1 = rm.create('test', ...)
# 新建实例验证数据可恢复
rm2 = RequirementManager()
assert rm2.get(req1.id) is not None, "持久化失败：重启后数据丢失"

# 测试错误输入不崩溃
try:
    rm2.get('nonexistent_id')
except Exception:
    pass  # 应返回None而非抛异常
```

**Step 6: 双AI交叉验证（不同模型审查结果）**
- 第一个AI做功能测试（API+模块）
- 第二个AI做代码审查（逐文件阅读+路由交叉验证）
- 两个AI独立输出问题清单后合并
- 两个AI的输出如果有不一致（一个说PASS一个说FAIL），以FAIL为准

**Step 7: 修复后全量回归验证**
所有修复完成后，重新跑一遍Step 1-4，确认：
- ✅ 模块导入无报错
- ✅ API端点全部200
- ✅ 数据持久化（创建→重启→恢复）
- ✅ 前端CDN可加载
- ✅ 前端路由调用与后端声明一致

**Step 8: 输出"已知问题清单"**
修复完毕后必须诚实列出所有未修复的问题，包括：
- 已知但未修的bug（严重级别+原因）
- 功能不完整的地方
- 下一轮应该优先做什么

### 🕳️ 致命陷阱：子Agent并行修改同一文件

当多个子Agent并行对同一个模块做不同修改时（如子AI-A加持久化，子AI-B修接口签名），合并后的文件可能：
1. 丢失对方加的代码（最后一个write/patch覆盖）
2. 接口签名不一致（一个改了create参数，一个没改）
3. 状态逻辑冲突（一个加了状态机，一个直接赋值）

**对策：**
1. 排他性文件用串行，同一文件一次只给一个子Agent修改
2. 子Agent修改完成后立即 `read_file` 确认文件完整性
3. 所有子Agent完成后运行一次 `pytest` 和 `curl API` 验证

### 🕳️ 致命陷阱：子Agent的PersistentManager继承破坏原有接口

`PersistentManager` 基类的 `__init__` 调用了 `_ensure_table()` 和 `_load_from_db()`。如果子类Manager的__init__中 `super().__init__()` 在原有初始化逻辑之前/之后调用不当，会导致：
1. 原有`__init__`逻辑被跳过
2. `_load_from_db` 从空数据库加载后覆盖了内存数据（如`_default_admin`创建的admin被清掉）
3. `_load_from_db`中Pydantic类型转换失败（DB存字符串，模型要枚举）

**对策：**
- 持久化改造后的Manager验证命令：
```python
# 验证原有接口未破坏
m = ManagerClass()
result = m.create(...)  # 原有create签名必须不变
m2 = ManagerClass()     # 新实例能恢复数据
assert m2.get(result.id) is not None

# 验证类型转换
for row in m2._load_all():
    # 枚举字段必须正确反序列化
    assert isinstance(row.get('status'), EnumType), f"状态字段类型错误: {type(row.get('status'))}"
```

### Step 5: 回归验证

最终全量测试 + 构建验证：

```bash
# 后端测试
python3 -m pytest tests/ --timeout=30 -q

# 语法检查
python3 -c "import py_compile; py_compile.compile('server.py')"

# 前端构建
npx vite build 2>&1 | tail -5

# API冒烟测试
curl -s http://localhost:8001/health
```

### Step 6: 输出审计报告

报告格式为 `AUDIT_REPORT_FULL.md`，包含：

1. **问题总览表**（按14维度分类 + P0-P3统计）
2. **最优先修复清单**（Top 10）
3. **已修复记录**（修复前状态→修复后状态）
4. **剩余问题**（本轮不修的P2/P3）
5. **验证结果**（测试通过数/构建状态/API状态）

### Step 7: 项目清理与模块化重构（可选）

当审计发现大量修复脚本（fix_*.py）、测试脚本（test_*.py）、备份目录（*_backup*）、单文件过大（>5000行）时，执行本步骤。

#### 7.1 清理清单

| 清理项 | 命令 | 风险 |
|--------|------|------|
| 修复脚本 | `rm -f fix_*.py` | ✅ 安全 |
| 调试测试脚本 | `rm -f test_*.py`（保留正式tests/目录） | ✅ 安全 |
| 备份目录 | `rm -rf .nanobot_*_backups *_backup*` | ✅ git已有历史 |
| 一次性验证脚本 | `rm -f verify_*.py check_*.py` | ⚠️ 先确认不在cron中 |

#### 7.2 创建标准包结构（pyproject.toml）

root级pyproject.toml示例：
```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "project-backend"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0", ...]

[project.scripts]
server = "package.server:main"

[tool.setuptools.packages.find]
where = ["backend"]
include = ["package*", "routes*"]
```

创建包目录：
```python
# backend/project_package/__init__.py
"""包入口"""
# backend/project_package/server.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server import app, main
```

#### 7.3 路由模块化（routes/目录）

当server.py超过5000行时，按资源拆分为独立APIRouter模块：

```
backend/routes/
├── __init__.py              # register_all_routers(app)
├── health.py                # 健康检查路由
├── generation.py            # 生成路由
├── data_quality.py          # 质量引擎
├── data_annotation.py       # 标注管线
├── data_watermark.py        # 水印版权
├── data_dataset.py          # 数据集管理
├── agents.py                # Agents CRUD
├── skills.py                # Skills CRUD
└── system.py                # 系统管理
```

每个路由模块的模式：
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/api/resource")
async def list_resources():
    return {"items": []}
```

**安全迁移策略：**
1. 先在routes/中创建新路由
2. 在server.py末尾添加 `register_all_routers(app)`
3. **不删除**server.py中的旧路由（新旧并存）
4. 运行测试验证所有路由可用
5. 后续版本再删除旧路由

## 参数真实性穿透验证协议

当用户质疑"所有功能都是真实运行的吗"或"参数是否真实生效"时，执行以下穿透验证：

### 6步验证协议

| 步骤 | 验证项 | 验证方法 | 通过标准 |
|------|--------|---------|---------|
| 1 | 评分区分度 | 3种极端不同图像做comprehensive_report | 跨度≥0.25 |
| 2 | 标注坐标转换 | COCO像素坐标 vs YOLO归一化坐标 vs LS百分比坐标 | 三者一致 |
| 3 | 水印二元区分 | 正确消息检测 vs 错误消息检测 | correct >> wrong (diff≥0.5) |
| 4 | 数据集读写一致性 | HF JSON写进去→读出来比较字段 | 100%一致 |
| 5 | 格式正确性 | YOLO label文件5列检查、COCO JSON schema校验 | 全部合法 |
| 6 | 去重有效性 | 相同图像距离=0 vs 不同图像距离>15 | 符合预期 |

### 控制变量法测试

对质量评分引擎：
```python
# 极端对比
img_high = complex_artistic_image   # 预期高分
img_low  = pixelated_degraded_image # 预期低分
img_pure = solid_white_image        # 预期最低分

p_h = engine.comprehensive_report(img_high, 'high quality')
p_l = engine.comprehensive_report(img_low, 'low quality')
p_p = engine.comprehensive_report(img_pure, 'pure white')

assert p_h.score_mean - p_p.score_mean >= 0.25, "Score range too narrow"
assert p_h.aesthetic > p_l.aesthetic, "Aesthetic should differentiate"
```

## 典型陷阱

### 🕳️ 陷阱1: 符号使用误判
在server.py等大文件中搜索import时，符号可能被用于**类型注解**或`global`声明中，简单的文本搜索会误判为"死import"。

**对策：** 删除前用两个方法交叉验证：
1. `grep -c "SymbolName" server.py` 检查出现次数
2. 删掉后运行 `python3 -c "compile open('server.py').read()"` 检查语法

### 🕳️ 陷阱2: 子代理修改冲突
多个子Agent并行修改同一个文件（如server.py）时，patch可能基于过时的文件内容。

**对策：** 排他性修改串行化。大文件（server.py）的修改一次只分配给一个子代理。

### 🕳️ 陷阱16: 数据库碎片化——多套独立数据库系统不互通

项目中可能存在多套独立的数据库系统：`database.py`的assets系统(SQLite)、`database_manager.py`的`SQLiteDataStore`(独立SQLite `nanobot_data.db`)、`AnnotationManager`的`annotations.db`。三套数据库完全独立，数据格式不同、表结构不同、路径不同，但功能高度重叠。

**检测方法：**
```python
# 找出项目中所有SQLite数据库文件
find . -name "*.db" -type f 2>/dev/null
# 检查database.py中的建表语句
grep -n 'CREATE TABLE' backend/database.py | head -20
# 检查database_manager.py中的建表语句
grep -n 'CREATE TABLE' backend/database_manager.py | head -20
# 检查annotation_system_enhanced.py中的建表语句
grep -n 'CREATE TABLE' backend/annotation_system_enhanced.py | head -20
```

**对策：** 审计报告必须明确指出数据库碎片化的范围和影响。修复策略要么统一到一套数据库，要么通过`project_id`/`user_id`跨库关联并提供路由层。

### 🕳️ 陷阱17: Electron前端在浏览器中无法运行

React/TypeScript前端如果是为Electron设计的（使用`window.electronAPI`桥接），在浏览器中加载时会缺失所有IPC函数。表现为：
- 页面渲染正常但点击按钮无反应（`startGeneration is not defined`、`window.electronAPI.xxx is not a function`）
- API路径是相对路径而不是绝对路径（`api/generate/image`而不是`/api/generate/image`），因为Electron的`base: './'`只对静态资源有效
- 菜单切换、模态框等纯UI操作可以工作，但所有需要后端API的功能都不可用

**检测方法：**
```javascript
// 在浏览器控制台
typeof window.electronAPI !== 'undefined'
// 检查API路径格式
typeof startGeneration === 'function'
// 检查前端请求的API路径
fetch('/studio').then(r => r.text()).then(html => {
  const matches = [...html.matchAll(/['"`](\/?api\/[^'"`]*)['"`]/g)];
  console.log([...new Set(matches.map(m => m[1]))].slice(0,30));
});
```

**验证方式：** 用 `grep` 检查构建产物中的API调用路径格式。
```bash
# 如果API路径没有前导"/"（如api/generate/image而非/api/generate/image），就是Electron模式
grep -o "'api/[^']*'" dist/index_new.html | sort -u | head -20
```

**对策：** 审计报告中必须注明哪些功能是Electron-only的，哪些是浏览器可用的。Electron前端如需在浏览器中使用，必须改造API路径（加前导`/`）和增加未定义函数的fallback。

### 🕳️ 陷阱18: 前端生成按钮调用未定义的全局函数

某些前端页面（特别是单页HTML而非React SPA）使用 `onclick="startGeneration()"` 这种全局函数调用方式。如果该函数仅在Electron preload脚本中定义，在浏览器中点击按钮时会抛 `ReferenceError`。

**检测方法：**
```javascript
browser_console({ expression: 'typeof window.startGeneration === "function"' })
```

**对策：** 审计时必须对每个页面点每个按钮，然后检查 `browser_console` 是否有 `ReferenceError`。所有前端按钮的onclick函数都必须实际存在。

### 🕳️ 陷阱9: 跨模块算子/常量ID不一致
当子Agent并行创建 operators_lib.py（定义具体算子类及其`id`属性）和 workflow_engine.py（定义`DEFAULT_OPERATORS`列表）时，两个模块中的算子ID可能不一致（如operators_lib中`label.image_caption`但workflow_engine中`label.caption`）。审计看不出来，但运行时add_node返回None。

**对策：** 算子/常量ID应该从单一来源定义。要么operators_lib统一导出ID字符串常量，workflow_engine引用它们；要么在创建第二个模块后立即运行`python3 -c "assert set(op.id for op in workflow_engine.DEFAULT_OPERATORS).issubset(operators_lib.OPERATOR_REGISTRY.keys())"`交叉验证。

### 🕳️ 陷阱10: 路由层每次请求新建管理器实例
FastAPI路由函数中，如果`_get_xxx()`每次都`return ManagerClass()`（新建实例），所有API操作都在空的内存数据库上执行——创建的数据当下请求可见但下一个请求就丢了。这是审查中最隐蔽的bug之一——路由函数本身看起来正常，测试也"通过"，但实际是无效的。

**对策：** 在审计checklist中强制添加"单例模式验证"项。检查所有`_get_*()`惰性导入函数是否使用了全局缓存变量（`_cache = None; def _get(): global _cache; if _cache is None: _cache = Class(); return _cache`）。在路由层审查时运行两次请求验证数据持久化。

### 🕳️ 陷阱11: 跨路由模块路径冲突
当项目拆分为多个 `routes/*.py` 文件（每个有自己的 APIRouter），不同模块可能注册了完全相同的路径。FastAPI 会静默覆盖先注册的路由，后注册的才生效。例如 `production.py` 的 `POST /api/v2/tasks` 和 `v2_zhiying.py` 的 `POST /api/v2/tasks` 冲突。

**检测方法：**
```python
from routes.xxx import router as r1
from routes.yyy import router as r2
paths1 = {r.path for r in r1.routes}
paths2 = {r.path for r in r2.routes}
assert not (paths1 & paths2), f"路由冲突: {paths1 & paths2}"
```
**对策：** 冲突模块必须使用不同前缀或路径。
### 🕳️ 陷阱13: P0结论未经独立验证

子Agent逐行审查后得出"db_manager.assets是内存字典无持久化"的P0结论，但实际`database.py`存在完整SQLite表的`INSERT`语句。子Agent只读了Manager层的代码，没看到database.py的完整实现，导致误判。

**对策（强制协议）：**
1. 每个P0级别指控必须独立验证：
   - 持久化断言 → `grep -n 'INSERT INTO\|CREATE TABLE' database.py`
   - 随机数断言 → `grep -n 'random.uniform\|random.random' server.py`
   - 路由断言 → 直接 `curl -s http://localhost:8001/xxx`验证
2. 子Agent说"不存在"必须用`grep`证伪，说"存在"必须用`curl`/`python3 -c "import as m; print(m.X)"`证实
3. 子Agent的P1/P2建议可直接采纳，但P0必须有子Agent + 直接验证 两个独立来源才能写入报告

### 🕳️ 陷阱14: 跨路由模块路径冲突

当项目拆分为多个 `routes/*.py` 文件（每个有自己的 APIRouter），不同模块可能注册了完全相同的路径。FastAPI 会静默覆盖先注册的路由，后注册的才生效。例如 `production.py` 的 `POST /api/v2/tasks` 和 `v2_zhiying.py` 的 `POST /api/v2/tasks` 冲突。

**检测方法：**
```python
from routes.xxx import router as r1
from routes.yyy import router as r2
paths1 = {r.path for r in r1.routes}
paths2 = {r.path for r in r2.routes}
assert not (paths1 & paths2), f"路由冲突: {paths1 & paths2}"
```

**对策：** 冲突模块必须使用不同前缀或路径。审计时对所有 `APIRouter` 的路由做集合运算交叉验证。

### 🕳️ 陷阱15: 枚举反序列化崩溃

`PersistentManager._save` 对所有非key字段做 `json.dumps`，枚举值被转为字符串存储。`_load_all` 用 `json.loads` 恢复为字符串，但Pydantic `BaseModel(**row)` 需要枚举成员。当 `type` / `status` / `priority` 等字段是字符串而非枚举成员时，Pydantic v2默认抛出 `ValidationError`。

**影响范围：** RequirementManager、TaskManager、AssetManager、EvalManager 的 `_load_from_db`。

**检测方法：**
```python
# 在审计中验证
m = ManagerClass()
rows = m._load_all()
for r in rows[:5]:
    for field in ['status', 'type', 'priority']:
        if field in r:
            assert not isinstance(r[field], str), f"{field}是字符串不是枚举: {r[field]}"
```

**修复方案：**
在 `_load_from_db` 中手动转换枚举：
```python
if isinstance(row.get('status'), str):
    row['status'] = EvalStatus(row['status'])
if isinstance(row.get('type'), str):
    row['type'] = EvalTaskType(row['type'])
```

### 🕳️ 陷阱3: 忽略前端strict模式的类型错误
TypeScript `strict: true` 后首次构建可能暴露100+类型错误。不能一次全修——需要增量方式。

**对策：** 分文件/分模块增量修复。先确认构建不挂（`strict: true` + `skipLibCheck: true` 兼容）。

### 🕳️ 陷阱4: 测试框架创建后忘记运行
建立了测试文件但不执行，等于没建立。

**对策：** 每个测试文件创建后立即 `pytest` 确认能跑；所有测试创建完后再次全量验证。

### 🕳️ 陷阱5: 根目录清理漏掉隐藏目录
`.nanobot_backups`、`.backup/` 等隐藏目录容易忽略。

**对策：** 同时检查 `rm -rf .*_backup*` 和 `.*backup/` 模式。

### 🕳️ 陷阱6: 删除测试脚本前检查cron引用
`rm -f test_*.py` 之前要确认cron中没引用这些脚本。

**对策：** `crontab -l | grep test_` 或检查 `.hermes/crons/` 配置。

### 🕳️ 陷阱7: pip install -e . 卡住
server.py在import时启动服务（连接ollama等），`pip install -e .` 会超时。

**对策：** `pip install -e . --no-build-isolation` 或用 `from project_package.server import app` 隔离导入路径。

### 🕳️ 陷阱8: 路由模块和server.py路由冲突
同一路径在routes/和server.py中同时注册，FastAPI 会报 `Duplicate route` 错误。

**对策：** 安全迁移策略——先新增不删旧。旧路线在新路线注册前被匹配，实际上新路线永远不会被调用。仅在确定旧路由没在使用后才删除。

## 参考

- `deep-code-architecture-analysis` skill — 用于Step 2的深度源码分析（架构级审计）
- `test-driven-development` skill — 用于Step 4的测试驱动修复
- `systematic-debugging` skill — 用于发现难以定位的运行时bug
- `multimodal-data-production` skill — 包含数据管线模块的详细测试协议
- `infinite-canvas-engine` skill — 无限画布Agent引擎架构参考
- `systematic-debugging` skill — 用于发现难以定位的运行时bug
- `multimodal-data-production` skill — 包含数据管线模块的详细测试协议
- `infinite-canvas-engine` skill — 无限画布Agent引擎架构参考
- `references/nanobot-factory-audit-20260608.md` — 实战审计日志
- `references/sqlite-persistent-layer-pattern.md` — SQLite持久化基类继承模式
- `references/deep-line-by-line-code-review-checklist.md` — 深度逐行代码审查清单
- `references/nanobot-factory-massive-refactoring-20260609.md` — IMDF架构重构实战
- `references/wsl-browser-frontend-patterns.md` — WSL下CDN本地化+弹窗修复+浏览器真实验证协议
- `references/nanobot-factory-audit-20260611.md` — 145,000行全项目逐行审计实战记录
