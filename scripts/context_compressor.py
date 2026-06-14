#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.ContextCompressor"""
import json
import sys

from compression_engine import ContextCompressor

if __name__ == "__main__":
    c = ContextCompressor(); cmd = sys.argv[1] if len(sys.argv)>1 else "help"
    if cmd == "compress" and len(sys.argv)>2:
        print(json.dumps(c.compress_conversation(sys.argv[2])))
    elif cmd == "checkpoint":
        import json as _j
        print(json.dumps(c.store_task_checkpoint(sys.argv[2] if len(sys.argv)>2 else "unknown", sys.argv[3] if len(sys.argv)>3 else "running",
            _j.loads(sys.argv[4]) if len(sys.argv)>4 else [], _j.loads(sys.argv[5]) if len(sys.argv)>5 else [],
            sys.argv[6] if len(sys.argv)>6 else "", sys.argv[7] if len(sys.argv)>7 else "")))
    elif cmd == "snapshot":
        print(json.dumps(c.store_audit_snapshot(sys.argv[2] if len(sys.argv)>2 else "report", sys.argv[3] if len(sys.argv)>3 else "")))
