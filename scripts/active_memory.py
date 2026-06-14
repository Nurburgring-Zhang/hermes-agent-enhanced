#!/usr/bin/env python3
"""转发器 — 功能已迁移到 memory_engine.ActiveMemory"""
import sys

from memory_engine import auto_evolve

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    result = auto_evolve(dry_run=dry_run)
    print(f"ActiveMemory: {result['changes_count']}次变化")
    if result["changes"]:
        for c in result["changes"]:
            print(f"  {c['keyword']}: {c.get('old_weight','?')}->{c.get('new_weight','?')} ({c.get('reason','')})")
