#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.EmergencyCompressor"""
import sys

from compression_engine import EmergencyCompressor

if __name__ == "__main__":
    e = EmergencyCompressor()
    text = sys.argv[2] if len(sys.argv) > 2 else (sys.stdin.read() if not sys.stdin.isatty() else "")
    if text:
        r = e.compress(text)
        print(f"Original: {r['original_tokens']}t → Compressed: {r['compressed_tokens']}t Saved: {r['saved_tokens']}t ({r['saved_percent']}%) Level: {r['level']}")
