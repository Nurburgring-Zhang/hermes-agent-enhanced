#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.archive_old_intelligence"""
import json
import sys

from compression_engine import archive_old_intelligence

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv or "--dry_run" in sys.argv
    exec_flag = "--execute" in sys.argv
    result = archive_old_intelligence(days=7, dry_run=dry and not exec_flag)
    print(json.dumps(result, ensure_ascii=False, indent=2))
