#!/usr/bin/env python3
"""转发器 — 功能已迁移到 memory_tools.py stats"""
import sys

from memory_tools import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "stats"] + sys.argv[1:]
    main()
