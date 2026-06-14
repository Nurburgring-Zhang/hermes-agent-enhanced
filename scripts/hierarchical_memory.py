#!/usr/bin/env python3
"""转发器 — 功能已迁移到 memory_engine.HierarchicalMemory"""
import json

from memory_engine import HierarchicalMemory

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hierarchical Memory Engine")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--store", nargs=2, metavar=("FACT","IMPORTANCE"))
    parser.add_argument("--query", type=str)
    parser.add_argument("--consolidate", action="store_true")
    parser.add_argument("--prune", type=int, default=14)
    args = parser.parse_args()
    engine = HierarchicalMemory()
    if args.stats: print(json.dumps(engine.get_stats(), indent=2))
    if args.store:
        e = engine.create_event(args.store[0], importance=float(args.store[1]))
        engine.store_event(e); print(f"✅ Stored: {e.event_id}")
    if args.prune:
        a = engine.archive_old_events(args.prune)
        p = engine.prune_expired()
        print(f"✅ Archived: {a}, Pruned: {p}")
