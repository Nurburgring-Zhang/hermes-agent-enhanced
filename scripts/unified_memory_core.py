#!/usr/bin/env python3
"""转发器 — 功能已迁移到 memory_engine.UnifiedMemoryEngine"""
import sys

from memory_engine import UnifiedMemoryEngine

if __name__ == "__main__":
    engine = UnifiedMemoryEngine()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        s = engine.status()
        sem = s.get("memory_semantic",{}).get("count",0)
        epi = s.get("memory_episodic",{}).get("count",0)
        wings = s.get("wings",0)
        entities = s.get("entities",0)
        print(f"总语义:{sem} 事件:{epi} 翅膀:{wings} 实体:{entities}")
    elif cmd == "search" and len(sys.argv) > 2:
        results = engine.search(sys.argv[2])
        for r in results:
            method = r.get("method","?")
            content = r.get("content","")[:100]
            print(f"  [{method}] {content}")
    elif cmd == "wakeup":
        print(engine.wakeup())
