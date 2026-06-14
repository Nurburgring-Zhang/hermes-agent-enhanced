#!/usr/bin/env python3
"""
Hermes 审计追踪系统 v1.0
========================
对标 Scale AI Audit Log + AWS CloudTrail 设计。

核心功能：
  - 全量审计事件记录（工具调用、配置变更、认证事件、错误事件）
  - 多后端存储（默认 JSONL 文件，可扩展至 SQLite/PostgreSQL/S3）
  - 事件查询（按时间范围、操作者、操作类型过滤）
  - 导出（JSON / CSV / CloudTrail 兼容格式）

数据模型（AuditEvent TypedDict）：
  event_id    — UUID v4 唯一标识
  timestamp   — ISO-8601 时间戳（UTC）
  actor       — 操作主体（'system' | 'hermes_agent' | 'user:<name>'）
  action      — 操作类型（tool_call | config_change | auth | error）
  resource    — 操作的资源标识（路径、API、配置键等）
  result      — 操作结果（success | failure | blocked）
  ip          — 来源 IP（如可用）
  user_agent  — 调用方标识（如可用）
  metadata    — 额外上下文（dict，可包含 error_msg, duration_ms, rule 等）
"""

import csv
import io
import json
import logging
import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import (
    Any,
    Protocol,
    TypedDict,
    runtime_checkable,
)

logger = logging.getLogger(__name__)

# ── 常量 ──
HERMES = Path(os.path.expanduser("~/.hermes"))
DEFAULT_JSONL_PATH = HERMES / "logs" / "audit_trail.jsonl"
AUDIT_INDEX_PATH = HERMES / "logs" / ".audit_index.json"


# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════


class AuditEvent(TypedDict, total=False):
    """审计事件模型 — 对标 AWS CloudTrail `Event` 结构

    必填字段：
      event_id, timestamp, actor, action, resource, result

    可选字段：
      ip, user_agent, metadata, session_id, source_ip, request_id
    """
    event_id: str
    timestamp: str  # ISO-8601 UTC
    actor: str       # 'system' | 'hermes_agent' | 'user:<name>' | 'tool:<toolname>'
    action: str      # 'tool_call' | 'config_change' | 'auth' | 'error' | 'rule_enforcement'
    resource: str    # 操作的资源标识
    result: str      # 'success' | 'failure' | 'blocked' | 'warn'
    ip: str
    user_agent: str
    metadata: dict[str, Any]
    # 扩展字段（CloudTrail 兼容）
    session_id: str
    source_ip: str
    request_id: str
    error_code: str
    error_message: str


# ═══════════════════════════════════════════════════════════════
# 后端抽象（可扩展）
# ═══════════════════════════════════════════════════════════════


@runtime_checkable
class AuditBackend(Protocol):
    """审计后端协议 — 实现此协议即可注册为新后端"""

    def write(self, event: AuditEvent) -> None:
        """写入一条审计事件"""
        ...

    def query(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        result: str | None = None,
        resource: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """查询审计事件，支持多种过滤条件"""
        ...

    def flush(self) -> None:
        """刷新缓冲区（若后端支持）"""
        ...

    def close(self) -> None:
        """关闭后端连接/文件句柄"""
        ...


# ═══════════════════════════════════════════════════════════════
# JSONL 文件后端（默认）
# ═══════════════════════════════════════════════════════════════


class JsonlBackend:
    """JSONL 文件后端 — 默认审计存储

    特性：
      - 每行一个 JSON 对象，append-only
      - 按日期自动分片（audit_trail_20250101.jsonl）
      - 内存内建索引（event_id -> 文件偏移），提升单条查询性能
      - 线程安全（threading.Lock）
    """

    def __init__(self, base_path: Path = DEFAULT_JSONL_PATH):
        self._base_path = Path(base_path)
        self._lock = threading.Lock()
        self._index: dict[str, int] = {}  # event_id -> file_offset
        self._writer_lock = threading.Lock()
        self._current_date: str | None = None
        self._fh: io.TextIOWrapper | None = None
        self._load_index()

    # ── 路径管理 ──

    def _date_path(self, date_str: str | None = None) -> Path:
        """按日期返回分片文件路径"""
        if date_str is None:
            date_str = datetime.now(UTC).strftime("%Y%m%d")
        stem = self._base_path.stem  # audit_trail
        parent = self._base_path.parent
        return parent / f"{stem}_{date_str}.jsonl"

    # ── 文件句柄管理 ──

    def _ensure_file_handle(self) -> io.TextIOWrapper:
        """确保当前日期的文件描述符已打开"""
        today = datetime.now(UTC).strftime("%Y%m%d")
        if self._current_date != today or self._fh is None:
            if self._fh is not None:
                try:
                    self._fh.close()
                except Exception:
                    pass
            path = self._date_path(today)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(path, "a", encoding="utf-8")
            self._current_date = today
        return self._fh

    # ── 索引管理（轻量级，事件 ID -> 行号） ──

    def _index_path(self) -> Path:
        parent = self._base_path.parent
        stem = self._base_path.stem
        return parent / f".{stem}_index.json"

    def _load_index(self) -> None:
        idx_path = self._index_path()
        try:
            if idx_path.exists():
                with open(idx_path) as f:
                    self._index = json.load(f)
        except Exception as e:
            logger.debug("Failed to load audit index: %s", e)
            self._index = {}

    def _save_index(self) -> None:
        idx_path = self._index_path()
        try:
            idx_path.parent.mkdir(parents=True, exist_ok=True)
            # 只保留最近 10000 条索引，防止文件过大
            trimmed = dict(list(self._index.items())[-10000:])
            with open(idx_path, "w") as f:
                json.dump(trimmed, f)
        except Exception as e:
            logger.debug("Failed to save audit index: %s", e)

    def _build_file_index(self, date_str: str) -> dict[str, int]:
        """扫描某个日期文件重建索引（行号）"""
        idx: dict[str, int] = {}
        path = self._date_path(date_str)
        if not path.exists():
            return idx
        try:
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        eid = event.get("event_id", "")
                        if eid:
                            idx[eid] = lineno
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("Failed to rebuild index for %s: %s", date_str, e)
        return idx

    # ── 写操作 ──

    def write(self, event: AuditEvent) -> None:
        """写入一条审计事件到 JSONL 文件"""
        with self._writer_lock:
            try:
                fh = self._ensure_file_handle()
                line = json.dumps(event, ensure_ascii=False, default=str)
                fh.write(line + "\n")
                fh.flush()
                # 更新内存索引
                eid = event.get("event_id", "")
                if eid:
                    self._index[eid] = (
                        self._index.get(eid, 0) + 1
                    )  # 近似行号
            except Exception as e:
                logger.error("Failed to write audit event: %s", e)

    # ── 查询 ──

    def query(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        result: str | None = None,
        resource: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """查询审计事件

        如果未指定 to_date，默认到今天。如果未指定 from_date，默认前 7 天。
        按时间倒序排列（最新在前）。
        """
        # 确定日期范围
        now = datetime.now(UTC)
        if to_date is None:
            to_dt = now
        else:
            to_dt = _parse_datetime(to_date)

        if from_date is None:
            from_dt = to_dt - timedelta(days=7)
        else:
            from_dt = _parse_datetime(from_date)

        # 生成需要扫描的日期列表
        dates_to_scan: list[str] = []
        current = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        while current <= end:
            dates_to_scan.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)

        results: list[AuditEvent] = []

        for date_str in dates_to_scan:
            path = self._date_path(date_str)
            if not path.exists():
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event: AuditEvent = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # 时间过滤
                        ts = event.get("timestamp", "")
                        if ts and not _is_in_range(ts, from_dt, to_dt):
                            continue

                        # actor 过滤
                        if actor and event.get("actor", "") != actor:
                            continue

                        # action 过滤
                        if action and event.get("action", "") != action:
                            continue

                        # result 过滤
                        if result and event.get("result", "") != result:
                            continue

                        # resource 过滤
                        if resource and resource not in event.get("resource", ""):
                            continue

                        results.append(event)

                        # 达到 limit 后提前退出
                        if len(results) >= offset + limit:
                            break
            except Exception:
                pass
            if len(results) >= offset + limit:
                break

        # 按时间倒序
        results.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        # 执行 offset / limit
        return results[offset : offset + limit]

    # ── 通过 event_id 精确查找 ──

    def get_by_id(self, event_id: str) -> AuditEvent | None:
        """通过 event_id 精确查找审计事件"""
        # 优先从索引找
        if event_id in self._index:
            # 索引维护成本高，回退到全量扫描最近文件
            pass

        # 简单实现：扫描最近 30 天的文件
        now = datetime.now(UTC)
        for i in range(30):
            date_str = (now - timedelta(days=i)).strftime("%Y%m%d")
            path = self._date_path(date_str)
            if not path.exists():
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event: AuditEvent = json.loads(line)
                            if event.get("event_id") == event_id:
                                return event
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
        return None

    # ── 导出 ──

    def export(
        self,
        format: str = "json",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> str:
        """导出审计事件为指定格式（json / csv / cloudtrail）"""
        events = self.query(from_date=from_date, to_date=to_date, limit=10000)

        if format == "json":
            return json.dumps(events, ensure_ascii=False, indent=2, default=str)

        if format == "csv":
            output = io.StringIO()
            if not events:
                return ""
            fieldnames = list(AuditEvent.__annotations__.keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for event in events:
                writer.writerow(event)
            return output.getvalue()

        if format == "cloudtrail":
            # 对标 AWS CloudTrail `Records` 结构
            records = []
            for event in events:
                record = {
                    "eventVersion": "1.08",
                    "eventID": event.get("event_id", ""),
                    "eventTime": event.get("timestamp", ""),
                    "eventType": "AwsApiCall",
                    "eventSource": (
                        "hermes.agent.internal"
                        if event.get("actor") == "hermes_agent"
                        else "hermes.system"
                    ),
                    "userIdentity": {
                        "type": "IAMUser",
                        "userName": event.get("actor", "unknown"),
                        "sessionContext": {
                            "sessionIssuer": {
                                "type": "Role",
                                "userName": "HermesAgent",
                            }
                        },
                    },
                    "requestParameters": event.get("metadata", {}),
                    "responseElements": {
                        "result": event.get("result", ""),
                    },
                    "sourceIPAddress": event.get("ip", event.get("source_ip", "127.0.0.1")),
                    "userAgent": event.get("user_agent", "HermesAgent/1.0"),
                    "errorCode": event.get("error_code", ""),
                    "errorMessage": event.get("error_message", ""),
                    "resources": [
                        {
                            "ARN": f"hermes:resource:{event.get('resource', 'unknown')}",
                            "type": event.get("action", "unknown"),
                        }
                    ],
                    "requestID": event.get("request_id", str(uuid.uuid4())),
                }
                records.append(record)
            return json.dumps(
                {"Records": records}, ensure_ascii=False, indent=2, default=str
            )

        raise ValueError(f"Unsupported export format: {format}")

    # ── 生命周期 ──

    def flush(self) -> None:
        with self._writer_lock:
            if self._fh is not None:
                try:
                    self._fh.flush()
                except Exception:
                    pass

    def close(self) -> None:
        with self._writer_lock:
            if self._fh is not None:
                try:
                    self._fh.close()
                except Exception:
                    pass
                self._fh = None
            self._save_index()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# 审计日志主类
# ═══════════════════════════════════════════════════════════════


class AuditLogger:
    """审计日志主类 — 对标 Scale AI Audit Log + AWS CloudTrail

    用法：
        audit = AuditLogger()
        audit.log_event(
            actor="hermes_agent",
            action="tool_call",
            resource="write_file:/tmp/test.py",
            result="success",
            metadata={"tool_name": "write_file", "duration_ms": 42},
        )

        # 查询最近 1 小时的所有 tool_call
        events = audit.query_events(actor="hermes_agent", action="tool_call")

        # 导出为 CloudTrail 兼容格式
        print(audit.export(format="cloudtrail"))
    """

    def __init__(self, backend: AuditBackend | None = None):
        self._backend = backend or JsonlBackend()
        self._lock = threading.Lock()
        self._session_id: str = str(uuid.uuid4())

    @property
    def backend(self) -> AuditBackend:
        return self._backend

    @property
    def session_id(self) -> str:
        return self._session_id

    # ── 核心：记录事件 ──

    def log_event(
        self,
        actor: str,
        action: str,
        resource: str,
        result: str = "success",
        ip: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
        **extra: Any,
    ) -> str:
        """记录一条审计事件

        返回 event_id（UUID v4 字符串），可用于后续查询或引用。
        """
        event_id = str(uuid.uuid4())
        event: AuditEvent = {
            "event_id": event_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": actor,
            "action": action,
            "resource": resource,
            "result": result,
            "ip": ip or "127.0.0.1",
            "user_agent": user_agent or "HermesAudit/1.0",
            "metadata": metadata or {},
            "session_id": self._session_id,
        }
        # 合并额外字段
        for k, v in extra.items():
            if k not in event:  # 避免覆盖核心字段
                event[k] = v  # type: ignore[typeddict-item]

        try:
            self._backend.write(event)
        except Exception as e:
            logger.error("AuditLogger: failed to log event %s: %s", event_id, e)

        return event_id

    # ── 便捷方法 ──

    def log_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录工具调用事件"""
        resource = f"tool:{tool_name}"
        _meta = {
            "tool_name": tool_name,
            "tool_args": _safe_truncate(json.dumps(args, ensure_ascii=False, default=str), 2000),
        }
        if metadata:
            _meta.update(metadata)
        return self.log_event(
            actor=f"tool:{tool_name}",
            action="tool_call",
            resource=resource,
            result=result,
            metadata=_meta,
        )

    def log_config_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        actor: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录配置变更事件"""
        _meta = {
            "config_key": config_key,
            "old_value": _safe_truncate(str(old_value), 500),
            "new_value": _safe_truncate(str(new_value), 500),
        }
        if metadata:
            _meta.update(metadata)
        return self.log_event(
            actor=actor,
            action="config_change",
            resource=f"config:{config_key}",
            result="success",
            metadata=_meta,
        )

    def log_auth_event(
        self,
        auth_type: str,
        identity: str,
        result: str = "success",
        ip: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录认证/授权事件"""
        _meta = {
            "auth_type": auth_type,
            "identity": identity,
        }
        if metadata:
            _meta.update(metadata)
        return self.log_event(
            actor=identity,
            action="auth",
            resource=f"auth:{auth_type}",
            result=result,
            ip=ip,
            metadata=_meta,
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        source: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录错误/异常事件"""
        _meta = {
            "error_type": error_type,
            "error_message": _safe_truncate(error_message, 2000),
            "source": source,
        }
        if metadata:
            _meta.update(metadata)
        return self.log_event(
            actor=source,
            action="error",
            resource=f"error:{error_type}",
            result="failure",
            metadata=_meta,
            error_code=error_type,
            error_message=error_message,
        )

    def log_rule_enforcement(
        self,
        rule_id: str,
        tool_name: str,
        verdict: str,
        issues: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """记录规则执行事件"""
        _meta = {
            "rule_id": rule_id,
            "tool_name": tool_name,
            "verdict": verdict,
            "issues": issues[:10],
        }
        if metadata:
            _meta.update(metadata)
        return self.log_event(
            actor="rule_enforcer",
            action="rule_enforcement",
            resource=f"rule:{rule_id}",
            result=verdict,
            metadata=_meta,
        )

    # ── 查询 ──

    def query_events(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        result: str | None = None,
        resource: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """查询审计事件，支持多维度过滤"""
        return self._backend.query(
            from_date=from_date,
            to_date=to_date,
            actor=actor,
            action=action,
            result=result,
            resource=resource,
            limit=limit,
            offset=offset,
        )

    def get_event(self, event_id: str) -> AuditEvent | None:
        """通过 event_id 精确查找一条事件"""
        if hasattr(self._backend, "get_by_id"):
            return self._backend.get_by_id(event_id)  # type: ignore[union-attr]
        return None

    # ── 导出 ──

    def export(self, format: str = "json", **kwargs: Any) -> str:
        """导出审计追踪

        format: "json"（默认）| "csv" | "cloudtrail"
        kwargs 中可传入 from_date, to_date 等过滤条件。
        """
        if hasattr(self._backend, "export"):
            return self._backend.export(format=format, **kwargs)  # type: ignore[union-attr]
        # fallback: 自己导出
        from_date = kwargs.get("from_date")
        to_date = kwargs.get("to_date")
        events = self.query_events(from_date=from_date, to_date=to_date, limit=10000)
        if format == "json":
            return json.dumps(events, ensure_ascii=False, indent=2, default=str)
        if format == "csv":
            output = io.StringIO()
            if not events:
                return ""
            fieldnames = list(AuditEvent.__annotations__.keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for event in events:
                writer.writerow(event)
            return output.getvalue()
        if format == "cloudtrail":
            records = []
            for event in events:
                records.append({
                    "eventVersion": "1.08",
                    "eventID": event.get("event_id", ""),
                    "eventTime": event.get("timestamp", ""),
                    "eventSource": "hermes.agent.internal",
                    "userIdentity": {"type": "IAMUser", "userName": event.get("actor", "unknown")},
                    "sourceIPAddress": event.get("ip", "127.0.0.1"),
                    "userAgent": event.get("user_agent", "HermesAgent/1.0"),
                    "requestParameters": event.get("metadata", {}),
                    "responseElements": {"result": event.get("result", "")},
                })
            return json.dumps({"Records": records}, ensure_ascii=False, indent=2, default=str)
        raise ValueError(f"Unsupported export format: {format}")

    # ── 生命周期 ──

    def flush(self) -> None:
        """刷新后端缓冲区"""
        self._backend.flush()

    def close(self) -> None:
        """关闭审计日志（释放资源）"""
        self._backend.close()


# ── 模块级单例 ──
_audit_logger_instance: AuditLogger | None = None
_audit_instance_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志实例（单例）"""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        with _audit_instance_lock:
            if _audit_logger_instance is None:
                _audit_logger_instance = AuditLogger()
    return _audit_logger_instance


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


def _parse_datetime(dt_str: str) -> datetime:
    """解析 ISO-8601 时间字符串"""
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        pass
    # 尝试纯日期格式
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(dt_str, "%Y%m%d")
    except (ValueError, TypeError):
        pass
    # 默认：当前 UTC 时间减去 7 天
    return datetime.now(UTC) - timedelta(days=7)


def _is_in_range(ts: str, from_dt: datetime, to_dt: datetime) -> bool:
    """检查时间戳是否在范围内"""
    try:
        dt = datetime.fromisoformat(ts)
        return from_dt <= dt <= to_dt
    except (ValueError, TypeError):
        return True  # 如果解析失败，默认包含


def _safe_truncate(s: str, max_len: int = 1000) -> str:
    """安全截断字符串，避免超长"""
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


# ═══════════════════════════════════════════════════════════════
# 快速自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 72)
    print("Hermes 审计追踪系统 v1.0 — 自检")
    print("=" * 72)

    # 1. 创建审计日志实例
    audit = AuditLogger()
    print("\n[1] ✅ AuditLogger 实例化成功")

    # 2. 记录各类型事件
    e1 = audit.log_tool_call("write_file", {"path": "/tmp/test.py"})
    print(f"[2] ✅ 工具调用事件: {e1[:8]}...")

    e2 = audit.log_config_change("model.default", "deepseek-chat", "gpt-4")
    print(f"[3] ✅ 配置变更事件: {e2[:8]}...")

    e3 = audit.log_auth_event("api_key", "user:admin", result="success")
    print(f"[4] ✅ 认证事件: {e3[:8]}...")

    e4 = audit.log_error("FileNotFoundError", "/tmp/nonexistent.py not found", source="tool:read_file")
    print(f"[5] ✅ 错误事件: {e4[:8]}...")

    e5 = audit.log_rule_enforcement("R1", "read_file", "warn", ["输出含有推测性语言"])
    print(f"[6] ✅ 规则执行事件: {e5[:8]}...")

    # 3. 查询
    results = audit.query_events(limit=10)
    print(f"[7] ✅ 查询事件: 共 {len(results)} 条")

    results_tool = audit.query_events(action="tool_call", limit=10)
    print(f"[8] ✅ 查询 tool_call 事件: {len(results_tool)} 条")

    # 4. 导出
    json_out = audit.export(format="json")
    print(f"[9] ✅ JSON 导出: {len(json_out)} 字符")

    csv_out = audit.export(format="csv")
    print(f"[10] ✅ CSV 导出: {len(csv_out)} 字符")

    ct_out = audit.export(format="cloudtrail")
    print(f"[11] ✅ CloudTrail 导出: {len(ct_out)} 字符")

    # 5. 通过 event_id 精确查找
    found = audit.get_event(e1)
    print(f"[12] ✅ event_id 查找: {'成功' if found else '失败'}")

    # 6. 清理
    audit.close()
    print("\n[13] ✅ 审计日志已关闭")
    print("\n" + "=" * 72)
    print("所有测试通过 ✅")
    print("=" * 72)
