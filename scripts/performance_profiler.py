#!/usr/bin/env python3
"""
Hermes Performance Profiler v1.0
=================================
P3功能 — 代码性能分析工具。

功能:
  1. cProfile 集成 — 对目标函数/模块运行性能分析
  2. 慢函数检测 — 自动检测耗时超过阈值的函数，输出调用链
  3. 内存分析 — 使用 tracemalloc 追踪内存分配热点
  4. 生成性能报告 — JSON/Markdown 格式的性能概要

对标:
  - Python cProfile + pstats 标准工具链
  - py-spy / scalene 商业级性能分析理念
  - Datadog APM 慢端点检测

用法:
  python3 scripts/performance_profiler.py profile <target.py> [--top 20] [--threshold 0.1]
  python3 scripts/performance_profiler.py memory <target.py> [--top 10]
  python3 scripts/performance_profiler.py benchmark <expr> [--repeat 100]
"""

import cProfile
import io
import json
import logging
import pstats
import time
import tracemalloc
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HERMES = Path.home() / ".hermes"
PROFILE_DIR = HERMES / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


class PerformanceProfiler:
    """cProfile 集成性能分析器。

    包装 cProfile/pstats，提供慢函数检测和调用链分析。
    """

    def __init__(self, threshold_sec: float = 0.1, top_n: int = 20):
        """初始化性能分析器。

        Args:
            threshold_sec: 慢函数检测阈值（秒），超过此值的函数被标记为慢函数。
            top_n: 报告中最慢函数的数量。
        """
        self.threshold_sec = threshold_sec
        self.top_n = top_n
        self._profiler = cProfile.Profile()
        self._stats: pstats.Stats | None = None

    def enable(self) -> None:
        """开始性能分析。"""
        self._profiler.enable()
        logger.info("Performance profiler enabled")

    def disable(self) -> None:
        """停止性能分析。"""
        self._profiler.disable()
        logger.info("Performance profiler disabled")

    def profile_function(self, func: Callable, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """对单个函数运行性能分析。

        Args:
            func: 目标函数。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            性能分析结果字典，包含 slow_functions、total_time、call_count 等。
        """
        self._profiler.enable()
        start = time.perf_counter()
        result = None
        error = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            error = str(e)
        elapsed = time.perf_counter() - start
        self._profiler.disable()

        stats = pstats.Stats(self._profiler)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)

        # 捕获 stats 输出
        out = io.StringIO()
        stats.stream = out
        stats.print_stats(self.top_n)
        stats_output = out.getvalue()

        slow_funcs = self._extract_slow_functions(stats)

        return {
            "total_time_sec": round(elapsed, 4),
            "slow_functions": slow_funcs,
            "top_n_stats": stats_output,
            "error": error,
            "result": repr(result) if result is not None else None,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def profile_module(self, module_path: str) -> dict[str, Any]:
        """对 Python 模块运行性能分析。

        Args:
            module_path: Python 文件路径。

        Returns:
            性能分析结果字典。
        """
        self._profiler.enable()
        start = time.perf_counter()
        error = None
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_profile_target", module_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            error = str(e)
            logger.exception(f"Failed to profile module {module_path}: {e}")
        elapsed = time.perf_counter() - start
        self._profiler.disable()

        stats = pstats.Stats(self._profiler)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)

        out = io.StringIO()
        stats.stream = out
        stats.print_stats(self.top_n)
        stats_output = out.getvalue()

        slow_funcs = self._extract_slow_functions(stats)

        return {
            "module": module_path,
            "total_time_sec": round(elapsed, 4),
            "slow_functions": slow_funcs,
            "top_n_stats": stats_output,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _extract_slow_functions(self, stats: pstats.Stats) -> list[dict[str, Any]]:
        """从 pstats 提取超过阈值的慢函数列表。

        Args:
            stats: pstats.Stats 对象。

        Returns:
            慢函数详情列表，按累计时间降序排列。
        """
        slow = []
        for func_info, stat_info in stats.stats.items():
            cc, nc, tt, ct, _callers = stat_info
            if tt >= self.threshold_sec:
                filename, lineno, func_name = func_info
                slow.append({
                    "function": func_name,
                    "file": filename,
                    "line": lineno,
                    "total_time_sec": round(tt, 4),
                    "cumulative_time_sec": round(ct, 4),
                    "call_count": cc,
                    "primitive_calls": nc,
                })
        slow.sort(key=lambda x: x["cumulative_time_sec"], reverse=True)
        return slow[:self.top_n]

    def benchmark(self, expr: str, repeat: int = 100) -> dict[str, Any]:
        """对单行表达式运行微基准测试。

        Args:
            expr: Python 表达式（如 'sum(range(1000))'）。
            repeat: 重复次数。

        Returns:
            基准测试结果字典，包含均值、中位数、标准差等。
        """
        import statistics

        times: list[float] = []
        compiled = compile(expr, "<benchmark>", "eval")
        namespace: dict[str, Any] = {}

        for _ in range(repeat):
            start = time.perf_counter()
            try:
                eval(compiled, namespace)
            except Exception as e:
                logger.exception(f"Benchmark expression failed: {e}")
                return {"error": str(e), "expression": expr}
            times.append(time.perf_counter() - start)

        times.sort()
        return {
            "expression": expr,
            "repeat": repeat,
            "mean_sec": round(statistics.mean(times), 6),
            "median_sec": round(statistics.median(times), 6),
            "min_sec": round(times[0], 6),
            "max_sec": round(times[-1], 6),
            "stdev_sec": round(statistics.stdev(times) if len(times) > 1 else 0, 6),
            "total_sec": round(sum(times), 4),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def save_report(self, report: dict[str, Any], name: str = "profile") -> Path:
        """保存性能报告为 JSON 文件。

        Args:
            report: 性能报告字典。
            name: 报告名称（不含扩展名）。

        Returns:
            保存的 JSON 文件路径。
        """
        report_path = PROFILE_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Performance report saved to {report_path}")
        return report_path


class MemoryProfiler:
    """使用 tracemalloc 进行内存分析。

    追踪 Python 内存分配热点，识别内存泄漏和过量分配。
    对标: scalene / memory_profiler 商业级方案。
    """

    def __init__(self, top_n: int = 10):
        """初始化内存分析器。

        Args:
            top_n: 报告中内存分配最多的条目数。
        """
        self.top_n = top_n
        self._snapshot_before: tracemalloc.Snapshot | None = None
        self._snapshot_after: tracemalloc.Snapshot | None = None

    def enable(self) -> None:
        """启用内存追踪。"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        tracemalloc.start()
        logger.info("Memory profiler enabled (tracemalloc)")

    def disable(self) -> None:
        """禁用内存追踪。"""
        tracemalloc.stop()
        logger.info("Memory profiler disabled")

    def snapshot(self, label: str = "before") -> None:
        """记录内存快照。

        Args:
            label: 快照标签（'before' 或 'after'）。
        """
        if label == "before":
            self._snapshot_before = tracemalloc.take_snapshot()
        else:
            self._snapshot_after = tracemalloc.take_snapshot()

    def profile_function(self, func: Callable, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """对函数执行内存分析。

        Args:
            func: 目标函数。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            内存分析结果字典，包含内存增长、Top-N 分配等。
        """
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        tracemalloc.start()

        self.snapshot("before")
        result = None
        error = None
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            error = str(e)
            logger.exception(f"Memory profile function error: {e}")
        self.snapshot("after")

        tracemalloc.stop()

        # 计算差异
        if self._snapshot_before and self._snapshot_after:
            top_stats = self._snapshot_after.compare_to(
                self._snapshot_before, "lineno"
            )
            self._snapshot_after.compare_to(self._snapshot_before, "filename")
        else:
            top_stats = []

        top_allocations = []
        for stat in top_stats[:self.top_n]:
            frame = stat.traceback[0] if stat.traceback else None
            top_allocations.append({
                "file": frame.filename if frame else "unknown",
                "line": frame.lineno if frame else 0,
                "size_diff_bytes": stat.size_diff,
                "count_diff": stat.count_diff,
            })

        return {
            "top_allocations": top_allocations,
            "error": error,
            "result": repr(result) if result is not None else None,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def get_current_stats(self) -> dict[str, Any]:
        """获取当前内存使用统计。

        Returns:
            当前内存统计，包括当前/峰值内存。
        """
        if not tracemalloc.is_tracing():
            return {"error": "tracemalloc is not tracing"}

        current, peak = tracemalloc.get_traced_memory()
        return {
            "current_bytes": current,
            "current_mb": round(current / (1024 * 1024), 2),
            "peak_bytes": peak,
            "peak_mb": round(peak / (1024 * 1024), 2),
            "timestamp": datetime.now(UTC).isoformat(),
        }


def generate_summary_report(profile_results: list[dict[str, Any]]) -> str:
    """生成 Markdown 格式的性能总结报告。

    Args:
        profile_results: 多次性能分析的结果列表。

    Returns:
        Markdown 格式的总结文本。
    """
    lines = [
        "# Hermes Performance Summary",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Total profiles: {len(profile_results)}",
        "",
    ]

    # 汇总慢函数
    all_slow: dict[str, dict[str, Any]] = {}
    for result in profile_results:
        for func in result.get("slow_functions", []):
            key = f"{func['file']}:{func['function']}"
            if key not in all_slow:
                all_slow[key] = {
                    "function": func["function"],
                    "file": func["file"],
                    "occurrences": 0,
                    "max_time": 0.0,
                    "total_time": 0.0,
                }
            all_slow[key]["occurrences"] += 1
            all_slow[key]["max_time"] = max(all_slow[key]["max_time"], func["total_time_sec"])
            all_slow[key]["total_time"] += func["total_time_sec"]

    if all_slow:
        lines.append("## Slow Functions (> threshold)")
        lines.append("| Function | File | Occurrences | Max Time | Total Time |")
        lines.append("|----------|------|-------------|----------|------------|")
        for key, info in sorted(all_slow.items(), key=lambda x: -x[1]["total_time"]):
            lines.append(
                f"| {info['function']} | {info['file']} | {info['occurrences']} | "
                f"{info['max_time']:.4f}s | {info['total_time']:.4f}s |"
            )

    return "\n".join(lines)


def profile_file(filepath: str, threshold: float = 0.1, top: int = 20) -> dict[str, Any]:
    """便捷函数：对给定 Python 文件进行性能分析。

    Args:
        filepath: Python 文件路径。
        threshold: 慢函数阈值（秒）。
        top: 显示的最慢函数数量。

    Returns:
        性能分析结果字典。
    """
    profiler = PerformanceProfiler(threshold_sec=threshold, top_n=top)
    return profiler.profile_module(filepath)


def profile_memory(filepath: str, top: int = 10) -> dict[str, Any]:
    """便捷函数：对给定 Python 文件进行内存分析。

    Args:
        filepath: Python 文件路径。
        top: 显示的最多内存分配条目。

    Returns:
        内存分析结果字典。
    """
    mem = MemoryProfiler(top_n=top)

    def _run_module() -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_mem_target", filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    return mem.profile_function(_run_module)


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Hermes Performance Profiler — cProfile + Memory Analysis"
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # profile 子命令
    p = subparsers.add_parser("profile", help="Profile a Python file")
    p.add_argument("target", help="Python file to profile")
    p.add_argument("--threshold", type=float, default=0.1, help="Slow function threshold in seconds")
    p.add_argument("--top", type=int, default=20, help="Number of top functions to show")

    # memory 子命令
    m = subparsers.add_parser("memory", help="Memory profile a Python file")
    m.add_argument("target", help="Python file to profile")
    m.add_argument("--top", type=int, default=10, help="Number of top allocations to show")

    # benchmark 子命令
    b = subparsers.add_parser("benchmark", help="Micro-benchmark an expression")
    b.add_argument("expression", help="Python expression to benchmark")
    b.add_argument("--repeat", type=int, default=100, help="Number of repetitions")

    args = parser.parse_args()

    if args.command == "profile":
        result = profile_file(args.target, threshold=args.threshold, top=args.top)
    elif args.command == "memory":
        result = profile_memory(args.target, top=args.top)
    elif args.command == "benchmark":
        pr = PerformanceProfiler()
        result = pr.benchmark(args.expression, repeat=args.repeat)
    else:
        parser.print_help()
