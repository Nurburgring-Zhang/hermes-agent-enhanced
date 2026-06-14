# llm_bridge Migration — 2026-05-29

## Purpose
Unify all LLM calling across Hermes scripts into a single bridge layer that auto-selects the best available backend.

## Architecture

```
llm_bridge.py (scripts/llm_bridge.py)
├── _call_delegate()    — Hermes own LLM (via delegate_task, active conversation only)
├── _call_lmstudio()    — localhost:8080/v1/chat/completions
├── _call_ollama()      — localhost:11434/api/generate
└── fallback            — preset default value
```

Backend detection is cached for 30 seconds to avoid repeated probe latency on every call.

## Three public interfaces

```python
from llm_bridge import llm_call, llm_call_json, llm_simple, detect_available_backends

# General call: returns LLMResult with .text, .success, .backend, .data
result = llm_call(system_prompt="", user_prompt="", fallback="default", max_tokens=2000, timeout=60)

# JSON output: auto-parses .data
result = llm_call_json(system_prompt="", user_prompt="", fallback=None, ...)
if result.success:
    data = result.data  # parsed dict/list

# Simple text call
text = llm_simple("prompt", fallback="fallback text")

# Detect available backends
info = detect_available_backends()
# -> {"delegate": True, "lmstudio": False, "ollama": False, "primary": "delegate", "all_fallback": False}
```

## Migration pattern

### Before (old — 5 files, all identical pattern):
```python
raw = None
try:
    import urllib.request
    payload = json.dumps({...}).encode()
    req = urllib.request.Request("http://localhost:8080/v1/chat/completions", ...)
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = json.loads(resp.read())["choices"][0]["message"]["content"]
except Exception:
    pass
if not raw:
    try:
        # same for localhost:11434
    except Exception:
        pass
if raw:
    # parse JSON
    ...
    return parsed
return None
```

### After (new — unified):
```python
from llm_bridge import llm_call_json
result = llm_call_json(system_prompt="...", user_prompt="...", fallback=None, max_tokens=500, timeout=10)
if result.success and result.data is not None:
    return result.data
return None
```

## Migrated modules (2026-05-29)

| Module | Before | After | Status |
|--------|--------|-------|--------|
| task_boundary.py | 25 lines LM+Ollama | 8 lines llm_bridge | ✅ |
| auto_recall.py | 30 lines LM+Ollama | 10 lines llm_bridge | ✅ |
| tool_unloader.py | 30 lines LM+Ollama | 10 lines llm_bridge | ✅ |
| episodic_injector.py | 30 lines LM+Ollama | 10 lines llm_bridge | ✅ |
| skillopt_trainer.py | 30 lines LM+Ollama | 10 lines llm_bridge | ✅ |
| self_evolution_engine.py | 25 lines LM+Ollama | 4 lines llm_bridge | ✅ |

## Scripts still with localhost direct calls (future migration candidates)
- l3_persona_scheduler.py
- wake_injector.py  
- l1_extractor.py
- l2_scene_scheduler.py

## Pitfalls
- `delegate_task` is NOT available in cron/background scripts. Those must use fallback or degrade to rules.
- The bridge does NOT retry on timeout — it tries each backend once and falls through. This is by design (cron shouldn't block).
- Backend detection cache is 30s — use `detect_available_backends(force=True)` if you need fresh results.
- llm_bridge.py itself uses localhost:8080/11434 internally — those are NOT "old HTTP calls" needing migration. The bridge IS the abstraction.
