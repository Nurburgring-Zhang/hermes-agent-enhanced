#!/usr/bin/env python3
"""
Hermes Stress Tester v1.0
==========================
P3功能 — 并发压力测试工具。

功能:
  1. 并发工具调用模拟 — 多线程/多进程模拟工具调用负载
  2. 错误率统计 — 实时追踪成功/失败/超时比率
  3. 延迟分布 — P50/P90/P95/P99 延迟百分位统计
  4. 吞吐量度量 — QPS (每秒请求数) 实时监控
  5. 自适应负载 — 逐步提升并发直到达到错误率阈值

对标:
  - Apache JMeter / wrk / k6 压力测试理念
  - Datadog / Prometheus 延迟分布监控
  - Locust 自适应负载模式

用法:
  python3 scripts/stress_tester.py --target <endpoint/command> --concurrency 10 --duration 30
  python3 scripts/stress_tester.py --adaptive --max-concurrency 100 --error-threshold 0.05
"""

import json
import logging
import math
import statistics
import subprocess
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HERMES = Path.home() / ".hermes"
STRESS_DIR = HERMES / "stress_results"
STRESS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RequestResult:
    """单次请求结果。

    包含延迟、成功/失败状态、错误信息等。
    """
    success: bool
    latency_sec: float
    error: str | None = None
    output: str | None = None
    timestamp: float = field(default_factory=time.time)
    request_id: int = 0


@dataclass
class StressReport:
    """压力测试完整报告。

    汇总所有统计指标。
    """
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    error_rate: float = 0.0
    throughput_qps: float = 0.0
    latency_min: float = 0.0
    latency_max: float = 0.0
    latency_mean: float = 0.0
    latency_median: float = 0.0
    latency_p50: float = 0.0
    latency_p90: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_stdev: float = 0.0
    duration_sec: float = 0.0
    concurrency: int = 0
    errors_by_type: dict[str, int] = field(default_factory=dict)
    raw_latencies: list[float] = field(default_factory=list)
    timestamp: str = ""


class LatencyStats:
    """延迟统计计算器。

    从延迟样本计算 P50/P90/P95/P99 等百分位，以及均值、标准差。
    """

    @staticmethod
    def percentile(data: list[float], p: float) -> float:
        """计算百分位。

        Args:
            data: 已排序的延迟列表。
            p: 百分位 (0-100)。

        Returns:
            对应百分位的延迟值。
        """
        if not data:
            return 0.0
        k = (len(data) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        d0 = data[int(f)] * (c - k)
        d1 = data[int(c)] * (k - f)
        return d0 + d1

    @staticmethod
    def compute(latencies: list[float]) -> dict[str, float]:
        """从延迟列表计算完整统计。

        Args:
            latencies: 延迟值列表（秒）。

        Returns:
            包含所有统计指标的字典。
        """
        if not latencies:
            return {
                "min": 0, "max": 0, "mean": 0, "median": 0,
                "p50": 0, "p90": 0, "p95": 0, "p99": 0, "stdev": 0,
                "count": 0,
            }

        sorted_lat = sorted(latencies)
        return {
            "min": round(sorted_lat[0], 6),
            "max": round(sorted_lat[-1], 6),
            "mean": round(statistics.mean(latencies), 6),
            "median": round(statistics.median(latencies), 6),
            "p50": round(LatencyStats.percentile(sorted_lat, 50), 6),
            "p90": round(LatencyStats.percentile(sorted_lat, 90), 6),
            "p95": round(LatencyStats.percentile(sorted_lat, 95), 6),
            "p99": round(LatencyStats.percentile(sorted_lat, 99), 6),
            "stdev": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 6),
            "count": len(latencies),
        }


class ConcurrencyController:
    """并发控制器。

    管理线程池，发出请求并收集结果。
    支持固定并发和自适应并发两种模式。
    """

    def __init__(self, max_workers: int = 10):
        """初始化并发控制器。

        Args:
            max_workers: 线程池最大工作线程数。
        """
        self.max_workers = max_workers
        self._executor: ThreadPoolExecutor | None = None
        self._results: list[RequestResult] = []
        self._lock = threading.Lock()
        self._request_counter = 0
        self._start_time: float = 0.0
        self._stop_event = threading.Event()

    def start(self) -> None:
        """启动线程池。"""
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._start_time = time.time()
        logger.info(f"ConcurrencyController started with {self.max_workers} workers")

    def stop(self) -> None:
        """停止线程池。"""
        self._stop_event.set()
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        logger.info("ConcurrencyController stopped")

    def execute_requests(
        self,
        target: Callable[[], tuple[bool, str | None, str | None]],
        duration_sec: float,
        ramp_up_sec: float = 0.0,
    ) -> StressReport:
        """在指定时长内持续发出请求。

        Args:
            target: 目标函数，返回 (success, error_msg, output)。
            duration_sec: 测试总时长。
            ramp_up_sec: 预热时间（逐步增加并发）。

        Returns:
            StressReport 压力测试报告。
        """
        self.start()
        end_time = time.time() + duration_sec
        futures: list[Future] = []
        request_id = 0

        # 预热阶段：逐步增加并发
        ramp_end = time.time() + ramp_up_sec

        while time.time() < end_time and not self._stop_event.is_set():
            # 在预热阶段限制并发增长
            if time.time() < ramp_end and ramp_up_sec > 0:
                elapsed_ramp = ramp_up_sec - (ramp_end - time.time())
                current_max = max(1, int(self.max_workers * (elapsed_ramp / ramp_up_sec)))
            else:
                current_max = self.max_workers

            # 确保池中总是有 current_max 个任务在运行
            active = sum(1 for f in futures if not f.done())
            for _ in range(current_max - active):
                request_id += 1
                future = self._executor.submit(self._run_single, target, request_id)
                futures.append(future)

            # 清理已完成的任务
            futures = [f for f in futures if not f.done()]
            time.sleep(0.01)  # 短暂休眠，避免忙等待

        # 等待剩余任务完成
        for future in futures:
            try:
                future.result(timeout=30)
            except Exception as e:
                logger.exception(f"Future result error: {e}")

        self.stop()
        elapsed = time.time() - self._start_time
        return self._build_report(elapsed)

    def _run_single(
        self,
        target: Callable[[], tuple[bool, str | None, str | None]],
        request_id: int,
    ) -> None:
        """执行单次请求并记录结果。"""
        start = time.perf_counter()
        success = False
        error = None
        output = None
        try:
            success, error, output = target()
        except Exception as e:
            success = False
            error = f"{type(e).__name__}: {e!s}"
            logger.exception(f"Request {request_id} failed: {error}")
        latency = time.perf_counter() - start

        result = RequestResult(
            success=success,
            latency_sec=latency,
            error=error,
            output=output,
            request_id=request_id,
        )
        with self._lock:
            self._results.append(result)

    def _build_report(self, elapsed_sec: float) -> StressReport:
        """从收集的结果构建压力测试报告。"""
        with self._lock:
            results = list(self._results)

        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        error_rate = failed / total if total > 0 else 0.0
        throughput = total / elapsed_sec if elapsed_sec > 0 else 0.0

        latencies = [r.latency_sec for r in results]
        stats = LatencyStats.compute(latencies)

        # 统计错误类型
        errors_by_type: dict[str, int] = defaultdict(int)
        for r in results:
            if r.error:
                error_type = r.error.split(":")[0] if ":" in r.error else r.error
                errors_by_type[error_type] += 1

        return StressReport(
            total_requests=total,
            successful=successful,
            failed=failed,
            error_rate=round(error_rate, 4),
            throughput_qps=round(throughput, 2),
            latency_min=stats["min"],
            latency_max=stats["max"],
            latency_mean=stats["mean"],
            latency_median=stats["median"],
            latency_p50=stats["p50"],
            latency_p90=stats["p90"],
            latency_p95=stats["p95"],
            latency_p99=stats["p99"],
            latency_stdev=stats["stdev"],
            duration_sec=round(elapsed_sec, 2),
            concurrency=self.max_workers,
            errors_by_type=dict(errors_by_type),
            raw_latencies=latencies,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def execute_adaptive(
        self,
        target: Callable[[], tuple[bool, str | None, str | None]],
        max_concurrency: int = 100,
        error_threshold: float = 0.05,
        step_duration: float = 10.0,
        concurrency_step: int = 5,
    ) -> list[StressReport]:
        """自适应压力测试：逐步提升并发直到达到错误率阈值。

        Args:
            target: 目标函数。
            max_concurrency: 最大并发数。
            error_threshold: 错误率阈值（超过此值停止）。
            step_duration: 每步持续时间。
            concurrency_step: 每次增加的并发数。

        Returns:
            每步的 StressReport 列表。
        """
        reports: list[StressReport] = []
        current_concurrency = concurrency_step

        logger.info(
            f"Starting adaptive stress test: max_concurrency={max_concurrency}, "
            f"error_threshold={error_threshold}"
        )

        while current_concurrency <= max_concurrency:
            logger.info(f"Step: concurrency={current_concurrency}")
            self.max_workers = current_concurrency
            self._results.clear()
            self._stop_event.clear()

            report = self.execute_requests(target, duration_sec=step_duration)
            reports.append(report)

            logger.info(
                f"  throughput={report.throughput_qps} qps, "
                f"error_rate={report.error_rate}, p95={report.latency_p95}s"
            )

            if report.error_rate > error_threshold:
                logger.warning(
                    f"Error rate {report.error_rate} exceeds threshold {error_threshold}, stopping"
                )
                break

            current_concurrency += concurrency_step

        return reports


def command_target(command: str, timeout: float = 30.0) -> tuple[bool, str | None, str | None]:
    """将 shell 命令包装为压力测试目标函数。

    Args:
        command: 要执行的 shell 命令。
        timeout: 命令超时时间。

    Returns:
        (success, error_msg, output) 元组。
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, None, result.stdout[:500]
        return False, f"exit_code={result.returncode}: {result.stderr[:200]}", None
    except subprocess.TimeoutExpired:
        return False, "timeout", None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", None


def function_target(func: Callable, *args: Any, **kwargs: Any) -> Callable[[], tuple[bool, str | None, str | None]]:
    """将 Python 函数包装为压力测试目标。

    Args:
        func: 要测试的 Python 函数。
        *args: 位置参数。
        **kwargs: 关键字参数。

    Returns:
        包装后的无参数可调用对象。
    """
    def _wrapper() -> tuple[bool, str | None, str | None]:
        try:
            result = func(*args, **kwargs)
            return True, None, str(result)[:500]
        except Exception as e:
            return False, f"{type(e).__name__}: {e}", None
    return _wrapper


def stress_test_command(
    command: str,
    concurrency: int = 10,
    duration: float = 30.0,
    timeout: float = 30.0,
    ramp_up: float = 0.0,
) -> StressReport:
    """便捷函数：对 shell 命令进行压力测试。

    Args:
        command: shell 命令。
        concurrency: 并发数。
        duration: 测试时长（秒）。
        timeout: 命令超时（秒）。
        ramp_up: 预热时间（秒）。

    Returns:
        StressReport 报告。
    """
    controller = ConcurrencyController(max_workers=concurrency)
    def target():
        return command_target(command, timeout=timeout)
    return controller.execute_requests(target, duration_sec=duration, ramp_up_sec=ramp_up)


def adaptive_stress_command(
    command: str,
    max_concurrency: int = 100,
    error_threshold: float = 0.05,
    step_duration: float = 10.0,
    concurrency_step: int = 5,
    timeout: float = 30.0,
) -> list[StressReport]:
    """便捷函数：对 shell 命令进行自适应压力测试。

    Args:
        command: shell 命令。
        max_concurrency: 最大并发数。
        error_threshold: 错误率阈值。
        step_duration: 每步时长。
        concurrency_step: 并发步进。
        timeout: 命令超时。

    Returns:
        每步的 StressReport 列表。
    """
    controller = ConcurrencyController()
    def target():
        return command_target(command, timeout=timeout)
    return controller.execute_adaptive(
        target,
        max_concurrency=max_concurrency,
        error_threshold=error_threshold,
        step_duration=step_duration,
        concurrency_step=concurrency_step,
    )


def save_report(report: StressReport, filepath: Path | None = None) -> Path:
    """保存压力测试报告为 JSON 文件。

    Args:
        report: 压力测试报告。
        filepath: 输出文件路径（可选，默认自动生成）。

    Returns:
        保存的 JSON 文件路径。
    """
    if filepath is None:
        filepath = STRESS_DIR / f"stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    data = {
        "total_requests": report.total_requests,
        "successful": report.successful,
        "failed": report.failed,
        "error_rate": report.error_rate,
        "throughput_qps": report.throughput_qps,
        "latency": {
            "min": report.latency_min,
            "max": report.latency_max,
            "mean": report.latency_mean,
            "median": report.latency_median,
            "p50": report.latency_p50,
            "p90": report.latency_p90,
            "p95": report.latency_p95,
            "p99": report.latency_p99,
            "stdev": report.latency_stdev,
        },
        "duration_sec": report.duration_sec,
        "concurrency": report.concurrency,
        "errors_by_type": report.errors_by_type,
        "timestamp": report.timestamp,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Stress report saved to {filepath}")
    return filepath


def format_report_markdown(report: StressReport) -> str:
    """将压力测试报告格式化为 Markdown。

    Args:
        report: 压力测试报告。

    Returns:
        Markdown 格式文本。
    """
    lines = [
        "# Hermes Stress Test Report",
        f"Generated: {report.timestamp}",
        "",
        "## Summary",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Requests | {report.total_requests} |",
        f"| Successful | {report.successful} |",
        f"| Failed | {report.failed} |",
        f"| Error Rate | {report.error_rate:.2%} |",
        f"| Throughput | {report.throughput_qps:.2f} qps |",
        f"| Duration | {report.duration_sec}s |",
        f"| Concurrency | {report.concurrency} |",
        "",
        "## Latency Distribution",
        "| Percentile | Latency (s) |",
        "|------------|-------------|",
        f"| Min | {report.latency_min:.6f} |",
        f"| Mean | {report.latency_mean:.6f} |",
        f"| P50 | {report.latency_p50:.6f} |",
        f"| P90 | {report.latency_p90:.6f} |",
        f"| P95 | {report.latency_p95:.6f} |",
        f"| P99 | {report.latency_p99:.6f} |",
        f"| Max | {report.latency_max:.6f} |",
        f"| Stdev | {report.latency_stdev:.6f} |",
    ]

    if report.errors_by_type:
        lines.append("")
        lines.append("## Errors by Type")
        for error_type, count in sorted(report.errors_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {error_type}: {count}")

    return "\n".join(lines)


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Hermes Stress Tester — concurrent load / latency / error tracking"
    )

    parser.add_argument("--command", "-c", help="Shell command to stress test")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--duration", type=float, default=30.0, help="Test duration in seconds")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout")
    parser.add_argument("--ramp-up", type=float, default=0.0, help="Ramp-up time in seconds")
    parser.add_argument("--adaptive", action="store_true", help="Run adaptive stress test")
    parser.add_argument("--max-concurrency", type=int, default=100, help="Max concurrency for adaptive mode")
    parser.add_argument("--error-threshold", type=float, default=0.05, help="Error rate threshold for adaptive mode")
    parser.add_argument("--step-duration", type=float, default=10.0, help="Step duration for adaptive mode")
    parser.add_argument("--concurrency-step", type=int, default=5, help="Concurrency step size")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--markdown", action="store_true", help="Output as Markdown")

    args = parser.parse_args()

    if not args.command:
        sys.exit(1)

    if args.adaptive:
        reports = adaptive_stress_command(
            args.command,
            max_concurrency=args.max_concurrency,
            error_threshold=args.error_threshold,
            step_duration=args.step_duration,
            concurrency_step=args.concurrency_step,
            timeout=args.timeout,
        )
        data = [
            {
                "step": i + 1,
                "concurrency": r.concurrency,
                "throughput_qps": r.throughput_qps,
                "error_rate": r.error_rate,
                "latency_p95": r.latency_p95,
            }
            for i, r in enumerate(reports)
        ]
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        report = stress_test_command(
            args.command,
            concurrency=args.concurrency,
            duration=args.duration,
            timeout=args.timeout,
            ramp_up=args.ramp_up,
        )

        if args.markdown:
            pass
        else:
            data = {
                "total_requests": report.total_requests,
                "successful": report.successful,
                "failed": report.failed,
                "error_rate": report.error_rate,
                "throughput_qps": report.throughput_qps,
                "latency_p50": report.latency_p50,
                "latency_p90": report.latency_p90,
                "latency_p95": report.latency_p95,
                "latency_p99": report.latency_p99,
                "duration_sec": report.duration_sec,
                "concurrency": report.concurrency,
            }

        if args.output:
            save_report(report, Path(args.output))
