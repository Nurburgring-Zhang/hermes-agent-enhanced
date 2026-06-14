#!/usr/bin/env python3
"""Full coverage tests for gear_enforcer.py, gear_master.py, gear_task_validator.py, gear_task_driver.py

Goal: raise gear_enforcer from 17% → 50%, gear_task_validator from 45% → 55%
Target: 20+ tests
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".hermes"))
sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))

TZ = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════

def _make_fake_subprocess(returncode=0, stdout="", stderr=""):
    def fake_run(cmd, **kwargs):
        return type("R", (), {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr
        })()
    return fake_run


class FakeMonitorEngine:
    class FakeSignal:
        def __init__(self, val):
            self.value = val
    CONTINUE = FakeSignal("CONTINUE")
    REFLECT = FakeSignal("REFLECT")
    RECOVER = FakeSignal("RECOVER")
    CHECKPOINT = FakeSignal("CHECKPOINT")
    def evaluate(self, state):
        return (self.CONTINUE, {"reason": "normal"})


class FakeReflectorEngine:
    def reflect(self, ctx):
        return {"report_id": "RPT-001", "summary": {"improvements": ["no issues"]}}


class FakeSegmentManager:
    def get_stats(self):
        return {
            "current_segment": 1,
            "turns_in_segment": 3,
            "max_turns_per_segment": 50,
            "total_turns_all": 3
        }


class FakeConsistencyGuard:
    def check(self, turns):
        return []


@pytest.fixture
def ge_module(tmp_path, monkeypatch):
    """Import gear_enforcer with deps mocked."""
    for mod in list(sys.modules.keys()):
        if "gear_enforcer" in mod.lower():
            if mod in sys.modules:
                del sys.modules[mod]

    (tmp_path / ".hermes" / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "evolution_v3").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "workflows").mkdir(parents=True, exist_ok=True)

    import types

    agent_monitor = types.ModuleType("agent.monitor")
    agent_monitor.MonitorEngine = FakeMonitorEngine
    agent_monitor.MonitorSignal = FakeMonitorEngine
    sys.modules["agent"] = types.ModuleType("agent")
    sys.modules["agent.monitor"] = agent_monitor

    agent_reflector = types.ModuleType("agent.reflector")
    agent_reflector.ReflectorEngine = FakeReflectorEngine
    sys.modules["agent.reflector"] = agent_reflector

    cg_mod = types.ModuleType("scripts.consistency_guard")
    cg_mod.ConsistencyGuard = FakeConsistencyGuard
    sys.modules["scripts.consistency_guard"] = cg_mod

    sm_mod = types.ModuleType("scripts.segment_manager")
    sm_mod.SegmentManager = FakeSegmentManager
    sys.modules["scripts.segment_manager"] = sm_mod

    me_mod = types.ModuleType("workflows.mandatory_engine")
    me_mod.MODULES = [{"name": "mod1"}, {"name": "mod2"}]
    def fake_run_self_check():
        return {"all_ok": True, "healthy": 2, "restored": 0, "failed": 0}
    me_mod.run_self_check = fake_run_self_check
    sys.modules["workflows"] = types.ModuleType("workflows")
    sys.modules["workflows.mandatory_engine"] = me_mod

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _make_fake_subprocess())
    monkeypatch.setattr(time, "sleep", lambda s: None)

    import scripts.gear_enforcer as ge
    monkeypatch.setattr(ge, "HERMES", tmp_path / ".hermes")
    monkeypatch.setattr(ge, "SCRIPTS", tmp_path / ".hermes" / "scripts")
    monkeypatch.setattr(ge, "LOGS", tmp_path / ".hermes" / "logs")
    monkeypatch.setattr(ge, "REPORTS", tmp_path / ".hermes" / "reports")
    monkeypatch.setattr(ge, "EVO_V3", tmp_path / ".hermes" / "evolution_v3")
    monkeypatch.setattr(ge, "ENHANCE_LOG", tmp_path / ".hermes" / "logs" / "self_enhance.log")
    monkeypatch.setattr(ge, "LAST_CTX_FILE", tmp_path / ".hermes" / "reports" / ".last_context_round.txt")

    return ge


# ═══════════════════════════════════════════════════
# Tests: gear_enforcer.py — context_manager_auto()
# ═══════════════════════════════════════════════════

class TestContextManagerAuto:
    def test_no_context_file(self, ge_module):
        """When current_context.txt doesn't exist, returns early."""
        result = ge_module.context_manager_auto()
        assert result["ok"] is True
        assert any("无待处理上下文" in a for a in result.get("actions", []))

    def test_empty_context_file(self, ge_module):
        """Empty context file should be detected."""
        ctx_file = ge_module.REPORTS / "current_context.txt"
        ctx_file.write_text("")
        result = ge_module.context_manager_auto()
        assert result["ok"] is True
        assert any("为空" in a for a in result.get("actions", []))

    def test_context_no_change(self, ge_module):
        """Unchanged context (same hash) should be skipped."""
        content = "USER: hello\nASSISTANT: hi there"
        ctx_file = ge_module.REPORTS / "current_context.txt"
        ctx_file.write_text(content)

        hash_file = ge_module.REPORTS / ".last_context_hash.txt"
        hash_file.write_text(str(hash(content)))

        result = ge_module.context_manager_auto()
        assert result["ok"] is True
        assert any("无变化" in a for a in result.get("actions", []))

    def test_context_processing(self, ge_module, monkeypatch):
        """Context with new content should be processed."""
        content = "USER: hello world\nASSISTANT: hello user"
        ctx_file = ge_module.REPORTS / "current_context.txt"
        ctx_file.write_text(content)
        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0, stdout='{"total_rounds": 6}'
        ))
        result = ge_module.context_manager_auto()
        assert result["ok"] is True
        assert "actions" in result


# ═══════════════════════════════════════════════════
# Tests: gear_enforcer.py — meta_thinker_auto()
# ═══════════════════════════════════════════════════

class TestMetaThinkerAuto:
    def test_no_active_task(self, ge_module):
        """No active task → skip drift detection."""
        result = ge_module.meta_thinker_auto()
        assert result["ok"] is True
        assert any("无活跃任务" in a for a in result.get("actions", []))

    def test_no_goal_file(self, ge_module):
        """Active task but no goal file."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "task_001",
            "next_action": "test"
        }))
        result = ge_module.meta_thinker_auto()
        assert result["ok"] is True
        assert any("无任务目标文件" in a for a in result.get("actions", []))

    def test_with_goal_and_drift_check(self, ge_module, monkeypatch):
        """Goal file exists, meta_thinker is called."""
        gc = ge_module.REPORTS / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "task_001",
            "next_action": "test"
        }))
        goal_file = ge_module.REPORTS / "task_goal.txt"
        goal_file.write_text("Test goal for drift detection")
        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0,
            stdout="综合漂移分数: 0.05\n等级: ok\n"
        ))
        result = ge_module.meta_thinker_auto()
        assert result["ok"] is True
        assert "drift_score" in result


# ═══════════════════════════════════════════════════
# Tests: gear_enforcer.py — memory_orchestrator_auto()
# ═══════════════════════════════════════════════════

class TestMemoryOrchestratorAuto:
    def test_no_context_file(self, ge_module):
        result = ge_module.memory_orchestrator_auto()
        assert result["ok"] is True
        assert any("无待处理上下文" in a for a in result.get("actions", []))

    def test_empty_context(self, ge_module):
        ctx_file = ge_module.REPORTS / "current_context.txt"
        ctx_file.write_text("")
        result = ge_module.memory_orchestrator_auto()
        assert result["ok"] is True


# ═══════════════════════════════════════════════════
# Tests: gear_enforcer.py — encryption_audit_auto()
# ═══════════════════════════════════════════════════

class TestEncryptionAuditAuto:
    def test_no_encrypt_queue(self, ge_module):
        result = ge_module.encryption_audit_auto()
        assert result["ok"] is True

    def test_with_pending_encrypt_queue(self, ge_module, monkeypatch):
        # Create required script files for run_script() to find
        (ge_module.SCRIPTS / "encryption_layer.py").write_text("")
        (ge_module.SCRIPTS / "audit_logger.py").write_text("")
        enc_queue = ge_module.REPORTS / ".encrypt_queue.json"
        enc_queue.write_text(json.dumps({
            "pending": [{"path": "/tmp/test.txt"}]
        }))
        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0, stdout="encrypted"
        ))
        result = ge_module.encryption_audit_auto()
        assert result["ok"] is True
        assert any("加密文件" in a for a in result.get("actions", []))
        # Queue should be cleared
        queue_data = json.loads(enc_queue.read_text())
        assert len(queue_data["pending"]) == 0


# ═══════════════════════════════════════════════════
# Tests: gear_task_validator.py
# ═══════════════════════════════════════════════════

@pytest.fixture
def gtv_module(tmp_path, monkeypatch):
    """Import gear_task_validator with path mocks."""
    for mod in list(sys.modules.keys()):
        if "gear_task_validator" in mod.lower():
            if mod in sys.modules:
                del sys.modules[mod]

    (tmp_path / ".hermes" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "logs").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _make_fake_subprocess())

    import scripts.gear_task_validator as gtv
    monkeypatch.setattr(gtv, "HERMES", tmp_path / ".hermes")
    monkeypatch.setattr(gtv, "REPORTS", tmp_path / ".hermes" / "reports")
    monkeypatch.setattr(gtv, "LOGS", tmp_path / ".hermes" / "logs")
    monkeypatch.setattr(gtv, "REGISTRY", tmp_path / ".hermes" / "reports" / "gear_registry.json")
    monkeypatch.setattr(gtv, "DELIVERY_LOG", tmp_path / ".hermes" / "reports" / "delivery_log.json")
    monkeypatch.setattr(gtv, "VERIFICATION_LOG", tmp_path / ".hermes" / "reports" / "verification_log.json")
    monkeypatch.setattr(gtv, "now", lambda: datetime.now(TZ))
    return gtv


class TestVerifyGearChain:
    def test_no_registry(self, gtv_module):
        result = gtv_module.verify_gear_chain("task_001")
        assert result["status"] == "failed"
        assert "不存在" in result["reason"]

    def test_task_not_in_registry(self, gtv_module):
        registry = gtv_module.REGISTRY
        registry.write_text(json.dumps({"tasks": {}}))
        result = gtv_module.verify_gear_chain("task_999")
        assert result["status"] == "failed"
        assert "未注册" in result["reason"]

    def test_chain_verification(self, gtv_module):
        registry = gtv_module.REGISTRY
        registry.write_text(json.dumps({
            "tasks": {
                "task_001": {
                    "gear_chain": {
                        "G1": {"ts": "2025-01-01T00:00:00", "claim": {}, "prev_verified": True},
                        "G2": {"ts": "2025-01-01T00:01:00", "claim": {}, "prev_verified": True},
                    }
                }
            }
        }))
        result = gtv_module.verify_gear_chain("task_001")
        assert result["status"] in ("verified", "chain_incomplete")
        assert "missing_gears" in result


class TestVerifyTaskRequirements:
    def test_no_registry(self, gtv_module):
        result = gtv_module.verify_task_requirements("task_001")
        # Without registry, task defaults to total_steps=1, completed_steps=0
        # so status becomes "in_progress (0/1)"
        assert "status" in result
        assert result["completion_pct"] == 0

    def test_completed_task(self, gtv_module):
        registry = gtv_module.REGISTRY
        registry.write_text(json.dumps({
            "tasks": {
                "task_001": {
                    "total_steps": 10,
                    "completed_steps": 10,
                }
            }
        }))
        result = gtv_module.verify_task_requirements("task_001")
        assert result["status"] == "completed"
        assert result["completion_pct"] == 100.0


class TestInspectCheckpointFiles:
    def test_no_files(self, gtv_module):
        result = gtv_module.inspect_checkpoint_files()
        assert result["status"] == "inspected"
        assert result["existing"] == 0
        assert len(result["missing"]) > 0

    def test_some_files_exist(self, gtv_module):
        (gtv_module.HERMES / "task_current.json").write_text(
            json.dumps({"ts": datetime.now(TZ).isoformat(), "task_id": "t1"})
        )
        result = gtv_module.inspect_checkpoint_files()
        assert result["existing"] >= 1


class TestInspectCronHealth:
    def test_cron_check(self, gtv_module, monkeypatch):
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 0,
                "stdout": "*/1 * * * * cd ~/.hermes && python scripts/gear_enforcer.py\n*/5 * * * * cd ~/.hermes && python scripts/context_failsafe.py\n",
                "stderr": ""
            })()
        monkeypatch.setattr(subprocess, "run", fake_run)
        result = gtv_module.inspect_cron_health()
        assert result["status"] == "inspected"
        assert "gear_crons" in result


class TestTestGearScripts:
    def test_all_scripts_checked(self, gtv_module):
        result = gtv_module.test_gear_scripts()
        assert result["status"] == "tested"
        assert len(result["tests"]) > 0
        for t in result["tests"]:
            assert "gear" in t
            assert "exists" in t


class TestAcceptTask:
    def test_accept_task_with_registry(self, gtv_module, monkeypatch):
        registry = gtv_module.REGISTRY
        registry.write_text(json.dumps({
            "tasks": {
                "task_001": {
                    "total_steps": 10,
                    "completed_steps": 10,
                    "gear_chain": {
                        "G1": {"ts": "2025-01-01T00:00:00", "claim": {}, "prev_verified": True},
                        "G2": {"ts": "2025-01-01T00:01:00", "claim": {}, "prev_verified": True,
                               "verified_by": "G3"},
                        "G3": {"ts": "2025-01-01T00:02:00", "claim": {}, "prev_verified": True,
                               "verified_by": "G4"},
                        "G4": {"ts": "2025-01-01T00:03:00", "claim": {}, "prev_verified": True},
                    }
                }
            }
        }))
        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0, stdout="signed"
        ))
        result = gtv_module.accept_task("task_001")
        assert "status" in result
        assert result["task_id"] == "task_001"


class TestDeliverTask:
    def test_deliver_blocked_if_not_accepted(self, gtv_module):
        result = gtv_module.deliver_task("task_nonexistent")
        assert result["status"] == "delivery_blocked"
        assert "验收未通过" in result["reason"]


class TestRunFullValidation:
    def test_full_validation_no_tasks(self, gtv_module, monkeypatch):
        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0, stdout="signed"
        ))
        result = gtv_module.run_full_validation()
        assert "summary" in result
        assert result["summary"]["total_tasks"] == 0

    def test_full_validation_with_tasks(self, gtv_module, monkeypatch):
        registry = gtv_module.REGISTRY
        registry.write_text(json.dumps({
            "tasks": {
                "task_001": {
                    "total_steps": 10, "completed_steps": 5,
                    "gear_chain": {
                        "G1": {"ts": "2025-01-01T00:00:00", "claim": {}, "prev_verified": True},
                    }
                }
            }
        }))
        monkeypatch.setattr(subprocess, "run", _make_fake_subprocess(
            returncode=0, stdout="signed"
        ))
        result = gtv_module.run_full_validation()
        assert result["summary"]["total_tasks"] == 1
        assert len(result["results"]) == 1


# ═══════════════════════════════════════════════════
# Tests: gear_task_driver.py
# ═══════════════════════════════════════════════════

@pytest.fixture
def gtd_module(tmp_path, monkeypatch):
    """Import gear_task_driver with path mocks."""
    for mod in list(sys.modules.keys()):
        if "gear_task_driver" in mod.lower():
            if mod in sys.modules:
                del sys.modules[mod]

    (tmp_path / ".hermes" / "reports").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    import scripts.gear_task_driver as gtd
    monkeypatch.setattr(gtd, "HERMES", tmp_path / ".hermes")
    monkeypatch.setattr(gtd, "QUEUE_FILE", tmp_path / ".hermes" / "reports" / "gear_task_queue.json")
    monkeypatch.setattr(gtd, "QUEUE_LOCK", tmp_path / ".hermes" / "reports" / ".gear_task_queue.lock")
    monkeypatch.setattr(gtd, "REGISTRY_FILE", tmp_path / ".hermes" / "reports" / "gear_registry.json")
    monkeypatch.setattr(gtd, "now", lambda: datetime.now(TZ))
    return gtd


class TestStepIndex:
    def test_valid_steps(self, gtd_module):
        assert gtd_module._step_index("registered") == 0
        assert gtd_module._step_index("gear_chain_1") == 1
        assert gtd_module._step_index("delivered") == 10

    def test_invalid_step(self, gtd_module):
        assert gtd_module._step_index("nonexistent") == -1


class TestLoadSaveQueue:
    def test_load_empty_queue(self, gtd_module):
        q = gtd_module.load_queue()
        assert "tasks" in q
        assert "total_pushes" in q
        assert q["total_pushes"] == 0

    def test_save_and_load_queue(self, gtd_module):
        q = gtd_module.load_queue()
        q["tasks"]["test_task"] = {"status": "active"}
        q["total_pushes"] = 1
        gtd_module.save_queue(q)
        loaded = gtd_module.load_queue()
        assert "test_task" in loaded["tasks"]


class TestRegisterTask:
    def test_register_basic(self, gtd_module):
        result = gtd_module.register_task("task_001", "Test task description", 10)
        assert result["task_id"] == "task_001"
        assert result["current_ratchet_step"] == "registered"
        assert result["next_ratchet"] == "gear_chain_1"
        assert result["status"] == "active"

    def test_register_with_requirements(self, gtd_module):
        result = gtd_module.register_task("task_002", "Task with reqs", 5,
                                          source="hermes", requirements="Must be fast")
        assert result["task_id"] == "task_002"
        assert result["source"] == "hermes"
        assert "Must be fast" in result["requirements"]


class TestAdvanceRatchet:
    def test_advance_basic(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        result = gtd_module.advance_ratchet("task_001", "gear_chain_1", note="Moving forward")
        assert result["success"] is True
        assert result["old_step"] == "registered"
        assert result["new_step"] == "gear_chain_1"

    def test_advance_cannot_go_backward(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        gtd_module.advance_ratchet("task_001", "gear_chain_1")
        result = gtd_module.advance_ratchet("task_001", "registered")
        assert result["success"] is False
        assert "锁定" in result["error"] or "后退" in result["error"]

    def test_advance_unknown_step(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        result = gtd_module.advance_ratchet("task_001", "unknown_step")
        assert result["success"] is False
        assert "未知步骤" in result["error"]

    def test_advance_force(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        result = gtd_module.advance_ratchet("task_001", "delivered", force=True)
        assert result["success"] is True

    def test_advance_task_not_registered(self, gtd_module):
        result = gtd_module.advance_ratchet("nonexistent", "gear_chain_1")
        assert result["success"] is False
        assert "未在队列中注册" in result["error"]

    def test_advance_limits_jump(self, gtd_module):
        """Jumping multiple steps without force should only advance 1 step."""
        gtd_module.register_task("task_001", "Test", 10)
        result = gtd_module.advance_ratchet("task_001", "gear_chain_5")  # should only go to gear_chain_1
        assert result["success"] is True
        assert result["new_step"] == "gear_chain_1"


class TestMarkInterrupted:
    def test_mark_existing(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        result = gtd_module.mark_interrupted("task_001", "Something broke")
        assert result["interrupted"] is True

    def test_mark_nonexistent_auto_registers(self, gtd_module):
        result = gtd_module.mark_interrupted("new_task", "Auto created")
        assert result["interrupted"] is True
        q = gtd_module.load_queue()
        assert "new_task" in q["tasks"]


class TestCheckInterrupted:
    def test_no_interrupted(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        result = gtd_module.check_interrupted(age_minutes=10)
        assert len(result) == 0

    def test_interrupted_found(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        q = gtd_module.load_queue()
        old_time = (datetime.now(TZ) - timedelta(minutes=10)).isoformat()
        q["tasks"]["task_001"]["last_pushed_at"] = old_time
        gtd_module.save_queue(q)
        result = gtd_module.check_interrupted(age_minutes=5)
        assert len(result) > 0
        assert result[0]["task_id"] == "task_001"


class TestAutoRecover:
    def test_no_interrupted_to_recover(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        recovered = gtd_module.auto_recover()
        assert len(recovered) == 0


class TestPushFromValidation:
    def test_push_no_matching_results(self, gtd_module):
        gtd_module.register_task("task_001", "Test", 10)
        validation = {"results": [], "summary": {}}
        result = gtd_module.push_from_validation(validation, "task_001")
        assert result["success"] is True  # Falls through to manual push


class TestStatus:
    def test_status_returns_structure(self, gtd_module):
        s = gtd_module.status()
        assert "total_tasks" in s
        assert "active" in s
        assert "completed" in s
        assert "step_distribution" in s
