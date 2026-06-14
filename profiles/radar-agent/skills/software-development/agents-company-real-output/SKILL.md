---
name: agents-company-real-output
title: Make Agents Company Generate Real, Runnable Projects
description: Fix the Agents Company workflow to produce actual runnable software instead of simulated/mock data by patching handlers to call RealProjectGenerator methods. Covers indentation issues, verification, and extending the generator.
difficulty: intermediate
duration: 30 minutes
---

## Problem

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Agents Company's workflow handlers (`_handler_backend_dev`, `_handler_frontend_dev`, etc.) were returning **simulated dictionaries** instead of generating real project files. The `RealProjectGenerator` class existed with actual file-writing methods, but handlers weren't calling them.

Example of broken handler:
```python
def _handler_backend_dev(self, context: Dict) -> Dict:
    result = {
        'developed_modules': ['用户服务', '业务逻辑服务', '数据访问层'],
        'apis_implemented': ['REST API', 'GraphQL端点'],
        'status': 'backend_completed'
    }
    return result  # ← Returns fake data, no files written!
```

## Solution

### Step 1: Patch Handlers to Call Real Generators

Replace simulated returns with actual calls to `self.project_generator`:

```python
def _handler_backend_dev(self, context: Dict) -> Dict:
    project_dir = self._find_project_dir(context)
    if project_dir and project_dir.exists():
        files = self.project_generator.generate_backend_code(project_dir)
        result = {
            'status': 'backend_completed',
            'output_path': str(project_dir),
            'files_generated': [str(f.relative_to(project_dir)) for f in files.values()]
        }
    return result
```

Same pattern for:
- `_handler_frontend_dev` → calls `generate_frontend_code()`
- `_handler_system_integration` → writes `tests/integration/` files
- `_handler_deployment` → writes `deploy/` k8s manifests
- `_handler_project_closure` → writes `docs/CLOSURE.md`

### Step 2: Fix Indentation Corruption

**Pitfall:** When patching with multi-line strings, extra indentation gets added, causing `IndentationError`.

**Symptoms:**
```
IndentationError: expected an indented block after function definition on line 672
Line 672:         def _handler_deployment(...)  # 8 spaces instead of 4
```

**Fix:** Check method def lines - they must have exactly **4 spaces** at class level. If any have 8, dedent the entire function body by 4 spaces. Verify with:
```bash
python3 -m py_compile agents_company_executor.py
```

### Step 3: Verify Full Workflow

Run each handler manually to confirm file generation:
```python
context = {'project_id': 'TEST001', 'project_name': 'Test App'}
result = executor._handler_workflow_init(context)
result = executor._handler_backend_dev(context)
result = executor._handler_frontend_dev(context)
# ... continue through all handlers
```

Then inspect output directory:
```bash
find ~/.hermes/agents_company/outputs/TEST001* -type f | sort
```

Expected real files:
- `src/backend/main.py` (FastAPI app)
- `src/backend/requirements.txt`
- `src/frontend/package.json`
- `src/frontend/src/App.tsx`
- `docker-compose.yml`
- `deploy/deploy.yaml`
- `tests/integration/test_integration.py`
- `docs/CLOSURE.md`

## Key Files

- **Executor:** `~/.hermes/agents_company/agents_company_executor.py`
- **Generator:** `~/.hermes/agents_company/real_project_generator.py`
- **Outputs:** `~/.hermes/agents_company/outputs/`

## Validation Checklist

- [ ] `py_compile` succeeds on executor
- [ ] All `_handler_*` methods have exactly 4-space indent for `def`
- [ ] `RealProjectGenerator.generate_backend_code()` writes at least 3 files
- [ ] `RealProjectGenerator.generate_frontend_code()` writes package.json + App.tsx
- [ ] Workflow completion creates ≥10 real files on disk
- [ ] Generated backend has valid FastAPI structure
- [ ] Generated frontend has valid React + Vite config

## What RealProjectGenerator Currently Generates

**Backend (minimal but valid):**
- `main.py` - FastAPI app with health endpoint
- `requirements.txt` - fastapi, uvicorn, sqlalchemy, pydantic
- `models.py` - placeholder SQLAlchemy models
- `crud.py` - placeholder CRUD stub

**Frontend (minimal but valid):**
- `package.json` - React 18 + Vite + TypeScript
- `src/App.tsx` - simple Hello World component

**Infrastructure:**
- `docker-compose.yml` - Postgres + Backend + Frontend services
- `deploy/deploy.yaml` - basic K8s Deployment manifest
- `tests/integration/test_integration.py` - placeholder test

## Advanced: Extending RealProjectGenerator — Production-Grade Pattern

**Real-world experience:** The original minimal generator produced ~30 files but only 1 working endpoint. Through iterative enhancement we discovered a repeatable pattern for upgrading any scaffold to **enterprise production-grade systems**.

### Architecture: Multi-Layer Production Stack

When you need **100k+ RPS, 100M+ records, 1B+ orders**, generate ALL these layers:

#### Backend (28 files) — FastAPI + SQLAlchemy + Celery + Redis

**Database Layer:**
```python
# config/database.py — Connection pooling tuned for scale
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Base connections per worker
    max_overflow=40,        # Burst capacity
    pool_pre_ping=True,     # Detect stale connections
    pool_recycle=1800,      # Recycle every 30min
)
```

**Models with Scale Hints:**
```python
from sqlalchemy import BigInteger, Index, ForeignKey

class Product(Base):
    __tablename__ = "products"
    id = Column(BigInteger, primary_key=True)          # Supports 2B+ records
    sku = Column(String(50), unique=True, index=True) # Unique business key
    price = Column(Float, index=True)                  # Range query index
    stock = Column(Integer, index=True)                # Inventory queries

    __table_args__ = (
        Index("idx_product_category_active", "category_id", "is_active", "stock"),
    )
```

**CRUD with Row-Level Locking:**
```python
def reserve_stock(db: Session, product_id: int, quantity: int):
    # SELECT ... FOR UPDATE prevents overselling
    product = db.query(Product).filter(
        Product.id == product_id
    ).with_for_update().first()
    if product.available_stock < quantity:
        return False
    product.reserved_stock += quantity
    db.commit()
```

**Main App — Performance Middlewares:**
```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse  # 2x faster than std json

app = FastAPI(default_response_class=ORJSONResponse)
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Async Workers (Celery):**
```python
# celery_worker.py
from celery import Celery
celery_app = Celery(broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_routes = {
    "workers.tasks.import_*": {"queue": "import"},
    "workers.tasks.report_*": {"queue": "reports"},
}
```

**Files to generate (complete list):**
- `config/database.py` — pool config + session manager
- `core/config.py` — Pydantic settings + env vars
- `core/security.py` — JWT + bcrypt + OAuth2PasswordBearer
- `models.py` — User, Product, Category, Order, OrderItem, InventoryLog, Cart, AuditLog
- `schema.py` — Pydantic schemas with validators
- `crud.py` — full CRUD + pagination + filtering + stats
- `api/v1/auth.py` — register/login endpoints
- `api/v1/users.py` — user list/detail (protected)
- `api/v1/products.py` — product listing with search/filters
- `api/v1/orders.py` — order creation + fulfillment
- `api/v1/stats.py` — dashboard aggregates
- `celery_worker.py` + `workers/tasks.py` — async task definitions
- `alembic.ini` + `alembic/env.py` — DB migrations
- `requirements.txt` — all deps (fastapi, uvicorn, sqlalchemy, celery, redis, passlib, python-jose, orjson, gunicorn)
- `Dockerfile` — multi-stage with non-root user
- `.env.example` — all config vars documented

#### Frontend (37 files) — React 18 + TypeScript + Vite

**State + Caching:**
```typescript
// store/authStore.ts — Zustand with persistence
export const useAuthStore = create<AuthState>()(
  persist((set) => ({...}), { name: "auth" })
);

// hooks/useProducts.ts — React Query for server state
export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => api.productsAPI.list().then(r => r.data),
    staleTime: 5 * 60 * 1000,  // 5min cache
  });
}
```

**Routing + Protected Routes:**
```tsx
<Routes>
  <Route path="/" element={<HomePage />} />
  <Route path="/products" element={<ProductsPage />} />
  <Route path="/checkout" element={
    <ProtectedRoute><CheckoutPage /></ProtectedRoute>
  } />
</Routes>
```

**Pages to generate:**
- `pages/HomePage.tsx` — landing + CTA
- `pages/LoginPage.tsx` — username/password + mutation
- `pages/ProductsPage.tsx` — grid with search + pagination
- `pages/ProductDetailPage.tsx` — stock/rating + add-to-cart
- `pages/CartPage.tsx` — quantity adjust + total
- `pages/CheckoutPage.tsx` — address + payment + order creation
- `pages/OrdersPage.tsx` — order history

**Components:**
- `components/Navbar.tsx` — nav + cart badge + auth links
- `components/ProductCard.tsx` — reusable product tile

**Services:**
- `services/api.ts` — axios instance with JWT interceptor + typed endpoints

**Config files:**
- `package.json` (react, react-dom, react-router-dom, zustand, axios, @tanstack/react-query)
- `vite.config.ts` (code-splitting: manualChunks vendor)
- `tsconfig.json` (strict mode, path aliases)
- `tailwind.config.js` (custom primary color palette)
- `Dockerfile` (Node builder → nginx)

#### Infrastructure (15+ files)

**Docker Compose (multi-service):**
```yaml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    command: ["postgres", "-c", "max_connections=500"]
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
  celery-worker:
    command: celery -A celery_worker.celery_app worker --concurrency=8
  backend:
    build: ./src/backend
    command: uvicorn main:app --workers 4
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379/0
  frontend:
    build: ./src/frontend
    ports: ["3000:80"]
```

**Kubernetes Production (HPA autoscaling):**
```yaml
# k8s/backend-deployment.yaml
spec:
  replicas: 4  # min
  template:
    spec:
      containers:
      - name: backend
        resources:
          requests: {cpu: "500m", memory: "1Gi"}
          limits: {cpu: "2", memory: "2Gi"}
        livenessProbe:  # restart on hang
          httpGet: {path: /health, port: 8000}
        readinessProbe: # traffic only when ready
          httpGet: {path: /health/ready, port: 8000}

# k8s/backend-hpa.yaml
spec:
  minReplicas: 4
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # scale at 70% CPU
```

**NGINX Rate Limiting:**
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
location /api/auth/login {
    limit_req zone=login burst=5 nodelay;
}
```

**Monitoring Stack:**
- `deploy/monitoring/prometheus.yml` — scrape `/metrics` every 15s
- `deploy/monitoring/grafana/dashboards/api-dashboard.json` — pre-built QPS/latency/DB panels
- Alerts: error_rate > 5%, p99 > 500ms, db_connections > 80%, redis_memory > 85%

**CI/CD (GitHub Actions):**
```yaml
on: [push, pull_request]
jobs:
  test-backend:
    runs-on: ubuntu-latest
    services: {postgres: {image: postgres:16}}
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r src/backend/requirements.txt
      - run: pytest tests/
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - run: cd src/frontend && npm ci && npm run build
  deploy:
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v0.1.7
        with:
          host: ${{ secrets.SERVER_HOST }}
          script: cd /opt/app && docker-compose up -d --build
```

#### Documentation (7 files)

```
docs/
├── README.md              # Project overview + quick start
├── api/README.md          # Endpoint reference
├── architecture/
│   ├── README.md          # ADR index
│   ├── ADR-001-fastapi.md # Why FastAPI (async, auto-docs)
│   ├── ADR-002-database.md # Why PostgreSQL (ACID, JSONB)
│   ├── ADR-003-caching.md  # Why Redis (2GB LRU)
│   └── ADR-004-async.md   # Why Celery (task queues)
└── operations/
    ├── README.md          # Deployment + monitoring
    ├── runbook.md         # Incident response (DB down, high latency)
    ├── performance-tuning.md  # PostgreSQL shared_buffers, pool tuning
    ├── backup-recovery.md      # PITR + WAL archiving
    └── security.md        # Secrets, network, audit logging
```

### Technique: Base64-Encoded Whole-File Replacement

**Problem:** Triple-quoted f-strings (`f"""..."""`) with embedded braces `{project_dir.name}` cause `SyntaxError: unexpected character after line continuation` in the generated generator code. Nested quotes within multi-line strings create a "hell of escaping."

**Solution pattern:**
```python
import base64, subprocess, sys

# Build the ENTIRE replacement as raw bytes (no escaping needed)
replacement = b'''    def generate_backend_code(self, project_dir: Path):
        backend = project_dir / "src/backend"
        # Full implementation with raw strings...
'''

# Encode to base64 and decode in the target file
encoded = base64.b64encode(replacement).decode('ascii')
cmd = [
    sys.executable, "-c",
    f"import base64, pathlib; "
    f"pathlib.Path('{target}').write_text("
    f"base64.b64decode('{encoded}').decode('utf-8'), encoding='utf-8')"
]
subprocess.run(cmd)
```

**Why it works:** You write the replacement code exactly as you want it (no escaping), then base64-encode it. The target file receives decoded UTF-8 as if you'd written it directly.

**Alternative safer approach:** Build file content as a list concatenation in Python, then `"".join(lines)` — avoids triple quotes entirely.

### Validation Checklist (Production-Ready)

- [ ] Backend: 28+ files, FastAPI app with `/health` + `/metrics`
- [ ] Database: QueuePool 20/40, BigInteger IDs, composite indexes, BigInt for 2B+ records
- [ ] Security: JWT + bcrypt + OAuth2 + password validators
- [ ] Concurrency: SELECT FOR UPDATE for stock, Celery workers + Redis
- [ ] Performance: ORJSONResponse + GZipMiddleware + Redis cache
- [ ] Frontend: React 18 + Router v6 + Zustand + React Query + Tailwind
- [ ] Features: product listing (pagination + search), cart, checkout, order history
- [ ] Infrastructure: Docker Compose + K8s Deployment + HPA (4-20 replicas)
- [ ] Monitoring: Prometheus scrape + Grafana dashboard JSON + health probes
- [ ] CI/CD: GitHub Actions pipeline (test → build → deploy)
- [ ] Documentation: API spec + ADRs + ops runbook + tuning guide
- [ ] Scale targets documented: 100k RPS, 100M products, 1B orders, 10M users
- [ ] All files write non-empty, `py_compile` succeeds, generated project runs

### Common Pitfalls & Fixes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| `SyntaxError: unexpected character after line continuation` | f-string with `{` or `}` inside triple quotes (brace interpreted as f-string placeholder) | Use list-join pattern: `"".join([...])` or base64 encoding |
| `NameError: name 'project_id' is not defined` in `_create_root_files` | Parameter not passed from `create_project_structure` | Add `project_id` param to helper, update caller |
| `IndentationError: expected an indented block` after patch | Multi-line string in patch added extra indent | Dedent entire replacement block by 4 spaces before inserting |
| No files appear on disk | Handler returns mock dict instead of calling generator | Patch handler to call `self.project_generator.generate_*_code()` |
| Frontend store not working | Zustand store missing `persist` middleware or wrong import path | Add `persist()` wrapper, verify `useAuthStore` usage |
| DB connection exhaustion | Pool size too small for worker count | Increase QueuePool `pool_size` + `max_overflow`, match uvicorn workers |
| "Product out of stock" race condition | Missing `with_for_update()` lock | Add `with_for_update()` to product query before stock check |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Indentation at line 672 shows 8 spaces | Corrupted patch indentation | Rewrite method with exact 4-space indent |
| Backend only generates 1 file | `generate_backend_code` too minimal | Expand to full 28-file production stack |
| Frontend missing pages | `App.tsx` has no routes | Add Routes + Pages entries |
| No K8s HPA file | `generate_infrastructure` incomplete | Add `backend-hpa.yaml` with minReplicas/maxReplicas |

### Enhanced Frontend Generator (Vite + React)

```python
def generate_frontend_code(self, project_dir: Path) -> Dict[str, Path]:
    frontend = project_dir / "src/frontend"
    (frontend / "src").mkdir(parents=True, exist_ok=True)

    # Package.json
    pkg = {
        "name": project_dir.name,
        "version": "1.0.0",
        "private": True,
        "type": "module",
        "scripts": {"dev": "vite", "build": "tsc && vite build"},
        "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
        "devDependencies": {"@vitejs/plugin-react": "^4.2.0", "typescript": "^5.3.0", "vite": "^5.0.0"},
    }
    (frontend / "package.json").write_text(json.dumps(pkg, indent=2), encoding="utf-8")

    # Vite config
    (frontend / "vite.config.ts").write_text(
        'import { defineConfig } from "vite";\n'
        'import react from "@vitejs/plugin-react";\n\n'
        'export default defineConfig({ plugins: [react()], server: { port: 3000 } });\n',
        encoding="utf-8"
    )

    # Index + App
    (frontend / "index.html").write_text(
        '<!DOCTYPE html>\n<html><head><meta charset="UTF-8" /><title>App</title></head>'
        '<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>\n',
        encoding="utf-8"
    )
    (frontend / "src" / "main.tsx").write_text(
        'import React from "react";\n'
        'import ReactDOM from "react-dom/client";\n'
        'import App from "./App";\n\n'
        'ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App />);\n',
        encoding="utf-8"
    )
    (frontend / "src" / "App.tsx").write_text(
        'export default function App() {\n'
        '  return (\n'
        '    <div>\n'
        '      <h1>Generated App</h1>\n'
        '      <p>Welcome to your auto-generated project!</p>\n'
        '    </div>\n'
        '  );\n'
        '}\n',
        encoding="utf-8"
    )
    return {"package": frontend / "package.json", "app": frontend / "src" / "App.tsx"}
```

### Technique: Base64-Encoded Whole-File Replacement

**When to use:** When `patch()` fails due to triple-quoted string hell (f-strings with embedded quotes, braces, newlines)

**Why:** Line-by-line string concatenation in Python source breaks when strings contain `"""`, `'''`, braces `{}`, or backslashes. Multiple escape layers become unmaintainable.

**How:**

```python
import subprocess, base64

# 1. Build the ENTIRE replacement section as raw bytes (no escaping)
new_code = b'''    def generate_backend_code(self, project_dir: Path):
        backend = project_dir / "src/backend"
        # ... complete method with raw string content
'''

# 2. Encode to base64
encoded = base64.b64encode(new_code).decode('ascii')

# 3. Write via subprocess to avoid sandbox quoting issues
subprocess.run([
    sys.executable, "-c",
    f"import base64, pathlib; "
    f"pathlib.Path('{target_path}').write_text("
    f"base64.b64decode('{encoded}').decode('utf-8'), encoding='utf-8')"
])
```

**Benefits:**
- Single source of truth - write normal Python code in the `b'''...'''` block
- No escape character nightmares
- Works even with nested triple quotes
- Compile-verify before deployment

**Caveat:** Must patch the file before it's loaded into memory to avoid reference conflicts.

### Troubleshooting Addendum

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SyntaxError: unexpected character after line continuation` | F-string with unescaped braces in string literal | Build strings as lists then `"".join()`, not inline f-strings |
| `NameError: name 'X' is not defined` in helper method | Closure captured variable not passed as parameter | Add missing parameter to helper method signature and update all call sites |
| `IndentationError` after patch | Extra indent from multiline string quoting | Dedent entire block; verify with `py_compile` |
| No output files | Generator not invoked or returns mock data | Check handlers call `self.project_generator.generate_*_code()` |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `IndentationError` line 672+ | Corrupted patch added extra indent | Dedent function body by 4 spaces |
| No files in output/ | Handlers not calling generator | Patch handlers to use `self.project_generator` |
| Only placeholder code | RealProjectGenerator not improved | Edit `real_project_generator.py` to write real logic |
| Workflow stops early | Previous handler failed | Check `previous_output['output_path']` propagation |

## Related Skills

- `software-development/test-driven-development` - for writing tests for generated code
- `devops/python-project-setup-with-uv` - for setting up Python projects
## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
