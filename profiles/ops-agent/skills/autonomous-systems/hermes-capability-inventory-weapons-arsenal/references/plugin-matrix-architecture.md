# 插件矩阵架构详解 (2026-06-01)

## 设计动机

之前所有增强功能的共同问题:
1. 功能写在不同脚本中, 各自为政, 没有统一入口
2. gear_enforcer.py 试图整合但只管理了中断检测/AI评分 — 其他增强无接入
3. dialogue_context_init.py 负责武器注入但从未被cron调用
4. cron有34条但大部分与对话层无关 — 日志空转

## 架构

```
[管理]                         [执  行  层]
                               run_agent.py (2个注入点)
                                    │
agent_enhancement_manager.py         ├─ pre_conversation 钩子 (L11722)
  │  (统一入口, 16插件注册表)         │    → 加载所有pre类型插件
  │                                   │    → 执行武器强制调用
  │  安全降级:                         │    → 合并上下文
  │  · 文件不存在→跳过                │    → 返回_plugin_force_context
  │  · 每个插件try-except              │
  │  · 导入循环短路保护                ├─ system prompt 注入 (L12263)
  │                                   │    → locals().get('_plugin_force_context')
  │  插件类型:                         │    → 追加到 effective_system
  │  · pre:  对话前执行                │
  │  · post: 对话后执行                └─ post_conversation 钩子 (future)
  │                                            → 检查点保存
  │                                            → 一致性自检
  │                                            → 复盘标记
  │
  └─ 子插件清单 ────────────────────────────────── 每个都是独立.py文件
       ├─ forced_executor.py      (3武器+3阶段)
       ├─ engine_core.py          (武器库969件)
       ├─ consistency_guard.py    (质量自检)
       ├─ hermes_retrospect.py    (复盘)
       ├─ checkpoint_recorder.py  (断点)
       ├─ hy_memory_orchestrator.py (记忆)
       ├─ l1_extractor.py         (事实提取)
       ├─ episodic_injector.py    (情景注入)
       ├─ hermes_camel_guard.py   (安全护栏)
       ├─ task_boundary.py        (任务边界)
       ├─ dod_checklist.py        (DoD验收)
       ├─ reflexion_engine.py     (反思循环)
       ├─ auto_healer.py          (自动修复)
       ├─ status_reporter.py      (状态反馈)
       ├─ layered_planner.py      (分层规划, 默认关)
       └─ segment_manager.py      (对话分段, 默认关)
```

## run_agent.py 注入代码

### 注入点1: pre_conversation (2处, 约30行)

```python
# 在 run_conversation() 方法内, L11722-L11748
self.iteration_budget = IterationBudget(self.max_iterations)

# ════════════════════════════════════════════════════════════
# [PLUGIN-MANAGER] Hermes 系统增强插件矩阵
# ════════════════════════════════════════════════════════════
_plugin_force_context = None
try:
    import importlib
    _pm_path = os.path.join(os.path.dirname(get_hermes_home()),
        "scripts", "agent_enhancement_manager.py")
    if os.path.exists(_pm_path):
        _pm_spec = importlib.util.spec_from_file_location(
            "agent_enhancement_manager", _pm_path)
        if _pm_spec and _pm_spec.loader:
            _pm_mod = importlib.util.module_from_spec(_pm_spec)
            _pm_spec.loader.exec_module(_pm_mod)
            if hasattr(_pm_mod, 'safe_hook_pre_conversation'):
                _plugin_force_context = _pm_mod.safe_hook_pre_conversation(
                    self, user_message)
                if _plugin_force_context:
                    logger.info(f"[PLUGIN-MANAGER] ✅ 强制上下文已生成 "
                        f"({len(_plugin_force_context)} chars)")
except Exception:
    pass
# [PLUGIN-MANAGER 结束]
```

### 注入点2: system prompt (4行)

```python
# 在run_conversation()内, L12263-L12269
# [PLUGIN-MANAGER] 注入强制上下文到system prompt
try:
    _plugin_ctx = locals().get('_plugin_force_context')
    if _plugin_ctx:
        effective_system = (effective_system + "\n\n" + _plugin_ctx).strip()
except Exception:
    pass
```

**关键设计选择:**
- 使用 `importlib.util.spec_from_file_location` 而非普通 `import`
  - 因为 `agent_enhancement_manager.py` 不在hermes-agent的venv中
  - 动态加载保证文件路径可配置
- 使用 `locals().get('_plugin_force_context')` 而非全局变量
  - 因为 `_plugin_force_context` 是run_conversation方法的局部变量
  - 同一方法内, 前段定义的变量后段可访问
- 全部用 `try-except` 包裹, 不抛异常到主流程

## 安全降级测试

```bash
# 1. 插件文件不存在 → 安全跳过
mv scripts/agent_enhancement_manager.py scripts/agent_enhancement_manager.py.bak
python3 -c "
# 模拟run_agent.py的加载逻辑
import importlib.util, os
path = os.path.expanduser('~/.hermes/scripts/agent_enhancement_manager.py')
if os.path.exists(path): print('存在')  # 跳过
else: print('安全跳过: 文件不存在')
"
mv scripts/agent_enhancement_manager.py.bak scripts/agent_enhancement_manager.py

# 2. 插件内异常 → 被try-except捕获
python3 -c "
import importlib.util, os
HERMES = os.path.expanduser('~/.hermes')
_pm_path = os.path.join(HERMES, 'scripts', 'agent_enhancement_manager.py')
try:
    _pm_spec = importlib.util.spec_from_file_location(
        'agent_enhancement_manager', _pm_path)
    if _pm_spec and _pm_spec.loader:
        _pm_mod = importlib.util.module_from_spec(_pm_spec)
        _pm_spec.loader.exec_module(_pm_mod)
        # safe_hook_pre_conversation(None, 'test') 中forced_executor需要agent_self
        # 但在测试环境中agent_self=None → 函数内部try-except捕获 → 静默返回None
        ctx = _pm_mod.safe_hook_pre_conversation(None, '采集AI新闻并推送')
        if ctx: print(f'✅ 上下文生成: {len(ctx)} chars')
        else: print(f'✅ 安全降级: agent_self=None时返回None')
except Exception:
    print('❌ 异常逃逸 - 这是bug')
"

# 3. 恢复测试
python3 scripts/restore_run_agent.py check
python3 scripts/restore_run_agent.py 0  # 恢复备份
```

## 与旧方案对比

| 维度 | 旧方案(dialogue_context_init.py) | 新方案(plugin manager) |
|------|----------------------------------|----------------------|
| 执行时机 | 每次对话开始时被print | 每次LLM调用API前注入system prompt |
| 触发方式 | LLM需看到print输出 | 代码直接修改messages数组 |
| 可靠性 | LLM可以选择性忽略 | LLM无法忽略(在system prompt里) |
| 插件化 | 单一功能 | 16插件注册表, 可插拔 |
| 安全降级 | 无 | 三重保险+自动恢复 |
| 依赖 | 无cron调用→从未执行 | 直接嵌入run_agent.py→每次对话必执行 |
| 可扩展 | 需手动修改代码 | 注册表添加一行即可 |
