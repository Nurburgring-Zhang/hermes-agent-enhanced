# FastAPI Full-API Audit Methodology

## When to Use This Approach

When auditing a FastAPI backend, testing ALL endpoints systematically to verify:
- Every endpoint responds correctly (not just the happy path)
- State management is thread-safe (common FastAPI anti-pattern)
- Query vs Body parameter binding is correct
- Error responses for edge cases (not found, invalid input)

## Step 1: Discover All Routes

```bash
grep -n "@app\.\(get\|post\|put\|delete\|websocket\|patch\)" backend/server.py | head -50
```

Categorize routes into logical groups: system health, agent management, skills, assets/CRUD, generation, LLM/models, API keys, OmniGen, AIRI, database ops.

## Step 2: Group-by-Group API Testing

For each group test: list, detail, create (full + minimal params), update, delete, filter, and error cases.

### Testing Pattern

```bash
# List with structured output parsing
curl -s http://localhost:8001/api/resources | python3 -c "
import sys,json
data = json.load(sys.stdin)
resources = data if isinstance(data, list) else data.get('resources', data.get('items', []))
print(f'Total: {len(resources)}')
"

# Create with full parameters
curl -s -X POST http://localhost:8001/api/resources -H "Content-Type: application/json" \
  -d '{"field1":"value1","nested":{"key":"val"},"tags":["a","b"]}' | python3 -m json.tool

# Error case
curl -s http://localhost:8001/api/resources/nonexistent | python3 -m json.tool
```

## Step 3: State Management Bug Pattern (Critical)

### The Copy-vs-Mutation Trap

**Symptom:** POST returns 201 with correct data, but GET returns empty.

**Root cause:** AppState property returns `.copy()`, mutation on the copy is silently lost.

```python
# BAD — creates a copy, mutates copy, never writes back
class AppState:
    @property
    def assets(self):
        return self._assets.copy()  # Returns a COPY

@app.post("/api/assets")
async def create_asset(asset: Asset):
    assets = state.assets  # GETS A COPY
    assets[asset.id] = asset  # MUTATES THE COPY — LOST!
    return asset

# GOOD — directly mutate the underlying dict
@app.post("/api/assets")
async def create_asset(asset: Asset):
    with state._lock:
        state._assets[asset.id] = asset
    return asset
```

**Detection:** Search for patterns where `state.X` property is used for mutation: `items = state.items; items[key] = value`.

**Fix:** Replace with direct `state._items[key] = value` inside the lock.

## Step 4: Body vs Query Parameter Binding

```python
# BAD — Dict[str, Any] defaults to Query parameter
@app.post("/api/tasks")
async def submit_task(
    name: str,
    payload: Dict[str, Any],  # Parsed from query string!
): pass

# GOOD — explicitly mark as Body
@app.post("/api/tasks")
async def submit_task(
    name: str = Query(...),
    payload: Dict[str, Any] = Body(...),
): pass
```

**Detection:** POST endpoint with complex `payload` returning 422 "Field required" = being parsed as query. Fix with `from fastapi import Body, Query`.

## Step 5: Pydantic V2 Migration

```python
# BAD (V1, deprecated):
skill.dict()

# GOOD (V2):
skill.model_dump()
```

## Reference: Test Data Shapes

| Endpoint Type | Data to Include |
|--------------|-----------------|
| Create | Full params, minimal params, duplicate, invalid type |
| Update | Partial update, full overwrite, invalid field |
| List | No filter, type filter, search, limit+offset |
| Get | Existing ID, non-existent ID |
| Delete | Existing, non-existing, already deleted |
| Chat/Execute | With context, without context, empty message |

## Chinese URL Encoding

```bash
# Good practice for Chinese params in URLs
curl -s -X POST "http://...?name=$(python3 -c 'import urllib.parse; print(urllib.parse.quote(\"批量生成\"))')"
```
