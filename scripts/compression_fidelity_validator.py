#!/usr/bin/env python3
"""转发器 — 功能已迁移到 compression_engine.run_fidelity_validation"""
import sys

from compression_engine import run_fidelity_validation

if __name__ == "__main__":
    check = len(sys.argv) > 1 and sys.argv[1] == "check"
    run_fidelity_validation(update_stats=not check)
