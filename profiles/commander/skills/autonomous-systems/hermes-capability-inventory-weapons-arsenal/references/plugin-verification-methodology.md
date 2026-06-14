# Plugin Verification Methodology

**Why this exists**: 2026-06-02 audit revealed that "插件加载成功" ≠ "插件真实生效". 
20+ plugins loaded without error but produced zero meaningful output (just "✅已加载").

**Root cause**: `_run_script_module` was a `pass` — it imported the module and stopped. 
No `main()`, no `check()`, no class instantiation was ever called.

## The verification ladder

There are 4 levels of "working". Never claim level 4 until you've proven level 1-3.

```
Level 1: File exists                     → os.path.exists(path)
Level 2: Module imports without error    → try: import; except: log
Level 3: Module produces output          → subprocess.run + capture_output
Level 4: Output is meaningful            → check output length > plugin_name + "✅已加载"
```

## How to verify a plugin (step by step)

### Step 1: Check the module actually has callable functions

```python
import importlib.util
spec = importlib.util.spec_from_file_location("name", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# List classes and functions
classes = [x for x in dir(mod) if isinstance(getattr(mod, x), type) and not x.startswith('_')]
functions = [x for x in dir(mod) if callable(getattr(mod, x)) and not x.startswith('_') and not isinstance(getattr(mod, x), type)]
print(f"Classes: {classes}")
print(f"Functions: {functions}")

# Check for key methods
if "SomeClass" in classes:
    instance = getattr(mod, "SomeClass")()
    methods = [x for x in dir(instance) if not x.startswith('_') and callable(getattr(instance, x))]
    print(f"Instance methods: {methods}")
```

**2026-06-02 findings using this method:**
- `agent_company_engine.py` had `AgentsCompanyEngine` (with 's'), not `AgentCompanyEngine`
- `capability_registry.py` had `get_stats()`, not `get_registry()`
- `model_router.py` had `select()`, not `route()` or `analyze()`
- `auto_recall.py` had `AutoRecall` class, not top-level `search()`/`recall()` functions

### Step 2: Run the module as a subprocess (most reliable)

```python
import subprocess
r = subprocess.run([sys.executable, mod_path], capture_output=True, text=True, timeout=15)
out = r.stdout.strip() or r.stderr.strip()
if out and len(out) > 20:  # meaningful output
    print(f"✅ Produces output ({len(out)} chars)")
else:
    print(f"❌ No output — module may be decoration")
```

This is the `_run_script_module_subprocess()` pattern. It's the most stable because:
- It doesn't depend on knowing internal class/method names
- It captures stdout/stderr regardless of how the module prints
- Timeout prevents blocking

### Step 3: Check the output is not just "✅已加载"

```python
# In the injected context, filter out decoration-only lines:
stripped = line.replace(plugin_name, '').replace('[', '').replace(']', '').replace('✅', '').replace(' ', '').strip()
if stripped in ['已加载', '已加载(无输出)', ''] or len(stripped) < 3:
    print(f"❌ {plugin_name} → 空壳")
else:
    print(f"✅ {plugin_name} → {line.strip()[:100]}")
```

### Step 4: Check the LLM actually sees the output (pre plugins only)

```python
ctx = safe_hook_pre_conversation(None, "test task")
for name in plugin_names:
    if name in ctx:
        idx = ctx.find(name)
        line_end = ctx.find('\n', idx)
        line = ctx[idx:line_end] if line_end > 0 else ctx[idx:]
        print(f"  [{name}] {line.strip()[:100]}")
    else:
        print(f"  [{name}] NOT IN CONTEXT")
```

## The anti-hallucination trap

**2026-06-02 failure**: I said "PRE 21个中只有1个失效". The actual data showed 11.

Why it happened:
1. I ran a quick test that showed `loaded=21, failed=1` — interpreted as "20 working"
2. I didn't check what each plugin *actually output* — just that it loaded without error
3. I confused "imported successfully" with "produced meaningful output"

**Fix**: Never say "X个插件生效" without running the actual output check (Step 3 above).
Always run the full audit script before making any quantitative claim about plugin health.

## Full audit script

```python
# Run this whenever asked "how many plugins are really working"
import os, sys
os.environ.pop('_HERMES_PLUGIN_MGR', None)
sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
for k in list(sys.modules.keys()):
    if 'enhancement' in k:
        del sys.modules[k]
import agent_enhancement_manager as m
m._mod_cache = {}
m._pre_conversation_done = False
m._loaded_plugins.clear()
m._failed_plugins.clear()
m._plugin_errors.clear()
m._force_context = None

ctx = m.safe_hook_pre_conversation(None, '检查推送系统')
s = m.get_plugin_status()

plugin_names = [...all 21 pre plugins...]
real = 0; empty = 0
for name in plugin_names:
    if ctx and name in ctx:
        idx = ctx.find(name)
        line_end = ctx.find('\n', idx)
        line = ctx[idx:line_end] if line_end > 0 else ctx[idx:]
        stripped = line.replace(name,'').replace('[','').replace(']','').replace('✅','').replace(' ','').strip()
        if stripped in ['已加载','已加载(无输出)',''] or len(stripped) < 3:
            empty += 1
        else:
            real += 1
    else:
        empty += 1

print(f"PRE: {real}真实 / {empty}空壳 / {s['failed']}失败")
```
