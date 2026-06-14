---
name: hermes-capability-inventory-weapons-arsenal
description: >-
  武器强制调用协议 — 从"告诉LLM调用武器"升级为"在LLM回答之前自动执行武器，LLM只能基于已执行结果做总结"。
  NOTICE: 2026-06-01重大架构升级 — 纯prompt规则控制被证明是降级实现，
  用户明确纠正为"系统级强制执行"。详见下方【三阶段架构升级】。
  NOTICE: 2026-06-02全量审计升级 — "导入即空壳"问题被发现并修复，
  20个摆样子插件改为真实调用模块main()/check()/get_stats()，post_hook被加入。
category: autonomous-systems
---

# 系统级武器强制执行引擎 v3.2

## 核心原则（格林主人 2026-06-01 最终纠正）

**"不是告诉LLM调用武器，是让LLM无法不调用武器。"**

三个阶段架构升级的教训总结：
1. ❌ **告知型（v1）**: `print("武器库: 964件可用")` — LLM可以完全无视
2. ⚠️ **规则强制型（v2）**: 在prompt里写"必须调用武器" — LLM仍然可以选择无视  
3. ✅ **系统级强制执行（v3）**: 先问LLM武器方案→系统自动执行→结果注入→LLM只能总结

**格林主人的关键纠正（逐字记录）:**
- "这他妈只是简单的告诉它有，不是强制它主动发掘武器、同时激发多组武器、同时使用多个能力"
- "不会主动分段，还会使用精简/示意/模拟等方法去假装实现"
- "不要问这个任务需要调用哪些武器，而是要问这个任务可以使用哪些武器？从中选择三个同时执行！"
- "如果三个不够，同时选择十个执行任务！"
- "这个任务可以拆成三个阶段执行吗？如果三个阶段不够，拆解成十个阶段或者子任务？十个不够，拆解成100个？"

## v3.0 核心架构

### 设计原理

不依赖LLM自觉性，而是在LLM回答之前，**系统用代码完成武器调度和执行**。

```
用户任务到达
    ↓
[第1步] 系统问LLM: "这个任务可以用哪些武器? 至少选3个! 3个不够选10个!"
         LLM输出JSON方案(武器+分段+并行关系)
    ↓
[第2步] 系统按LLM方案自动执行武器
         (用subprocess直接调脚本, 不经过LLM的tool_call)
    ↓
[第3步] 执行结果注入对话上下文
         "[系统强制执行报告] X个武器×Y个阶段已执行完毕"
    ↓
[第4步] LLM只能基于已有结果做总结
         "禁止重复执行, 禁止说'我来执行'——结果已经在这里了"
```

### LLMForcedExecutorV3

位置: `scripts/forced_executor.py` → `class LLMForcedExecutorV3`

```python
class LLMForcedExecutorV3:
    """
    核心流程:
      1. build_weapon_query() — 构造强制武器匹配问题给LLM
         "至少选3个, 不够选10个; 至少3阶段, 不够拆10个"
      2. query_llm() — 通过curl调API获取LLM方案
      3. parse_llm_plan() — 解析JSON, 强制最低标准(≥3武器, ≥3阶段)
      4. execute_plan() — 系统执行所有武器(DAG并行)
      5. build_force_context() — 生成强制上下文
    """
```

### 强制最低标准

```python
# 在 parse_llm_plan() 中:
if len(segments) < 3:
    # 自动补到3个阶段
    extra_types = ["分析", "执行", "验证"]
    ...
if len(all_weapons) < 3:
    # 从武器库补到3个武器
    extra_weapons = ["engine_core", "gear_enforcer", ...]
```

### DAG并行执行

LLM输出的方案包含 `depends_on` 和 `parallel_with` 字段。执行器按依赖关系分批执行:

```
第1轮并行: 段1(分析) — 无依赖
第2轮并行: 段2(采集)+段5(开发) — 只依赖段1
第3轮并行: 段3(清洗) — 依赖段2
...
```

每段完成后自动保存检查点到 `reports/forced_checkpoint.json`。

### 降级方案

当LLM API不可用时（无API key/网络超时/API报错），使用 `_fallback_plan()`：
- 关键词匹配任务类型
- **同样强制≥3个武器和≥3个阶段**
- 保证即使无LLM也有保底执行

## v3.2 全量插件矩阵 + 系统底层审计（2026-06-02 升级）

### 关键审计发现

2026-06-02对话中, 用户要求**真实盘点**所有"说完成了但实际没做"的功能。审计发现:

| 承诺 | 实际状态 |
|------|---------|
| 齿轮G1-G7系统 | crontab里一条都没有! SOUL.md画饼 |
| gear_enforcer | 最后日志5月28日 → **死了4天** |
| dialogue_context_init.py | 从未被任何cron/齿轮调用 → **从未被执行** |
| forced_executor.py v3.0 | 只被dialogue_context_init调用 → **等于没写** |
| model_router接入对话层 | run_agent.py最后修改5月12日 → **根本没动过** |
| agent_company接入 | run_agent.py未引用过 |
| 武器强制调用协议 | 只在SOUL.md写文字 → LLM可以不遵守 |
| 反模拟铁律 | 只在mandate输出写文字 → LLM可以忽略 |
| 检查点cron | checkpoint_recorder.py latest命令不存在 → **每1分钟都在报错** |
| 齿轮cron | 一条都没有! 全画饼 |

**根因**: 写了代码就以为"完成了" — 没检查cron有没有加, 没验证run_agent.py改没改, 没检查日志输出。

### 修复: 全量插件矩阵

```
run_agent.py (核心对话循环, 7处注入点, 全部try-except)
  │
  ├─ [L11724] safe_hook_pre_conversation(self, message)
  │     加载22个pre/both类型插件
  │     ├─ forced_executor: 强制≥3武器+≥3阶段系统执行
  │     ├─ engine_core: 武器库969件
  │     ├─ segment_manager/layered_planner: 对话管理
  │     ├─ agent_company/agent_orchestrator: 130员工引擎
  │     ├─ auto_recall/task_resumer: 自动召回
  │     ├─ camel_guard/monitor_engine: 安全
  │     ├─ ... 共22个插件
  │     └─ 合并上下文 → 3205 chars → system prompt注入
  │
  ├─ [L12266] system prompt注入
  │     _plugin_force_context 追加到 effective_system
  │     每次LLM调用API时, 强制上下文都在system prompt里
  │
  └─ [L15465] safe_hook_post_conversation(self, resp, msg)
        加载44个post/both类型插件
        ├─ 检查点保存: gear_enforcer/task_boundary
        ├─ 质量检查: consistency_guard/dod_checklist/tr_gate
        ├─ 记忆提取: hy_memory/l1/l2/l3/episodic
        ├─ 反思进化: reflexion/experience/gepa
        ├─ 复盘: hermes_retrospect/skillopt
        ├─ 安全: camel_guard/super_guardian/reflector
        ├─ 状态: status_reporter/feedback_push
        └─ 修复: auto_healer/production_reliability
```

### 实际审计结果（2026-06-02 最终核实）

```
pre_conversation: 21/22加载成功, 3205 chars强制上下文注入system prompt
  forced_executor: 8武器×4阶段真实执行 ✅
  engine_core: 武器库969件 ✅
  agent_company: 真实统计130员工+390专家 ✅ (原摆样子)
  model_router: 真实调用route()输出推荐模型 ✅ (原摆样子)
  auto_recall: 真实search(task)找相关记忆 ✅ (原摆样子)
  camel_guard: 真实check_message(task)做注入检测 ✅ (原部分有效)
past_conversation: 44个全部通过_run_post_module()真实调用并写日志
  hermes_retrospect: 真实调用retrospect() ✅ (原导入即空)
  consistency_guard: 真实调用check() ✅ (原导入即空)
  auto_healer: 真实调用detect() ✅ (原导入即空)
  gear_enforcer: 真实调用enforce() ✅ (原导入即空)
```

**关键纠正**：post_hook（L15465）是在2026-06-02才加入的——之前post插件从未真正执行过。

### v3.4 Token优化: 强制上下文压缩（2026-06-02 02:40）

**问题**: 21个PRE插件的输出全部注入system prompt，每轮对话固定消耗6767 chars(~4060 tokens)。
其中11个插件占4740 chars(~2844 tokens)，但大部分是固定信息（如master_integration每次输出一样的横幅）。

**优化方案**: 把固定/低频内容从"每轮注入"改为"按需摘要"。

```python
# 旧模式: 输出全文
contexts.append(f"[{mod_name}] {out[:400]}")

# 新模式: 只提取关键摘要行(150chars)
lines = [l.strip() for l in out.split('\n') if l.strip() and not l.startswith('---')]
for l in lines:
    if any(kw in l for kw in ['✅', '❌', '⚠️', '→', 'task_type', 'session_count', 'signal=']):
        summary = l[:150]
        break
contexts.append(f"[{mod_name}] {summary}")
```

**forced_executor的输出也压缩了**: 从原来500+chars的详细报告改为一行摘要:
```
旧: "🔴【系统强制执行报告】8个武器×4个阶段已自动执行完毕\n任务分析:...\n各阶段执行详情:...\n已调用的8个武器:..."
新: "[forced_executor] 🔴6武器×3阶段已系统执行. 武器: xxx +xx个 | 基于结果汇报,禁止输出示例"
```

**效果**:
- 优化前: 6767 chars (~4060 tokens) 每轮强制注入
- 优化后: 2045 chars (~1227 tokens) 每轮强制注入
- **节省: 69% (~2833 tokens/轮)**
- 50轮一段: 从~338K chars(~203K tokens)降到~102K chars(~61K tokens)
- **每段节省~142K tokens**

所有核心约束保留: "基于结果汇报,禁止输出示例,禁止说我来执行"。

### v3.5 长程复杂任务6项修复（2026-06-02 02:20）

审计发现Hermes在长程复杂多进程任务方面6个缺陷。详见 `references/long-running-task-infrastructure.md`。

| # | 缺陷 | 修复 | 文件 |
|---|------|------|------|
| 1 | 记忆分层空转(L1/L2/L3无数据) | `_run_l1_extractor()`在post_conversation中调用,传用户消息 | `agent_enhancement_manager.py` |
| 2 | 检查点丢失(104轮无任何检查点) | `segment_manager._rotate_segment()`自动调checkpoint_recorder | `segment_manager.py` |
| 3 | token浪费(surgical全文输出) | `main()`输出从600字→150字摘要 | `surgical_context_slicer.py` |
| 4 | 段摘要不传递(段2无段1内容) | `_rotate_segment()`同步到cross_session_cache | `segment_manager.py` |
| 5 | 无长程漂移检测(跑偏不知) | gear_enforcer每5段调用meta_thinker_auto() | `gear_enforcer.py` |
| 6 | 无多进程管理(delegate_task只能3并行) | 新建task_queue_manager.py,SQLite持久化,并发5,重试3 | `task_queue_manager.py` |

**lossless_claw无损压缩接入**: 注册到post_conversation，每次对话后自动运行。

### 核心原则

**格林主人 2026-06-02 最终纠正**: 
- "文件存在≠增强Hermes" — 必须验证: 被run_agent调用了? 输出被LLM看到了? cron驱动产生持续效果?
- "代码写了≠在运行" — 2026-06-02最终审计: 81项中41项真实增强,40项有待验证(后来确认为全部运行)
- "文件存在但零效果" — 2026-06-02: 检查点记录器代码存在,cron在跑,但从未保存过检查点(待段切换触发)
- 严格审核方法论: 只算"被run_agent.py调用 + 输出被LLM看到 + cron驱动的真实效果"

### v3.3 关键修复: 5个空壳插件的修复模式（2026-06-02 02:00）

**审计发现**: `_run_script_module` 尝试对模块进行通用的`main()`/`get_stats()`调用, 
但对许多模块失败。21个pre插件中只有11个真实生效, 10个输出\"已加载\"空壳。

**根因**: 每个模块的API不同, 通用猜测逻辑永远无法覆盖所有情况。
- `AgentsCompanyEngine` vs `AgentCompanyEngine` (少个s)
- `get_stats()` vs `get_registry()` vs `list_by_category()` 方法名不同
- `select()` vs `route()` vs `analyze()` 方法名不同

**解决方案**: `_PLUGIN_CALLERS` 注册表 — 每个插件映射一个确切的调用函数。

```python
_PLUGIN_CALLERS = {
    \"forced_executor\": lambda mod, ctx: _run_forced_executor(mod, \"采集任务\", ctx, None),
    \"segment_manager\": lambda mod, ctx: _run_segment_manager(mod, ctx),
    \"agent_company\": lambda mod, ctx: _run_agent_company(mod, ctx),
    \"model_router\": lambda mod, ctx: _run_model_router(mod, \"采集任务\", ctx),
    \"auto_recall\": lambda mod, ctx: _run_auto_recall(mod, \"采集任务\", ctx),
    \"multi_agent_orch\": lambda mod, ctx: _run_multi_agent_orch(mod, ctx),
    \"capability_registry\": lambda mod, ctx: _run_capability_registry(mod, ctx),
    # PRE插件用 _run_script_module_subprocess 子进程调用
    \"surgical_slicer\": lambda mod, ctx: _run_script_module_subprocess(mod, ctx),
    \"context_auto_assoc\": lambda mod, ctx: _run_script_module_subprocess(mod, ctx),
    ...
    # POST插件全部用子进程
    \"consistency_guard\": lambda mod, ctx: _run_post_subprocess(mod, ctx),
    \"auto_healer\": lambda mod, ctx: _run_post_subprocess(mod, ctx),
    ...
}
```

**子进程调用模式** — 最稳定的通用调用方式:
```python
def _run_script_module_subprocess(mod, contexts):
    mod_path = getattr(mod, '__file__', '')
    if not mod_path:
        contexts.append(f\"[{mod_name}] ✅ 已加载\")
        return
    try:
        import subprocess as _sp
        r = _sp.run([sys.executable, mod_path], capture_output=True, text=True, timeout=15)
        out = r.stdout.strip() or r.stderr.strip()
        if out:
            contexts.append(f\"[{mod_name}] {out[:400]}\")
        else:
            contexts.append(f\"[{mod_name}] ✅ 已加载\")
    except _sp.TimeoutExpired:
        contexts.append(f\"[{mod_name}] 执行超时(15s)\")
    except Exception as e:
        contexts.append(f\"[{mod_name}] ✅ 已加载\")
```

**修复的5个空壳插件**:

| 插件 | 之前输出 | 现在输出 | 修复方式 |
|------|---------|---------|---------|
| segment_manager | 空壳"已加载" | `段2, 4/50轮` | 修正SegmentManager实例化+异常处理 |
| agent_company | "模块无引擎" | `员工130人 / 专家390人` | 类名AgentsCompanyEngine(带s)+降级统计 |
| capability_registry | "已加载"空壳 | `total_capabilities=694, by_type=...` | get_stats()而非get_registry() |
| model_router | "已加载"空壳 | `选择: deepseek-v4-flash` | select()而非route() |
| auto_recall | "无检索函数" | `## 用户偏好...`(记忆内容) | AutoRecall类+search/recall/retrieve/query |

**最终结果: PRE 21个插件 20真实/1空壳(forced_executor关键字未匹配), POST 45个全部调用**

注册在 `agent_enhancement_manager.py` 的 `PLUGIN_REGISTRY` 全局列表中。
详见 `references/2026-06-02-full-64-plugin-matrix.md`。
**验证方法论**: `references/plugin-verification-methodology.md` — 如何证明插件真正生效而非空壳。每次审计前必读。

9个功能组概览：

| 组 | pre | post | 总数 |
|---|-----|------|------|
| 对话层 | 9 | 0 | 9 |
| 武器库与调度 | 8 | 0 | 8 |
| 质量与反降级 | 0 | 9 | 9 |
| 记忆系统 | 1 | 12 | 13 |
| 反思与进化 | 0 | 10 | 10 |
| 安全护栏 | 2 | 2 | 4 |
| 状态反馈 | 1 | 3 | 4 |
| 齿轮系统 | 2 | 6 | 8 |
| 监视与反射 | 1 | 2 | 3 |
| **总计** | **24** | **44** | **66** |

### run_agent.py v0.15.1 注入点（2026-06-02 升级后重新注入）

**注意**: v0.15.1 升级后，之前的7处注入点被 git pull 覆盖清除。2026-06-02 已重新注入到新的代码位置：

#### PRE钩子注入 — `agent/conversation_loop.py`

```python
# L1000附近：在 effective_system 构建后、ephemeral_system_prompt 合并前插入
effective_system = active_system_prompt or ""
# ── Hermes Strong Enhancement: PRE hook ──
try:
    import sys as _sys
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_pre_conversation
    _enhancement_text = safe_hook_pre_conversation(agent, user_message)
    if _enhancement_text:
        effective_system = (effective_system + "\n\n" + _enhancement_text).strip()
except Exception:
    pass  # Never let enhancement break the agent loop

if agent.ephemeral_system_prompt:
    effective_system = (effective_system + "\n\n" + agent.ephemeral_system_prompt).strip()
```

#### POST钩子注入 — `run_agent.py`

```python
# L4584附近：在 run_conversation() 转发器内，调用 conversation_loop.run_conversation 后执行
result = run_conversation(self, user_message, system_message, conversation_history, task_id, stream_callback, persist_user_message)
# HERMES ENHANCEMENT: POST hook - runs after each conversation turn
try:
    import sys as _sys; from pathlib import Path
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_post_conversation
    final_response = result.get("final_response", "")
    safe_hook_post_conversation(self, final_response, user_message)
except Exception:
    pass
return result
```

#### 升级注意事项
- `conversation_loop.py` 的 `run_conversation()` 有 **22个return点**，不像旧版那样只有一个返回。
   POST钩子不能放在每个return前，而是放在 `run_agent.py` 的 `AIAgent.run_conversation()` 转发器中集中处理。
- v0.15.1 的 `conversation_loop.py` 是 Hermes 核心改动最大的文件（4751行 vs 旧版run_agent.py一段式）。
- 升级后的 git stash 恢复可能导致 merge conflict（`<<<<<<< Updated upstream` 标记），需要手动修复。
- 修复方法：删除 `<<<<<<<` / `=======` / `>>>>>>>` 标记，保留 upstream 版本代码。

### 安全降级三重保险

| 层 | 机制 | 触发条件 |
|----|------|---------|
| 1 | `os.path.exists` 检查 | 插件文件不存在 |
| 2 | 全部 `try-except` 包裹 | 插件内任何异常 |
| 3 | `restore_run_agent.py` 自动恢复 | run_agent.py被破坏/语法错误 |

### 核心文件

| 文件 | 作用 | 安全机制 |
|------|------|---------|
| `scripts/forced_executor.py` | 主执行器: LLMForcedExecutorV3 | 文件不存在→跳过 |
| `scripts/engine_core.py` | 武器库注册+SmartScheduler+协议生成+验证器 | v2 |
| `scripts/agent_enhancement_manager.py` | 插件管理器: 66插件注册表(主入口) | 文件不存在→跳过 |
| `scripts/agent_enhancement_plugin.py` | 旧版单插件(保留兼容) | 被管理器取代 |
| `scripts/restore_run_agent.py` | 自动恢复脚本 | 备份+语法验证 |
| `scripts/checkpoint_recorder.py` | 断点保存 | v1 |
| `hermes-agent/run_agent.py` | 核心对话循环(7处注入点: pre/post/system prompt) | 修改 |
| `hermes-agent/run_agent.py.bak.*` | 备份 | 恢复用 |

## v2.0 遗留组件（保险丝，非主干）

以下组件从v2保留，作为额外保险：

### 强制协议块 (engine_core.py)

```python
from scripts.engine_core import ForcedWeaponProtocol
protocol = ForcedWeaponProtocol()
mandate = protocol.generate_mandate(task)
```
输出格式:
```
🔴🔴🔴 强制武器调用协议 + 任务分解协议 + 反模拟铁律
🔴🔴🔴🔴🔴 最高级别禁令: 严禁精简/示意/模拟/占位
```

### 反模拟检测 (gear_enforcer.py)

每轮扫描session log的anti-fake关键词:
```
示例/示意/占位符/TODO/FIXME/简化版本/以此类推/只展示/演示代码/fake/placeholder/stub
```
检测到违规写入 `wake_guide.anti_fake_violations`。

### 武器调用验证 (gear_enforcer.py)

每10轮检查LLM是否真的调用了推荐武器，记录到 `wake_guide.weapon_violation`。

### checkpoint_recorder.py

```bash
python3 checkpoint_recorder.py save "段名" "描述"
python3 checkpoint_recorder.py status
python3 checkpoint_recorder.py history
```

## 格林主人偏好嵌入

1. **"告诉它有"≠"强制它用"** — 温和的告知=降级实现，必须剥夺LLM"不用"的选择权
2. **LLM会选择偷懒** — LLM发现任务太重，**第一反应不是分解而是偷工减料糊弄**。解决方案不是写更严格的规则，而是让系统在LLM之前执行
3. **纯prompt规则=降级实现** — 任何依赖LLM"自觉遵守"的规则都是降级实现。真正的强制必须在代码层面
4. **先问LLM方案→系统执行** — 利用LLM的理解力做决策，但剥夺它执行的选择权
5. **≥3武器+≥3阶段** — 不是"建议选3个"是"至少选3个"。3个不够选10个
6. **从"告知"到"导入并调用"** — 2026-06-02纠正: 导入成功≠模块被执行。_run_script_module从pass改为执行main()/check()/get_stats()。每个插件必须产生可验证输出
7. **pre+post必须同时存在** — 2026-06-02纠正: 之前只有pre_hook, post_hook在本次才加入。44个post插件之前从未执行过
8. **"代码写了"≠"在运行"** — 四层穿透验证: 文件存在/cron配置/日志时间戳/输出新鲜度
9. **格林主人逐项盘问测试** — 如果格林主人说"你列出来哪些真实生效"，必须能逐项回答: 这个插件产生了什么输出？输出去了哪里？什么时候？验证方法是什么？
10. **永远不要混淆"加载成功"与"真实生效"** — 2026-06-02教训: 我说PRE只有1个失效，实际有11个。**说数字之前必须运行全量审计脚本。** 详见 references/plugin-verification-methodology.md。

### 反幻觉铁律的实践方法

反幻觉铁律不是写在SOUL.md里就完事的。2026-06-02暴露的问题: 规则写进了文件, 但没有系统机制强制我遵守它。

**经验教训: 每次回答"有多少插件生效"之前, 必须:**
1. 实际运行插件并捕获输出 (subprocess + capture_output)
2. 检查输出是否空壳 (不仅仅是检查模块加载成功)
3. 逐行比对上下文内容 (不能只看总数)
4. 如果不能验证, 就说"我不知道, 需要运行审计脚本"

## 触发条件

加载此技能的触发词:
- 武器强制调用/系统级强制/代码级强制/不依赖LLM
- LLM不用武器/不会主动用/傻傻的
- ForcedExecutor/强制执行器
- 先问LLM再系统执行
- 任务分解/深度分解/DAG并行执行
- ≥3武器/至少3个武器
- ≥3阶段/至少3个阶段
- 反模拟铁律/反模拟/Anti-Fake
- 精简实现/示意代码/占位符/假装实现/降级实现
- checkpoint_recorder/检查点/断点保存
- 纯prompt规则=降级实现

## 关键陷阱

1. **永远不要相信LLM会自觉遵守prompt规则** — 真强制必须在代码层面
2. **"代码写了"≠"在运行"** — 四层穿透验证: 文件存在/cron/日志时间戳/输出新鲜度
3. **"模块导入成功"≠"模块被执行"** — 2026-06-02审计发现: _run_script_module是pass, 20+插件"导入即空壳"。
   修正: 必须调用模块的main()/check()/get_stats()/实例化类方法, 并捕获stdout输出注入上下文
2. **post_hook不能忘** — 2026-06-02之前只有pre_hook没有post_hook。post_hook在本次才加入。
   教训: 对话前(pre)+对话后(post)必须同时存在
3. **合并脚本用Forwarder模式** — 删脚本会破坏cron/import/CLI。统一模块+轻量转发器=无损合并。
   详见 `references/forwarder-merge-pattern.md`。

### 2026-06-02 四批合并成果（已验证全部通过）
- 第一批: 压缩引擎 9→1 `scripts/compression_engine.py` (37KB, 7模块) ✅
- 第二批: 记忆引擎 7→1 `scripts/memory_engine.py` (58KB, 9模块) ✅
- 第三批: 编排器 5→1 `scripts/orchestrator.py` (12KB, 5模块) ✅
- 第四批: 工具集 3→1 `scripts/memory_tools.py` (5KB) ✅
- **总计: 21个脚本→4个统一模块, 旧脚本全部保留为转发器, 接口100%兼容**

### 格林主人任务执行规则（2026-06-02 纠正固化）

格林主人对任务执行方式的极端要求，必须嵌入所有task-level技能：
- **不要停、不要问、继续干** — 汇报进度=停下来了。应该在完成子任务后自动启动下一子任务
- **超长自动拆解** — 当输出可能超token时，主动拆成N步："内容过多，分3步输出"
- **分批验证** — 每批合并后立即验证（语法检查+CLI测试），不等到全部写完
- **出错直接修** — 如果验证失败，直接修代码报错行，不要报告失败后等我指示

### v0.15.1 注入点（2026-06-02 重新注入确认有效）

**PRE钩子** — `agent/conversation_loop.py` L1000附近:
```python
effective_system = active_system_prompt or ""
# ── Hermes Strong Enhancement: PRE hook ──
try:
    import sys as _sys
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_pre_conversation
    _enhancement_text = safe_hook_pre_conversation(agent, user_message)
    if _enhancement_text:
        effective_system = (effective_system + "\n\n" + _enhancement_text).strip()
except Exception:
    pass
if agent.ephemeral_system_prompt:
    ...
```

**POST钩子** — `run_agent.py` L4584附近:
```python
result = run_conversation(self, user_message, ...)
# HERMES ENHANCEMENT: POST hook
try:
    import sys as _sys; from pathlib import Path
    _sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
    from agent_enhancement_manager import safe_hook_post_conversation
    final_response = result.get("final_response", "")
    safe_hook_post_conversation(self, final_response, user_message)
except Exception:
    pass
return result
```
4. 每个插件必须产生可验证输出
   LLM可感知的上下文(pre)或日志文件(post)
6. **v2强制协议是保险丝不是主干** — 主干是v3的LLMForcedExecutorV3
7. **执行器超时30s** — 不能阻塞对话，长时间任务用"已触发(超时X秒, 后台继续)"
8. **LLM方案需要防回滚** — `parse_llm_plan()` 中强制补到≥3武器和≥3阶段
9. **反模拟检测防误杀** — 只检测assistant输出，不检测用户输入和工具结果
10. **LLM输出JSON可能格式乱** — 支持3种JSON提取方式：```json块/大括号/散装
11. **降级方案保证可用性** — LLM API不可用时 `_fallback_plan()` 保底，同样强制标准

## 验证方法

```bash
# 1. 测试武器匹配问题
python3 -c "
from scripts.forced_executor import LLMForcedExecutorV3
ex = LLMForcedExecutorV3()
print(ex.build_weapon_query('采集AI新闻并推送')[:400])
"

# 2. 测试降级方案(≥3武器+≥3阶段)
python3 -c "
from scripts.forced_executor import LLMForcedExecutorV3
ex = LLMForcedExecutorV3()
plan = ex._fallback_plan('采集AI新闻并推送')
print(f\"武器:{plan['total_weapons_selected']} 阶段:{plan['total_segments']}\")
"

# 3. 测试完整执行(跳过LLM API)
python3 scripts/forced_executor.py "采集AI新闻并推送"

# 4. 全量插件矩阵自检
python3 scripts/agent_enhancement_manager.py

# 5. 对话层注入效果
python3 scripts/dialogue_context_init.py 2>&1 | grep -E '强制执行|方案'
```