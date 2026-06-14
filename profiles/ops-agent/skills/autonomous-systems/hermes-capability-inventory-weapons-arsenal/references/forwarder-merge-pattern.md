# Forwarder Merge Pattern — Script Consolidation Without Breaking Interfaces

## Problem
Hermes accumulates scripts over time. Multiple scripts evolve overlapping functionality (e.g., 9 compression scripts, 7 memory engine scripts). Deleting them breaks cron jobs, other scripts' imports, and CLI muscle memory.

## Solution: Unified Module + Forwarder Pattern
1. Create a new `unified_module.py` containing all functionality merged
2. Keep old scripts as lightweight forwarders: `from unified_module import ...`
3. Old CLI entry points redirect to the unified CLI
4. Everything keeps working: cron, imports, direct execution

## Forwarder Template

### Simple module forwarder
```python
#!/usr/bin/env python3
"""转发器 — 功能已迁移到 unified_module"""
from unified_module import SomeClass, some_function

if __name__ == "__main__":
    # Redirect CLI to unified module
    sys.argv[0] = "unified_module.py"
    from unified_module import main
    main()
```

### CLI forwarder with command mapping
```python
#!/usr/bin/env python3
"""转发器 — 功能已迁移到 unified_module.CommandClass"""
from unified_module import CommandClass
import sys, json

if __name__ == "__main__":
    obj = CommandClass()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(obj.status(), ensure_ascii=False, indent=2))
    elif cmd == "do_something":
        print(obj.do_something(sys.argv[2]))
```

## Verification Checklist
- [ ] `python3 old_script.py` — CLI still works
- [ ] `from old_script import SomeClass` — import still works  
- [ ] cron path unchanged — cron continues to run
- [ ] All old public function signatures preserved (same params, same return types)
- [ ] New unified module passes `py_compile` syntax check
- [ ] Each unified module's CLI entry is tested (`--help` shows all commands)
