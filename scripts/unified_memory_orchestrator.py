#!/usr/bin/env python3
"""转发器 — 功能已迁移到 orchestrator.py"""
import sys

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + (sys.argv[1:] if len(sys.argv) > 1 else ["all"])
    from orchestrator import main
    main()
