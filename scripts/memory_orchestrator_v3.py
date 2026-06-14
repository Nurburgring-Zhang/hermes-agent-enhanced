#!/usr/bin/env python3
"""转发器 — 功能已迁移到 orchestrator.TripleRedundantStore"""
import json
import sys

from orchestrator import TripleRedundantStore

if __name__ == "__main__":
    store = TripleRedundantStore()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "query" and len(sys.argv) > 2: print(json.dumps(store.query(sys.argv[2])))
    elif cmd == "store" and len(sys.argv) > 3: print(json.dumps(store.store(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")))
    elif cmd == "verify": print(json.dumps(store.verify()))
    elif cmd == "health": print(json.dumps(store.health()))
    else: print("状态: MemoryOrchestratorV3 (功能已迁移到 orchestrator.py)")
