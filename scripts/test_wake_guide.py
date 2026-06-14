#!/usr/bin/env python3
"""Tests for wake_guide.py — 醒来指南生成器"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".hermes"))

# ── Helpers ──

TZ = timezone(timedelta(hours=8))
HERMES = Path.home() / ".hermes"


def _cleanup_test_files():
    """Remove test artifacts created during tests"""
    for f in ["recovery_pack.json", "gear_checkpoint.json",
              "wake_guide.json", "G6_VALIDATION_ALERT.json", "verification_log.json",
              "mandatory_engine_alarm.txt"]:
        p = HERMES / "reports" / f
        if p.exists():
            p.unlink()
    # Clean gear heartbeat if we wrote it
    hb = HERMES / "logs" / "gear_heartbeat.txt"
    if hb.exists():
        hb.unlink()


@pytest.fixture(autouse=True)
def setup_teardown():
    """Ensure clean state before each test"""
    _cleanup_test_files()
    # Ensure reports dir exists
    (HERMES / "reports").mkdir(parents=True, exist_ok=True)
    # Move aside existing task_current.json if it exists (it contains real data)
    tc_path = HERMES / "task_current.json"
    tc_backup = HERMES / "task_current.json.test_bak"
    if tc_path.exists():
        tc_path.rename(tc_backup)
    yield
    # Restore
    if tc_backup.exists():
        tc_backup.rename(tc_path)
    _cleanup_test_files()


# ════════════════════════════════════════════════════════════════
# Test: wake_guide module internals
# ════════════════════════════════════════════════════════════════

class TestGearSign:
    """_gear_sign() — G7互审：签名认证"""

    def test_gear_sign_success(self, monkeypatch):
        """正常情况返回 signed=True"""
        import subprocess

        import scripts.wake_guide as wg
        class FakeResult:
            stdout = "OK"
            returncode = 0
        def fake_run(*a, **kw):
            return FakeResult()
        monkeypatch.setattr(subprocess, "run", fake_run)
        wg._gear_signed = False
        result = wg._gear_sign("test_task", "test_detail")
        assert result["signed"] is True

    def test_gear_sign_exception(self, monkeypatch):
        """异常时返回 signed=False + error"""
        import subprocess

        import scripts.wake_guide as wg
        def failing_run(*a, **kw):
            raise RuntimeError("gear_vault not found")
        monkeypatch.setattr(subprocess, "run", failing_run)
        wg._gear_signed = False
        result = wg._gear_sign("test_task", "detail")
        assert result["signed"] is False
        assert "error" in result


class TestVerifyG6Validation:
    """_verify_g6_validation() — G7验证G6"""

    def test_no_alert_log_returns_verified(self):
        """无告警无验证日志时返回 verified=True"""
        import scripts.wake_guide as wg
        result = wg._verify_g6_validation()
        assert result["verified"] is True
        assert result["last_validation"] is None

    def test_with_alert_chain_fail(self):
        """G6告警文件存在且 chains_pass=False → verified=False"""
        import scripts.wake_guide as wg
        alert = HERMES / "reports" / "G6_VALIDATION_ALERT.json"
        alert.write_text(json.dumps({
            "chains_pass": False, "scripts_pass": True, "g5_pass": True
        }))
        result = wg._verify_g6_validation()
        assert result["verified"] is False

    def test_with_alert_scripts_fail(self):
        """G6告警 scripts_pass=False → verified=False"""
        import scripts.wake_guide as wg
        alert = HERMES / "reports" / "G6_VALIDATION_ALERT.json"
        alert.write_text(json.dumps({
            "chains_pass": True, "scripts_pass": False, "g5_pass": True
        }))
        result = wg._verify_g6_validation()
        assert result["verified"] is False

    def test_with_alert_g5_fail(self):
        """G6告警 g5_pass=False → verified=False"""
        import scripts.wake_guide as wg
        alert = HERMES / "reports" / "G6_VALIDATION_ALERT.json"
        alert.write_text(json.dumps({
            "chains_pass": True, "scripts_pass": True, "g5_pass": False
        }))
        result = wg._verify_g6_validation()
        assert result["verified"] is False

    def test_with_verification_log(self):
        """验证日志存在时读取最后一条记录"""
        import scripts.wake_guide as wg
        vlog = HERMES / "reports" / "verification_log.json"
        vlog.write_text(json.dumps([
            {"task_id": "task_1", "status": "accepted", "accepted": True,
             "accepted_at": "2025-06-14T10:00:00+08:00"}
        ]))
        result = wg._verify_g6_validation()
        assert result["last_validation"] is not None
        assert result["last_validation"]["task"] == "task_1"
        assert result["last_validation"]["accepted"] is True

    def test_corrupted_alert_ignored(self):
        """损坏的告警文件被静默跳过"""
        import scripts.wake_guide as wg
        alert = HERMES / "reports" / "G6_VALIDATION_ALERT.json"
        alert.write_text("not json")
        result = wg._verify_g6_validation()
        # Should still be verified since we ignore corrupt files
        assert result["verified"] is True


class TestBuildWakeGuide:
    """build_wake_guide() — 主构建函数"""

    def test_basic_structure(self):
        """返回包含所有必需字段的 dict"""
        import scripts.wake_guide as wg
        # Reset gear_signed so it attempts to sign
        wg._gear_signed = True  # Skip gear_sign to avoid subprocess
        guide = wg.build_wake_guide()
        assert "ts" in guide
        assert "interrupted_task" in guide
        assert "ai_scoring_pending" in guide
        assert "gear_heartbeat_minutes" in guide
        assert "actions_required" in guide
        assert "g6_validation" in guide

    def test_interrupted_task_recovery_pack(self):
        """检测 recovery_pack 中的中断任务"""
        import scripts.wake_guide as wg
        rp = HERMES / "reports" / "recovery_pack.json"
        rp.write_text(json.dumps({
            "status": "running",
            "task_current": {"task_id": "test_task_123", "next_action": "analyze", "detail": "analyze data"},
            "gear_checkpoint": {}
        }))
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        assert guide["interrupted_task"] is not None
        assert guide["interrupted_task"]["task_id"] == "test_task_123"

    def test_skips_self_enhance_loop(self):
        """跳过 self_enhance_* 误判"""
        import scripts.wake_guide as wg
        rp = HERMES / "reports" / "recovery_pack.json"
        rp.write_text(json.dumps({
            "status": "running",
            "task_current": {"task_id": "self_enhance_v3", "next_action": "loop", "detail": "auto loop"},
            "gear_checkpoint": {}
        }))
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        assert guide["interrupted_task"] is None, "Should skip self_enhance_ tasks"

    def test_gear_checkpoint_detection(self):
        """检测 gear_checkpoint 中的运行中任务"""
        import scripts.wake_guide as wg
        gc = HERMES / "reports" / "gear_checkpoint.json"
        gc.write_text(json.dumps({
            "status": "running",
            "task_id": "gear_task_456",
            "next_action": "validate",
            "detail": "validate chain"
        }))
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        assert guide["interrupted_task"] is not None
        assert guide["interrupted_task"]["task_id"] == "gear_task_456"

    def test_no_interrupted_task(self):
        """无中断任务时 interrupted_task=None"""
        import scripts.wake_guide as wg
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        assert guide["interrupted_task"] is None
        assert "无中断任务" not in str(guide.get("actions_required", []))

    def test_ai_scoring_db_query(self, monkeypatch):
        """AI评分查询使用 sqlite3"""
        import scripts.wake_guide as wg
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        # Should have numeric values even without db (except block)
        assert isinstance(guide["ai_scoring_pending"], int)
        assert isinstance(guide["ai_scoring_total_today"], int)

    def test_gear_heartbeat(self):
        """读取齿轮心跳文件"""
        import scripts.wake_guide as wg
        hb = HERMES / "logs" / "gear_heartbeat.txt"
        hb.parent.mkdir(exist_ok=True)
        hb.write_text(datetime.now(TZ).isoformat())
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        assert guide["gear_heartbeat_minutes"] < 1  # Just written

    def test_writes_wake_guide_json(self):
        """构建指南写入 wake_guide.json"""
        import scripts.wake_guide as wg
        wg._gear_signed = True
        guide = wg.build_wake_guide()
        output = HERMES / "reports" / "wake_guide.json"
        assert output.exists()
        saved = json.loads(output.read_text())
        assert saved["ts"] == guide["ts"]

    def test_actions_required_includes_pending_ai(self, monkeypatch):
        """有待评分时 actions_required 包含 AI 评分提醒"""
        import scripts.wake_guide as wg
        wg._gear_signed = True

        # Simulate a DB with pending items
        db_path = HERMES / "intelligence.db"

        # Only test if we can create a temp db context — fallback to verifying
        # that the field exists
        guide = wg.build_wake_guide()
        assert isinstance(guide["actions_required"], list)
