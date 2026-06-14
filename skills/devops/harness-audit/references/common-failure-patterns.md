# Common Failure Patterns Found in Real Audits

## Pattern 1: .venv vs venv Path Typo
**Symptom**: systemd service shows `activating (auto-restart)`, `status=1/FAILURE`, but manual `gateway run` works fine.
**Root Cause**: systemd unit file has `ExecStart=.../.venv/bin/python` but the actual virtualenv is at `.../venv/bin/python`.
**Fix**: `patch` the unit file path, then `systemctl --user daemon-reload && systemctl --user restart`.

## Pattern 2: PYTHONPATH Missing for Editable Install
**Symptom**: `ImportError: cannot import name '__version__' from 'hermes_cli'` in systemd journal but not in manual run.
**Root Cause**: Hermes is installed via `pip install -e .` (editable). The `.pth` file resolves relative to the source directory. systemd needs `WorkingDirectory=/path/to/hermes-agent` to find the package.
**Fix**: Set `WorkingDirectory=/home/administrator/.hermes/hermes-agent` in the systemd unit.

## Pattern 3: Cron Scripts Not in crontab
**Symptom**: Script exists, runs fine manually, but never executes on schedule.
**Root Cause**: Script was added but crontab was never updated.
**Fix**: Add to crontab with explicit python path and log output.

## Pattern 4: Video Engine All Dependencies Present But No Cron
**Symptom**: ffmpeg available, comfyui exists, but no video output ever produced.
**Root Cause**: No cron entry or trigger to invoke video_cron_jobs.py.
**Fix**: Add `*/30 * * * *` cron entry.

## Pattern 5: Multiple systemd Services Conflicting
**Symptom**: `⚠ Both user and system gateway services are installed` — status ambiguous.
**Root Cause**: User installed gateway twice (user-level + system-level).
**Fix**: `sudo hermes gateway uninstall --system` to remove system-level duplicate.

## Pattern 6: Pipeline Script Runs But Produces Fake Success
**Symptom**: `status=delivered` in database but the actual delivery artifacts are skeletons, not real products. QA scores are identical across all products (e.g. always 93.5).
**Root Cause**: No quality gate — pipeline always sets `status=delivered` regardless of actual phase success. Multi-line hardcoded release notes.
**Detection**: Read the pipeline's output database directly. Compare QA scores across products — identical scores = synthetic.
```sql
SELECT id, name, status, qa_score FROM products;
```
**Fix**: Add a quality gate that only marks delivered when ≥4/6 phases actually succeed. Randomize or remove hardcoded test scores.

## Pattern 7: Interface Drift Between Cross-File Callers
**Symptom**: `TypeError: __init__() got an unexpected keyword argument 'sop'` in pipeline logs.
**Root Cause**: A @dataclass was modified in one file, but not in its consumers.
**Detection**: `grep -rn "IsolationTask("` to find all callers. Then check that each caller's keyword args match the dataclass fields.
**Fix**: Add the missing fields. Verify with a constructor smoke-test:
```python
from multi_agent_engine import IsolationTask
t = IsolationTask(task_id='t', agent_id='a', agent_name='n', sop={'steps':['x']}, tools=['f'])
```

## Pattern 8: Frontend Static Shell (CRITICAL) — 2026-06-10
**Symptom**: HTML_TEMPLATE renders in browser but nothing works — can't drag nodes, can't upload files, can't connect to backend. All backend APIs are real and tested, but the frontend is a static display.

**Root Cause**: Skip-the-frontend fallacy. Agent tells itself "the backend is the real work, the frontend is just a display" and writes a placeholder HTML that looks like a UI but has zero interaction. This is a form of self-deception — treating partial work as complete.

**Detection** (automated check, see audit.py):
- `grep -c 'addEventListener'` = 0 → no event binding
- `grep -c 'draggable'` = 0 AND `grep -c 'mousedown'` = 0 → no drag interaction
- `grep -c 'fetch('` = 0 → no API calls from frontend
- `grep -c 'FileReader'` = 0 AND `grep -c 'type="file"'` = 0 → no file upload

**Fix**: Complete rewrite of HTML_TEMPLATE. Must include at minimum:
1. Drag-and-drop node placement from a sidebar tool palette
2. Node movement on canvas (mousedown + mousemove with position tracking)
3. Connection system: output ports to input ports, rendered as SVG bezier curves
4. File upload support: drag-and-drop files onto canvas nodes + FileReader API
5. fetch() calls to at least one real backend API endpoint (e.g. /canvas/state, /engine/plan)
6. Execute/production button that calls a real engine endpoint
7. Undo/redo history stack
8. Save/load workflow as JSON file

**Prevention gate**: Before reporting "frontend done", run:
```bash
curl localhost:PORT/ | grep -c 'addEventListener'   # must be > 0
curl localhost:PORT/ | grep -c 'draggable'           # must be > 0
curl localhost:PORT/ | grep -c 'fetch('              # must be > 0
```

## Audit Methodology: Layer 4 — Data-Truth Verification
The 3-layer methodology (Surface→Log→Functional) is not enough for pipelines that silently produce bad output. Add Layer 4:

**4. Data-Truth**: Read the system's own database/state. Don't ask "is the system running" — ask "what did the system actually produce?".
- Open SQLite/JSON store and inspect records directly
- Check for hardcoded patterns (identical QA scores, same delivery text across products)
- Verify that cron events actually fired by checking log timestamps, not just crontab listings
- For pipeline systems: read products table, not pipeline status indicator
