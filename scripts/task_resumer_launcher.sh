#!/bin/bash
# Hermes 任务断点快速检查 — 输出高度压缩的恢复信息
cd "$HOME/.hermes" && python3 scripts/context_guardian.py check
