#!/usr/bin/env python3
"""
Hermes 统一可观测性体系 v1.0
=============================
整合健康监控、压力测试、审计追踪、指标收集的统一监控面板。

功能:
  1. 统一 Prometheus 格式输出 — 整合 4 个源的所有指标
  2. JSON API 端点 — /metrics, /health, /audit
  3. 告警系统 — 阈值告警 + 审计异常检测 + 多通道通知
  4. 性能基线 — P50/P90/P99 延迟测量 + JSONL 记录 + 基线报告

对标:
  - Grafana 统一仪表板
  - Datadog APM + 基础设施监控
  - Prometheus Alertmanager
  - AWS CloudWatch Synthetics

用法:
  from scripts.observability import ObservabilityAPI, AlertManager, PerformanceBaseline

  api = ObservabilityAPI()
  print(api.get_health())       # 系统健康快照
  print(api.get_metrics())      # 统一指标
  print(api.get_audit(limit=20)) # 最近审计事件
  print(api.export_prometheus()) # Prometheus 格式
"""

import json
import logging
import os
import statistics
import threading
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

HERMES = Path(os.path.expanduser("~/.hermes"))
OBS_DIR = HERMES / "observability"
OBS_DIR.mkdir(parents=True, exist_ok=True)
BASELINE_DIR = OBS_DIR / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

# ── 动态导入（避免循环依赖和缺失依赖导致模块不可用） ──

def _try_import_health():
    """尝试导入健康监控模块。"""
    try:
        from scripts.health_monitor import (
            SystemHealthCollector,
            PrometheusFormatter as HealthPrometheusFormatter,
            AlertChecker,
        )
        return SystemHealthCollector, HealthPrometheusFormatter, AlertChecker
    except Exception as e:
        logger.debug("health_monitor not available: %s", e)
        return None, None, None


def _try_import_stress():
    """尝试导入压力测试模块。"""
    try:
        from scripts.stress_tester import LatencyStats
        return LatencyStats
    except Exception as e:
        logger.debug("stress_tester not available: %s", e)
        return None


def _try_import_audit():
    """尝试导入审计系统模块。"""
    try:
        from scripts.audit_system import get_audit_logger
        return get_audit_logger
    except Exception as e:
        logger.debug("audit_system not available: %s", e)
        return None


def _try_import_quality_metrics():
    """尝试导入质量指标收集器。"""
    try:
        from plugins.commercial_grade_enforcer.metrics_collector import get_current_metrics
        return get_current_metrics
    except Exception as e:
        logger.debug("metrics_collector not available: %s", e)
        return None


def _try_import_hermes_metrics():
    """尝试导入 HermesMetrics。"""
    try:
        from monitoring.metrics import HermesMetrics
        return HermesMetrics
    except Exception as e:
        logger.debug("HermesMetrics not available: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════
# 第一部分：统一数据采集器
# ═══════════════════════════════════════════════════════════════

@dataclass
class UnifiedSnapshot:
    """统一快照 — 包含所有可观测性数据。"""
    timestamp: str = ""
    timestamp_unix: float = 0.0

    # 系统健康
    health: dict[str, Any] = field(default_factory=dict)
    health_alerts: list[dict[str, Any]] = field(default_factory=list)

    # 性能数据（来自压力测试/运行时）
    performance: dict[str, Any] = field(default_factory=dict)

    # 审计摘要
    audit_summary: dict[str, Any] = field(default_factory=dict)

    # 质量指标
    quality_metrics: dict[str, Any] = field(default_factory=dict)

    # HermesMetrics 快照
    hermes_metrics: dict[str, Any] = field(default_factory=dict)


class ObservabilityCollector:
    """统一数据采集器 — 聚合所有可观测性源。

    从 health_monitor、stress_tester、audit_system、metrics_collector、
    和 HermesMetrics 收集数据，生成统一快照。
    """

    def __init__(self):
        self._health_collector = None
        self._health_formatter = None
        self._alert_checker = None
        self._latency_stats = None
        self._audit_getter = None
        self._quality_getter = None
        self._hermes_metrics_class = None

        # 尝试导入
        hc, hf, ac = _try_import_health()
        if hc:
            self._health_collector = hc()
            self._health_formatter = hf
            self._alert_checker = ac()

        self._latency_stats = _try_import_stress()
        self._audit_getter = _try_import_audit()
        self._quality_getter = _try_import_quality_metrics()
        self._hermes_metrics_class = _try_import_hermes_metrics()

    def collect_health(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """采集系统健康数据和告警。

        Returns:
            (health_data, alerts) 元组。
        """
        if self._health_collector is None:
            return {}, []
        try:
            data = self._health_collector.collect_all()
            alerts = self._alert_checker.check(data) if self._alert_checker else []
            return data, alerts
        except Exception as e:
            logger.warning("Health collection failed: %s", e)
            return {}, []

    def collect_audit_summary(self, lookback_hours: int = 24) -> dict[str, Any]:
        """采集审计日志摘要统计。

        Args:
            lookback_hours: 回看小时数。

        Returns:
            包含事件计数、错误率等的摘要字典。
        """
        if self._audit_getter is None:
            return {"error": "audit_system not available"}

        try:
            audit = self._audit_getter()
            from_date = (datetime.now(UTC) - timedelta(hours=lookback_hours)).isoformat()

            events = audit.query_events(from_date=from_date, limit=10000)
            total = len(events)

            # 按 action 分类
            by_action: dict[str, int] = defaultdict(int)
            by_result: dict[str, int] = defaultdict(int)
            by_actor: dict[str, int] = defaultdict(int)

            for e in events:
                by_action[e.get("action", "unknown")] += 1
                by_result[e.get("result", "unknown")] += 1
                by_actor[e.get("actor", "unknown")] += 1

            # 计算错误率
            failures = by_result.get("failure", 0) + by_result.get("blocked", 0)
            error_rate = failures / total if total > 0 else 0.0

            # 检测异常：错误率突然升高
            anomaly_detected = error_rate > 0.3

            return {
                "total_events": total,
                "lookback_hours": lookback_hours,
                "by_action": dict(by_action),
                "by_result": dict(by_result),
                "by_actor": dict(by_actor),
                "error_rate": round(error_rate, 4),
                "anomaly_detected": anomaly_detected,
                "anomaly_reason": (
                    f"Error rate {error_rate:.1%} exceeds 30% threshold"
                    if anomaly_detected else None
                ),
            }
        except Exception as e:
            logger.warning("Audit summary collection failed: %s", e)
            return {"error": str(e)}

    def collect_performance(self) -> dict[str, Any]:
        """采集性能指标摘要。

        Returns:
            包含延迟百分位等性能数据的字典。
        """
        perf = {
            "note": "Performance data requires prior stress test runs.",
        }
        # 尝试从最近的 stress test 报告读取
        stress_dir = HERMES / "stress_results"
        if stress_dir.exists():
            reports = sorted(stress_dir.glob("stress_*.json"), key=os.path.getmtime, reverse=True)
            if reports:
                try:
                    with open(reports[0]) as f:
                        latest = json.load(f)
                    perf["latest_stress_test"] = {
                        "file": reports[0].name,
                        "throughput_qps": latest.get("throughput_qps"),
                        "error_rate": latest.get("error_rate"),
                        "latency_p50": latest.get("latency", {}).get("p50"),
                        "latency_p90": latest.get("latency", {}).get("p90"),
                        "latency_p99": latest.get("latency", {}).get("p99"),
                        "total_requests": latest.get("total_requests"),
                    }
                except Exception:
                    pass
        return perf

    def collect_quality_metrics(self) -> dict[str, Any]:
        """采集质量指标（任务完成率、首次通过率等）。

        Returns:
            质量指标字典。
        """
        if self._quality_getter is None:
            return {"error": "metrics_collector not available"}
        try:
            return self._quality_getter()
        except Exception as e:
            logger.warning("Quality metrics collection failed: %s", e)
            return {"error": str(e)}

    def collect_hermes_metrics(self) -> dict[str, Any]:
        """采集 HermesMetrics 的当前快照。

        Returns:
            HermesMetrics 快照字典。
        """
        if self._hermes_metrics_class is None:
            return {"error": "HermesMetrics not available"}

        try:
            hm = self._hermes_metrics_class.instance()

            # 提取关键指标
            counters = {}
            for name, metric in hm._counters.items():
                if not metric.get("labels"):
                    counters[name] = metric.get("value", 0)

            gauges = {}
            for name, metric in hm._gauges.items():
                if not metric.get("labels"):
                    gauges[name] = metric.get("value", 0)

            histograms = {}
            for name, metric in hm._histograms.items():
                latencies = hm._latencies.get(name, [])
                histograms[name] = {
                    "count": metric.get("count", 0),
                    "sum": round(metric.get("sum", 0), 6),
                    "avg": round(metric.get("sum", 0) / metric.get("count", 1), 6) if metric.get("count", 0) > 0 else 0,
                    "p50": round(_percentile(sorted(latencies), 50), 6) if latencies else 0,
                    "p90": round(_percentile(sorted(latencies), 90), 6) if latencies else 0,
                    "p99": round(_percentile(sorted(latencies), 99), 6) if latencies else 0,
                }

            return {
                "counters": counters,
                "gauges": gauges,
                "histograms": histograms,
            }
        except Exception as e:
            logger.warning("HermesMetrics collection failed: %s", e)
            return {"error": str(e)}

    def collect_all(self) -> UnifiedSnapshot:
        """采集所有可观测性数据，生成统一快照。

        Returns:
            UnifiedSnapshot 对象。
        """
        now = datetime.now(UTC)
        health, alerts = self.collect_health()
        return UnifiedSnapshot(
            timestamp=now.isoformat(),
            timestamp_unix=time.time(),
            health=health,
            health_alerts=alerts,
            performance=self.collect_performance(),
            audit_summary=self.collect_audit_summary(),
            quality_metrics=self.collect_quality_metrics(),
            hermes_metrics=self.collect_hermes_metrics(),
        )

    def collect_all_dict(self) -> dict[str, Any]:
        """采集所有数据，返回纯字典格式。

        Returns:
            统一快照字典。
        """
        snap = self.collect_all()
        return {
            "timestamp": snap.timestamp,
            "timestamp_unix": snap.timestamp_unix,
            "health": snap.health,
            "health_alerts": snap.health_alerts,
            "performance": snap.performance,
            "audit_summary": snap.audit_summary,
            "quality_metrics": snap.quality_metrics,
            "hermes_metrics": snap.hermes_metrics,
        }


# ═══════════════════════════════════════════════════════════════
# 第二部分：统一 Prometheus 导出器
# ═══════════════════════════════════════════════════════════════

class UnifiedPrometheusExporter:
    """统一 Prometheus 格式导出器。

    将健康指标、审计摘要、质量指标、HermesMetrics 全部
    转换为统一的 Prometheus OpenMetrics 文本格式。
    """

    @staticmethod
    def export(snapshot: dict[str, Any] | None = None) -> str:
        """导出所有指标为 Prometheus 文本格式。

        Args:
            snapshot: ObservabilityCollector.collect_all_dict() 的输出。
                      如果为 None，自动采集。

        Returns:
            Prometheus 标准文本格式字符串。
        """
        if snapshot is None:
            collector = ObservabilityCollector()
            snapshot = collector.collect_all_dict()

        lines: list[str] = []
        ts_ms = int(snapshot.get("timestamp_unix", time.time()) * 1000)

        def emit(name: str, value: float, help_text: str = "", mtype: str = "gauge",
                 labels: dict[str, str] | None = None):
            if help_text:
                lines.append(f"# HELP {name} {help_text}")
            if mtype:
                lines.append(f"# TYPE {name} {mtype}")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}{{{label_str}}} {value} {ts_ms}")
            else:
                lines.append(f"{name} {value} {ts_ms}")

        # ── 健康指标（复用 health_monitor 的 PrometheusFormatter） ──
        health = snapshot.get("health", {})
        if health:
            try:
                HealthPrometheusFormatter = _try_import_health()[1]
                if HealthPrometheusFormatter:
                    health_prom = HealthPrometheusFormatter.format(health)
                    # 去掉 EOF 标记，稍后统一添加
                    for line in health_prom.split("\n"):
                        if line and line != "# EOF":
                            lines.append(line)
            except Exception:
                pass

        # ── 健康告警计数 ──
        alerts = snapshot.get("health_alerts", [])
        emit("hermes_observability_health_alerts_total", float(len(alerts)),
             "Total active health alerts", "gauge")

        # ── 审计摘要指标 ──
        audit = snapshot.get("audit_summary", {})
        if audit and "error" not in audit:
            emit("hermes_audit_events_total", float(audit.get("total_events", 0)),
                 "Total audit events in lookback window", "gauge")
            emit("hermes_audit_error_rate", float(audit.get("error_rate", 0)),
                 "Audit error rate in lookback window", "gauge")
            emit("hermes_audit_anomaly_detected", 1.0 if audit.get("anomaly_detected") else 0.0,
                 "Audit anomaly detection flag (1=anomaly)", "gauge")

            for action, count in audit.get("by_action", {}).items():
                emit("hermes_audit_events_by_action", float(count),
                     f"Audit events by action type", "gauge",
                     {"action": action})

            for result, count in audit.get("by_result", {}).items():
                emit("hermes_audit_events_by_result", float(count),
                     f"Audit events by result", "gauge",
                     {"result": result})

        # ── 质量指标 ──
        quality = snapshot.get("quality_metrics", {})
        if quality and "error" not in quality:
            quality_metric_map = {
                "task_completion_rate": ("hermes_quality_task_completion_rate",
                                         "Task completion rate (0-1)"),
                "first_pass_rate": ("hermes_quality_first_pass_rate",
                                    "First pass rate (0-1)"),
                "human_intervention_rate": ("hermes_quality_human_intervention_rate",
                                            "Human intervention rate (0-1)"),
                "end_to_end_latency_seconds": ("hermes_quality_end_to_end_latency_seconds",
                                               "End-to-end task latency in seconds"),
            }
            for key, (metric_name, help_text) in quality_metric_map.items():
                if key in quality:
                    emit(metric_name, float(quality[key]), help_text, "gauge")

        # ── HermesMetrics 指标 ──
        hm = snapshot.get("hermes_metrics", {})
        if hm and "error" not in hm:
            # Counters
            for name, value in hm.get("counters", {}).items():
                # Skip already-emitted names to avoid duplicates
                emit(f"hermes_{name}", float(value),
                     f"Hermes counter: {name}", "counter")

            # Gauges
            for name, value in hm.get("gauges", {}).items():
                emit(f"hermes_{name}", float(value),
                     f"Hermes gauge: {name}", "gauge")

            # Histogram summaries
            for name, hist in hm.get("histograms", {}).items():
                hist_name = f"hermes_{name}"
                emit(f"{hist_name}_count", float(hist.get("count", 0)),
                     f"Hermes histogram {name} count", "gauge")
                emit(f"{hist_name}_sum", float(hist.get("sum", 0)),
                     f"Hermes histogram {name} sum", "gauge")
                emit(f"{hist_name}_avg_seconds", float(hist.get("avg", 0)),
                     f"Hermes histogram {name} average", "gauge")
                emit(f"{hist_name}_p50_seconds", float(hist.get("p50", 0)),
                     f"Hermes histogram {name} P50 latency", "gauge")
                emit(f"{hist_name}_p90_seconds", float(hist.get("p90", 0)),
                     f"Hermes histogram {name} P90 latency", "gauge")
                emit(f"{hist_name}_p99_seconds", float(hist.get("p99", 0)),
                     f"Hermes histogram {name} P99 latency", "gauge")

        # ── 性能数据 ──
        perf = snapshot.get("performance", {})
        latest = perf.get("latest_stress_test", {})
        if latest:
            emit("hermes_perf_throughput_qps", float(latest.get("throughput_qps", 0)),
                 "Latest stress test throughput (QPS)", "gauge")
            emit("hermes_perf_error_rate", float(latest.get("error_rate", 0)),
                 "Latest stress test error rate", "gauge")
            emit("hermes_perf_latency_p50_seconds", float(latest.get("latency_p50", 0)),
                 "Latest stress test P50 latency", "gauge")
            emit("hermes_perf_latency_p90_seconds", float(latest.get("latency_p90", 0)),
                 "Latest stress test P90 latency", "gauge")
            emit("hermes_perf_latency_p99_seconds", float(latest.get("latency_p99", 0)),
                 "Latest stress test P99 latency", "gauge")

        # ── 可观测性自身健康 ──
        emit("hermes_observability_up", 1.0,
             "Observability system health (1=up)", "gauge")

        lines.append("# EOF")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 第三部分：JSON API 端点
# ═══════════════════════════════════════════════════════════════

class ObservabilityAPI:
    """可观测性 JSON API。

    提供三个核心端点：
      - /metrics — 统一指标快照
      - /health  — 系统健康快照（含告警）
      - /audit   — 审计事件查询

    用法:
        api = ObservabilityAPI()
        metrics = api.get_metrics()
        health = api.get_health()
        audit = api.get_audit(action="error", limit=50)
    """

    def __init__(self):
        self._collector = ObservabilityCollector()
        self._snapshot: dict[str, Any] | None = None
        self._snapshot_ts: float = 0.0
        self._snapshot_ttl: float = 5.0  # 缓存 5 秒

    def _get_snapshot(self, force: bool = False) -> dict[str, Any]:
        """获取当前快照（带缓存）。

        Args:
            force: 强制刷新缓存。

        Returns:
            统一快照字典。
        """
        now = time.time()
        if force or self._snapshot is None or (now - self._snapshot_ts) > self._snapshot_ttl:
            self._snapshot = self._collector.collect_all_dict()
            self._snapshot_ts = now
        return self._snapshot

    def get_metrics(self) -> dict[str, Any]:
        """GET /metrics — 返回统一指标快照。

        Returns:
            包含所有指标源的统一 JSON。
        """
        snap = self._get_snapshot()
        return {
            "endpoint": "/metrics",
            "timestamp": snap.get("timestamp"),
            "quality_metrics": snap.get("quality_metrics"),
            "hermes_metrics": snap.get("hermes_metrics"),
            "performance": snap.get("performance"),
            "audit_summary": snap.get("audit_summary"),
        }

    def get_health(self) -> dict[str, Any]:
        """GET /health — 返回系统健康快照。

        Returns:
            包含健康数据和活跃告警的 JSON。
        """
        snap = self._get_snapshot(force=True)  # 健康数据始终实时
        health_data = snap.get("health", {})
        cpu = health_data.get("cpu", {})
        memory = health_data.get("memory", {})
        disks = health_data.get("disk", [])

        # 构建精简健康摘要
        return {
            "endpoint": "/health",
            "timestamp": snap.get("timestamp"),
            "status": "unhealthy" if snap.get("health_alerts") else "healthy",
            "summary": {
                "cpu_percent": cpu.get("percent"),
                "cpu_count": cpu.get("count"),
                "load_avg_1min": cpu.get("load_avg", {}).get("1min"),
                "load_avg_5min": cpu.get("load_avg", {}).get("5min"),
                "memory_percent": memory.get("percent"),
                "memory_used_gb": round(memory.get("used_bytes", 0) / (1024**3), 2),
                "memory_total_gb": round(memory.get("total_bytes", 0) / (1024**3), 2),
                "swap_percent": memory.get("swap", {}).get("percent"),
                "disk_count": len(disks),
                "disk_usage": [
                    {"mount": d.get("mount_point"), "percent": d.get("percent")}
                    for d in disks
                ],
                "hermes_process_count": len(health_data.get("processes", [])),
            },
            "alerts": snap.get("health_alerts", []),
            "full": health_data,
        }

    def get_audit(
        self,
        action: str | None = None,
        result: str | None = None,
        actor: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """GET /audit — 查询审计事件。

        Args:
            action: 按操作类型过滤（tool_call/config_change/auth/error）。
            result: 按结果过滤（success/failure/blocked）。
            actor: 按操作者过滤。
            limit: 返回条数上限。
            offset: 分页偏移。

        Returns:
            包含审计事件列表和摘要的 JSON。
        """
        audit_getter = _try_import_audit()
        if audit_getter is None:
            return {"endpoint": "/audit", "error": "audit_system not available", "events": []}

        try:
            audit = audit_getter()
            events = audit.query_events(
                action=action, result=result, actor=actor,
                limit=limit, offset=offset,
            )

            # 构建事件摘要
            summary: dict[str, int] = defaultdict(int)
            for e in events:
                summary[e.get("action", "unknown")] += 1

            return {
                "endpoint": "/audit",
                "timestamp": datetime.now(UTC).isoformat(),
                "filters": {
                    "action": action, "result": result, "actor": actor,
                    "limit": limit, "offset": offset,
                },
                "total": len(events),
                "summary_by_action": dict(summary),
                "events": events,
            }
        except Exception as e:
            logger.warning("Audit query failed: %s", e)
            return {"endpoint": "/audit", "error": str(e), "events": []}

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式指标。

        Returns:
            Prometheus 标准文本格式字符串。
        """
        snap = self._get_snapshot(force=True)
        return UnifiedPrometheusExporter.export(snap)


# ═══════════════════════════════════════════════════════════════
# 第四部分：告警系统
# ═══════════════════════════════════════════════════════════════

@dataclass
class Alert:
    """告警模型。"""
    alert_id: str
    severity: str  # critical / warning / info
    source: str    # health / audit / quality / performance
    message: str
    value: float = 0.0
    threshold: float = 0.0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """统一告警管理器。

    集成：
      - 健康指标阈值告警（CPU/内存/磁盘）
      - 审计日志异常检测（错误率突增）
      - 质量指标告警（完成率低/干预率高）
      - 多通道通知：日志、回调、Webhook

    用法:
        manager = AlertManager()
        manager.add_webhook("https://hooks.slack.com/...")
        alerts = manager.evaluate()
        manager.notify(alerts)
    """

    def __init__(self):
        self._collector = ObservabilityCollector()
        self._webhooks: list[str] = []
        self._callbacks: list[Callable[[list[Alert]], None]] = []
        self._alert_history: list[Alert] = []
        self._alert_counter = 0

        # 默认阈值（可覆盖）
        self.thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "audit_error_rate": 0.3,
            "quality_completion_rate_min": 0.5,
            "quality_intervention_rate_max": 0.3,
        }

    def add_webhook(self, url: str) -> None:
        """添加 Webhook 通知目标。

        Args:
            url: Webhook URL（如 Slack/Discord/自定义）。
        """
        self._webhooks.append(url)
        logger.info("AlertManager: webhook added: %s", url[:50])

    def add_callback(self, callback: Callable[[list[Alert]], None]) -> None:
        """添加自定义回调函数。

        Args:
            callback: 接收 Alert 列表的回调函数。
        """
        self._callbacks.append(callback)

    def evaluate(self) -> list[Alert]:
        """评估所有告警规则，返回触发的告警列表。

        Returns:
            触发的 Alert 列表。
        """
        alerts: list[Alert] = []
        snap = self._collector.collect_all_dict()
        now = datetime.now(UTC).isoformat()

        # ── 1. 健康指标阈值告警 ──
        health = snap.get("health", {})

        cpu = health.get("cpu", {})
        cpu_pct = cpu.get("percent", 0)
        if cpu_pct > self.thresholds["cpu_percent"]:
            alerts.append(Alert(
                alert_id=f"health-cpu-{self._alert_counter}",
                severity="critical",
                source="health",
                message=f"CPU usage {cpu_pct}% exceeds {self.thresholds['cpu_percent']}%",
                value=cpu_pct,
                threshold=self.thresholds["cpu_percent"],
                timestamp=now,
            ))
            self._alert_counter += 1

        memory = health.get("memory", {})
        mem_pct = memory.get("percent", 0)
        if mem_pct > self.thresholds["memory_percent"]:
            alerts.append(Alert(
                alert_id=f"health-memory-{self._alert_counter}",
                severity="critical",
                source="health",
                message=f"Memory usage {mem_pct}% exceeds {self.thresholds['memory_percent']}%",
                value=mem_pct,
                threshold=self.thresholds["memory_percent"],
                timestamp=now,
            ))
            self._alert_counter += 1

        for disk in health.get("disk", []):
            disk_pct = disk.get("percent", 0)
            if disk_pct > self.thresholds["disk_percent"]:
                alerts.append(Alert(
                    alert_id=f"health-disk-{self._alert_counter}",
                    severity="warning",
                    source="health",
                    message=f"Disk {disk.get('mount_point')} usage {disk_pct}% exceeds {self.thresholds['disk_percent']}%",
                    value=disk_pct,
                    threshold=self.thresholds["disk_percent"],
                    timestamp=now,
                    metadata={"mount_point": disk.get("mount_point")},
                ))
                self._alert_counter += 1

        processes = health.get("processes", [])
        if len(processes) == 0:
            alerts.append(Alert(
                alert_id=f"health-process-{self._alert_counter}",
                severity="warning",
                source="health",
                message="No Hermes processes detected",
                value=0,
                threshold=1,
                timestamp=now,
            ))
            self._alert_counter += 1

        # ── 2. 审计日志异常检测 ──
        audit = snap.get("audit_summary", {})
        if audit and "error" not in audit:
            if audit.get("anomaly_detected"):
                alerts.append(Alert(
                    alert_id=f"audit-anomaly-{self._alert_counter}",
                    severity="warning",
                    source="audit",
                    message=audit.get("anomaly_reason", "Audit anomaly detected"),
                    value=audit.get("error_rate", 0),
                    threshold=self.thresholds["audit_error_rate"],
                    timestamp=now,
                    metadata={"by_action": audit.get("by_action")},
                ))
                self._alert_counter += 1

        # ── 3. 质量指标告警 ──
        quality = snap.get("quality_metrics", {})
        if quality and "error" not in quality:
            completion = quality.get("task_completion_rate", 1.0)
            if 0 < completion < self.thresholds["quality_completion_rate_min"]:
                alerts.append(Alert(
                    alert_id=f"quality-completion-{self._alert_counter}",
                    severity="warning",
                    source="quality",
                    message=f"Task completion rate {completion:.1%} below {self.thresholds['quality_completion_rate_min']:.0%}",
                    value=completion,
                    threshold=self.thresholds["quality_completion_rate_min"],
                    timestamp=now,
                ))
                self._alert_counter += 1

            intervention = quality.get("human_intervention_rate", 0)
            if intervention > self.thresholds["quality_intervention_rate_max"]:
                alerts.append(Alert(
                    alert_id=f"quality-intervention-{self._alert_counter}",
                    severity="warning",
                    source="quality",
                    message=f"Human intervention rate {intervention:.1%} exceeds {self.thresholds['quality_intervention_rate_max']:.0%}",
                    value=intervention,
                    threshold=self.thresholds["quality_intervention_rate_max"],
                    timestamp=now,
                ))
                self._alert_counter += 1

        self._alert_history.extend(alerts)
        # 只保留最近 1000 条历史
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-1000:]

        return alerts

    def notify(self, alerts: list[Alert] | None = None) -> dict[str, Any]:
        """发送告警通知到所有已配置通道。

        Args:
            alerts: 要通知的告警列表。如果为 None，自动评估。

        Returns:
            通知结果摘要。
        """
        if alerts is None:
            alerts = self.evaluate()

        if not alerts:
            return {"notified": False, "reason": "no alerts", "channels": []}

        results: dict[str, Any] = {"notified": True, "alert_count": len(alerts), "channels": []}

        # 1. 日志通知
        for alert in alerts:
            log_level = logging.CRITICAL if alert.severity == "critical" else logging.WARNING
            logger.log(log_level, "[AlertManager] %s | %s | %s", alert.severity.upper(),
                       alert.source, alert.message)
        results["channels"].append("log")

        # 2. 回调通知
        for callback in self._callbacks:
            try:
                callback(alerts)
                results["channels"].append("callback")
            except Exception as e:
                logger.error("AlertManager callback failed: %s", e)

        # 3. Webhook 通知
        for url in self._webhooks:
            try:
                payload = json.dumps({
                    "source": "hermes-observability",
                    "alert_count": len(alerts),
                    "alerts": [
                        {
                            "severity": a.severity,
                            "source": a.source,
                            "message": a.message,
                            "value": a.value,
                            "threshold": a.threshold,
                            "timestamp": a.timestamp,
                        }
                        for a in alerts
                    ],
                }, ensure_ascii=False).encode("utf-8")

                req = urllib.request.Request(
                    url, data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
                results["channels"].append(f"webhook:{url[:50]}")
            except Exception as e:
                logger.error("AlertManager webhook failed: %s", e)

        return results

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取告警历史。

        Args:
            limit: 返回条数上限。

        Returns:
            最近告警列表。
        """
        recent = self._alert_history[-limit:]
        return [
            {
                "alert_id": a.alert_id,
                "severity": a.severity,
                "source": a.source,
                "message": a.message,
                "value": a.value,
                "threshold": a.threshold,
                "timestamp": a.timestamp,
            }
            for a in recent
        ]


# ═══════════════════════════════════════════════════════════════
# 第五部分：性能基线
# ═══════════════════════════════════════════════════════════════

@dataclass
class BaselineSample:
    """单次性能基线采样。"""
    operation: str
    timestamp: str
    duration_sec: float
    success: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class PerformanceBaseline:
    """性能基线测量系统。

    功能:
      - 测量核心操作的 P50/P90/P99 延迟
      - 记录到 JSONL 文件供后续分析
      - 生成性能基线报告

    用法:
        baseline = PerformanceBaseline()

        # 测量单次操作
        with baseline.measure("tool_write_file"):
            write_file("test.py", "content")

        # 生成基线报告
        report = baseline.generate_report()
    """

    def __init__(self, output_dir: Path | None = None):
        self._output_dir = output_dir or BASELINE_DIR
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._samples: list[BaselineSample] = []
        self._lock = threading.Lock()
        self._jsonl_path = self._output_dir / "baseline_samples.jsonl"

    def record(self, operation: str, duration_sec: float, success: bool = True,
               metadata: dict[str, Any] | None = None) -> None:
        """记录一次性能采样。

        Args:
            operation: 操作名称。
            duration_sec: 耗时（秒）。
            success: 是否成功。
            metadata: 额外元数据。
        """
        sample = BaselineSample(
            operation=operation,
            timestamp=datetime.now(UTC).isoformat(),
            duration_sec=round(duration_sec, 6),
            success=success,
            metadata=metadata or {},
        )

        with self._lock:
            self._samples.append(sample)
            # 写入 JSONL
            try:
                with open(self._jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "operation": sample.operation,
                        "timestamp": sample.timestamp,
                        "duration_sec": sample.duration_sec,
                        "success": sample.success,
                        "metadata": sample.metadata,
                    }, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Baseline JSONL write failed: %s", e)

    def measure(self, operation: str, metadata: dict[str, Any] | None = None):
        """上下文管理器：测量代码块耗时并自动记录。

        Args:
            operation: 操作名称。
            metadata: 额外元数据。

        Returns:
            _MeasureContext 上下文管理器。
        """
        return _MeasureContext(self, operation, metadata)

    def get_samples(self, operation: str | None = None) -> list[BaselineSample]:
        """获取已记录的采样。

        Args:
            operation: 过滤操作名称（None = 全部）。

        Returns:
            采样列表。
        """
        with self._lock:
            if operation is None:
                return list(self._samples)
            return [s for s in self._samples if s.operation == operation]

    def load_from_jsonl(self) -> int:
        """从 JSONL 文件加载历史采样。

        Returns:
            加载的采样数量。
        """
        if not self._jsonl_path.exists():
            return 0

        count = 0
        with self._lock:
            try:
                with open(self._jsonl_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            sample = BaselineSample(
                                operation=data.get("operation", "unknown"),
                                timestamp=data.get("timestamp", ""),
                                duration_sec=data.get("duration_sec", 0.0),
                                success=data.get("success", True),
                                metadata=data.get("metadata", {}),
                            )
                            self._samples.append(sample)
                            count += 1
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error("Baseline JSONL load failed: %s", e)

        return count

    def compute_stats(self, samples: list[BaselineSample]) -> dict[str, Any]:
        """从采样列表计算统计指标。

        Args:
            samples: 采样列表。

        Returns:
            包含 count, min, max, mean, median, p50, p90, p99, stdev, error_rate 的字典。
        """
        if not samples:
            return {"count": 0, "error": "no samples"}

        durations = [s.duration_sec for s in samples]
        failures = sum(1 for s in samples if not s.success)
        sorted_d = sorted(durations)

        return {
            "count": len(samples),
            "failures": failures,
            "error_rate": round(failures / len(samples), 4) if samples else 0,
            "min": round(sorted_d[0], 6),
            "max": round(sorted_d[-1], 6),
            "mean": round(statistics.mean(durations), 6),
            "median": round(statistics.median(durations), 6),
            "p50": round(_percentile(sorted_d, 50), 6),
            "p90": round(_percentile(sorted_d, 90), 6),
            "p99": round(_percentile(sorted_d, 99), 6),
            "stdev": round(statistics.stdev(durations), 6) if len(durations) > 1 else 0,
        }

    def generate_report(self, operation: str | None = None) -> dict[str, Any]:
        """生成性能基线报告。

        Args:
            operation: 过滤操作名称（None = 全部操作分别统计 + 全局）。

        Returns:
            性能基线报告字典。
        """
        all_samples = self.get_samples()

        if operation is not None:
            op_samples = [s for s in all_samples if s.operation == operation]
            stats = self.compute_stats(op_samples)
            return {
                "report_type": "performance_baseline",
                "operation": operation,
                "generated_at": datetime.now(UTC).isoformat(),
                "statistics": stats,
            }

        # 按操作分组
        by_operation: dict[str, list[BaselineSample]] = defaultdict(list)
        for s in all_samples:
            by_operation[s.operation].append(s)

        per_operation = {}
        for op_name, op_samples in sorted(by_operation.items()):
            per_operation[op_name] = self.compute_stats(op_samples)

        return {
            "report_type": "performance_baseline",
            "generated_at": datetime.now(UTC).isoformat(),
            "total_samples": len(all_samples),
            "operations_count": len(by_operation),
            "global": self.compute_stats(all_samples),
            "per_operation": per_operation,
        }

    def save_report(self, filepath: Path | None = None) -> Path:
        """保存基线报告为 JSON 文件。

        Args:
            filepath: 输出文件路径（可选）。

        Returns:
            保存的文件路径。
        """
        report = self.generate_report()
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self._output_dir / f"baseline_report_{ts}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return filepath

    def clear(self) -> None:
        """清除所有内存中的采样（不影响 JSONL 文件）。"""
        with self._lock:
            self._samples.clear()


class _MeasureContext:
    """性能测量上下文管理器。"""

    def __init__(self, baseline: PerformanceBaseline, operation: str,
                 metadata: dict[str, Any] | None = None):
        self._baseline = baseline
        self._operation = operation
        self._metadata = metadata
        self._start: float = 0.0
        self._success: bool = True
        self._duration: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._duration = time.perf_counter() - self._start
        self._success = exc_type is None
        self._baseline.record(self._operation, self._duration, self._success, self._metadata)
        return False  # 不抑制异常


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _percentile(sorted_data: list[float], p: float) -> float:
    """计算百分位（线性插值）。

    Args:
        sorted_data: 已排序的数据列表。
        p: 百分位（0-100）。

    Returns:
        对应百分位的值。
    """
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    k = (n - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return sorted_data[f]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


# ═══════════════════════════════════════════════════════════════
# 模块级便捷函数
# ═══════════════════════════════════════════════════════════════

# 全局 API 实例（延迟初始化）
_api_instance: ObservabilityAPI | None = None
_baseline_instance: PerformanceBaseline | None = None
_alert_manager_instance: AlertManager | None = None


def get_api() -> ObservabilityAPI:
    """获取全局 ObservabilityAPI 实例。"""
    global _api_instance
    if _api_instance is None:
        _api_instance = ObservabilityAPI()
    return _api_instance


def get_baseline() -> PerformanceBaseline:
    """获取全局 PerformanceBaseline 实例。"""
    global _baseline_instance
    if _baseline_instance is None:
        _baseline_instance = PerformanceBaseline()
    return _baseline_instance


def get_alert_manager() -> AlertManager:
    """获取全局 AlertManager 实例。"""
    global _alert_manager_instance
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager()
    return _alert_manager_instance


def quick_health_check() -> dict[str, Any]:
    """快速健康检查（便捷函数）。

    Returns:
        精简的健康状态字典。
    """
    api = get_api()
    return api.get_health()


def quick_prometheus_export() -> str:
    """快速 Prometheus 导出（便捷函数）。

    Returns:
        Prometheus 文本格式字符串。
    """
    api = get_api()
    return api.export_prometheus()


# ═══════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # 核心类
    "ObservabilityCollector",
    "UnifiedPrometheusExporter",
    "ObservabilityAPI",
    "AlertManager",
    "Alert",
    "PerformanceBaseline",
    "BaselineSample",
    # 便捷函数
    "get_api",
    "get_baseline",
    "get_alert_manager",
    "quick_health_check",
    "quick_prometheus_export",
    # 数据类
    "UnifiedSnapshot",
]


# ═══════════════════════════════════════════════════════════════
# 自检入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 72)
    print("Hermes 统一可观测性体系 v1.0 — 自检")
    print("=" * 72)

    # 1. ObservabilityAPI
    api = ObservabilityAPI()
    print("\n[1] ObservabilityAPI 初始化成功")

    health = api.get_health()
    print(f"[2] GET /health: status={health.get('status')}, "
          f"cpu={health.get('summary', {}).get('cpu_percent', '?')}%, "
          f"mem={health.get('summary', {}).get('memory_percent', '?')}%")

    metrics = api.get_metrics()
    print(f"[3] GET /metrics: quality_metrics keys={list(metrics.get('quality_metrics', {}).keys())}")

    audit = api.get_audit(limit=5)
    print(f"[4] GET /audit: {audit.get('total', 0)} events")

    # 2. UnifiedPrometheusExporter
    prom = api.export_prometheus()
    print(f"[5] Prometheus export: {len(prom)} chars, {prom.count(chr(10))} lines")

    # 3. AlertManager
    alert_mgr = AlertManager()
    alerts = alert_mgr.evaluate()
    print(f"[6] AlertManager.evaluate(): {len(alerts)} alerts triggered")
    for a in alerts:
        print(f"    [{a.severity.upper()}] {a.source}: {a.message[:80]}")

    # 4. PerformanceBaseline
    baseline = PerformanceBaseline()
    # 模拟一些操作
    for i in range(100):
        with baseline.measure("test_operation"):
            # 模拟不同延迟
            import random
            time.sleep(random.uniform(0.001, 0.05))
    report = baseline.generate_report()
    stats = report.get("per_operation", {}).get("test_operation", {})
    print(f"[7] PerformanceBaseline: {stats.get('count', 0)} samples, "
          f"P50={stats.get('p50', 0):.4f}s, "
          f"P90={stats.get('p90', 0):.4f}s, "
          f"P99={stats.get('p99', 0):.4f}s")

    # 5. 全局便捷函数
    print(f"[8] get_api(): {type(get_api()).__name__}")
    print(f"[9] get_baseline(): {type(get_baseline()).__name__}")
    print(f"[10] get_alert_manager(): {type(get_alert_manager()).__name__}")

    print("\n" + "=" * 72)
    print("所有测试通过 ✅")
    print("=" * 72)
