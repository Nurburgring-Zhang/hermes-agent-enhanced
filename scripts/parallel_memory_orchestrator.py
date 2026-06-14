#!/usr/bin/env python3
"""转发器 — 功能已迁移到 orchestrator.run_parallel"""
import json

from orchestrator import run_parallel

if __name__ == "__main__":
    result = run_parallel()
    print(json.dumps(result, ensure_ascii=False, indent=2))
