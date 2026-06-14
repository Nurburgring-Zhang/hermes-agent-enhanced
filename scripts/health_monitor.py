#!/usr/bin/env python3
"""
Hermes Health Monitor v1.0
===========================
P3功能 — 系统健康监控。

功能:
  1. CPU 使用率监控 — 整体/每核心使用率
  2. 内存监控 — 总量/已用/可用/使用率百分比
  3. 磁盘监控 — 挂载点/总量/已用/可用/使用率
  4. 进程监控 — Hermes 相关进程状态
  5. Prometheus 格式指标输出 — 标准 OpenMetrics 格式，可被 Prometheus 抓取
  6. 阈值告警 — 资源使用超过阈值自动告警

对标:
  - Prometheus Node Exporter 指标格式
  - Grafana Agent 健康检查
  - Datadog Agent 系统监控

用法:
  python3 scripts/health_monitor.py              # 健康检查 + 输出JSON
  python3 scripts/health_monitor.py --prometheus  # Prometheus 格式输出
  python3 scripts/health_monitor.py --watch 30    # 持续监控（每30秒）
  python3 scripts/health_monitor.py --alert       # 仅检查告警阈值
"""

import json
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HERMES = Path.home() / ".hermes"
HEALTH_LOG_DIR = HERMES / "health_logs"
HEALTH_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 默认告警阈值
DEFAULT_THRESHOLDS = {
    "cpu_percent": 90.0,
    "memory_percent": 85.0,
    "disk_percent": 90.0,
    "process_count_min": 1,
}


@dataclass
class CPUStats:
    """CPU 统计信息。"""
    percent: float = 0.0
    count: int = 0
    per_cpu: list[float] = field(default_factory=list)
    load_avg_1min: float = 0.0
    load_avg_5min: float = 0.0
    load_avg_15min: float = 0.0


@dataclass
class MemoryStats:
    """内存统计信息。"""
    total_bytes: int = 0
    available_bytes: int = 0
    used_bytes: int = 0
    percent: float = 0.0
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0
    swap_percent: float = 0.0


@dataclass
class DiskStats:
    """单个磁盘挂载点统计。"""
    mount_point: str = ""
    device: str = ""
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    percent: float = 0.0


@dataclass
class ProcessStats:
    """进程统计信息。"""
    pid: int = 0
    name: str = ""
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    memory_percent: float = 0.0
    status: str = ""
    create_time: float = 0.0


class SystemHealthCollector:
    """系统健康指标采集器。

    采集 CPU、内存、磁盘、进程等系统指标。
    对标 Prometheus Node Exporter。
    """

    def collect_cpu(self) -> CPUStats:
        """采集 CPU 统计信息。

        Returns:
            CPUStats 对象。
        """
        try:
            import psutil
        except ImportError:
            logger.exception("psutil is required for CPU monitoring")
            return CPUStats()

        percent = psutil.cpu_percent(interval=0.5)
        count = psutil.cpu_count(logical=True)
        per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)

        try:
            load_avg = os.getloadavg()
            load_1, load_5, load_15 = load_avg[0], load_avg[1], load_avg[2]
        except (OSError, AttributeError):
            load_1, load_5, load_15 = 0.0, 0.0, 0.0

        return CPUStats(
            percent=round(percent, 1),
            count=count or 0,
            per_cpu=[round(p, 1) for p in per_cpu],
            load_avg_1min=round(load_1, 2),
            load_avg_5min=round(load_5, 2),
            load_avg_15min=round(load_15, 2),
        )

    def collect_memory(self) -> MemoryStats:
        """采集内存统计信息。

        Returns:
            MemoryStats 对象。
        """
        try:
            import psutil
        except ImportError:
            logger.exception("psutil is required for memory monitoring")
            return MemoryStats()

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return MemoryStats(
            total_bytes=mem.total,
            available_bytes=mem.available,
            used_bytes=mem.used,
            percent=round(mem.percent, 1),
            swap_total_bytes=swap.total,
            swap_used_bytes=swap.used,
            swap_percent=round(swap.percent, 1),
        )

    def collect_disks(self, min_percent: float = 0.0) -> list[DiskStats]:
        """采集磁盘统计信息。

        Args:
            min_percent: 最小使用率过滤，只返回使用率超过此值的挂载点。

        Returns:
            DiskStats 列表。
        """
        try:
            import psutil
        except ImportError:
            logger.exception("psutil is required for disk monitoring")
            return []

        disks = []
        for partition in psutil.disk_partitions(all=False):
            # 跳过只读文件系统和特殊文件系统
            if "ro" in partition.opts.split(",") and "rw" not in partition.opts.split(","):
                continue
            try:
                usage = shutil.disk_usage(partition.mountpoint)
                percent = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0.0
                if percent >= min_percent:
                    disks.append(DiskStats(
                        mount_point=partition.mountpoint,
                        device=partition.device,
                        total_bytes=usage.total,
                        used_bytes=usage.used,
                        free_bytes=usage.free,
                        percent=percent,
                    ))
            except (PermissionError, OSError):
                continue

        return disks

    def collect_hermes_processes(self) -> list[ProcessStats]:
        """采集 Hermes 相关进程信息。

        Returns:
            与 Hermes 相关的 ProcessStats 列表。
        """
        try:
            import psutil
        except ImportError:
            logger.exception("psutil is required for process monitoring")
            return []

        hermes_keywords = ["hermes", "python", "node", "cron"]
        processes = []

        for proc in psutil.process_iter(["pid", "name", "cmdline", "status", "create_time"]):
            try:
                info = proc.info
                cmdline = " ".join(info.get("cmdline") or [])
                name = (info.get("name") or "").lower()

                # 过滤 Hermes 相关进程
                is_hermes = any(kw in cmdline.lower() for kw in hermes_keywords) or \
                    any(kw in name for kw in hermes_keywords)

                # 排除自身
                if proc.pid == os.getpid():
                    is_hermes = False

                if is_hermes:
                    with proc.oneshot():
                        processes.append(ProcessStats(
                            pid=proc.pid,
                            name=info.get("name", "unknown"),
                            cpu_percent=round(proc.cpu_percent(), 1),
                            memory_bytes=proc.memory_info().rss if proc.memory_info() else 0,
                            memory_percent=round(proc.memory_percent(), 1),
                            status=info.get("status", "?"),
                            create_time=info.get("create_time", 0.0),
                        ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes

    def collect_all(self) -> dict[str, Any]:
        """采集所有系统健康指标。

        Returns:
            包含所有指标的字典。
        """
        cpu = self.collect_cpu()
        memory = self.collect_memory()
        disks = self.collect_disks()
        processes = self.collect_hermes_processes()

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "timestamp_unix": time.time(),
            "cpu": {
                "percent": cpu.percent,
                "count": cpu.count,
                "per_cpu": cpu.per_cpu,
                "load_avg": {
                    "1min": cpu.load_avg_1min,
                    "5min": cpu.load_avg_5min,
                    "15min": cpu.load_avg_15min,
                },
            },
            "memory": {
                "total_bytes": memory.total_bytes,
                "available_bytes": memory.available_bytes,
                "used_bytes": memory.used_bytes,
                "percent": memory.percent,
                "swap": {
                    "total_bytes": memory.swap_total_bytes,
                    "used_bytes": memory.swap_used_bytes,
                    "percent": memory.swap_percent,
                },
            },
            "disk": [
                {
                    "mount_point": d.mount_point,
                    "device": d.device,
                    "total_bytes": d.total_bytes,
                    "used_bytes": d.used_bytes,
                    "free_bytes": d.free_bytes,
                    "percent": d.percent,
                }
                for d in disks
            ],
            "processes": [
                {
                    "pid": p.pid,
                    "name": p.name,
                    "cpu_percent": p.cpu_percent,
                    "memory_bytes": p.memory_bytes,
                    "memory_percent": p.memory_percent,
                    "status": p.status,
                }
                for p in processes
            ],
        }


class PrometheusFormatter:
    """Prometheus 格式指标输出器。

    将 SystemHealthCollector 采集的指标转换为 Prometheus 标准 OpenMetrics 格式。
    对标: prometheus_client Python 库的输出格式。
    """

    # HELP/TYPE 元信息
    METRICS_META = {
        "hermes_cpu_usage_percent": ("gauge", "Overall CPU usage percentage"),
        "hermes_cpu_core_percent": ("gauge", "Per-core CPU usage percentage"),
        "hermes_cpu_load_avg": ("gauge", "System load average"),
        "hermes_memory_total_bytes": ("gauge", "Total physical memory in bytes"),
        "hermes_memory_used_bytes": ("gauge", "Used physical memory in bytes"),
        "hermes_memory_available_bytes": ("gauge", "Available physical memory in bytes"),
        "hermes_memory_usage_percent": ("gauge", "Memory usage percentage"),
        "hermes_swap_total_bytes": ("gauge", "Total swap memory in bytes"),
        "hermes_swap_used_bytes": ("gauge", "Used swap memory in bytes"),
        "hermes_swap_usage_percent": ("gauge", "Swap usage percentage"),
        "hermes_disk_total_bytes": ("gauge", "Total disk space in bytes"),
        "hermes_disk_used_bytes": ("gauge", "Used disk space in bytes"),
        "hermes_disk_free_bytes": ("gauge", "Free disk space in bytes"),
        "hermes_disk_usage_percent": ("gauge", "Disk usage percentage"),
        "hermes_process_cpu_percent": ("gauge", "Process CPU usage percentage"),
        "hermes_process_memory_bytes": ("gauge", "Process memory RSS in bytes"),
        "hermes_process_memory_percent": ("gauge", "Process memory usage percentage"),
        "hermes_health_alerts_total": ("counter", "Total health alerts triggered"),
    }

    @staticmethod
    def format(data: dict[str, Any]) -> str:
        """将系统健康数据格式化为 Prometheus 文本格式。

        Args:
            data: SystemHealthCollector.collect_all() 的输出。

        Returns:
            Prometheus 标准文本格式字符串。
        """
        lines = []
        ts_ms = int(data.get("timestamp_unix", time.time()) * 1000)

        # 输出 HELP/TYPE 元信息（仅首次需要的指标）
        emitted_metrics = set()

        def emit_metric(name: str, value: float, labels: dict[str, str] | None = None) -> str:
            """生成单行 Prometheus 指标。"""
            if name not in emitted_metrics and name in PrometheusFormatter.METRICS_META:
                mtype, help_text = PrometheusFormatter.METRICS_META[name]
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} {mtype}")
                emitted_metrics.add(name)

            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                metric_line = f"{name}{{{label_str}}} {value} {ts_ms}"
            else:
                metric_line = f"{name} {value} {ts_ms}"
            return metric_line

        # CPU 指标
        cpu = data.get("cpu", {})
        lines.append(emit_metric("hermes_cpu_usage_percent", cpu.get("percent", 0.0)))
        for i, pct in enumerate(cpu.get("per_cpu", [])):
            lines.append(emit_metric("hermes_cpu_core_percent", pct, {"core": str(i)}))

        load_avg = cpu.get("load_avg", {})
        for period, key in [("1m", "1min"), ("5m", "5min"), ("15m", "15min")]:
            lines.append(emit_metric("hermes_cpu_load_avg", load_avg.get(key, 0.0), {"period": period}))

        # 内存指标
        memory = data.get("memory", {})
        lines.append(emit_metric("hermes_memory_total_bytes", memory.get("total_bytes", 0)))
        lines.append(emit_metric("hermes_memory_used_bytes", memory.get("used_bytes", 0)))
        lines.append(emit_metric("hermes_memory_available_bytes", memory.get("available_bytes", 0)))
        lines.append(emit_metric("hermes_memory_usage_percent", memory.get("percent", 0.0)))

        swap = memory.get("swap", {})
        lines.append(emit_metric("hermes_swap_total_bytes", swap.get("total_bytes", 0)))
        lines.append(emit_metric("hermes_swap_used_bytes", swap.get("used_bytes", 0)))
        lines.append(emit_metric("hermes_swap_usage_percent", swap.get("percent", 0.0)))

        # 磁盘指标
        for disk in data.get("disk", []):
            mount = disk.get("mount_point", "/")
            lines.append(emit_metric("hermes_disk_total_bytes", disk.get("total_bytes", 0), {"mountpoint": mount}))
            lines.append(emit_metric("hermes_disk_used_bytes", disk.get("used_bytes", 0), {"mountpoint": mount}))
            lines.append(emit_metric("hermes_disk_free_bytes", disk.get("free_bytes", 0), {"mountpoint": mount}))
            lines.append(emit_metric("hermes_disk_usage_percent", disk.get("percent", 0.0), {"mountpoint": mount}))

        # 进程指标
        for proc in data.get("processes", []):
            labels = {"pid": str(proc.get("pid", 0)), "name": proc.get("name", "unknown")}
            lines.append(emit_metric("hermes_process_cpu_percent", proc.get("cpu_percent", 0.0), labels))
            lines.append(emit_metric("hermes_process_memory_bytes", proc.get("memory_bytes", 0), labels))
            lines.append(emit_metric("hermes_process_memory_percent", proc.get("memory_percent", 0.0), labels))

        lines.append("# EOF")
        return "\n".join(lines)


class AlertChecker:
    """健康告警检查器。

    检查各指标是否超过阈值，生成告警列表。
    """

    def __init__(self, thresholds: dict[str, float] | None = None):
        """初始化告警检查器。

        Args:
            thresholds: 自定义阈值字典，覆盖默认值。
        """
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    def check(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """检查系统健康数据是否触发告警。

        Args:
            data: SystemHealthCollector.collect_all() 的输出。

        Returns:
            告警列表，每个告警包含 severity/message/value/threshold/timestamp。
        """
        alerts = []
        now = datetime.now(UTC).isoformat()

        # CPU 告警
        cpu = data.get("cpu", {})
        cpu_pct = cpu.get("percent", 0.0)
        if cpu_pct > self.thresholds["cpu_percent"]:
            alerts.append({
                "severity": "critical",
                "resource": "cpu",
                "message": f"CPU usage {cpu_pct}% exceeds threshold {self.thresholds['cpu_percent']}%",
                "value": cpu_pct,
                "threshold": self.thresholds["cpu_percent"],
                "timestamp": now,
            })

        # 内存告警
        memory = data.get("memory", {})
        mem_pct = memory.get("percent", 0.0)
        if mem_pct > self.thresholds["memory_percent"]:
            alerts.append({
                "severity": "critical",
                "resource": "memory",
                "message": f"Memory usage {mem_pct}% exceeds threshold {self.thresholds['memory_percent']}%",
                "value": mem_pct,
                "threshold": self.thresholds["memory_percent"],
                "timestamp": now,
            })

        # 磁盘告警
        for disk in data.get("disk", []):
            disk_pct = disk.get("percent", 0.0)
            if disk_pct > self.thresholds["disk_percent"]:
                alerts.append({
                    "severity": "warning",
                    "resource": "disk",
                    "mount_point": disk.get("mount_point"),
                    "message": f"Disk {disk.get('mount_point')} usage {disk_pct}% exceeds threshold {self.thresholds['disk_percent']}%",
                    "value": disk_pct,
                    "threshold": self.thresholds["disk_percent"],
                    "timestamp": now,
                })

        # 进程告警
        processes = data.get("processes", [])
        if len(processes) < self.thresholds.get("process_count_min", 1):
            alerts.append({
                "severity": "warning",
                "resource": "process",
                "message": f"Hermes processes count {len(processes)} below minimum {self.thresholds['process_count_min']}",
                "value": len(processes),
                "threshold": self.thresholds["process_count_min"],
                "timestamp": now,
            })

        return alerts


def collect_health() -> dict[str, Any]:
    """便捷函数：采集系统健康指标。

    Returns:
        完整的系统健康数据字典。
    """
    collector = SystemHealthCollector()
    return collector.collect_all()


def format_prometheus(data: dict[str, Any]) -> str:
    """便捷函数：格式化为 Prometheus 格式。

    Args:
        data: 系统健康数据。

    Returns:
        Prometheus 文本格式字符串。
    """
    return PrometheusFormatter.format(data)


def check_alerts(
    data: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """便捷函数：检查健康告警。

    Args:
        data: 系统健康数据。
        thresholds: 自定义阈值。

    Returns:
        告警列表。
    """
    checker = AlertChecker(thresholds)
    return checker.check(data)


def watch_health(interval_sec: float = 30.0, duration_sec: float = 0.0) -> None:
    """持续监控系统健康（打印到 stdout/日志）。

    Args:
        interval_sec: 采集间隔（秒）。
        duration_sec: 监控时长（0 = 无限）。
    """
    collector = SystemHealthCollector()
    checker = AlertChecker()
    start_time = time.time()


    while True:
        data = collector.collect_all()
        alerts = checker.check(data)

        ts = data.get("timestamp", "")
        cpu = data.get("cpu", {}).get("percent", "?")
        mem = data.get("memory", {}).get("percent", "?")
        disks = len(data.get("disk", []))
        procs = len(data.get("processes", []))

        status_line = f"[{ts}] CPU:{cpu}% MEM:{mem}% DISKS:{disks} PROCS:{procs}"
        if alerts:
            status_line += f" ALERTS:{len(alerts)}"

        for alert in alerts:
            pass

        # 保存到日志
        log_file = HEALTH_LOG_DIR / f"health_{datetime.now().strftime('%Y%m%d')}.jsonl"
        log_entry = {"data": data, "alerts": alerts}
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.exception(f"Failed to write health log: {e}")

        if duration_sec > 0 and (time.time() - start_time) > duration_sec:
            break

        time.sleep(interval_sec)


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Hermes Health Monitor — CPU/Memory/Disk/Process + Prometheus metrics"
    )

    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON (default)")
    parser.add_argument("--prometheus", action="store_true", help="Output in Prometheus text format")
    parser.add_argument("--alert", action="store_true", help="Only check and output alerts")
    parser.add_argument("--watch", type=float, default=0.0, help="Watch mode: interval in seconds")
    parser.add_argument("--duration", type=float, default=0.0, help="Duration for watch mode (0=infinite)")
    parser.add_argument("--output", "-o", help="Output file path")

    args = parser.parse_args()

    collector = SystemHealthCollector()

    if args.watch > 0:
        watch_health(interval_sec=args.watch, duration_sec=args.duration)
        sys.exit(0)

    data = collector.collect_all()

    if args.prometheus:
        output = PrometheusFormatter.format(data)
    elif args.alert:
        checker = AlertChecker()
        alerts = checker.check(data)
        output = json.dumps(alerts, ensure_ascii=False, indent=2)
    else:
        output = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        pass
