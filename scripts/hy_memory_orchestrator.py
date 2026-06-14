#!/usr/bin/env python3
"""转发器 — 功能已迁移到 orchestrator.hy_memory_*"""
import json
import sys

from orchestrator import hy_memory_all, hy_memory_audit, hy_memory_check, hy_memory_cleanup

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    modes = {"all": hy_memory_all, "check": hy_memory_check, "audit": hy_memory_audit, "cleanup": hy_memory_cleanup}
    if mode in modes:
        result = modes[mode]()
        print(json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result))
    else:
        print(f"未知模式: {mode}")
