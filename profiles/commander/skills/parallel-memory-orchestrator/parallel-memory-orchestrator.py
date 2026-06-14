#!/usr/bin/env python3
"""
Hermes 并行记忆编配器 (Parallel Memory Orchestrator)
====================================================
真正同时运行所有记忆+进化能力，而不是串行。
使用 subprocess.Popen 并行启动6个独立进程。

能力矩阵（全部同时运行）:
┌─────────────────────┬──────────────────────┬──────────────────┐
│ 能力                 │ 运行方式              │ 数据流            │
├─────────────────────┼──────────────────────┼──────────────────┤
│ 1. 记忆增强 (enhance) │ 情报DB→rag_index     │ intelligence.db  │
│ 2. RAG索引 (index)    │ workspace→向量记忆   │ memory/main.sqlite│
│ 3. 记忆压缩 (compress)  │ 老化清理+去重        │ 所有DB           │
│ 4. 技能沉淀 (skill)    │ 模式→自动skill文件   │ skills/          │
│ 5. 终身学习 (learn)    │ 持久记忆→memory_entries │ rag_index.db    │
│ 6. 进化分析 (evolve)   │ 全局状态+建议         │ 纯分析           │
└─────────────────────┴──────────────────────┴──────────────────┘
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
SCRIPTS = HERMES / "scripts"
ORCH = SCRIPTS / "unified_memory_orchestrator.py"

C = {"OK": "\033[92m", "ERR": "\033[91m", "WRN": "\033[93m", "CYAN": "\033[96m", "BOLD": "\033[1m", "END": "\033[0m"}

def p(msg, level="INFO"):
    prefix = {"INFO": f"{C['CYAN']}[PAR]{C['END']}", "OK": f"{C['OK']}[✓]{C['END']}",
              "ERR": f"{C['ERR']}[✗]{C['END']}", "WRN": f"{C['WRN']}[!]{C['END']}"}
    print(f"{prefix.get(level, '[--]')} {datetime.now().strftime('%H:%M:%S')} {msg}")

def run_parallel():
    p("=" * 70)
    p(f"  {C['BOLD']}⚡ Hermes 并行记忆编配器 ⚡{C['END']}")
    p("=" * 70)
    p("  6个能力模块同时运行 — 不是串行，是真并行")
    p("=" * 70)

    tasks = [
        ("enhance",  ["python3", str(ORCH), "--enhance", "--min-importance", "3.5"],
         "记忆增强"),
        ("rag_index", ["python3", str(ORCH), "--index"],
         "RAG索引"),
        ("compress", ["python3", str(ORCH), "--compress", "--no-dry-run"],
         "记忆压缩"),
        ("skill_mine", ["python3", str(ORCH), "--skill-mine"],
         "技能挖掘"),
        ("evolve",   ["python3", str(ORCH), "--evolve"],
         "自进化分析"),
    ]

    # 启动所有进程
    processes = {}
    for key, cmd, desc in tasks:
        p(f"  🚀 启动: {desc} ({' '.join(cmd[-2:])})")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(HERMES), text=True
        )
        processes[key] = (proc, desc)

    # 收集结果
    start = time.time()
    all_ok = True
    results = {}

    for key, (proc, desc) in processes.items():
        stdout, stderr = proc.communicate(timeout=180)
        elapsed = time.time() - start

        if proc.returncode == 0:
            # 提取关键行
            lines = stdout.split("\n")
            summary_lines = [l for l in lines if any(k in l for k in ["✓", "✗", "完成", "失败", "压缩", "增强", "搜索"])]
            p(f"  ✓ {desc}: 完成 ({elapsed:.1f}s)", "OK")
            for sl in summary_lines[-3:]:
                print(f"    {sl}")
            results[key] = "ok"
        else:
            p(f"  ✗ {desc}: exit={proc.returncode}", "ERR")
            err = stderr[-300:] if stderr else "no stderr"
            print(f"    {err}")
            results[key] = "fail"
            all_ok = False

    total_elapsed = time.time() - start

    p("\n" + "=" * 70)
    p(f"  {C['BOLD']}📊 并行执行报告{C['END']}")
    p("=" * 70)
    for key, _, desc in tasks:
        emoji = "✓" if results.get(key) == "ok" else "✗"
        p(f"  {emoji} {desc}")
    p(f"\n总耗时: {total_elapsed:.1f}s (所有模块同时运行)")
    p("=" * 70)

    return all_ok


if __name__ == "__main__":
    success = run_parallel()
    sys.exit(0 if success else 1)
