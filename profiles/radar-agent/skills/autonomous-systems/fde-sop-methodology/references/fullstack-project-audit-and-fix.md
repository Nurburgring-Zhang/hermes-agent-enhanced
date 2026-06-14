# Full-Stack Project Audit & Fix Pattern

## When to use this

You're given a project directory — unfamiliar codebase, no context — and the goal is to audit it, test it, fix issues, and deliver a working version. This is NOT a deep architecture analysis (use `deep-code-architecture-analysis` for that) — this is a practical "make it run" audit.

## 7-Step Protocol

### Step 1: Read the docs (15min)

Read in order:
1. `README.md` — what is this project?
2. `start_linux.sh` / `start.bat` — how is it supposed to run?
3. `package.json` — frontend deps + scripts
4. `backend/requirements.txt` / `pyproject.toml` — backend deps
5. `vite.config.ts` / `webpack.config.js` — build config
6. Key doc files in `docs/` — SETUP_GUIDE, API docs, audit reports

**Key findings to extract**: ports used, startup sequence, dependency list, whether DB/Redis/GPU are actually required or optional.

### Step 2: Check running state (5min)

```bash
# Check if anything is already running
curl -s http://127.0.0.1:8001/health | python3 -m json.tool
curl -s http://127.0.0.1:5173/ | head -5
lsof -i:8001 -i:5173 2>/dev/null

# Check node_modules/venv
ls node_modules/.package-lock.json 2>/dev/null && echo "npm deps installed"
ls backend/venv/bin/python 2>/dev/null && echo "venv exists"
```

### Step 3: Check proxy connectivity (critical for Vite+FastAPI stacks)

This is the #1 gotcha in Vite+backend setups. The frontend runs on one port (5173) and needs to proxy API calls to the backend (8001).

**Common problems:**
- `/health` endpoint is NOT under `/api` — FastAPI often has `/health` at root, but Vite proxy only forwards `/api/*`
- WebSocket proxy may not be configured
- Static assets from publicDir may have wrong paths

**How to check:**
```bash
# From the browser, test through Vite proxy:
curl -s http://localhost:5173/api/health      # Should return 200 from backend
curl -s http://localhost:5173/health           # Should proxy to backend, NOT serve HTML

# If /health returns HTML, proxy is missing
# Fix: add proxy rule in vite.config.ts:
#   '/health': { target: 'http://localhost:8001', changeOrigin: true },
```

### Step 4: Check static asset paths (Vite + publicDir)

When `vite.config.ts` sets `root: 'src/renderer'` and `publicDir: '../../public'`:

- The `public/` directory is relative to project root, NOT to `root`
- Files in `public/` are served at `/` in the dev server
- HTML files in `root` (e.g., `src/renderer/index.html`) reference public assets as `/asset-name.ext`
- **DO NOT use relative paths** like `./live2d/file.js` — use `/live2d/file.js`

**Common symptom:** Vite logs "This file is in ../../public and will be copied as-is... should not be imported from source code"

**Fix:** Change `<script src="./live2d/file.js">` to `<script src="/live2d/file.js">`

### Step 5: Start and verify backend

```bash
cd backend && python3 server.py
# Wait for health check to pass
for i in 1..30; do
  curl -s http://127.0.0.1:8001/health > /dev/null && break
  sleep 1
done
```

**Verify endpoints work, not just health:**
```bash
curl -s http://127.0.0.1:8001/api/agents | python3 -c "import sys,json;print(len(json.load(sys.stdin)))"
curl -s http://127.0.0.1:8001/api/skills | python3 -c "import sys,json;print(len(json.load(sys.stdin)))"
```

### Step 6: Start and verify frontend

```bash
cd project-root && npx vite --host 0.0.0.0
```

**Verify via browser or curl:**
```bash
curl -s http://localhost:5173/ | head -5  # Should return HTML
```

**Check console for JS errors** using browser_console tool. Key things to verify:
- No runtime JS errors
- WebSocket connected
- Backend data loads (agents count, skills count show in UI)
- Navigation between pages works

### Step 7: Production build check

```bash
npx vite build 2>&1 | tail -10
```

**Check for:**
- Build succeeds (exit 0)
- Module count reasonable
- Chunk size warnings (non-blocking, but note them)

## Typical Fix Patterns

| Problem | Symptom | Fix |
|---------|---------|-----|
| Vite proxy missing routes | `/health` returns HTML, frontend shows "Offline" | Add proxy rules for `/health`, `/metrics`, `/ws` |
| Static asset path wrong | "This file is in public and will be copied as-is" | Use absolute path `/asset.js` not relative `./asset.js` |
| Old process still running | Port conflict | `pkill -f "server.py\|vite"` before restart |
| Startup script brittle | No health check, no cleanup | Add wait-for-health loop + trap for SIGTERM |

## Startup Script Template

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"

# 1. Clean stale processes
pkill -f "server.py\|vite" 2>/dev/null || true
sleep 1

# 2. Start backend
python3 backend/server.py &
BACKEND_PID=$!

# 3. Wait for health
for i in $(seq 1 30); do
  curl -s http://127.0.0.1:8001/health > /dev/null 2>&1 && break
  sleep 1
done

# 4. Start frontend
npx vite --host 0.0.0.0 &
FRONTEND_PID=$!

# 5. Show status
echo "Backend: http://localhost:8001"
echo "Frontend: http://localhost:5173"

# 6. Clean shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
```

## NanoBot Factory Real Case (2026-06-06)

Project: `D:\minimax\nanobot-factory\nanobot-factory`
Stack: FastAPI (port 8001) + Vite/React (port 5173)
Backend: 33 agents, 18 skills registered

**Fixes applied:**
1. Vite config: added `/health`, `/metrics`, `/ws` proxy rules
2. `index.html`: changed `./live2d/live2dcubismcore.min.js` → `/live2d/live2dcubismcore.min.js`
3. `start_linux.sh`: rewrote with proper health check loop, cleanup, and status reporting

**Known issues (non-blocking):**
- Live2D WebGL shader warning on some hosts (PIXI.js v6 compatibility)
- Build chunk >500KB warning (normal for large apps)
