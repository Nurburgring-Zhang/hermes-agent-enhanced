# Nanobot Factory Project Deployment Notes

Collected from the first full deployment of a FastAPI+Vue3 project with uvicorn workers.

## Production deployment checklist

Before declaring a FastAPI+Vue3 project production-ready:

1. [ ] Server entry: `production_app.py` importing `app` from main server module
2. [ ] Workers: `uvicorn production_app:app --host 0.0.0.0 --workers 4`
3. [ ] Verify: `ss -tlnp | grep <port>` shows workers active
4. [ ] Verify: `curl <endpoint>` returns 200
5. [ ] README: covers dev mode + prod mode + nginx deployment

## Memory-state sharing caveat

In-memory class-level state (e.g. `CrowdManager._workers: Dict = {}`) is NOT shared across uvicorn workers.
Each worker process has its own copy. This means:
- Data added in worker A is invisible to worker B
- For shared state, use SQLite/PostgreSQL, not in-memory dicts

This is not a bug — it's how multi-process works. But it MUST be documented in the project's design notes.

## Port cleanup ritual (WSL specific)

```bash
# Step 1: Find all listeners on the target port
ss -tlnp | grep 8001

# Step 2: Kill by PID (specific)  
kill -9 <PID>

# Step 3: Verify free
ss -tlnp | grep 8001 || echo "free"

# Step 4: (Alternative) Kill by process name — ONLY when certain it's the right process
pkill -9 -f "python3 server.py"

# Do NOT use pkill -f with a broad pattern — it kills unrelated processes
```

## .env for production

Minimal production .env should set:
- `ALLOWED_ORIGINS` — comma-separated list of frontend URLs
- `DATABASE_PATH` — absolute path to SQLite file
- `LOG_LEVEL=INFO` (not DEBUG)
- `DEV_MODE=false` — disables CORS permissiveness