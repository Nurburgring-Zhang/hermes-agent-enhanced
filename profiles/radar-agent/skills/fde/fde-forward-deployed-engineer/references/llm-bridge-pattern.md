# LLM Bridge Unified Call Layer — FDE Implementation Pattern

## Problem
Every script had its own hardcoded LM Studio + Ollama HTTP calls. Duplicated code, inconsistent timeout handling, no unified fallback, no backend detection caching. 6 modules with the same ~40-line boilerplate.

## Solution: `scripts/llm_bridge.py`
Single entry point for all LLM calls across the system. Three backends auto-selected by priority:

```
delegate_task (Hermes自身LLM, 始终可用)
    → LM Studio (localhost:8080/v1) — 本地开源模型
        → Ollama (localhost:11434) — 本地开源模型
            → fallback (预设默认值, 确保系统不卡死)
```

## API
```python
from llm_bridge import llm_call, llm_call_json, llm_simple, detect_available_backends

# General call
result = llm_call(system_prompt="", user_prompt="", fallback="default",
                  temperature=0.1, max_tokens=2000, timeout=60)
result.text     # output text
result.success  # bool
result.backend  # which backend served it

# JSON-structured call
result = llm_call_json(system_prompt="", user_prompt="", fallback=None,
                       max_tokens=400, timeout=30)
result.data     # parsed dict/list (auto-strips ```json blocks)

# Simple one-shot
text = llm_simple("write a poem", fallback="unavailable")

# Backend detection (cached 30s)
info = detect_available_backends()
# info['primary'] = 'delegate' | 'lmstudio' | 'ollama' | 'fallback'
```

## Migration Stats
- 6 modules migrated in this session: task_boundary, auto_recall, tool_unloader, episodic_injector, skillopt_trainer, self_evolution_engine
- Pattern: replace ~40 lines of try/except HTTP boilerplate with 1 `llm_call_json()` call
- Backend detection cached for 30s — avoids checking port availability on every call
- delegate_task detection returns True if hermes_tools is importable (in-context), False in cron

## Design Decisions
1. `delegate_task` is checked first but often None in cron — this is correct behavior, not a bug
2. LM Studio port 8080 check uses `/v1/models` GET, not `/health` — more reliable
3. Ollama auto-selects best model (qwen2.5 > qwen > llama3.1 > llama3 > mistral)
4. `fallback=None` triggers `{"status": "error"}` JSON — don't parse None
5. Cache TTL 30s — balances freshness vs. port-check overhead
