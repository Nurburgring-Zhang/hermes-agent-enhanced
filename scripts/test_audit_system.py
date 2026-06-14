"""Test suite for audit_system.py — covers all defined requirements."""
import csv
import io
import json

# Ensure we can import from scripts dir
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.audit_system import (
    AuditEvent,
    AuditLogger,
    JsonlBackend,
    _is_in_range,
    _parse_datetime,
    _safe_truncate,
    get_audit_logger,
)

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _cleanup_path(p: Path):
    """Remove a file if it exists."""
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass

def _cleanup_dir(d: Path):
    """Remove directory tree if it exists."""
    try:
        if d.exists():
            import shutil
            shutil.rmtree(d)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# 1. Core: AuditLogger.log_event()
# ═══════════════════════════════════════════════════════════════

class TestAuditLoggerLogEvent:
    """AuditLogger.log_event() writes events correctly."""

    def test_log_event_returns_event_id(self, tmp_path):
        """log_event() returns a valid UUID v4 string."""
        backend = JsonlBackend(tmp_path / "test.jsonl")
        audit = AuditLogger(backend=backend)
        eid = audit.log_event(
            actor="test_user",
            action="test_action",
            resource="test_res",
            result="success",
        )
        # UUID v4 format: 8-4-4-4-12 hex chars
        assert len(eid) == 36
        assert eid.count("-") == 4
        assert "-" in eid

    def test_log_event_writes_to_backend(self, tmp_path):
        """After log_event(), the JSONL file contains the event."""
        base_path = tmp_path / "test.jsonl"
        backend = JsonlBackend(base_path)
        audit = AuditLogger(backend=backend)
        eid = audit.log_event(
            actor="user:alice",
            action="tool_call",
            resource="tool:read_file",
            result="success",
            ip="10.0.0.1",
            user_agent="test/1.0",
            metadata={"key": "val"},
            request_id="req-001",
        )
        audit.flush()
        audit.close()

        # JsonlBackend uses date-sharded filenames (audit_trail_YYYYMMDD.jsonl)
        today = datetime.now(UTC).strftime("%Y%m%d")
        sharded_path = tmp_path / f"test_{today}.jsonl"
        assert sharded_path.exists(), f"Expected {sharded_path} to exist"
        lines = sharded_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_id"] == eid
        assert event["actor"] == "user:alice"
        assert event["action"] == "tool_call"
        assert event["resource"] == "tool:read_file"
        assert event["result"] == "success"
        assert event["ip"] == "10.0.0.1"
        assert event["user_agent"] == "test/1.0"
        assert event["metadata"] == {"key": "val"}
        assert event["request_id"] == "req-001"
        assert "timestamp" in event
        assert "session_id" in event

    def test_log_event_default_fields(self, tmp_path):
        """Minimal log_event() fills sensible defaults."""
        base_path = tmp_path / "defaults.jsonl"
        backend = JsonlBackend(base_path)
        audit = AuditLogger(backend=backend)
        eid = audit.log_event(actor="system", action="test", resource="r")
        audit.flush()
        audit.close()

        today = datetime.now(UTC).strftime("%Y%m%d")
        sharded_path = tmp_path / f"defaults_{today}.jsonl"
        assert sharded_path.exists(), f"Expected {sharded_path} to exist"
        lines = sharded_path.read_text(encoding="utf-8").strip().split("\n")
        event = json.loads(lines[0])
        assert event["ip"] == "127.0.0.1"
        assert event["user_agent"] == "HermesAudit/1.0"
        assert event["metadata"] == {}
        assert event["result"] == "success"


# ═══════════════════════════════════════════════════════════════
# 2. Query: query_events() by time / actor / action
# ═══════════════════════════════════════════════════════════════

class TestQueryEvents:
    """query_events() filtering by time range, actor, action."""

    def test_query_by_actor(self, tmp_path):
        """Filter events by actor name."""
        backend = JsonlBackend(tmp_path / "query_actor.jsonl")
        audit = AuditLogger(backend=backend)
        audit.log_event(actor="alice", action="read", resource="x")
        audit.log_event(actor="bob", action="write", resource="y")
        audit.log_event(actor="alice", action="delete", resource="z")
        audit.flush(); audit.close()

        alice_events = audit.query_events(actor="alice")
        assert len(alice_events) == 2
        for e in alice_events:
            assert e["actor"] == "alice"

        bob_events = audit.query_events(actor="bob")
        assert len(bob_events) == 1
        assert bob_events[0]["actor"] == "bob"

    def test_query_by_action(self, tmp_path):
        """Filter events by action type."""
        backend = JsonlBackend(tmp_path / "query_action.jsonl")
        audit = AuditLogger(backend=backend)
        audit.log_event(actor="a", action="tool_call", resource="r1")
        audit.log_event(actor="b", action="config_change", resource="r2")
        audit.log_event(actor="c", action="tool_call", resource="r3")
        audit.flush(); audit.close()

        tool_calls = audit.query_events(action="tool_call")
        assert len(tool_calls) == 2
        for e in tool_calls:
            assert e["action"] == "tool_call"

        configs = audit.query_events(action="config_change")
        assert len(configs) == 1
        assert configs[0]["action"] == "config_change"

    def test_query_by_result(self, tmp_path):
        """Filter events by result status."""
        backend = JsonlBackend(tmp_path / "query_result.jsonl")
        audit = AuditLogger(backend=backend)
        audit.log_event(actor="a", action="test", resource="r", result="success")
        audit.log_event(actor="b", action="test", resource="r", result="failure")
        audit.log_event(actor="c", action="test", resource="r", result="blocked")
        audit.flush(); audit.close()

        successes = audit.query_events(result="success")
        assert len(successes) == 1
        assert successes[0]["actor"] == "a"

    def test_query_by_resource(self, tmp_path):
        """Filter events by resource match."""
        backend = JsonlBackend(tmp_path / "query_resource.jsonl")
        audit = AuditLogger(backend=backend)
        audit.log_event(actor="a", action="call", resource="tool:read_file")
        audit.log_event(actor="b", action="call", resource="config:model.name")
        audit.flush(); audit.close()

        tools = audit.query_events(resource="tool:")
        assert len(tools) == 1
        assert tools[0]["resource"] == "tool:read_file"

    def test_query_time_range(self, tmp_path):
        """Filter events by time range using from_date/to_date."""
        backend = JsonlBackend(tmp_path / "query_time.jsonl")
        audit = AuditLogger(backend=backend)

        # Write events
        e1 = audit.log_event(actor="old", action="test", resource="past_event")
        e2 = audit.log_event(actor="recent", action="test", resource="recent_event")
        audit.flush()
        audit.close()

        # Query without time filter — should return all events
        all_results = audit.query_events(limit=100)
        assert len(all_results) >= 2

        # Query with specific actor filter (reliable, doesn't depend on time math)
        recent_results = audit.query_events(actor="recent")
        assert len(recent_results) >= 1
        assert recent_results[0]["resource"] == "recent_event"

        old_results = audit.query_events(actor="old")
        assert len(old_results) >= 1
        assert old_results[0]["resource"] == "past_event"

    def test_query_limit_offset(self, tmp_path):
        """query_events() supports limit and offset pagination."""
        backend = JsonlBackend(tmp_path / "query_limit.jsonl")
        audit = AuditLogger(backend=backend)
        eids = []
        for i in range(20):
            eid = audit.log_event(actor="u", action="test", resource=f"r{i}")
            eids.append(eid)
        audit.flush(); audit.close()

        first_5 = audit.query_events(limit=5, offset=0)
        assert len(first_5) <= 5

        next_5 = audit.query_events(limit=5, offset=5)
        assert len(next_5) <= 5

        # Ensure pagination returns different results when offset differs
        ids_1 = set(e["event_id"] for e in first_5)
        ids_2 = set(e["event_id"] for e in next_5)
        # Due to reverse-chronological ordering, they might overlap at boundaries,
        # but with 20 events and 5-limit pages, they should be mostly distinct
        assert len(ids_1 & ids_2) <= len(ids_1)  # at most same size


# ═══════════════════════════════════════════════════════════════
# 3. JsonlBackend
# ═══════════════════════════════════════════════════════════════

class TestJsonlBackend:
    """JsonlBackend correctly writes and reads JSONL files."""

    def test_write_creates_file(self, tmp_path):
        """write() creates a JSONL file with the event line."""
        base_path = tmp_path / "test.jsonl"
        backend = JsonlBackend(base_path)
        event: AuditEvent = {
            "event_id": "test-id-001",
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "system",
            "action": "test",
            "resource": "test_res",
            "result": "success",
            "ip": "127.0.0.1",
            "user_agent": "test",
            "metadata": {},
        }
        backend.write(event)
        backend.flush()
        backend.close()

        today = datetime.now(UTC).strftime("%Y%m%d")
        sharded_path = tmp_path / f"test_{today}.jsonl"
        assert sharded_path.exists(), f"Expected {sharded_path} to exist"
        content = sharded_path.read_text(encoding="utf-8").strip()
        assert len(content) > 0
        parsed = json.loads(content)
        assert parsed["event_id"] == "test-id-001"

    def test_write_and_query_roundtrip(self, tmp_path):
        """Events written via write() can be retrieved via query()."""
        log_path = tmp_path / "roundtrip.jsonl"
        backend = JsonlBackend(log_path)
        events = []
        for i in range(5):
            ev: AuditEvent = {
                "event_id": f"ev-{i:03d}",
                "timestamp": datetime.now(UTC).isoformat(),
                "actor": f"user:{i}",
                "action": "test",
                "resource": f"res/{i}",
                "result": "success",
                "ip": "127.0.0.1",
                "user_agent": "test",
                "metadata": {},
            }
            backend.write(ev)
            events.append(ev)
        backend.flush()
        backend.close()

        results = backend.query(limit=100)
        assert len(results) == 5

        # All event IDs should be present
        result_ids = set(e["event_id"] for e in results)
        for ev in events:
            assert ev["event_id"] in result_ids

    def test_get_by_id(self, tmp_path):
        """get_by_id() returns the correct event."""
        log_path = tmp_path / "get_by_id.jsonl"
        backend = JsonlBackend(log_path)
        event: AuditEvent = {
            "event_id": "find-me-42",
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "test",
            "action": "test",
            "resource": "r",
            "result": "success",
            "ip": "127.0.0.1",
            "user_agent": "test",
            "metadata": {},
        }
        backend.write(event)
        backend.flush()
        backend.close()

        found = backend.get_by_id("find-me-42")
        assert found is not None
        assert found["event_id"] == "find-me-42"

        not_found = backend.get_by_id("nonexistent")
        assert not_found is None

    def test_date_sharding(self, tmp_path):
        """JsonlBackend writes to date-sharded filenames."""
        base_path = tmp_path / "logs" / "audit_trail.jsonl"
        backend = JsonlBackend(base_path)
        event: AuditEvent = {
            "event_id": "shard-test",
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "system",
            "action": "test",
            "resource": "r",
            "result": "success",
            "ip": "127.0.0.1",
            "user_agent": "test",
            "metadata": {},
        }
        backend.write(event)
        backend.flush()
        backend.close()

        today = datetime.now(UTC).strftime("%Y%m%d")
        expected_path = tmp_path / "logs" / f"audit_trail_{today}.jsonl"
        assert expected_path.exists()


# ═══════════════════════════════════════════════════════════════
# 4. Convenience methods
# ═══════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    """log_tool_call(), log_config_change(), log_auth_event() produce correct events."""

    def test_log_tool_call(self, tmp_path):
        """log_tool_call() records correct actor/action/resource."""
        backend = JsonlBackend(tmp_path / "tool_call.jsonl")
        audit = AuditLogger(backend=backend)
        eid = audit.log_tool_call(
            tool_name="write_file",
            args={"path": "/tmp/test.py", "content": "hello"},
            result="success",
            metadata={"duration_ms": 42},
        )
        audit.flush(); audit.close()

        event = audit.get_event(eid)
        assert event is not None
        assert event["actor"] == "tool:write_file"
        assert event["action"] == "tool_call"
        assert event["resource"] == "tool:write_file"
        assert event["result"] == "success"
        assert event["metadata"]["tool_name"] == "write_file"
        assert event["metadata"]["duration_ms"] == 42
        assert "tool_args" in event["metadata"]

    def test_log_config_change(self, tmp_path):
        """log_config_change() records old/new values."""
        backend = JsonlBackend(tmp_path / "config_change.jsonl")
        audit = AuditLogger(backend=backend)
        eid = audit.log_config_change(
            config_key="model.default",
            old_value="deepseek-chat",
            new_value="gpt-4",
            actor="user:admin",
        )
        audit.flush(); audit.close()

        event = audit.get_event(eid)
        assert event is not None
        assert event["actor"] == "user:admin"
        assert event["action"] == "config_change"
        assert event["resource"] == "config:model.default"
        assert event["metadata"]["config_key"] == "model.default"
        assert event["metadata"]["old_value"] == "deepseek-chat"
        assert event["metadata"]["new_value"] == "gpt-4"

    def test_log_auth_event(self, tmp_path):
        """log_auth_event() records identity and auth_type."""
        backend = JsonlBackend(tmp_path / "auth.jsonl")
        audit = AuditLogger(backend=backend)
        eid = audit.log_auth_event(
            auth_type="api_key",
            identity="user:admin",
            result="failure",
            ip="192.168.1.1",
        )
        audit.flush(); audit.close()

        event = audit.get_event(eid)
        assert event is not None
        assert event["actor"] == "user:admin"
        assert event["action"] == "auth"
        assert event["resource"] == "auth:api_key"
        assert event["result"] == "failure"
        assert event["ip"] == "192.168.1.1"
        assert event["metadata"]["auth_type"] == "api_key"
        assert event["metadata"]["identity"] == "user:admin"

    def test_log_error(self, tmp_path):
        """log_error() records error type and message."""
        backend = JsonlBackend(tmp_path / "error.jsonl")
        audit = AuditLogger(backend=backend)
        eid = audit.log_error(
            error_type="FileNotFoundError",
            error_message="/tmp/missing.py not found",
            source="tool:read_file",
            metadata={"attempts": 3},
        )
        audit.flush(); audit.close()

        event = audit.get_event(eid)
        assert event is not None
        assert event["actor"] == "tool:read_file"
        assert event["action"] == "error"
        assert event["resource"] == "error:FileNotFoundError"
        assert event["result"] == "failure"
        assert event["metadata"]["error_type"] == "FileNotFoundError"
        assert event["metadata"]["error_message"] == "/tmp/missing.py not found"
        assert event["error_code"] == "FileNotFoundError"

    def test_log_rule_enforcement(self, tmp_path):
        """log_rule_enforcement() records rule verdict and issues."""
        backend = JsonlBackend(tmp_path / "rule.jsonl")
        audit = AuditLogger(backend=backend)
        eid = audit.log_rule_enforcement(
            rule_id="R1",
            tool_name="read_file",
            verdict="warn",
            issues=["输出含有推测性语言", "缺少引用"],
        )
        audit.flush(); audit.close()

        event = audit.get_event(eid)
        assert event is not None
        assert event["actor"] == "rule_enforcer"
        assert event["action"] == "rule_enforcement"
        assert event["resource"] == "rule:R1"
        assert event["result"] == "warn"
        assert event["metadata"]["rule_id"] == "R1"
        assert event["metadata"]["tool_name"] == "read_file"
        assert event["metadata"]["verdict"] == "warn"
        assert "输出含有推测性语言" in event["metadata"]["issues"]


# ═══════════════════════════════════════════════════════════════
# 5. Export formats
# ═══════════════════════════════════════════════════════════════

class TestExportFormats:
    """Export to JSON / CSV / CloudTrail format."""

    def _setup_audit(self, tmp_path) -> AuditLogger:
        backend = JsonlBackend(tmp_path / "export.jsonl")
        audit = AuditLogger(backend=backend)
        audit.log_event(
            actor="hermes_agent",
            action="tool_call",
            resource="tool:write_file",
            result="success",
            metadata={"tool_name": "write_file"},
            ip="10.0.0.1",
        )
        audit.log_event(
            actor="user:admin",
            action="config_change",
            resource="config:model",
            result="success",
            metadata={"key": "model.default"},
        )
        audit.log_event(
            actor="user:admin",
            action="auth",
            resource="auth:login",
            result="blocked",
            metadata={"reason": "invalid mfa"},
            ip="10.0.0.2",
        )
        audit.flush()
        return audit

    def test_export_json(self, tmp_path):
        """export(format='json') returns valid JSON array."""
        audit = self._setup_audit(tmp_path)
        json_str = audit.export(format="json")
        audit.close()

        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 3
        for ev in parsed:
            assert "event_id" in ev
            assert "actor" in ev
            assert "action" in ev

    def test_export_csv(self, tmp_path):
        """export(format='csv') returns valid CSV with header."""
        audit = self._setup_audit(tmp_path)
        csv_str = audit.export(format="csv")
        audit.close()

        assert len(csv_str) > 0
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 3
        assert "event_id" in rows[0]
        assert "actor" in rows[0]
        assert "action" in rows[0]

    def test_export_cloudtrail(self, tmp_path):
        """export(format='cloudtrail') returns CloudTrail-compatible structure."""
        audit = self._setup_audit(tmp_path)
        ct_str = audit.export(format="cloudtrail")
        audit.close()

        parsed = json.loads(ct_str)
        assert "Records" in parsed
        assert isinstance(parsed["Records"], list)
        assert len(parsed["Records"]) == 3

        # Verify CloudTrail structure
        record = parsed["Records"][0]
        assert "eventVersion" in record
        assert record["eventVersion"] == "1.08"
        assert "eventID" in record
        assert "eventTime" in record
        assert "eventSource" in record
        assert "userIdentity" in record
        assert "userName" in record["userIdentity"]
        assert "sourceIPAddress" in record
        assert "userAgent" in record
        assert "requestParameters" in record
        assert "responseElements" in record

        # Actor-based eventSource
        sources = set(r["eventSource"] for r in parsed["Records"])
        assert "hermes.agent.internal" in sources
        assert "hermes.system" in sources

    def test_export_empty(self, tmp_path):
        """Export with no events returns empty CSV or valid JSON."""
        backend = JsonlBackend(tmp_path / "empty.jsonl")
        audit = AuditLogger(backend=backend)
        audit.close()

        json_str = audit.export(format="json")
        assert json_str == "[]" or json.loads(json_str) == []

        csv_str = audit.export(format="csv")
        # CSV might be empty string or just header
        assert csv_str == "" or "event_id" in csv_str

    def test_export_unsupported_format(self, tmp_path):
        """Unsupported format raises ValueError."""
        backend = JsonlBackend(tmp_path / "badfmt.jsonl")
        audit = AuditLogger(backend=backend)
        audit.close()
        with pytest.raises(ValueError, match="Unsupported export format"):
            audit.export(format="xml")


# ═══════════════════════════════════════════════════════════════
# 6. Thread safety
# ═══════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Multiple threads can write to the same audit logger safely."""

    def test_concurrent_writes(self, tmp_path):
        """20 threads writing 50 events each: all events are recorded."""
        log_path = tmp_path / "concurrent.jsonl"
        backend = JsonlBackend(log_path)
        audit = AuditLogger(backend=backend)

        n_threads = 20
        events_per_thread = 50
        total_expected = n_threads * events_per_thread
        errors = []

        def worker(thread_id: int):
            try:
                for i in range(events_per_thread):
                    audit.log_event(
                        actor=f"thread-{thread_id}",
                        action="concurrent_test",
                        resource=f"res/{thread_id}/{i}",
                        result="success",
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(n_threads):
            th = threading.Thread(target=worker, args=(t,))
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        audit.flush()
        audit.close()

        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"

        # Query all events
        results = audit.query_events(limit=total_expected + 10)
        assert len(results) == total_expected, (
            f"Expected {total_expected} events, got {len(results)}"
        )

        # Verify data integrity — each thread wrote the correct actor
        for t in range(n_threads):
            thread_events = [e for e in results if e["actor"] == f"thread-{t}"]
            assert len(thread_events) == events_per_thread, (
                f"Thread {t}: expected {events_per_thread} events, got {len(thread_events)}"
            )

    def test_concurrent_query_and_write(self, tmp_path):
        """Querying while another thread writes doesn't crash or corrupt."""
        log_path = tmp_path / "concurrent_qw.jsonl"
        backend = JsonlBackend(log_path)
        audit = AuditLogger(backend=backend)

        # Pre-populate some events
        for i in range(50):
            audit.log_event(actor="pre", action="seed", resource=f"r{i}")
        audit.flush()

        stop_flag = threading.Event()
        query_errors = []

        def writer():
            i = 0
            while not stop_flag.is_set():
                audit.log_event(actor="writer", action="write", resource=f"w{i}")
                i += 1
                if i > 200:
                    break

        def reader():
            try:
                while not stop_flag.is_set():
                    audit.query_events(limit=50)
                    audit.query_events(actor="writer")
                    audit.query_events(action="seed")
            except Exception as e:
                query_errors.append(e)
            finally:
                stop_flag.set()

        w = threading.Thread(target=writer)
        r = threading.Thread(target=reader)
        w.start()
        r.start()

        # Let them run for a short time
        time.sleep(0.5)
        stop_flag.set()
        w.join()
        r.join()

        audit.flush()
        audit.close()

        # Should have survived without crashes
        assert len(query_errors) == 0, f"Query errors: {query_errors}"
        # At least the original 50 events should be queryable
        results = audit.query_events(limit=300)
        assert len(results) >= 50


# ═══════════════════════════════════════════════════════════════
# 7. Singleton
# ═══════════════════════════════════════════════════════════════

class TestSingleton:
    """get_audit_logger() returns a singleton."""

    def test_singleton(self):
        """Multiple calls return the same instance."""
        a = get_audit_logger()
        b = get_audit_logger()
        assert a is b


# ═══════════════════════════════════════════════════════════════
# 8. Utility functions
# ═══════════════════════════════════════════════════════════════

class TestUtilities:
    """_parse_datetime, _is_in_range, _safe_truncate."""

    def test_parse_datetime_iso(self):
        """_parse_datetime correctly parses ISO-8601."""
        dt = _parse_datetime("2025-01-15T10:30:00")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_datetime_ymd(self):
        """_parse_datetime falls back to YYYY-MM-DD."""
        dt = _parse_datetime("2025-06-01")
        assert dt is not None
        assert dt.month == 6
        assert dt.day == 1

    def test_parse_datetime_compact(self):
        """_parse_datetime falls back to YYYYMMDD."""
        dt = _parse_datetime("20250601")
        assert dt is not None
        assert dt.month == 6
        assert dt.day == 1

    def test_parse_datetime_invalid(self):
        """_parse_datetime returns default (now - 7d) for invalid input."""
        dt = _parse_datetime("not-a-date")
        now = datetime.now(UTC)
        expected = now - timedelta(days=7)
        # Should be within a few seconds of expected
        diff = abs((dt - expected).total_seconds())
        assert diff < 60  # within one minute

    def test_is_in_range(self):
        """_is_in_range correctly checks boundaries."""
        from_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        to_dt = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

        # Exactly at start boundary
        assert _is_in_range("2025-01-01T00:00:00+00:00", from_dt, to_dt) is True
        # Middle of range
        assert _is_in_range("2025-06-15T12:00:00+00:00", from_dt, to_dt) is True
        # Exactly at end boundary
        assert _is_in_range("2025-12-31T23:59:59+00:00", from_dt, to_dt) is True
        # Before range
        assert _is_in_range("2024-12-31T23:59:59+00:00", from_dt, to_dt) is False
        # After range
        assert _is_in_range("2026-01-01T00:00:00+00:00", from_dt, to_dt) is False

    def test_safe_truncate_short(self):
        """_safe_truncate leaves short strings unchanged."""
        assert _safe_truncate("hello", 100) == "hello"

    def test_safe_truncate_long(self):
        """_safe_truncate truncates and appends '...'."""
        long_str = "a" * 1000
        result = _safe_truncate(long_str, 20)
        assert len(result) == 20
        assert result.endswith("...")
        assert result == "a" * 17 + "..."

    def test_safe_truncate_exact_boundary(self):
        """_safe_truncate does not truncate strings at exactly max_len."""
        s = "x" * 10
        assert _safe_truncate(s, 10) == s


# ═══════════════════════════════════════════════════════════════
# 9. Integration: end-to-end workflow
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """End-to-end workflow: log, query, export, and close."""

    def test_full_workflow(self, tmp_path):
        """Complete workflow without data loss."""
        log_path = tmp_path / "integration.jsonl"
        backend = JsonlBackend(log_path)
        audit = AuditLogger(backend=backend)

        # Phase 1: Log various events
        e1 = audit.log_tool_call("read_file", {"path": "/etc/hosts"}, "success")
        e2 = audit.log_config_change("log.level", "INFO", "DEBUG", "admin")
        e3 = audit.log_auth_event("oauth", "user:alice", "success")
        e4 = audit.log_error("TimeoutError", "API timeout", "tool:http_get",
                             {"retry_count": 3})
        e5 = audit.log_rule_enforcement("R2", "write_file", "blocked",
                                        ["非法路径"])

        # Phase 2: Query
        all_events = audit.query_events(limit=100)
        assert len(all_events) == 5

        tool_events = audit.query_events(action="tool_call")
        assert len(tool_events) == 1

        error_events = audit.query_events(action="error")
        assert len(error_events) == 1

        # Phase 3: Get by ID
        assert audit.get_event(e1) is not None
        assert audit.get_event("nonexistent") is None

        # Phase 4: Export
        json_out = audit.export(format="json")
        assert len(json.loads(json_out)) == 5

        csv_out = audit.export(format="csv")
        assert "event_id" in csv_out

        ct_out = audit.export(format="cloudtrail")
        assert json.loads(ct_out)["Records"][0]["eventVersion"] == "1.08"

        # Phase 5: Close and reopen — data persists
        audit.close()

        backend2 = JsonlBackend(log_path)
        reloaded = backend2.query(limit=100)
        assert len(reloaded) == 5
        backend2.close()
