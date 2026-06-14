#!/usr/bin/env python3
"""转发器 — 功能已迁移到 orchestrator.run_integrated_cycle"""
import json

from orchestrator import run_integrated_cycle

if __name__ == "__main__":
    result = run_integrated_cycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))
