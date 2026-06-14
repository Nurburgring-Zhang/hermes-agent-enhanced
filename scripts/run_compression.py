#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.archive_old_intelligence"""
import json

from compression_engine import archive_old_intelligence

if __name__ == "__main__":
    result = archive_old_intelligence(days=7)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("TASK_DONE")
