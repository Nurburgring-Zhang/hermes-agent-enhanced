---
name: deep-code-audit
description: 极端深度逐行代码审核方法论 — 基于150,000行代码极端深度逐行审核发现~250个bug/问题的实战经验。四阶段(语法→导入→方法调用→HTTP端到端)+17项排查清单+运行时验证+并行子Agent+浏览器实测。适用于所有需要真正深度审核而非走过场的场景。
triggers:
  - 用户要求"极端深度审核/逐行代码审核"  
  - 项目发布前最终代码复查
  - bug修复后审核修复质量
  - 接手新项目做基线质量评估
  - 审核"说自己完成了但用户不信"
  - 用户对交付质量表示不满/愤怒
  - 100K+行大型项目审计
  - 用户反复说"继续审别偷懒/继续深度/极端深度"
---

# 极端深度逐行代码审核方法论

## 核心原则

1. **审核定义不正确=没审** — "看起来没问题"不是审核结论，是免责借口
2. **必须实际运行** — 不运行测试的代码审核不叫审核
3. **拒绝读代码不跑** — 读代码能看出语法问题，看不出Body()绑定缺失、运行时import崩溃、异步循环崩溃
4. **逐行，逐文件，不跳过** — 项目代码+迁入的vendor代码，全部逐行进

## 四阶段审核流程（强制，不可跳过）

### Phase 1: 全部文件语法检查
```bash
for f in $(find . -name "*.py" | sort); do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>/dev/null || echo "❌ $f"
done
```

### Phase 2: 引擎全部导入+方法调用测试
```python
# 每个引擎:
from engines.文件名 import 主类
inst = 主类()
assert inst.核心方法() is not None
```

### Phase 3: 函数签名级检查
```bash
# POST端点Body()绑定:
grep -c "@router.post" api/文件 > grep -c "Body(" api/文件
# 如果body_count < post_count，说明有POST端点没绑Body()

# 变量名跨文件一致性:
grep "导入名" 源文件.py
grep "导出名" 目标文件.py

# 参数签名比对:
grep "def 方法名" 引擎文件.py
grep "调用了方法名" 路由文件.py
# 比对参数数量+顺序
```

### Phase 4: HTTP端点端到端测试
```bash
python3 api/main.py --port XXXX &
sleep 5
# 认证 → 注册 → 登录 → 资源创建 → 数据获取 → 资源操作
curl -s http://127.0.0.1:XXXX/api/端点 | grep "success.*true"
```

## 17项排查清单 + 死代码验证

详见 `references/dead-code-verification-pattern.md`:
- 调用链追溯：沿着import向上查找到底有没有被执行路径
- 返回值格式验证：假设函数返回字符串但实际返回dict → 所有调用端逻辑全错
- 代码规模vs调用深度：>10KB但<3个外部引用的模块大概率死代码
- 重启验证：Python进程缓存模块，不重启就测试=测试旧代码

### A. HTTP/API层（高优先级）
1. **POST端点Body()绑定** — 检查`data: dict`是否改为`data: Dict[str, Any] = Body(...)`
2. **端点返回静态JSON** — 每个`return {"success": True, ...}`检查是否真的调用了引擎
3. **跨文件变量名一致** — 导入名 vs 导出名
4. **URL前缀一致** — router前缀在定义处和注册处是否匹配
5. **HTTP方法正确** — POST用于变更，GET用于读取

### B. 引擎层（高优先级）
6. **算子注册≠实现** — Operator.run()是否真的处理数据而不是return data
7. **参数签名不匹配** — HTTP层传参 vs 引擎方法签名
8. **返回类型不匹配** — 方法->Type提示 vs 实际return
9. **异常处理** — 是否有空raise/空except/错误吞没
10. **同步调用异步函数** — `run_until_complete`在有事件循环的上下文中崩溃

### C. 前端层（中优先级）
11. **case分支无真实API** — execNode/effect中的case是否有`_cv_api`真实调用
12. **重复case** — 同switch中有重复case(dead code)
13. **闭包中lambda延迟绑定** — `for x in list: route.lambda: ...` 全部只使用最后一个x值

### D. 数据处理层
14. **空列表不检查就索引** — `items[0]`前没有`len(items) > 0`
15. **变量作用域检测不可靠** — `"x" in dir()` r̅ 改用`locals().get("x")`
16. **路径处理错误** — `.replace("ext", "otherext")`可能替换错位置，用`os.path.splitext`
17. **比较检查缺少大小写** — 字符串.contains()时两面是否都转了小写

## 特殊场景: vendor/第三方框架审核

vendor/下的代码是完整第三方开源项目迁移（如crawl4ai 80文件50,207行）。不是本项目手写的业务代码。审核策略：

1. **检查迁移完整性** — 路径是否正确/引用是否改名
2. **检查dead代码** — 同名函数覆盖/废弃函数残留
3. **只修复影响本项目的严重bug** — 不修改第三方框架的内部实现逻辑
4. **重点检查闭包bug** — Python lambda在循环中的延迟绑定是vendor代码中最常见的问题

## 代码真实度分类（审计结论标准）

审计结论不应只是"发现了X个bug"，应按以下维度分类整个项目的健康度：

| 分类 | 含义 | 示例 |
|------|------|------|
| ✅ 真实实现 | 代码真实完成其声称的功能 | SQLite写入/读取, 真实OpenCV处理 |
| ⚠️ 骨架实现 | 结构完整但核心逻辑是模拟/占位符 | 算子声明supports_ai但只返回固定值 |
| ⬜ 静态数据 | 页面/组件展示数据但数据是硬编码的 | "52个Agent"、"¥2.4K本月消耗"写在JS里 |
| 💀 空中楼阁 | 完整模块代码但从未被主入口引用 | agent/~10,500行代码未在server.py导入 |
| 🧱 壳 | 只有注册/定义没有执行体 | functions/下6个文件 |
| 🔌 未接通 | 前端UI完整但onclick调用了不存在的函数 | startGeneration()在Electron preload定义 |

### Provider/API fallback 诚实原则

当代码需要调用外部服务（AI模型/TTS/搜索API/3D引擎）但该服务不可用时，**禁止**假装成功。

**禁止模式**：
```python
return f"[Voice Clone] 克隆音色完成。样本:{sample}, 文本:'{text}'"  # ❌ 假装成功了
return {"aesthetic_score": 7.5}  # ❌ 假装AI评分了
output_file.write_text("Generated image placeholder")  # ❌ 写文本冒充图片
```

**要求模式**：
```python
return {"status": "unavailable", "message": "Voice cloning requires a TTS API (ElevenLabs). Configure TTS_PROVIDER."}
return {"aesthetic_score": 0.0, "details": {"model": "fallback", "reason": "model not loaded"}}
# fallback用PIL生成明确标"Generation Failed"的图片
```

**判断标准**：审计时，为每个"说不能用的"和"假装能用的"做标记。只有明确告知用户什么不可用以及如何修复的代码才通过审核。

深度审核完成后，必须进行商用级差距分析，判断项目离生产部署还有多远。

### 13维度评分

| 维度 | 检查要点 |
|------|---------|
| 1. API完整性 | 所有端点是否返回真实数据？是否有缺省接口？ |
| 2. 错误处理 | 是否有全局异常处理器？500错误是否暴露内部细节？ |
| 3. 输入验证 | Pydantic模型是否覆盖全量CRUD？是否有SQL注入防护？ |
| 4. 认证授权 | 是否有JWT/API Key？是否强制认证？ |
| 5. 配置管理 | 是否全部硬编码？.env/环境变量分离？ |
| 6. 日志系统 | 是否有RotatingFileHandler？结构化日志？审计日志？ |
| 7. 性能优化 | 是否有数据库连接池？缓存？批量操作？ |
| 8. 测试覆盖 | 测试是否可运行？覆盖率？集成测试？ |
| 9. 部署文档 | 是否有Dockerfile？docker-compose？部署说明？ |
| 10. UI完整度 | 前端功能是否与后端API对齐？Loading/Error/Empty状态？ |
| 11. 数据持久化 | 是否仅有SQLite？是否需要PostgreSQL？迁移工具？ |
| 12. 安全 | CORS配置？速率限制？HTTPS？ |
| 13. 可观测性 | 健康检查？/metrics？告警？ |

每个维度0-10打分。综合<5分=原型级，5-7=测试环境可用，8+=商用级。

### 致命缺陷清单

差距分析完成后，必须输出按修复工时的优先级清单。典型的P0必杀列表：
1. 无全局异常处理器 → 内部traceback暴露
2. 日志无轮转 → 磁盘耗尽
3. README严重过时 → 误导用户
4. 无Dockerfile → 无法一键部署
5. 认证未强制 → 安全漏洞

## 审核完成后：P0修复优先级作战

深度审核不是终点。必须按优先级系统化修复。

### 三阶段修复策略

```
Phase 1: 崩溃bug（修了就能运行，不破坏任何现有功能）
  - missing table/field → 加CREATE TABLE
  - 参数顺序颠倒 → 交换参数位置
  - 缩进错误导致死代码 → migrate代码块
  - 路由冲突 → 重命名冲突路径
  - 修复量: 通常5-10个CRITICAL，每人独立修复

Phase 2: 核心功能真实化（占位符→真实调用）
  - 算子/评分用random.uniform → 调真实AI模型
  - 标志变量未定义 → 定义OMNIGEN_AVAILABLE等
  - 异步session关闭后使用 → 扩展async with范围
  - 修复量: 通常10-20个HIGH+CRITICAL

Phase 3: 未接入模块打通（空中楼阁→真实调用链）
  - agent/模块 → 在server.py lifespan初始化+创建路由
  - functions/壳函数 → 加真实执行体
  - integrations崩溃bug → 修复类型不匹配
  - 修复量: 按模块数，每模块1-2h

Phase 4: 前端补全（UI→真实API对接）
  - 创建独立纯前端页面绕过Electron依赖
  - "开始生成"按钮对接 POST /api/v2/generate
  - 保持暗色主题视觉一致性

Phase 5: 基础设施商用化加固
  - 全局异常处理器 + 认证强制 + 日志轮转
  - .env.example + Dockerfile + docker-compose
  - README重写(反映真实架构)
  - 测试修复(跳过非pytest脚本)
```

### 并行修复策略

Phase1-3用delegate_task并行多个leaf子Agent同时修复。但Phase5基础设施加固由于涉及同一文件(server.py)的多处修改且需要精确位置感知，应由执行AI直接操作(patch)而非通过子Agent。

### 修复后验证

1. `py_compile.compile()` 语法检查
2. `from xxx import yyy` 导入检查
3. 重启服务器 → 所有端点200
4. 浏览器实测 → 点击每个按钮
5. `grep -rn 'random.uniform\\|placeholder\\|TODO\\|mock\\|_generate_placeholder\\|write_text.*png' --include='*.py' . | grep -v __pycache__` 确认无残留

### 用户要求"全部商用级真实实现"时的强制验证循环

当用户反复说"所有的功能全部都真的实现了商用级的真实实现吗"时，说明用户对交付质量极度不信任。此时需要执行**闭环验证循环**而不是继续提交新代码。

**循环**:
1. **选一个功能** → 用代码执行/curl验证它的真实输出
2. **如果发现假实现** → 立即修复（用patch精确修改，不通过子Agent）
3. **发布修复** → 对用户说清楚"之前是X，现在是Y"
4. **用真实输出证明** → `python3 -c "from module import Class; print(Class().method()[:100])"` 给出实际返回值
5. **回到第1步** → 选下一个功能

**中止条件**: 对代码执行+curl验证+metrics/DB三路交叉验证都通过的功能，才标记为"真实实现"。

**反模式**: 连续提交多个"已修复"声明而没有真实测试输出 → 每次都会收到"你确定真的实现了吗"的追问。

### 修复范围穷尽模式

在用户要求"彻底找出所有问题！修复所有问题！"后，必须系统地枚举所有可能的遗留假实现类别并逐类核实：

```bash
# 搜索所有类别
grep -rn 'random\.unif\|random\.randint\|random\.random\|random\.choice' ...
grep -rn -i 'placeholder' ...
grep -rn 'write_text.*\.png' ...
grep -rn 'mock_predict\|_mock_\|class.*Mock' ...
grep -rn 'TODO:\|FIXME:\|HACK:' ...
grep -rn '"简化"\|\"待实现\"\|"开发中"' ...
grep -rn 'return f\"Executed' ...
grep -rn 'return \\[\\]' ...
```

每个类别列出发现，然后逐一修复。最后给出"已扫描8个假实现类别，发现X个，已修复Y个，剩余Z个（有合理原因：Z1需要GPU/Z2需要外部API Key/Z3需要Playwright）"。

不要在"7/7修复完成"上停下——用户问的是"真的都实现了吗"，需要回答"经8个类别搜索，零假实现可疑"。

## "全部文件无遗漏"验证模式

大型项目审查后，必须用以下bash模式验证无遗漏文件：

```bash
for f in *.py; do
    case "$f" in
        file1.py) status="✅ batch1 逐行" ;;
        file2.py) status="✅ batch3 扫描" ;;
        *)         status="❓可能漏审" ;;
    esac
    echo "$status $f"
done
```

任何输出"❓可能漏审"的文件必须立即补审。这是不可跳过的最后步骤。

## 已发现的漏洞模式

### POST端点伪实现
```python
# ❌ 错误:
@router.post("/xxx")
def handler(data: dict):  # 缺Body()
    return {"success": True, "data": {**data}}  # 不调引擎

# ✅ 正确:
@router.post("/xxx")
def handler(data: Dict[str, Any] = Body(...)):
    from engines.xxx import XXXEngine
    eng = XXXEngine()
    result = eng.do_thing(data)
    return {"success": True, "data": result}
```

### 模块级import崩溃
```python
# ❌ 错误: 模块加载时执行失败
from passlib.context import CryptContext
pwd_context = CryptContext(...)  # bcrypt版本不匹配时就崩溃

# ✅ 正确: try包裹或惰性导入
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(...)
except Exception:
    pwd_context = None
```

### 闭包lambda延迟绑定
```python
# ❌ 错误: 所有lambda都使用最后一个ext值
for ext in extensions:
    await context.route(f"**/*.{ext}", lambda route: route.abort())

# ✅ 正确: 默认参数捕获当前值
for ext in extensions:
    await context.route(f"**/*.{ext}", lambda route, e=ext: route.abort())
```

### 空技能分配被筛掉
```python
# ❌ 错误: required_skills=[]时filter掉所有人
match_count = len(set(required_skills) & set(w.skills))  # 0=空
if match_count > 0: ...  # 没人匹配,全部被筛掉

# ✅ 正确:
if not required_skills:  # 空列表=匹配所有人
    candidates.append(...)
```

## 并行子Agent审计（100K+行项目专用）

对大型项目（100K+行），单窗口逐行审计不可行。必须并行。

### 模块拆分策略
按以下维度并行拆分给 delegate_task leaf subagents：
```
模块A: 核心入口文件（server.py/main.py/app.py）
模块B: 数据层（database/models/storage）
模块C: 业务逻辑层（engine/service/manager）
模块D: 路由/API层（routes/api/controller）
模块E: 前端代码（React/Vue源码）
模块F: 基础设施（agent/ 包、infrastructure/、functions/）
模块G: 未被主入口引用的"空中楼阁"模块（检查server.py的import链）
```

### 子Agent超时处理（重要！）

**问题**: leaf subagents在读取>8000行的大文件时频繁超时（600秒限制）。

**根因**: 子Agent先读全文件（大token消耗）再做编辑计划，15+次API调用超出超时限制。

**解决方案按文件大小分治**:
- `<3000行`: leaf subagent可以直接用
- `3000-8000行`: 在context中指定offset/limit范围，不要让它自己读全文件
- `>8000行`: **永远不要用子Agent**。直接用patch做2-3个精确定位修改。
## 并行子Agent审计（100K+行项目专用）

对大型项目（100K+行），单窗口逐行审计不可行。必须并行。

### 模块拆分策略
按以下维度并行拆分给 delegate_task leaf subagents：
```
模块A: 核心入口文件（server.py/main.py/app.py）
模块B: 数据层（database/models/storage）
模块C: 业务逻辑层（engine/service/manager）
模块D: 路由/API层（routes/api/controller）
模块E: 前端代码（React/Vue源码）
模块F: 基础设施（agent/ 包、infrastructure/、functions/）
模块G: 未被主入口引用的"空中楼阁"模块（检查server.py的import链）
```

### 子Agent超时处理（重要！）

**问题**: leaf subagents在读取>8000行的大文件时频繁超时（600秒限制）。

**根因**: 子Agent先读全文件（大token消耗）再做编辑计划，15+次API调用超出超时限制。

**解决方案按文件大小分治**:
- `<3000行`: leaf subagent可以直接用
- `3000-8000行`: 在context中指定offset/limit范围，不要让它自己读全文件
- `>8000行`: **永远不要用子Agent**。直接用patch做2-3个精确定位修改。

**超时子Agent恢复**:
1. 检查 `tool_trace` 中的 `result_bytes` — 它写了文件吗？
2. 运行 `wc -l` 或 `git diff` 检查目标文件是否有部分写入
3. 如果patch已应用但语法检查失败，手动修复

### 子Agent最大输出token溢出

**问题**: 当要求子Agent重写大文件（如HTML 806→1101行），它达到max_output_tokens限制后输出被截断。

**解决方案**: **分段推进**。不要把完整重写任务交给子Agent：
1. Patch HTML结构（新增div+样式）
2. Patch JS函数（新增数组函数）  
3. Patch UI控件（新增按钮+导航项）
4. 每个patch小到足以在一个token窗口内完成

### 大HTML/JS文件分段增强策略（陷阱规避）

当审核发现需要增强大型 HTML/JS 文件（如 studio.html 806→1101行），**禁止**一次把所有需求塞给子Agent。

**推荐模式**: 执行AI直接做3-5次精确patch：
1. 读关键区间（grep定位函数/导航栏/样式块）
2. 通过精确的old_string匹配做patch：一次加HTML结构，一次加CSS样式，一次加JS函数
3. 每次patch后验证总行数变化

**关键技巧**: 用 `grep -n '元素标识符'` 找到唯一匹配点做精确old_string。当`navigateTo`函数被覆盖时有2个副本，用更多上下文包围。

### 并行审计指令模板
```
delegate_task(
  goal="对 XXXX.py(YYYY行) 进行极端详细的逐行代码审核",
  context="项目路径以及每个文件的详细审核要求...",
  toolsets=["terminal","file"]
)
```

## 全系统商用级差距分析（System-Wide Gap Analysis）

当审计规模扩展到整个系统（300+文件、25万+行代码）时，不能只做逐行代码审核。必须从**商用级（TRL 7-9）** 的高度做系统级差距分析。

### 触发条件

- 用户要求"真正商用级的全部功能实现"
- 审计发现大量死代码/壳子/降级实现（20+问题）
- 系统声称"全自动AI驱动"但功能模块互相矛盾
- 需要输出P0-P3优先级排序的修复计划

### 方法论：系统级三路审计

```
1. 全网检索（session_search + fact_store + web_search）
   → 了解系统架构、历史坑位、已有发现
   
2. 极端深度文件审计（294+文件的扫描模式）
   → 逐目录扫描 .py 文件，分类记录每个文件的健康度
   
3. 三AI交叉验证
   → 架构AI（模块依赖/扩展性/技术债务）
   → 安全AI（漏洞/攻击面/认证/数据保护）
   → 工程AI（可维护性/测试/CI/CD/可观测性）
```

### 26点问题分类矩阵

P0（立即修复 — 安全+运行阻断）：
`API密钥明文 / SQL注入 / 壳子实现 / bare except:pass / 零认证`
示例: config.yaml密钥明文存储、f-string拼接SQL表名、三省六部全部返回模拟数据

P1（尽快修复 — 工程完整性）：
`零测试 / 全print()无logging / 无速率限制 / 路径硬编码 / 死代码 / cron与脚本不匹配`
示例: 293个脚本零单元测试、25处硬编码路径、 force_compressor.py 271行无人调用

P2（可延后 — 技术债务）：
`重复模块 / 版本管理缺失 / 日志无限增长 / 配置分散`
示例: 5个pipeline引擎功能重叠、无pyproject.toml、无.gitignore

### 审计输出规范

每个问题条目必须包含：
1. 文件路径和行号（精确）
2. 问题类型
3. 严重级别（P0/P1/P2/P3）
4. 具体描述和证据（代码片段或运行结果）
5. 建议修复方案

### 三AI去重验证

P0/P1/P2 清单中经常出现重复项。三AI交叉验证时必须：
1. **同义词合并**: 同一问题不同表述 → 合并
2. **因果去重**: "无单元测试" ≠ "无CI/CD" → 独立问题
3. **上下游分离**: 核心模块的bare except:pass（P0）vs 工具脚本的bare except:pass（P1）
4. **交叉投票**: 3份独立清单投票决定P0/P1归属

### 修复规划Phase化

```
Phase-0: 紧急止血（0.5天）— 密钥迁移.env + .gitignore + HTTPS确认
Phase-1: 安全基础设施（N天）
Phase-2: 架构修复（N天）
...
```

每个Phase要有：预估天数、验收标准、依赖关系（可并行/可串行）、三AI互审最终验证。

### 遗留问题跟踪

审计完成后必须输出"已知但未修复"清单，包含延期原因（如"需要GPU"、"需要API Key"），防止同样bug在下次审计中重复发现。

## 浏览器实测验证（必须步骤）

读代码能发现语法问题、import错误，但发现不了"按钮点了没反应"、"生成按钮调用了未定义的函数"这类问题。

### 浏览器验证清单
1. **导航到每个页面** — 页面是否正常加载（不是白屏/404）
2. **点击每个按钮** — console是否有JS报错
3. **检查API调用** — `browser_console(expression='检查fetch/XHR调用')`
4. **检查函数是否存在** — 如`onclick="startGeneration()"`在浏览器中`typeof startGeneration`是否为function
5. **检查数据来源** — 显示的数据是来自API还是硬编码

### browser_console JS检查模板
```javascript
// 检查Vue app是否挂载
typeof Vue !== 'undefined' && !!document.querySelector('#app').__vue_app__
// 检查全局函数是否存在
typeof startGeneration === 'function'
// 检查console错误
// browser_console()返回的js_errors字段
```

## UI架构设计偏好（本项目/用户专用）

用户反复强调：**\"对标Scale AI/Labelbox\"** 的界面设计思想。

### 核心原则

1. **常用功能直接放主界面** — 不藏在多层菜单后
2. **不常用的放菜单** — 左侧导航树用于组织但不隐藏高频操作
3. **全功能门户首页** — 8-12个功能卡片网格，每个卡片直达核心功能区
4. **每个功能卡片必须包含**: 大图标 + 功能名称 + 一句话描述 + hover效果(上移+边框发光)
5. **页面必须丰富** — \"简单的列表\"不够，每个页面要有数据总览+图表+操作入口

### 三站式导航架构

```
首页(/)                    — 功能门户(8卡片+顶部导航)
  ├── 智影工场(/zhiying)   — Vue3 SPA, 左侧14项侧边栏
  ├── AIGC工作室(/studio)  — 暗色主题, 8功能区
  ├── 工作流编辑(/workflow) — DAG节点图编辑器
  └── 独立API端点(/health/metrics/nodes/docs)
```

### 智影工场侧边栏组织（Vue3 SPA菜单项扩展模式）

当在Vue3 SPA中添加新页面时：
1. 在 `menuItems` 数组中插入新项（按逻辑分组，不是按时间追加）
2. 添加对应的 `<div class="page" :class=\"...\">` 内容区域
3. 在JS的setup()中添加data refs和API调用methods
4. 在onMounted中调用加载函数
5. 在return中导出新refs和methods

### 首页门户重写策略

当前首页是Vue.js渲染的SPA → 改为纯HTML+CSS导航门户：
- 暗色主题（与studio.html一致: #0f172a背景）
- 8个功能卡片网格（2行×4列）
- 顶部导航条（Logo + 4个快速链接）
- 底部footer（版本+运行状态+API health dot）
- 纯原生JS（无框架依赖），使用 fetch('/health') 检查API状态
- 总代码量控制在400行以内

### 每个卡片设计模板

```html
<a href=\"/target-path\" class=\"card\">
  <span class=\"card-icon\">📊</span>
  <h3>功能名称</h3>
  <p>功能描述 / 一句话说清楚</p>
</a>
```

卡片CSS: border-radius: 1rem, hover时 translateY(-5px) + border-color变蓝 + box-shadow发光

## 三路交叉验证（确认真实性而非模拟）

读代码+curl测试发现了随机数/占位符，但无法证明端点不是cached/硬编码响应。需要三路独立证据。

### 三路交叉验证框架

| 维度 | 工具 | 证明什么 |
|------|------|---------|
| ⑴ 应用 | `curl endpoint` + inspect body | 数据结构正确性 |
| ⑵ 浏览器 | `browser_snapshot` + `browser_console(expression=...)` | 前端实际渲染了数据 |
| ⑶ 指标 | `curl /metrics/json` 计数器与curl请求匹配 | API执行了真实代码路径（非缓存响应） |

### 证明链示例
```
1. curl POST /api/v2/generate → 返回500 "Diffusers module not available"（真实错误链）
2. browser 点击"开始生成" → 显示loading状态+后续错误信息
3. curl /metrics/json → POST_/api/v2/generate: count=2, errors=2 ✅
```
**metrics计数器匹配是最强的信号**——假端点无法增加真实Prometheus计数器。

### 反检测模式
```
curl /health → 200 OK
browser → 显示"API已连接"
/metrics → GET_/health: count=0 ❌ 代码返回了缓存/静态响应
```

## 实战案例

本技能包含多个完整实战案例：
- `references/nanobot-factory-2026-06-11-case.md` — 145,000行项目极端深度审核案例（285个问题，6维真实度分类）
- `references/full-api-test-generation-pattern.md` — 全量API集成测试生成模式（96测试覆盖45+端点，速率限制防御）
- `references/dead-declaration-pattern.md` — 死声明检测方法（代码存在但无运行时路径）
- `references/nanobot-factory-2026-06-11-p0-repair.md` — P0修复模式、商用级13维度框架、修复文件清单、反模式教训
- `references/nanobot-factory-2026-06-12-session.md` — A-E模块修复+三路交叉验证+子Agent超时恢复+最终7.5/10评分
- `references/nanobot-factory-2026-06-12-fix-and-verify.md` — 7个假实现修复案例、分段patch模式、Provider fallback诚实化、98 tests通过验证
- `references/imdf-2026-06-11-cases.md` — IMDF项目审核案例
- `references/dead-code-verification-pattern.md` — 死代码验证模式（restart验证、返回值类型校验、调用链追溯）
- `references/imdf-2026-06-12-audit-case.md` — IMDF审计+12/13端点修复实战（routes_extended假实现修复、MockObjectStore类名修复、重启验证教训）
- `references/nanobot-factory-2026-06-12-three-ai-audit.md` — 三AI互审模式+节点系统+批量任务队列+Pipeline状态机案例
- `references/nanobot-factory-2026-06-12-phase1-4.md` — Phase 1-4 新功能构建案例(ML Backend/多模态标注/RBAC/数据集版本管理)

## 三AI互审模式（行业对标+功能拆解+商用级差距）

当用户反复要求"三AI互审互查"或要求"全网搜索对标分析"时，使用本模式。

### 3个AI角色分工

| AI角色 | 任务 | toolsets |
|--------|------|----------|
| **监督AI-A（行业对标）** | 搜索竞品，输出差距矩阵 | ["web"] |
| **监督AI-B（功能拆解）** | 设计节点体系/工作流/维度拆分 | ["terminal","file"] |
| **监督AI-C（商用级验证）** | 检查代码真实性+架构健康度 | ["terminal","file"] |

### 启动模板
```python
# 并行启动3个子Agent
tasks = [
    {"goal": "全网检索竞品对标，找出功能差距", "toolsets": ["web"]},
    {"goal": "设计可组合功能节点体系(60+节点)", "toolsets": ["terminal","file"]},
    {"goal": "审核代码质量+真实性+安全", "toolsets": ["terminal","file"]}
]
```

### 行业对标分析模板
对标来源: Label Studio, CVAT, HuggingFace Datasets, FiftyOne, ComfyUI, Scale AI, Labelbox, Clarifai, Ultralytics Hub
差距矩阵格式: 功能维度 | 我们 | 行业最佳 | 差距 | 对标来源
优先级: P0(核心差距)→P3(规模化差距)

### 三AI互审验收报告格式
| 模块 | 分数 | 结论 |
|------|------|------|
| 每个新模块 | X/100 | 发现/结论 |
| 总体判定 | ✅/❌ | |

## 分段patch策略（大文件增强专用）

当审核发现需要增强>500行的大HTML/JS文件时：

### 禁止模式
❌ 把所有需求一次性塞给delegate_task → 子Agent超时(600s)或output overflow

### 推荐模式（执行AI直接做3-5次精确patch）
1. **第一步**: 用grep定位关键插入点（函数边界/HTML结构边界/样式块边界）
2. **第二步**: 每次patch只做一件事 — 加HTML结构 / 加CSS / 加JS函数
3. **第三步**: 每次patch后验证总行数变化
4. **关键技巧**: 用`grep -n '唯一标识符'`找到精确匹配，用足够多的上下文包围old_string确保唯一

## Fallback诚实化原则

当代码调用外部服务不可用时：

### 禁止模式
```python
return f"[Voice Clone] 克隆音色完成"  # ❌ 假装成功了
output_file.write_text("placeholder")  # ❌ 文本冒充图片
return {"aesthetic_score": 7.5}  # ❌ 假装AI评分了
```

### 要求模式
```python
return {"status": "unavailable", "message": "需要TTS API"}  # ✅ 明确告知
# PIL生成含"Generation Failed"的图片  # ✅ 真实占位但不冒充
return {"aesthetic_score": 0.0, "details": {"reason": "model not loaded"}}  # ✅ 明确返回0
```

## 用户风格偏好（本项目专用）

从Nanobot Factory实战提炼的用户行为特征：
- 极端严苛，零容忍占位符/模拟实现/降级声明的"假装能用"
- 命令式，厌恶开放性问题
- "执行然后再报告" — 先给真实输出再给结论，不要反着来
- "彻底找出所有问题" — 必须系统枚举所有可能的假实现类别并逐类搜索
- 每次必须给出"已搜索X类，发现Y个，修复Z个，剩余N个(有原因)"的完整枚举
- 对"全部文件无遗漏"极度执着——要用for循环逐一标记每个文件的状态

### 强制前置流程（不可绕过）

在开始任何audit/修复任务前，必须先完成三步：**全局观念建立 → 深度思考分析 → 建立完整规划方案 → 按软件工程流程执行 → 三AI互审互查**。

缺少任何一步，用户会直接打断并要求重新来。这是硬性工作流约束，不是建议。

当用户反复说"全局观念建立，深度思考分析，建立完整规划方案，然后按照软件工程的完整流程严格执行。记得要三AI互审互查。"时，用户并不只是在提醒——这是在强制执行一个5步门控流程。你必须：

1. **停下来** — 不要继续执行
2. **先做全景审视** — 扫描整个项目所有模块
3. **3AI并行差距分析** — 执行AI/行业AI/质量AI三路独立出报告
4. **出执行计划** — 基于差距分析
5. **5步执行** — 全局观念→深度分析→规划→执行→三AI互审

如果用户在说"继续推进"时附带了这个5步要求，你必须先停下来完成前3步，不要直接跳到执行。

## 审查反模式（不可接受的行为）

1. **"看起来没问题"** — 没运行测试就不叫审核
2. **"先干活后面再补双审"** — 审核必须在步骤前执行
3. **"这个操作太简单了跳过预审"** — 没有例外
4. **"代码读完了没什么问题"** — 没跑curl/import/test三件套
5. **"引擎可导入说明功能正常"** — 导入≠HTTP端点能调用
6. **"前端按钮有样式说明交互正常"** — CSS≠JS，看着有按钮≠点击能用
7. **"完成了剩下的一点下次做"** — 没有"剩下一点"这回事
8. **"vendor的代码不需要审"** — 闭包bug就在vendor代码里。但不审业务逻辑，只审dead code和迁移完整性
