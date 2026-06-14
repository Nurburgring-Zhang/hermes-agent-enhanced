# Python Bug Patterns Found in LLM-Generated Code

A curated collection of recurring Python bugs that appear in AI-generated Python code.
These are **not** typical human bugs — they are patterns unique to how LLMs generate code.

## Pattern 1: Object Method Confusion (`float.cos()`)

**Symptom:** `AttributeError: 'float' object has no attribute 'cos'`

**Code before fix:**
```python
return (1 - (t * 3.14159 / 2).cos()) if t < 0.5 else ...
```

**Root cause:** The LLM wrote `.cos()` as if `float` had a `.cos()` method (like numpy arrays do with `np.cos()`). In standard Python, you must use `math.cos(t)`.

**Fix:**
```python
import math
return (1 - math.cos(t * 3.14159 / 2)) if t < 0.5 else (1 + math.cos(t * 3.14159 / 2 - 3.14159 / 2))
```

**Detection:** Search for `).cos(`, `).sin(`, `).tan(`, `).sqrt()` patterns.

**Similar patterns:**
- `.sin()` on float → `math.sin()`
- `.sqrt()` on float → `math.sqrt()`
- `.exp()` on float → `math.exp()`
- `.log()` on float → `math.log()`

## Pattern 2: FastAPI Body vs Query Parameter Confusion

**Symptom:** POST endpoint returns empty/422; curl JSON body ignored.

**Root cause:** FastAPI defaults simple types (str, int, Dict) to query params unless annotated with `Body()`.

**Fix:** `payload: Dict[str, Any] = Body(...)`

## Pattern 3: State Copy-vs-Mutation Trap

**Symptom:** Writes return 200 but subsequent reads are empty.

**Root cause:** Thread-safe AppState property returns `self._data.copy()`. Endpoints mutate the copy.

**Fix:** Always access `state._data[key] = value` inside the lock for mutations, not through the property.

## Pattern 4: Async Task KeyError on First Access

**Symptom:** Background async task crashes with `KeyError` on `active_tasks[task_id]` access.

Error trace:
```
state.active_tasks[task_id]["status"] = "running"
KeyError: 'task_xxx'
```

Then the catch block also crashes:
```
state.active_tasks[task_id]["status"] = "failed"
KeyError: 'task_xxx'
```

**Root cause:** Two scenarios:
1. Task dict entry was GC'd between `create_task()` and coroutine execution
2. Multiple rapid requests: task_id from one request leaks into another coroutine

**Fix (2 places):**
1. At the top of the async function, check/re-create:
```python
if task_id not in state.active_tasks:
    logger.warning(f"Task {task_id} not found, re-creating")
    state.active_tasks[task_id] = {"id": task_id, "status": "running", ...}
else:
    state.active_tasks[task_id]["status"] = "running"
```

2. In the catch block, guard the error writing:
```python
except Exception as e:
    if task_id in state.active_tasks:
        state.active_tasks[task_id]["status"] = "failed"
        state.active_tasks[task_id]["error"] = str(e)
    # Still broadcast so the frontend knows
    await manager.broadcast({"type": "generation_failed", ...})
```

## Pattern 5: Pydantic V2 Deprecations

| Deprecated | Replacement |
|---|---|
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.update()` | `.model_update()` |

## Pattern 6: Vite Public Asset Path

Files in `public/` must use absolute paths in HTML: `<script src="/file.js">` not `./file.js`.
