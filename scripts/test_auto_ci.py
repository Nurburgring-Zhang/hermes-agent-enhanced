#!/usr/bin/env python3
"""Tests for auto_ci.py — Hermes 本地自动CI循环"""

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
def auto_ci_module(tmp_path, monkeypatch):
    """Import auto_ci module with paths patched to tmp_path."""
    for mod in list(sys.modules.keys()):
        if "auto_ci" in mod.lower():
            del sys.modules[mod]

    # Create necessary directories
    (tmp_path / ".hermes" / "logs" / "auto_ci").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".hermes" / "scripts").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path / ".hermes"))
    monkeypatch.setattr("scripts.auto_ci.HERMES", tmp_path / ".hermes")
    monkeypatch.setattr("scripts.auto_ci.LOG_DIR", tmp_path / ".hermes" / "logs" / "auto_ci")
    monkeypatch.setattr("scripts.auto_ci.RESULTS_FILE", tmp_path / ".hermes" / "logs" / "auto_ci" / "ci_results.jsonl")

    # Suppress logging to file to avoid FileHandler issues in tests
    import logging
    monkeypatch.setattr(logging, "basicConfig", lambda *a, **kw: None)

    import scripts.auto_ci as auto_ci
    return auto_ci


@pytest.fixture
def mock_normal_subprocess(monkeypatch):
    """Mock subprocess.run that returns success by default."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        # Default: success
        return type("R", (), {
            "returncode": 0,
            "stdout": "ok output\n",
            "stderr": ""
        })()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


# ═══════════════════════════════════════════════════
# Tests: run_step()
# ═══════════════════════════════════════════════════

class TestRunStep:
    def test_run_step_success(self, auto_ci_module, monkeypatch):
        """Successful step returns (True, result_dict)."""
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 0,
                "stdout": "lint passed",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok, result = auto_ci_module.run_step("lint", "ruff check . --exit-zero")
        assert ok is True
        assert result["step"] == "lint"
        assert result["success"] is True
        assert "duration_s" in result
        assert "timestamp" in result

    def test_run_step_failure(self, auto_ci_module, monkeypatch):
        """Failed step returns (False, result_dict)."""
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 1,
                "stdout": "",
                "stderr": "E SyntaxError on line 42"
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok, result = auto_ci_module.run_step("lint", "ruff check .")
        assert ok is False
        assert result["step"] == "lint"
        assert result["success"] is False

    def test_run_step_timeout(self, auto_ci_module, monkeypatch):
        """Timeout returns (False, result_dict) with error='timeout'."""
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd="test", timeout=300)

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok, result = auto_ci_module.run_step("slow_step", "sleep 999")
        assert ok is False
        assert result["step"] == "slow_step"
        assert result["success"] is False
        assert result["error"] == "timeout"

    def test_run_step_general_exception(self, auto_ci_module, monkeypatch):
        """General exception returns (False, result_dict) with error=str."""
        def fake_run(cmd, **kwargs):
            raise RuntimeError("command not found")

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok, result = auto_ci_module.run_step("bad_step", "nonexistent_cmd")
        assert ok is False
        assert result["step"] == "bad_step"
        assert result["success"] is False
        assert "command not found" in result["error"]

    def test_run_step_cwd_defaults_to_hermes(self, auto_ci_module, monkeypatch):
        """If no cwd provided, defaults to HERMES dir."""
        call_args = []

        def fake_run(cmd, **kwargs):
            call_args.append(kwargs)
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        auto_ci_module.run_step("test", "echo hello")
        assert call_args
        assert "cwd" in call_args[0]

    def test_step_duration_recorded(self, auto_ci_module, monkeypatch):
        """Duration is recorded in result."""
        def fake_run(cmd, **kwargs):
            time.sleep(0.01)
            return type("R", (), {
                "returncode": 0,
                "stdout": "done",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        ok, result = auto_ci_module.run_step("timed_step", "sleep 0.01")
        assert ok is True
        assert result["duration_s"] > 0


# ═══════════════════════════════════════════════════
# Tests: run_full_ci()
# ═══════════════════════════════════════════════════

class TestRunFullCi:
    def test_all_steps_pass(self, auto_ci_module, monkeypatch):
        """When all steps succeed, returns True."""
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 0,
                "stdout": "all good",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        all_pass = auto_ci_module.run_full_ci()
        assert all_pass is True

    def test_one_step_fails(self, auto_ci_module, monkeypatch):
        """When any step fails, returns False."""
        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            # Fail the first step (lint), succeed the rest
            rc = 1 if call_count[0] == 1 else 0
            return type("R", (), {
                "returncode": rc,
                "stdout": "some output",
                "stderr": "error" if rc != 0 else ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        all_pass = auto_ci_module.run_full_ci()
        assert all_pass is False

    def test_results_written_to_jsonl(self, auto_ci_module, monkeypatch):
        """Results are appended to ci_results.jsonl."""
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 0,
                "stdout": "all good",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        auto_ci_module.run_full_ci()

        rfile = auto_ci_module.RESULTS_FILE
        assert rfile.exists()
        lines = rfile.read_text().strip().split("\n")
        assert len(lines) >= 1
        data = json.loads(lines[-1])
        assert "all_pass" in data
        assert "steps" in data
        assert "total_duration_s" in data

    def test_lint_step_present(self, auto_ci_module, monkeypatch):
        """Verify lint command is generated correctly."""
        commands_seen = []

        def fake_run(cmd, **kwargs):
            commands_seen.append(cmd)
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        auto_ci_module.run_full_ci()
        # Find the lint command
        lint_cmds = [c for c in commands_seen if isinstance(c, str) or "ruff" in str(c)]
        assert len(lint_cmds) > 0

    def test_security_step_present(self, auto_ci_module, monkeypatch):
        """Verify security (bandit) command is generated."""
        commands_seen = []

        def fake_run(cmd, **kwargs):
            commands_seen.append(cmd)
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        auto_ci_module.run_full_ci()
        # Commands are lists (split from string)
        bandit_cmds = [c for c in commands_seen if any("bandit" in str(x) for x in c)]
        assert len(bandit_cmds) > 0

    def test_coverage_step_present(self, auto_ci_module, monkeypatch):
        """Verify coverage command is generated."""
        commands_seen = []

        def fake_run(cmd, **kwargs):
            commands_seen.append(cmd)
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        auto_ci_module.run_full_ci()
        cov_cmds = [c for c in commands_seen if any("cov" in str(x) for x in c)]
        assert len(cov_cmds) > 0

    def test_total_duration_aggregated(self, auto_ci_module, monkeypatch):
        """total_duration_s sums all step durations."""
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        auto_ci_module.run_full_ci()

        rfile = auto_ci_module.RESULTS_FILE
        lines = rfile.read_text().strip().split("\n")
        data = json.loads(lines[-1])
        step_sum = sum(s.get("duration_s", 0) for s in data["steps"])
        assert data["total_duration_s"] == step_sum

    def test_run_full_ci_has_four_steps(self, auto_ci_module, monkeypatch):
        """CI runs exactly 4 steps: lint, test, coverage, security."""
        step_names = []

        def fake_run(cmd, **kwargs):
            # step name is passed as first arg to run_step
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        # Monkey-patch run_step to capture step names
        original_run_step = auto_ci_module.run_step

        captured = []
        def tracking_run_step(name, cmd, **kwargs):
            captured.append(name)
            return original_run_step(name, cmd, **kwargs)

        monkeypatch.setattr(auto_ci_module, "run_step", tracking_run_step)
        auto_ci_module.run_full_ci()
        assert len(captured) == 4
        assert "lint" in captured
        assert "test_core" in captured
        assert "coverage" in captured
        assert "security" in captured

    def test_gate_logic_all_pass_true(self, auto_ci_module, monkeypatch):
        """Gate logic: all steps passing → all_pass=True."""
        def fake_run(cmd, **kwargs):
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = auto_ci_module.run_full_ci()
        assert result is True

    def test_gate_logic_lint_fails(self, auto_ci_module, monkeypatch):
        """Gate logic: lint fails → all_pass=False."""
        call_count = [0]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return type("R", (), {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "lint error"
                })()
            return type("R", (), {
                "returncode": 0,
                "stdout": "ok",
                "stderr": ""
            })()

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = auto_ci_module.run_full_ci()
        assert result is False
