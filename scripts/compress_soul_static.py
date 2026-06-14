#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.compress_soul"""
import json

from compression_engine import compress_soul

if __name__ == "__main__":
    print(json.dumps(compress_soul(), ensure_ascii=False, indent=2))
