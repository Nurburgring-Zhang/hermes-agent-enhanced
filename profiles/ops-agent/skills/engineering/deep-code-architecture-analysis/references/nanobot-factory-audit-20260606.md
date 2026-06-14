# NanoBot Factory Audit — Bug Report & Fixes

Project: NanoBot Factory (FastAPI + React + Electron)
Session: 2026-06-06
Total tests: 85, Passed: 84 (98.8%)

## Bug #1: State Copy-vs-Mutation (CRITICAL)

**Symptom:** POST /api/assets returned 201 with correct data, but GET returned empty. DELETE also failed with 404.

**Root Cause:** `AppState.assets` property returned `self._assets.copy()`. POST/GET/DELETE endpoints called `state.assets` (getting the copy), mutated the copy, and never wrote back. The original `_assets` dict stayed empty.

**Files affected:** `backend/server.py` lines 2348-2364

**Fix:**
```python
# Before:
@app.post("/api/assets")
async def create_asset(asset: Asset):
    assets = state.assets  # COPY
    assets[asset.id] = asset
    return asset

# After:
@app.post("/api/assets")
async def create_asset(asset: Asset):
    with state._lock:
        state._assets[asset.id] = asset
    return asset
```

Same fix applied to GET and DELETE endpoints.

**Lesson:** Any AppState property that returns a copy is read-only. Always use `state._items[key] = value` inside the lock for mutations.

## Bug #2: Body vs Query Parameter (IMPORTANT)

**Symptom:** POST /api/cluster/tasks returned empty response with curl.

**Root Cause:** `payload: Dict[str, Any]` was parsed as a query parameter (FastAPI default for simple types), not from JSON body. Required `from fastapi import Body` and `payload: Dict[str, Any] = Body(...)`.

**Fix:**
```python
from fastapi import Body, Query

@app.post("/api/cluster/tasks")
async def submit_cluster_task(
    name: str = Query(...),
    task_type: str = Query(...),
    payload: Dict[str, Any] = Body(...),   # WAS: payload: Dict[str, Any]
    required_capabilities: Optional[List[str]] = Query(None),
    depends_on: Optional[List[str]] = Query(None)
):
```

## Bug #3: Missing Import (BUILD FAILURE)

**Symptom:** Server crashed on startup with `NameError: name 'Query' is not defined`

**Root Cause:** Fixed Bug #2 but forgot to add `Query` to the import statement.

**Fix:** Added `Query` to `from fastapi import ... Body, Query`

## Incidental Fix #4: Vite Proxy Configuration

**Symptom:** Frontend at localhost:5173 couldn't reach /health, /metrics, /ws endpoints (not proxied to backend at :8001).

**Fix:** Added proxy rules to `vite.config.ts`:
```javascript
'/health': { target: 'http://localhost:8001', changeOrigin: true },
'/metrics': { target: 'http://localhost:8001', changeOrigin: true },
'/ws': { target: 'ws://localhost:8001', ws: true },
```

## Incidental Fix #5: Live2D Path Resolution

**Symptom:** Vite tried to pre-transform `live2dcubismcore.min.js` as a module, causing repeated "Pre-transform error" warnings.

**Fix:** Changed `<script src="./live2d/..."` to `<script src="/live2d/..."` in index.html. The file lives in `public/live2d/` and is copied as-is by Vite — should be referenced with absolute path from publicDir root.

## Incidental Fix #6: Pydantic V2 Deprecation

**Symptom:** `PydanticDeprecatedSince20: The 'dict' method is deprecated; use 'model_dump' instead`

**Fix:** `return [skill.dict() for skill in state.skills.values()]` → `skill.model_dump()`
