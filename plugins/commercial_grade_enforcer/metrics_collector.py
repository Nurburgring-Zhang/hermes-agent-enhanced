"""
指标收集器 — 后台线程持续收集4项核心质量指标
====================================================
方法论依据: 二.5 评估与反馈闭环
"指标：任务完成率、首次通过率、人工干预率、端到端耗时"
"""

import json
import logging
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

METRICS_DB = Path("~/.hermes/data/metrics.db").expanduser()
METRICS_LOG = Path("~/.hermes/logs/metrics.jsonl").expanduser()

# ── 收集间隔 ──
COLLECT_INTERVAL = 60  # 每60秒收集一次

# ── 全局状态（线程安全）──
_lock = threading.Lock()
_collector_thread = None
_running = False

# ── 内存缓冲区（最多保留1小时=60条）──
_metrics_buffer = deque(maxlen=60)


def _init_metrics_db():
    """初始化指标数据库"""
    METRICS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(METRICS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quality_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            labels TEXT,  -- JSON key-value tags
            source TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_name_time
        ON quality_metrics(metric_name, timestamp)
    """)
    conn.commit()
    conn.close()


def _collect_metrics(ctx) -> dict:
    """收集当前时刻的4项核心指标"""
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_completion_rate": 0.0,    # 任务完成率
        "first_pass_rate": 0.0,          # 首次通过率
        "human_intervention_rate": 0.0,  # 人工干预率
        "end_to_end_latency_seconds": 0.0, # 端到端耗时
    }

    try:
        # 从SQLite获取统计数据
        conn = sqlite3.connect(str(METRICS_DB))

        # 任务完成率
        cursor = conn.execute(
            "SELECT COUNT(*) FROM quality_metrics WHERE metric_name = 'task_completed'"
        )
        completed = cursor.fetchone()[0]
        cursor = conn.execute(
            "SELECT COUNT(*) FROM quality_metrics WHERE metric_name = 'task_started'"
        )
        started = cursor.fetchone()[0]
        if started > 0:
            metrics["task_completion_rate"] = completed / started

        # 首次通过率
        cursor = conn.execute(
            "SELECT COUNT(*) FROM quality_metrics "
            "WHERE metric_name = 'first_pass' AND metric_value = 1"
        )
        first_pass_count = cursor.fetchone()[0]
        cursor = conn.execute(
            "SELECT COUNT(*) FROM quality_metrics WHERE metric_name = 'first_pass'"
        )
        total_attempts = cursor.fetchone()[0]
        if total_attempts > 0:
            metrics["first_pass_rate"] = first_pass_count / total_attempts

        # 人工干预率
        cursor = conn.execute(
            "SELECT COUNT(*) FROM quality_metrics WHERE metric_name = 'hitl_triggered'"
        )
        hitl_count = cursor.fetchone()[0]
        if started > 0:
            metrics["human_intervention_rate"] = hitl_count / started

        # 端到端耗时 (最近一次任务的耗时)
        cursor = conn.execute(
            "SELECT metric_value FROM quality_metrics "
            "WHERE metric_name = 'task_duration_seconds' "
            "ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            metrics["end_to_end_latency_seconds"] = row[0]

        conn.close()
    except Exception as e:
        logger.error(f"[指标收集] 数据库查询失败: {e}")

    return metrics


def _persist_metrics(metrics: dict):
    """持久化指标到数据库和日志"""
    conn = sqlite3.connect(str(METRICS_DB))
    try:
        for name, value in metrics.items():
            if name == "timestamp":
                continue
            conn.execute(
                """INSERT INTO quality_metrics (metric_name, metric_value, source)
                   VALUES (?, ?, ?)""",
                (name, float(value), "auto_collector")
            )
        conn.commit()
    finally:
        conn.close()

    # 写入JSONL日志
    METRICS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_LOG, "a") as f:
        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")


def _collector_loop(ctx):
    """后台收集循环"""
    global _running
    _init_metrics_db()
    logger.info("[指标收集器] 启动，间隔=%ds", COLLECT_INTERVAL)

    while _running:
        try:
            metrics = _collect_metrics(ctx)
            with _lock:
                _metrics_buffer.append(metrics)
            _persist_metrics(metrics)

            # 异常检测: 人力干预率过高时告警
            if metrics["human_intervention_rate"] > 0.3:
                logger.warning(
                    f"[指标收集器] 人工干预率过高: "
                    f"{metrics['human_intervention_rate']:.1%}"
                )

            # 完成率过低时告警
            if (metrics["task_completion_rate"] < 0.5
                    and metrics["task_completion_rate"] > 0):
                logger.warning(
                    f"[指标收集器] 任务完成率低: "
                    f"{metrics['task_completion_rate']:.1%}"
                )

        except Exception as e:
            logger.error(f"[指标收集器] 收集异常: {e}")

        time.sleep(COLLECT_INTERVAL)

    logger.info("[指标收集器] 已停止")


def start_collector(ctx):
    """启动指标收集器后台线程"""
    global _collector_thread, _running
    if _running:
        return

    _running = True
    _collector_thread = threading.Thread(
        target=_collector_loop,
        args=(ctx,),
        daemon=True,
        name="metrics-collector"
    )
    _collector_thread.start()


def stop_collector():
    """停止指标收集器"""
    global _running
    _running = False


def record_event(ctx, event_name: str, value: float = 1.0, labels: dict | None = None):
    """记录单个事件到指标系统"""
    _init_metrics_db()
    conn = sqlite3.connect(str(METRICS_DB))
    try:
        conn.execute(
            """INSERT INTO quality_metrics (metric_name, metric_value, labels)
               VALUES (?, ?, ?)""",
            (event_name, value, json.dumps(labels or {}))
        )
        conn.commit()
    finally:
        conn.close()


def get_current_metrics() -> dict:
    """获取当前指标快照"""
    with _lock:
        if _metrics_buffer:
            return dict(_metrics_buffer[-1])
    return {
        "task_completion_rate": 0.0,
        "first_pass_rate": 0.0,
        "human_intervention_rate": 0.0,
        "end_to_end_latency_seconds": 0.0,
    }
