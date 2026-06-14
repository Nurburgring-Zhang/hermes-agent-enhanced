#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.LosslessClawCompressor"""
import json
import sys

from compression_engine import LosslessClawCompressor

if __name__ == "__main__":
    c = LosslessClawCompressor()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status": print(json.dumps(c.status(), ensure_ascii=False, indent=2))
    elif cmd == "compress" and len(sys.argv) >= 4:
        print(json.dumps(c.compress(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv)>4 else 1), ensure_ascii=False, indent=2))
    elif cmd == "decompress" and len(sys.argv) >= 3:
        d = c.decompress(sys.argv[2]); print(d[:2000] if d else "None")
    elif cmd == "level1": print(json.dumps(c.level1_compress(), ensure_ascii=False, indent=2))
    elif cmd == "level2": print(json.dumps(c.level2_compress(), ensure_ascii=False, indent=2))
    elif cmd == "level3": print(json.dumps(c.level3_archive(int(sys.argv[2]) if len(sys.argv)>2 else 7), ensure_ascii=False, indent=2))
