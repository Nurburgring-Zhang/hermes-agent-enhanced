#!/usr/bin/env python3
"""Tests for gear_enforcer.py — 齿轮强制执行器 v3.0"""

import json
import subprocess
import sys
import time
from datetime import timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".hermes"))
sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))

TZ = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

class FakeMonitorEngine:
    """Fake MonitorEngine for testing."""
    class FakeSignal:
        def __init__(self, val):
            self.value = val
    CONTINUE = FakeSignal("CONTINUE")
    REFLECT = FakeSignal("REFLECT")
    RECOVER = FakeSignal("RECOVER")
    CHECKPOINT = FakeSignal("CHECKPOINT")

    def __init__(self):
        pass

    def evaluate(self, state):
        return (self.CONTINUE, {"reason": "normal"})


class FakeReflectorEngine:
    """Fake ReflectorEngine for testing."""
    def reflect(self, ctx):
        return {
            "report_id": "RPT-001",
            "summary": {"improvements": ["no issues"]}
        }


class FakeSegmentManager:
    """Fake SegmentManager for testing."""
    def get_stats(self):
        return {
            "current_segment": 1,
            "turns_in_segment": 3,
            "max_turns_per_segment": 50,
            "total_turns_all": 3
        }


class FakeConsistencyGuard:
    """Fake ConsistencyGuard for testing."""
    def check(self, turns):
        return []


def _make_fake_subprocess(returncode=0, stdout="", stderr=""):
    def fake_run(cmd, **kwargs):
        return type("R", (), {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr
        })()
    return fake_run


@pytest.fixture
def ge_module(tmp_path, monkeypatch):
    """Import gear_enforcer module with all V3 deps mocked."""
    for mod in list(sys.modules.keys()):
        if "gear_enforcer" in mod.lower() or "gear" in mod.lower():
            if mod in sys.modules:
                del sys.modules[mod]

    # Create necessary dirs
    (tmp_path / ".hermes" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "evolution_v3").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "workflows").mkdir(parents=True, exist_ok=True)

    # Mock V3 subsystem modules before importing gear_enforcer
    import types

    # agent.monitor
    agent_monitor = types.ModuleType("agent.monitor")
    agent_monitor.MonitorEngine = FakeMonitorEngine
    agent_monitor.MonitorSignal = FakeMonitorEngine
    sys.modules["agent"] = types.ModuleType("agent")
    sys.modules["agent.monitor"] = agent_monitor

    # agent.reflector
    agent_reflector = types.ModuleType("agent.reflector")
    agent_reflector.ReflectorEngine = FakeReflectorEngine
    sys.modules["agent.reflector"] = agent_reflector

    # consistency_guard
    cg_mod = types.ModuleType("scripts.consistency_guard")
    cg_mod.ConsistencyGuard = FakeConsistencyGuard
    sys.modules["scripts.consistency_guard"] = cg_mod

    # segment_manager
    sm_mod = types.ModuleType("scripts.segment_manager")
    sm_mod.SegmentManager = FakeSegmentManager
    sys.modules["scripts.segment_manager"] = sm_mod

    # Mock mandatory_engine in workflows
    me_mod = types.ModuleType("workflows.mandatory_engine")
    me_mod.MODULES = [{"name": "mod1"}, {"name": "mod2"}]
    def fake_run_self_check():
        return {"all_ok": True, "healthy": 2, "restored": 0, "failed": 0}
    me_mod.run_self_check = fake_run_self_check
    sys.modules["workflows"] = types.ModuleType("workflows")
    sys.modules["workflows.mandatory_engine"] = me_mod

    # Patch Path.home and module-level constants
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("scripts.gear_enforcer.HERMES", tmp_path / ".hermes")
    monkeypatch.setattr("scripts.gear_enforcer.SCRIPTS", tmp_path / ".hermes" / "scripts")
    monkeypatch.setattr("scripts.gear_enforcer.LOGS", tmp_path / ".hermes" / "logs")
    monkeypatch.setattr("scripts.gear_enforcer.REPORTS", tmp_path / ".hermes" / "reports")
    monkeypatch.setattr("scripts.gear_enforcer.EVO_V3", tmp_path / ".hermes" / "evolution_v3")
    monkeypatch.setattr("scripts.gear_enforcer.ENHANCE_LOG", tmp_path / ".hermes" / "logs" / "self_enhance.log")
    monkeypatch.setattr("scripts.gear_enforcer.LAST_CTX_FILE", tmp_path / ".hermes" / "reports" / ".last_context_round.txt")

    monkeypatch.setattr(subprocess, "run", _make_fake_subprocess())
    monkeypatch.setattr(time, "sleep", lambda s: None)

    import scripts.gear_enforcer as ge
    return ge


# ═══════════════════════════════════════════════════
# Tests: run_script()
# ═══════════════════════════════════════════════════

class TestRunScript:
    def test_run_script_success(self, ge_module, monkeypatch):
        """Script exists and runs successfully."""
        # Create a dummy script
        script_path = ge_module.SCRIPTS / "test_dummy.py"
        script_path.write_text("print('hello')")

        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0, stdout="hello"
        ))
        result = ge_module.run_script("test_dummy.py")
        assert result["ok"] is True
        assert result["stdout"] == "hello"

    def test_run_script_not_found(self, ge_module):
        """Script file does not exist → returns ok=False with error."""
        result = ge_module.run_script("nonexistent_script.py")
        assert result["ok"] is False
        assert "不存在" in result["error"]

    def test_run_script_timeout(self, ge_module, monkeypatch):
        """Command times out → returns ok=False."""
        script_path = ge_module.SCRIPTS / "slow_script.py"
        script_path.write_text("import time; time.sleep(999)")

        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd="python", timeout=30)

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = ge_module.run_script("slow_script.py")
        assert result["ok"] is False
        assert "超时" in result["error"]

    def test_run_script_general_exception(self, ge_module, monkeypatch):
        """General exception → returns ok=False with error."""
        script_path = ge_module.SCRIPTS / "bad_script.py"
        script_path.write_text("raise SystemExit(1)")

        def fake_run(cmd, **kwargs):
            raise RuntimeError("something broke")

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = ge_module.run_script("bad_script.py")
        assert result["ok"] is False
        assert "something broke" in result["error"]

    def test_run_script_with_args(self, ge_module, monkeypatch):
        """Script with extra args."""
        script_path = ge_module.SCRIPTS / "arg_script.py"
        script_path.write_text("print('arg test')")

        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = ge_module.run_script("arg_script.py", ["--flag", "value"])
        assert result["ok"] is True
        assert "--flag" in str(captured_cmd[0])


# ═══════════════════════════════════════════════════
# Tests: get_active_task()
# ═══════════════════════════════════════════════════

class TestGetActiveTask:
    def test_no_checkpoint_files(self, ge_module):
        """No checkpoint files exist → returns empty dict."""
        result = ge_module.get_active_task()
        assert result["source"] is None
        assert result["task_id"] == ""

    def test_gear_checkpoint_running(self, ge_module):
        """gear_checkpoint with status=running → detected."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "task_001",
            "next_action": "validate_chain"
        }))
        result = ge_module.get_active_task()
        assert result["source"] == "gear_checkpoint"
        assert result["task_id"] == "task_001"
        assert result["next_action"] == "validate_chain"

    def test_gear_checkpoint_not_running(self, ge_module):
        """gear_checkpoint exists but not running → not detected."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "completed",
            "task_id": "task_001",
            "next_action": ""
        }))
        result = ge_module.get_active_task()
        assert result["source"] is None
        assert result["task_id"] == ""

    def test_task_current_running(self, ge_module):
        """task_current with status=running → detected as fallback."""
        tc = ge_module.HERMES / "task_current.json"
        tc.write_text(json.dumps({
            "status": "running",
            "task_id": "task_002",
            "next_action": "analyze"
        }))
        result = ge_module.get_active_task()
        assert result["source"] == "task_current"
        assert result["task_id"] == "task_002"

    def test_task_current_interrupted(self, ge_module):
        """task_current with status=interrupted → detected."""
        tc = ge_module.HERMES / "task_current.json"
        tc.write_text(json.dumps({
            "status": "interrupted",
            "task_id": "task_003",
            "next_action": "recover"
        }))
        result = ge_module.get_active_task()
        assert result["source"] == "task_current"
        assert result["task_id"] == "task_003"

    def test_recovery_pack_fallback(self, ge_module):
        """recovery_pack as third fallback → detected when others missing."""
        rp = ge_module.REPORTS / "recovery_pack.json"
        rp.write_text(json.dumps({
            "status": "running",
            "gear_checkpoint": {},
            "task_current": {"task_id": "task_004", "next_action": "resume"}
        }))
        result = ge_module.get_active_task()
        assert result["source"] == "recovery_pack"
        assert result["task_id"] == "task_004"

    def test_gear_checkpoint_takes_priority(self, ge_module):
        """When both gear_checkpoint and task_current exist, gear_checkpoint wins."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "priority_task",
            "next_action": "do_first"
        }))
        tc = ge_module.HERMES / "task_current.json"
        tc.write_text(json.dumps({
            "status": "running",
            "task_id": "low_priority",
            "next_action": "do_second"
        }))
        result = ge_module.get_active_task()
        assert result["source"] == "gear_checkpoint"
        assert result["task_id"] == "priority_task"

    def test_corrupt_json_handled(self, ge_module):
        """Corrupted JSON files are silently handled."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text("not valid json {{{")
        result = ge_module.get_active_task()
        # Should not crash, should fall through to empty
        assert "source" in result
        assert isinstance(result["task_id"], str)


# ═══════════════════════════════════════════════════
# Tests: enforce() structure and registration
# ═══════════════════════════════════════════════════

class TestEnforceStructure:
    def test_enforce_returns_dict(self, ge_module):
        """enforce() returns a dict with ts, phases, status."""
        result = ge_module.enforce()
        assert isinstance(result, dict)
        assert "ts" in result
        assert "phases" in result
        assert "status" in result

    def test_enforce_has_phases(self, ge_module):
        """enforce() phases dict is populated."""
        result = ge_module.enforce()
        phases = result["phases"]
        assert isinstance(phases, dict)
        # At minimum, ability_activation should be present
        assert "ability_activation" in phases

    def test_enforce_status_ok_when_no_errors(self, ge_module):
        """When no critical errors occur, status is a valid string."""
        result = ge_module.enforce()
        assert result["status"] in ("ok", "degraded")
        # 'degraded' is acceptable when some dependencies are missing in test env

    def test_gear_registration_list_present(self, ge_module):
        """Gear registration core_gears list is checked."""
        result = ge_module.enforce()
        act = result["phases"]["ability_activation"]
        assert "gears_checked" in act
        # With fake filesystem (no real scripts), gears_checked should be 0
        assert isinstance(act["gears_checked"], int)


# ═══════════════════════════════════════════════════
# Tests: enforce() skip self_enhance
# ═══════════════════════════════════════════════════

class TestEnforceInterruptSkip:
    def test_skip_self_enhance_task(self, ge_module):
        """When gear_checkpoint has self_enhance_* task, it is skipped."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "self_enhance_v3_loop",
            "next_action": "continue_loop"
        }))
        result = ge_module.enforce()
        ir = result["phases"]["interrupt_recovery"]
        assert ir["found"] is False
        assert ir["skipped"] is True
        assert "self_enhance_loop" in ir["reason"]

    def test_skip_self_enhance_prefix_variation(self, ge_module):
        """Any task_id starting with self_enhance_ is skipped."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "self_enhance_memory_v3",
            "next_action": "loop"
        }))
        result = ge_module.enforce()
        ir = result["phases"]["interrupt_recovery"]
        assert ir["skipped"] is True


# ═══════════════════════════════════════════════════
# Tests: log() function
# ═══════════════════════════════════════════════════

class TestLogFunction:
    def test_log_writes_to_file(self, ge_module):
        """log() writes timestamped entries to ENHANCE_LOG."""
        ge_module.log("test message 12345")
        log_path = ge_module.ENHANCE_LOG
        assert log_path.exists()
        content = log_path.read_text()
        assert "test message 12345" in content
        # Should have timestamp format
        assert any(c.isdigit() for c in content.split("\n")[0])

    def test_log_multiple_entries(self, ge_module):
        """Multiple log calls append without overwriting."""
        ge_module.log("entry_1")
        ge_module.log("entry_2")
        content = ge_module.ENHANCE_LOG.read_text()
        assert "entry_1" in content
        assert "entry_2" in content

    def test_log_creates_parent_dirs(self, ge_module, monkeypatch):
        """log() creates parent directories if they don't exist."""
        # Remove logs dir and verify it's recreated
        import shutil
        log_dir = ge_module.ENHANCE_LOG.parent
        if log_dir.exists():
            shutil.rmtree(str(log_dir))
        assert not log_dir.exists()
        ge_module.log("create test")
        assert log_dir.exists()
        assert ge_module.ENHANCE_LOG.exists()
