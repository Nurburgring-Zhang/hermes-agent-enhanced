# v3 系统级强制执行器架构详解

## 核心文件

`scripts/forced_executor.py` → `class LLMForcedExecutorV3`

创建时间: 2026-06-01, 三次迭代(v1代码分析→v2先问LLM→v3强制最低标准)

## 设计原理对比

```
v1: 纯代码关键词匹配 → 不够准确
v2: 问LLM"用什么武器" → LLM可能说"不需要武器"  
v3: 问LLM"这个任务可以用哪些武器? 至少选3个!" + "拆几个阶段? 至少3个!"
    → LLM必须输出JSON方案
    → 系统强制执行LLM的方案
    → 如果有武器少于3个或阶段少于3个, 追问一次再强制补
```

## 关键方法

### build_weapon_query(task) → str

构造发给LLM的prompt, 包含:
- 完整武器库(按类型分类: 采集/推送/清洗/开发/修复/记忆/安全/分析/验证)
- 强制指令: "至少选3个武器, 3个不够选10个"
- 强制指令: "至少3个阶段, 3个不够拆10个, 10个不够拆100个"
- JSON输出格式要求

### build_decomposition_query(task) → str

当LLM第一次输出少于3个武器或3个阶段时触发:
"你刚才的分解还不够深。能不能拆成10个阶段? 10个不够拆100个?"

### parse_llm_plan(response) → dict

支持3种JSON提取:
1. ```json ... ``` 代码块
2. 裸 { ... "segments" ... } 大括号
3. 散装JSON

**强制最低标准**(在解析后):
```python
if len(segments) < 3:
    # 自动补到3个阶段: 分析/执行/验证
    ...
if len(all_weapons) < 3:
    # 从通用武器库补到3个
    ...
```

### execute_plan(plan, task) → dict

DAG并行执行, 按依赖关系分批:
```
第1轮: 无依赖的段(分析等)
第2轮: 依赖段1的段(采集等) + 依赖段1的独立段(开发等)
第3轮: 依赖段2的段(清洗等)
```

每个段完成后自动保存检查点到 `reports/forced_checkpoint.json`

### _fallback_plan(task) → dict

关键词匹配降级方案:
- 同样强制≥3个武器和≥3个阶段
- 基础结构: 分析→执行→验证 三段式
- 根据任务关键词追加: 采集/推送/清洗/修复/开发/记忆

### build_force_context(plan, results) → str

生成注入到对话的强制上下文:
```
🔴【系统强制执行报告】X个武器 × Y个阶段 已自动执行完毕
...
🔴 你的任务: 基于以上真实结果汇报
🔴 禁止重复执行已被调用的武器
🔴 禁止输出任何示例、示意、模拟、占位内容
```

## 武器执行方法逐个

| 方法 | 调用的脚本 | 超时 |
|------|-----------|------|
| _execute_weapon("unified_collector_v5") | scripts/unified_collector_v5.py --collect --parallel 4 | 20s |
| _execute_weapon("hermes_v12_push") | scripts/hermes_v12_push.py | 20s |
| _execute_weapon("gear_enforcer") | scripts/gear_enforcer.py | 20s |
| _execute_weapon("engine_core") | scripts/engine_core.py(scan) | 20s |
| _execute_weapon("consistency_guard") | scripts/consistency_guard.py | 20s |
| _execute_weapon("hermes_retrospect") | scripts/hermes_retrospect.py | 20s |
| _execute_weapon("guardian") | scripts/guardian.py | 20s |
| _execute_weapon("blogwatcher") | 非可执行脚本 → 识别但跳过 | — |
| 其他不存在的脚本 | 返回"已识别(非可执行脚本)" | — |

## 调用链路

```
dialogue_context_init.py (每次对话开始)
  → sys.path.insert(0, HERMES)
  → from scripts.forced_executor import LLMForcedExecutorV3
  → executor = LLMForcedExecutorV3()
  → llm_response = executor.query_llm(executor.build_weapon_query(str(task)))
  → if llm_response:
       plan = executor.parse_llm_plan(llm_response)
       if plan["total_weapons"] < 3 or plan["total_segments"] < 3:
         # 追问
         llm_response2 = executor.query_llm(executor.build_decomposition_query(str(task)))
         ...
     else:
       plan = executor._fallback_plan(str(task))
  → print(f"方案: {tw}个武器 × {ts}个阶段")
  → exec_results = executor.execute_plan(plan, str(task))
  → forced_context = executor.build_force_context(plan, exec_results)
  → print(forced_context)  # 注入到LLM上下文
```

## 关键陷阱

1. **LLM API依赖**: `query_llm()` 通过curl调API。如果没有API key或网络不通, 自动使用 `_fallback_plan()`。降级方案同样强制标准。

2. **执行器超时**: 每次武器调用20s, 超时返回"已触发(超时X秒, 后台继续)"。不会阻塞对话。

3. **JSON解析多样性**: LLM输出的JSON可能有各种格式问题。`parse_llm_plan()` 支持3种提取方式和一个兜底的fallback。

4. **不要在parse_llm_plan中用eval**: 永远用json.loads(), 不要eval LLM输出的字符串。

5. **DAG依赖死锁**: 如果LLM输出的依赖关系有环, execute_plan的 `max_rounds=50` 防护会终止循环。

## 对话层注入效果测试

```bash
# 完整测试
python3 ~/.hermes/scripts/forced_executor.py "采集AI新闻并推送"

# 仅测试武器匹配问题格式
python3 -c "
from scripts.forced_executor import LLMForcedExecutorV3
ex = LLMForcedExecutorV3()
print(ex.build_weapon_query('修复推送系统')[:400])
"

# 测试降级方案强制标准
python3 -c "
from scripts.forced_executor import LLMForcedExecutorV3
ex = LLMForcedExecutorV3()
plan = ex._fallback_plan('修复推送系统')
print(f'武器:{plan[\"total_weapons_selected\"]} 阶段:{plan[\"total_segments\"]}')
assert plan['total_weapons_selected'] >= 3
assert plan['total_segments'] >= 3
print('最低标准通过')
"

# 对话层注入日志检查
python3 ~/.hermes/scripts/dialogue_context_init.py 2>&1 | grep -E '强制执行|方案|武器库'
```

## 历史版本差异

| 版本 | 文件 | 核心逻辑 | 缺陷 |
|------|------|---------|------|
| v1 | forced_executor.py → ForcedExecutor | 纯代码关键词匹配任务类型 | 不够准确, 无法理解隐含意图 |
| v2 | forced_executor.py → LLMForcedExecutor | 先问LLM"需要什么武器"→系统执行 | LLM可能说"不需要武器" |
| v3 | forced_executor.py → LLMForcedExecutorV3 | "至少选3个! 至少3阶段!"→系统执行+强制最低标准 | 需要LLM API |
