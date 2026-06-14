# 14-Dimensional Software Engineering Quality Audit

## Origin
NanoBot Factory full-codebase audit (2026-06-08). 104 findings: P0(3), P1(5), P2(56), P3(40).
Audited 60 Python files (~123K lines) + 146 TS/TSX files (~61K lines).

## The 14 Audit Dimensions

When the user says "以真实软件工程的完整方法进行全流程分析、审核、测试" (full software engineering audit), run ALL 14 dimensions:

| # | Dimension | Scan Method | Output |
|---|-----------|-------------|--------|
| 1 | **Project Structure** | `find -type f \| sort` | Directory layout, orphan files, backup residue |
| 2 | **Dependencies** | `package.json`, `requirements.txt`, `pyproject.toml` | Dep sync, duplicates, unused deps, polyfills |
| 3 | **Code Style** | tsconfig flags, pytest/pyproject config, ruff/black | Strict mode status, lint config, inline styles |
| 4 | **Dead Code** | `search_files` for imports, grep for class usage | Unreferenced classes/functions, backup files |
| 5 | **Duplicated Logic** | grep enum/crud/dataclass pattern overlaps | Shared models, CRUD repetition |
| 6 | **Security** | Hardcoded keys, path traversal, WS auth, CORS | Risk level, remediation |
| 7 | **API Design** | RESTful conventions: HTTP verbs, naming, error format | Consistency violations |
| 8 | **Test Coverage** | `pytest --coverage`, check `tests/` dir existence | Test gaps, framework missing |
| 9 | **Build Config** | `vite.config.ts`, `tsconfig.json`, webpack | Source maps, host binding, polyfills |
| 10 | **Bare Except** | `grep -rn "^[[:space:]]*except:"` | Silent error swallowing locations |
| 11 | **Type Annotations** | mypy output count | Missing return/param types |
| 12 | **Long Files/Functions** | `wc -l`, grep function line count | Refactoring candidates |
| 13 | **Hardcoded Config** | grep absolute paths, port numbers, model names | Portability blockers |
| 14 | **Error Handling** | grep try/except/HTTPException patterns | Missing recovery, info leakage |

## Priority Classification

```
P0 — 灾难性 (must fix before deploy):
  • No tests at all
  • Tests directory doesn't exist
  • Security vulnerability with clear exploit path
  • Data loss risk

P1 — 严重 (fix in current sprint):
  • 2000+ line single file
  • 30+ bare except: blocks
  • Non-idempotent DELETE endpoints
  • Missing critical error handling

P2 — 一般 (fix within next sprint):
  • TypeScript strict mode disabled
  • Dependency duplication/mismatch
  • Security hardening (path traversal, WS auth)
  • Dead code / backup residue
  • Configuration hardcoding

P3 — 建议 (nice to have):
  • Backup file cleanup
  • Polyfill removal
  • Linting config
  • Mixed language comments
```

## Execution Pattern

### 1. Parallel Scanning Phase
Delegate into parallel workstreams:
- Subagent A: Python backend audit (dimensions 2, 3, 10, 11, 14)
- Subagent B: Frontend/TS audit (dimensions 2, 3, 9)
- Subagent C: Security/deadcode/duplication audit (dimensions 4, 5, 6)
- Self: Project structure, test coverage, API design (dimensions 1, 7, 8)

### 2. Report Aggregation
Consolidate into a single AUDIT_REPORT_FULL.md with:
- Per-dimension findings table (severity / file:line / fix)
- Summary table (P0-P3 counts per dimension)
- Top 10 priority fixes
- Optional: "post-fix" table showing remaining counts

### 3. Priority-Based Fix Execution
After audit output, execute fixes in P0→P1→P2 order:
- **P0 fixes**: Create test infrastructure first (pytest/vitest setup, conftest, sample tests)
- **P1 fixes**: Fix bare excepts, delete dead code, security patches
- **P2 fixes**: Enable strict flags, sync dependencies, extract hardcoded configs

### 4. Regression Verification
After ALL fixes, re-run tests and verify no regressions:
```bash
pytest backend/tests/ -v --timeout=30  # Expect SAME or HIGHER count
```

## What to Include in the Report

Each finding should include:
```
| Severity | Description | File:Line | Fix Suggestion |
```

End with a Top 10 priority list ordered by business impact.

## Traps

### 🕳️ Trap: Server.py 8962 lines — don't try to audit it all at once
The server.py grows to 9000+ lines easily in a FastAPI project. Break it down:
- Lines 1-500: imports, config, middleware
- Lines 500-2000: agent/skill CRUD endpoints (highly repetitive, can sample-check)
- Lines 2000-4000: generation/workflow endpoints (critical — audit fully)
- Lines 4000-6000: database/integration endpoints (medium)
- Lines 6000+: utility endpoints, legacy code (low priority)

### 🕳️ Trap: npm/git node_modules will inflate file counts
Always exclude `node_modules/`, `venv/`, `dist/`, `.git/` from counts.
Get accurate counts: `find backend/ -name "*.py" -not -path "*/venv/*" -not -path "*/node_modules/*" | wc -l`

### 🕳️ Trap: Bare `except:` vs `except Exception:`
Bare `except:` catches `KeyboardInterrupt`, `SystemExit`, `GeneratorExit` which should never be silently caught.
When fixing bare excepts, always type-lock to `except Exception:` or a more specific type.

### 🕳️ Trap: JSON serialization of numpy types
This is the SINGLE most common runtime error in audited Python AI projects.
Check every API endpoint that returns values from numpy/PyTorch operations:
- `np.float32/64` → must `float()`
- `np.int32/64` → must `int()`
- `PosixPath` → must `str()`
- `pd.Timestamp` → must `.isoformat()`
- `Decimal` → must `float()`

### 🕳️ Trap: Pydantic v1 → v2 migration
If the project has both usage patterns, flag it:
- `.dict()` → `.model_dump()`
- `__fields__` → `model_fields`
- `@validator` → `@field_validator`
- `__get_validators__` → `__get_pydantic_core_schema__`
