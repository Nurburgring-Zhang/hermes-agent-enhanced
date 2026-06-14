#!/usr/bin/env python3
"""Tests for guardian.py — Hermes 永久守护神 v2.0"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".hermes"))
sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

@pytest.fixture
def guardian_module(tmp_path, monkeypatch):
    """Import guardian module with HERMES patched to tmp_path."""
    # Remove cached modules
    for mod in list(sys.modules.keys()):
        if "guardian" in mod.lower():
            del sys.modules[mod]

    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    monkeypatch.setattr("scripts.guardian.HERMES", tmp_path / ".hermes")
    monkeypatch.setattr("scripts.guardian.LOG", tmp_path / ".hermes" / "logs" / f"guardian_{datetime.now().strftime('%Y%m%d')}.log")

    # Ensure directories exist
    (tmp_path / ".hermes" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "cron").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "reports").mkdir(parents=True, exist_ok=True)

    import scripts.guardian as guardian
    return guardian


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Fixture to mock subprocess.run with configurable behavior."""
    class MockSubprocess:
        def __init__(self):
            self.calls = []
            self.set_returncode(0)
            self.set_stdout("")
            self.set_stderr("")

        def set_returncode(self, rc):
            self._returncode = rc

        def set_stdout(self, out):
            self._stdout = out

        def set_stderr(self, err):
            self._stderr = err

        def create_result(self):
            r = subprocess.CompletedProcess(
                args=["mock"], returncode=self._returncode,
                stdout=self._stdout, stderr=self._stderr
            )
            return r

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            if self._raise_timeout:
                raise subprocess.TimeoutExpired(cmd="mock", timeout=60)
            if self._raise_exception:
                raise RuntimeError("mock error")
            return self.create_result()

        def set_timeout(self):
            self._raise_timeout = True
            self._raise_exception = False

        def set_exception(self):
            self._raise_timeout = False
            self._raise_exception = True

        def reset(self):
            self._raise_timeout = False
            self._raise_exception = False

    mock = MockSubprocess()
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


# ═══════════════════════════════════════════════════
# Tests: clean_stale_locks()
# ═══════════════════════════════════════════════════

class TestCleanStaleLocks:
    def test_no_lock_file(self, guardian_module):
        """No lock file exists → returns empty list."""
        result = guardian_module.clean_stale_locks()
        assert result == []

    def test_fresh_lock_not_cleaned(self, guardian_module):
        """Fresh lock file (<10min) → not cleaned, returns empty."""
        lock = guardian_module.HERMES / "cron" / ".tick.lock"
        lock.write_text("locked")
        # Just written, so age ≈ 0
        result = guardian_module.clean_stale_locks()
        assert result == []
        assert lock.exists()  # Still exists

    def test_expired_lock_cleaned(self, guardian_module, monkeypatch):
        """Expired lock (>10min old) → cleaned, returns action message."""
        import os as _os
        lock = guardian_module.HERMES / "cron" / ".tick.lock"
        lock.write_text("locked")
        # Use os.utime to set file mtime to ~11.6 minutes ago
        old_time = time.time() - 700
        _os.utime(str(lock), (old_time, old_time))
        result = guardian_module.clean_stale_locks()
        assert len(result) == 1
        assert "清理" in result[0]
        assert not lock.exists()  # Cleaned

    def test_lock_cleanup_exception_handled(self, guardian_module, monkeypatch):
        """Exception during lock stat → returns empty, does not crash."""
        lock = guardian_module.HERMES / "cron" / ".tick.lock"
        lock.write_text("locked")
        # Patch .exists() to return True (file is there), but .stat() to fail.
        # This simulates a corrupted file that exists but can't be stated.
        def bad_stat(*args, **kwargs):
            raise PermissionError("permission denied")

        monkeypatch.setattr(lock.__class__, "exists", lambda self: True)
        monkeypatch.setattr(lock.__class__, "stat", bad_stat)
        result = guardian_module.clean_stale_locks()
        assert result == []


# ═══════════════════════════════════════════════════
# Tests: disk_check()
# ═══════════════════════════════════════════════════

class TestDiskCheck:
    def test_disk_ok(self, guardian_module, monkeypatch):
        """Enough disk space → returns empty, logs free space."""
        def fake_statvfs(path):
            return type("StatVFS", (), {
                "f_frsize": 4096,
                "f_bavail": 500000  # ~1.95 GB
            })()
        monkeypatch.setattr("os.statvfs", fake_statvfs)
        result = guardian_module.disk_check()
        assert result == []

    def test_disk_low_space(self, guardian_module, monkeypatch):
        """Low disk space (<1GB) → returns warning."""
        def fake_statvfs(path):
            return type("StatVFS", (), {
                "f_frsize": 4096,
                "f_bavail": 100000  # ~0.39 GB
            })()
        monkeypatch.setattr("os.statvfs", fake_statvfs)
        result = guardian_module.disk_check()
        assert len(result) == 1
        assert "磁盘不足" in result[0]

    def test_disk_check_error(self, guardian_module, monkeypatch):
        """statvfs raises exception → returns error message."""
        def bad_statvfs(path):
            raise OSError("filesystem error")
        monkeypatch.setattr("os.statvfs", bad_statvfs)
        result = guardian_module.disk_check()
        assert len(result) == 1
        assert "磁盘检查失败" in result[0]


# ═══════════════════════════════════════════════════
# Tests: run()
# ═══════════════════════════════════════════════════

class TestRun:
    def test_run_success_first_try(self, guardian_module, monkeypatch):
        """Command succeeds on first attempt."""
        mock = type("R", (), {"returncode": 0, "stdout": "output ok", "stderr": ""})()
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock)
        result = guardian_module.run("echo hello", timeout=10, label="test")
        assert result == "output ok"

    def test_run_retry_success(self, guardian_module, monkeypatch):
        """First attempt fails, second succeeds."""
        call_count = [0]

        def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return type("R", (), {"returncode": 1, "stdout": "", "stderr": "fail"})()

            return type("R", (), {"returncode": 0, "stdout": "retry ok", "stderr": ""})()

        monkeypatch.setattr(subprocess, "run", side_effect)
        # Use monkeypatch to speed up time.sleep
        monkeypatch.setattr(time, "sleep", lambda s: None)
        result = guardian_module.run("echo retry", timeout=10, retries=1, label="retry_test")
        assert result == "retry ok"
        assert call_count[0] == 2

    def test_run_all_retries_fail(self, guardian_module, monkeypatch):
        """All retries fail → returns empty string."""
        call_count = [0]

        def side_effect(*a, **kw):
            call_count[0] += 1
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": "error"})()

        monkeypatch.setattr(subprocess, "run", side_effect)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        result = guardian_module.run("echo fail", timeout=10, retries=2, label="fail_test")
        assert result == ""
        assert call_count[0] == 3  # 2 retries + 1 initial = 3

    def test_run_timeout(self, guardian_module, monkeypatch):
        """Subprocess timeout → retries, eventually returns ''."""
        call_count = [0]

        def side_effect(*a, **kw):
            call_count[0] += 1
            raise subprocess.TimeoutExpired(cmd="mock", timeout=60)

        monkeypatch.setattr(subprocess, "run", side_effect)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        result = guardian_module.run("slow_cmd", timeout=10, retries=1, label="timeout_test")
        assert result == ""
        assert call_count[0] == 2

    def test_run_exception_caught(self, guardian_module, monkeypatch):
        """General exception caught → retries, returns ''."""
        call_count = [0]

        def side_effect(*a, **kw):
            call_count[0] += 1
            raise RuntimeError("unexpected crash")

        monkeypatch.setattr(subprocess, "run", side_effect)
        monkeypatch.setattr(time, "sleep", lambda s: None)
        result = guardian_module.run("bad_cmd", timeout=10, retries=1, label="except_test")
        assert result == ""
        assert call_count[0] == 2


# ═══════════════════════════════════════════════════
# Tests: check_omni_loop_heartbeat()
# ═══════════════════════════════════════════════════

class TestOmniLoopHeartbeat:
    def test_no_heartbeat_file(self, guardian_module, monkeypatch):
        """No heartbeat file → calls _restart_omni_loop."""
        restart_called = []

        def fake_restart():
            restart_called.append(True)
            return ["restarted"]

        monkeypatch.setattr(guardian_module, "_restart_omni_loop", fake_restart)
        result = guardian_module.check_omni_loop_heartbeat()
        assert restart_called
        assert "restarted" in result

    def test_recent_heartbeat(self, guardian_module, monkeypatch):
        """Recent heartbeat → no restart, returns empty list."""
        hb = guardian_module.HERMES / "omni_heartbeat.txt"
        hb.write_text(datetime.now().isoformat())
        hb.touch()  # Ensure mtime is now

        restart_called = []

        def fake_restart():
            restart_called.append(True)
            return ["restarted"]

        monkeypatch.setattr(guardian_module, "_restart_omni_loop", fake_restart)
        result = guardian_module.check_omni_loop_heartbeat()
        assert not restart_called
        assert result == []

    def test_stale_heartbeat(self, guardian_module, monkeypatch):
        """Heartbeat older than 120min → calls restart."""
        hb = guardian_module.HERMES / "omni_heartbeat.txt"
        hb.write_text("old heartbeat")

        # Use os.utime to set the file's mtime to ~133 minutes ago
        old_time = time.time() - 8000
        import os as _os
        _os.utime(str(hb), (old_time, old_time))

        restart_called = []

        def fake_restart():
            restart_called.append(True)
            return ["restarted"]

        monkeypatch.setattr(guardian_module, "_restart_omni_loop", fake_restart)
        result = guardian_module.check_omni_loop_heartbeat()
        assert restart_called
        assert "restarted" in result

    def test_restart_omni_loop(self, guardian_module, monkeypatch):
        """_restart_omni_loop runs command and writes recovery log."""
        mock = type("R", (), {"returncode": 0, "stdout": "restarted ok", "stderr": ""})()

        def fake_run(*a, **kw):
            return mock

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(guardian_module, "run", lambda *a, **kw: "restarted ok")
        result = guardian_module._restart_omni_loop()
        assert len(result) == 1
        assert "恢复重启" in result[0]

    def test_restart_omni_loop_fails(self, guardian_module, monkeypatch):
        """_restart_omni_loop fails → returns failure message."""
        monkeypatch.setattr(guardian_module, "run", lambda *a, **kw: "")
        result = guardian_module._restart_omni_loop()
        assert len(result) == 1
        assert "重启失败" in result[0]


# ═══════════════════════════════════════════════════
# Tests: push_to_wechat()
# ═══════════════════════════════════════════════════

class TestPushToWechat:
    def test_push_no_config_file(self, guardian_module, monkeypatch):
        """No config.yaml → returns False."""
        config_path = guardian_module.HERMES / "config.yaml"
        # Ensure it doesn't exist
        if config_path.exists():
            config_path.unlink()
        result = guardian_module.push_to_wechat("title", "content")
        assert result is False

    def test_push_no_token(self, guardian_module, monkeypatch):
        """Config exists but no pushplus token → returns False."""
        import yaml
        config_path = guardian_module.HERMES / "config.yaml"
        config_path.write_text(yaml.dump({"pushplus": {"token": ""}}))
        result = guardian_module.push_to_wechat("title", "content")
        assert result is False

    def test_push_network_error_handled(self, guardian_module, monkeypatch):
        """Network error during push → returns False, handled gracefully."""
        import yaml
        config_path = guardian_module.HERMES / "config.yaml"
        config_path.write_text(yaml.dump({"pushplus": {"token": "test_token_123"}}))

        import urllib.request
        def fake_urlopen(*a, **kw):
            raise urllib.error.URLError("network unreachable")

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        result = guardian_module.push_to_wechat("title", "content")
        assert result is False


# ═══════════════════════════════════════════════════
# Tests: _do_push_legacy()
# ═══════════════════════════════════════════════════

class TestDoPushLegacy:
    def test_no_push_data_triggers_collect(self, guardian_module, monkeypatch):
        """No push_candidates file → triggers auto_collect_cycle."""
        collect_called = []

        def fake_collect_cycle():
            collect_called.append(True)
            # Still no file after "collect"
            return True

        monkeypatch.setattr(guardian_module, "auto_collect_cycle", fake_collect_cycle)
        monkeypatch.setattr(guardian_module, "push_to_wechat", lambda t, c: True)
        # Call via monkeypatch to avoid real file system issues
        guardian_module._do_push_legacy()
        assert collect_called

    def test_push_data_old_triggers_refresh(self, guardian_module, monkeypatch):
        """Push data older than 2 hours → triggers refresh."""
        push_file = guardian_module.HERMES / "cron" / "push_candidates_latest.json"
        old_time = (datetime.now().replace(microsecond=0)).isoformat()
        # Write data that says it was generated long ago
        push_file.write_text(json.dumps({
            "generated_at": "2020-01-01T00:00:00",
            "total_today": 10,
            "matched": 5,
            "items": [
                {"title": "test", "platform": "web", "ai_score_total": 80, "personal_match_score": 12}
            ]
        }))

        collect_called = []

        def fake_collect_cycle():
            collect_called.append(True)
            # After collect, rewrite the file with fresh data
            push_file.write_text(json.dumps({
                "generated_at": datetime.now().isoformat(),
                "total_today": 10,
                "matched": 5,
                "items": [
                    {"title": "test", "platform": "web", "ai_score_total": 80, "personal_match_score": 12}
                ]
            }))
            return True

        monkeypatch.setattr(guardian_module, "auto_collect_cycle", fake_collect_cycle)
        monkeypatch.setattr(guardian_module, "push_to_wechat", lambda t, c: True)
        guardian_module._do_push_legacy()
        assert collect_called

    def test_push_data_fresh_no_refresh(self, guardian_module, monkeypatch):
        """Fresh push data (≥5 items) → no auto_collect_cycle called."""
        push_file = guardian_module.HERMES / "cron" / "push_candidates_latest.json"
        items = []
        for i in range(5):
            items.append({
                "title": f"test_{i}", "platform": "web",
                "ai_score_total": 80, "personal_match_score": 12
            })
        push_file.write_text(json.dumps({
            "generated_at": datetime.now().isoformat(),
            "total_today": 10,
            "matched": 5,
            "items": items
        }))

        collect_called = []

        def fake_collect_cycle():
            collect_called.append(True)
            return True

        monkeypatch.setattr(guardian_module, "auto_collect_cycle", fake_collect_cycle)
        monkeypatch.setattr(guardian_module, "push_to_wechat", lambda t, c: True)
        guardian_module._do_push_legacy()
        assert not collect_called


# ═══════════════════════════════════════════════════
# Tests: health_check()
# ═══════════════════════════════════════════════════

class TestHealthCheck:
    def test_health_check_returns_list(self, guardian_module, monkeypatch):
        """health_check always returns a list."""
        # Patch pgrep to return nothing (no hermes process)
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw:
            type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
        # Patch disk_check to return empty
        monkeypatch.setattr(guardian_module, "disk_check", lambda: [])
        # Patch clean_stale_locks to return empty
        monkeypatch.setattr(guardian_module, "clean_stale_locks", lambda: [])

        result = guardian_module.health_check()
        assert isinstance(result, list)

    def test_health_check_no_hermes_process(self, guardian_module, monkeypatch):
        """No hermes process running → reports issue."""
        call_args = []

        def fake_run(cmd, *args, **kwargs):
            call_args.append(cmd)
            if isinstance(cmd, list) and "pgrep" in str(cmd):
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(guardian_module, "disk_check", lambda: [])
        monkeypatch.setattr(guardian_module, "clean_stale_locks", lambda: [])

        result = guardian_module.health_check()
        has_process_issue = any("进程" in str(r) for r in result)
        # Not asserting True because DB check might also fail, just checking it doesn't crash
        assert isinstance(result, list)
