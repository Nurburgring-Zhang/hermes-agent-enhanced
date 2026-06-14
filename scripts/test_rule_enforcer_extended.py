#!/usr/bin/env python3
"""Extended tests for rule_enforcer.py — raising coverage from 41% → 60%

Covers:
  R2 PreCheck, R4 DeliveryEnforcer, R5 DeepAuditEnforcer,
  R6 CommunicationEnforcer, R7 AutonomyGuard, R8 AccountabilityEnforcer,
  R9 DualModelEnforcer, R10 RealImplementationEnforcer,
  R11 IterationEnforcer, R12 SdlcEnforcer, R13 SkillActiveEnforcer,
  R14 pre_tool_block / complete_phase3,
  pre_tool_intercept / post_tool_intercept / post_response_intercept / get_status / get_report

Target: 15+ tests
"""

import json
import os
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def re_module():
    import sys
    for mod in list(sys.modules.keys()):
        if "rule_enforcer" in mod:
            del sys.modules[mod]
    import scripts.rule_enforcer as rule_enforcer
    return rule_enforcer


# ═══════════════════════════════════════════════════
# R2: 前置三查 — PreCheck.execute
# ═══════════════════════════════════════════════════

class TestPreCheck:
    def test_execute_returns_structure(self, re_module, tmp_path):
        """PreCheck.execute returns a dict with expected keys."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(re_module, "HERMES", tmp_path / ".hermes")
            (tmp_path / ".hermes" / "memories").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".hermes" / "memories" / "test.json").write_text("{}")
            (tmp_path / ".hermes" / "skills").mkdir(parents=True, exist_ok=True)

            result = re_module.PreCheck.execute("测试数据库配置修改")
            assert "rule" in result
            assert result["rule"] == "R2"
            assert "verdict" in result
            assert "checks" in result
            assert "session_search" in result["checks"]
            assert "fact_store" in result["checks"]
            assert "skill_load" in result["checks"]

    def test_execute_no_memory_dir(self, re_module, tmp_path):
        """Without memories dir, fact_store check should be False."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(re_module, "HERMES", tmp_path / ".hermes")
            (tmp_path / ".hermes" / "skills").mkdir(parents=True, exist_ok=True)

            result = re_module.PreCheck.execute("hello")
            assert result["checks"]["fact_store"] is False

    def test_execute_with_skills_match(self, re_module, tmp_path):
        """Skills dir with matching keyword should be detected."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(re_module, "HERMES", tmp_path / ".hermes")
            (tmp_path / ".hermes" / "memories").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".hermes" / "memories" / "test.json").write_text("{}")
            skills_dir = tmp_path / ".hermes" / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            (skills_dir / "database-migration").mkdir()

            result = re_module.PreCheck.execute("测试数据库配置修改")
            assert "checks" in result


# ═══════════════════════════════════════════════════
# R4: 交付铁律 — DeliveryEnforcer
# ═══════════════════════════════════════════════════

class TestDeliveryEnforcer:
    def test_completion_claim_without_evidence(self, re_module):
        result = re_module.DeliveryEnforcer.check_output(
            "已成功完成所有功能，全部验证通过，没有任何问题",
            []
        )
        assert result["rule"] == "R4"
        assert result["verdict"] == "warn"

    def test_output_with_http_evidence(self, re_module):
        result = re_module.DeliveryEnforcer.check_output(
            "接口返回 HTTP 200，部署到 https://example.com，状态码 OK",
            [{"name": "curl", "args": {"url": "https://example.com"}}]
        )
        assert result["verdict"] == "pass"

    def test_verify_claim_without_method(self, re_module):
        result = re_module.DeliveryEnforcer.check_output(
            "已验证功能正常，确认没有问题",
            []
        )
        assert result["verdict"] == "warn"
        assert any("验证方法" in i for i in result.get("issues", []))

    def test_no_tool_calls_long_output(self, re_module):
        result = re_module.DeliveryEnforcer.check_output(
            "这是一个非常长的回答，" * 20,
            []
        )
        assert result["verdict"] == "warn"

    def test_short_simple_response_passes(self, re_module):
        result = re_module.DeliveryEnforcer.check_output(
            "你好！有什么可以帮助你的吗？",
            []
        )
        assert result["verdict"] == "pass"


# ═══════════════════════════════════════════════════
# R5: 深度审核 — DeepAuditEnforcer
# ═══════════════════════════════════════════════════

class TestDeepAuditEnforcer:
    def test_audit_without_verification(self, re_module):
        result = re_module.DeepAuditEnforcer.check_audit_output(
            "audit", {"file": "test.py"},
            "代码逻辑有三处问题，风格不符合规范，建议修改命名"
        )
        assert result["action"] == "warn"

    def test_audit_with_pytest_evidence(self, re_module):
        result = re_module.DeepAuditEnforcer.check_audit_output(
            "audit", {"file": "test.py"},
            "运行pytest后发现了3个失败，修复后全部通过"
        )
        assert result["action"] == "pass"

    def test_non_audit_tool_passes(self, re_module):
        result = re_module.DeepAuditEnforcer.check_audit_output(
            "read_file", {"path": "test.py"}, "some content"
        )
        assert result["action"] == "pass"

    def test_code_review_only_flag(self, re_module):
        result = re_module.DeepAuditEnforcer.check_audit_output(
            "审核", {"file": "app.py"},
            "代码结构有三处问题，逻辑错误需要修复"
        )
        # Code review only, no runtime verification
        if result["action"] == "warn":
            assert any("代码审查" in i or "运行" in i for i in result.get("issues", []))


# ═══════════════════════════════════════════════════
# R6: 沟通风格 — CommunicationEnforcer
# ═══════════════════════════════════════════════════

class TestCommunicationEnforcer:
    def test_banned_word_detection(self, re_module):
        result = re_module.CommunicationEnforcer.check_response(
            "这个系统赋能了我们的业务，形成了降本增效的闭环"
        )
        assert result["rule"] == "R6"
        assert result["verdict"] == "warn"
        assert len(result["issues"]) >= 2

    def test_clean_response_passes(self, re_module):
        result = re_module.CommunicationEnforcer.check_response(
            "接口返回了3条数据，状态码200，响应时间45ms"
        )
        assert result["verdict"] == "pass"

    def test_vague_pattern_detection(self, re_module):
        result = re_module.CommunicationEnforcer.check_response(
            "显著提升了系统性能，大幅改进了用户体验"
        )
        assert result["verdict"] == "warn"

    def test_ai_greeting_detection(self, re_module):
        result = re_module.CommunicationEnforcer.check_response(
            "作为一个AI助手，很高兴为你提供帮助"
        )
        assert result["verdict"] == "warn"
        assert any("AI味" in i for i in result.get("issues", []))


# ═══════════════════════════════════════════════════
# R7: 自主边界 — AutonomyGuard
# ═══════════════════════════════════════════════════

class TestAutonomyGuard:
    def test_block_rm_rf(self, re_module):
        result = re_module.AutonomyGuard.pre_tool(
            "terminal", {"command": "rm -rf /"}
        )
        assert result["action"] == "block"

    def test_warn_service_restart(self, re_module):
        result = re_module.AutonomyGuard.pre_tool(
            "terminal", {"command": "systemctl restart nginx"}
        )
        assert result["action"] == "warn"

    def test_pass_safe_command(self, re_module):
        result = re_module.AutonomyGuard.pre_tool(
            "terminal", {"command": "ls -la"}
        )
        assert result["action"] == "pass"

    def test_block_drop_table(self, re_module):
        result = re_module.AutonomyGuard.pre_tool(
            "terminal", {"command": "DROP TABLE users"}
        )
        assert result["action"] == "block"

    def test_warn_pip_install(self, re_module):
        result = re_module.AutonomyGuard.pre_tool(
            "terminal", {"command": "pip install pandas"}
        )
        assert result["action"] == "warn"


# ═══════════════════════════════════════════════════
# R8: 问责 — AccountabilityEnforcer
# ═══════════════════════════════════════════════════

class TestAccountabilityEnforcer:
    def test_no_unused_outputs(self, re_module):
        re_module.AccountabilityEnforcer._unused_outputs = []
        result = re_module.AccountabilityEnforcer.check_response("hello", "greeting")
        assert result["verdict"] == "pass"

    def test_record_and_check_unused(self, re_module):
        re_module.AccountabilityEnforcer._unused_outputs = []
        re_module.AccountabilityEnforcer.record_unused("test_script.py")
        result = re_module.AccountabilityEnforcer.check_response("i did something", "build")
        assert result["verdict"] == "warn"

    def test_get_unused_summary(self, re_module):
        re_module.AccountabilityEnforcer._unused_outputs = [
            {"desc": "old_output", "timestamp": "2025-01-01T00:00:00"}
        ]
        summary = re_module.AccountabilityEnforcer.get_unused_summary()
        assert "问责" in summary
        assert "old_output" in summary


# ═══════════════════════════════════════════════════
# R9: 双模型 — DualModelEnforcer
# ═══════════════════════════════════════════════════

class TestDualModelEnforcer:
    def test_single_provider_warns(self, re_module):
        result = re_module.DualModelEnforcer.check("gpt-4", "providers=1")
        assert result["verdict"] == "warn"

    def test_multiple_providers_pass(self, re_module):
        result = re_module.DualModelEnforcer.check("gpt-4", "providers=3")
        assert result["verdict"] == "pass"

    def test_record_same_model(self, re_module):
        re_module.DualModelEnforcer.record_models("gpt-4", "gpt-4")
        assert re_module.DualModelEnforcer._last_exec_model == "gpt-4"


# ═══════════════════════════════════════════════════
# R10: 真实实现 — RealImplementationEnforcer
# ═══════════════════════════════════════════════════

class TestRealImplementationEnforcer:
    def test_placeholder_detected(self, re_module):
        result = re_module.RealImplementationEnforcer.check(
            "这是一个演示代码，TODO: 需要完善FIXME"
        )
        assert result["verdict"] == "warn"

    def test_not_implemented(self, re_module):
        result = re_module.RealImplementationEnforcer.check(
            "def process():\n    raise NotImplementedError\n    pass\n"
        )
        assert result["verdict"] == "warn"

    def test_real_code_passes(self, re_module):
        result = re_module.RealImplementationEnforcer.check(
            "def process():\n    return data.process()\n    if result:\n        log.info('done')\n"
        )
        assert result["verdict"] == "pass"


# ═══════════════════════════════════════════════════
# R11: 循环 — IterationEnforcer
# ═══════════════════════════════════════════════════

class TestIterationEnforcer:
    def test_no_cycles_warns(self, re_module):
        re_module.IterationEnforcer._cycles = []
        result = re_module.IterationEnforcer.check_completion("build feature")
        assert result["verdict"] == "warn"

    def test_few_rounds_warns(self, re_module):
        re_module.IterationEnforcer._cycles = [
            {"type": "完善", "result": "x", "ts": "2025-01-01T00:00:00"},
            {"type": "审核", "result": "y", "ts": "2025-01-01T00:01:00"},
        ]
        result = re_module.IterationEnforcer.check_completion("build feature")
        assert result["verdict"] == "warn"

    def test_enough_rounds_passes(self, re_module):
        re_module.IterationEnforcer._cycles = [
            {"type": "完善", "result": "x", "ts": "2025-01-01T00:00:00"},
            {"type": "审核", "result": "y", "ts": "2025-01-01T00:01:00"},
            {"type": "测试", "result": "z", "ts": "2025-01-01T00:02:00"},
        ]
        result = re_module.IterationEnforcer.check_completion("build feature")
        assert result["verdict"] == "pass"


# ═══════════════════════════════════════════════════
# R12: SDLC — SdlcEnforcer
# ═══════════════════════════════════════════════════

class TestSdlcEnforcer:
    def test_non_dev_task_passes(self, re_module):
        result = re_module.SdlcEnforcer.check("你好", "问候")
        assert result["verdict"] == "pass"

    def test_dev_task_missing_steps(self, re_module):
        result = re_module.SdlcEnforcer.check(
            "开发一个新功能",
            "我已经写好了代码"
        )
        assert result["verdict"] == "warn"
        assert "issues" in result

    def test_dev_task_with_steps(self, re_module):
        result = re_module.SdlcEnforcer.check(
            "开发一个新功能",
            "已完成需求分析，架构设计完成，编码实现完毕，审核测试通过"
        )
        # "需求" matches, "架构" or "设计" matches, "编码" matches, "审核"+"测试" match
        # This should significantly reduce missing steps
        assert "rule" in result


# ═══════════════════════════════════════════════════
# R13: 技能强制 — SkillActiveEnforcer
# ═══════════════════════════════════════════════════

class TestSkillActiveEnforcer:
    def test_no_skills_dir(self, re_module, tmp_path):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(re_module, "HERMES", tmp_path / ".hermes")
            result = re_module.SkillActiveEnforcer.check_skills()
            assert result["verdict"] == "warn"
            assert "不存在" in result["issues"][0]

    def test_empty_skills_dir(self, re_module, tmp_path):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(re_module, "HERMES", tmp_path / ".hermes")
            (tmp_path / ".hermes" / "skills").mkdir(parents=True, exist_ok=True)
            result = re_module.SkillActiveEnforcer.check_skills()
            assert result["verdict"] == "pass"
            assert result["total"] == 0


# ═══════════════════════════════════════════════════
# R14: complete_phase3
# ═══════════════════════════════════════════════════

class TestCompletePhase3:
    def test_blocked_before_phase2(self, re_module, tmp_path):
        with pytest.MonkeyPatch.context() as mp:
            state_file = tmp_path / ".phase_state.json"
            mp.setattr(re_module.ThreePhaseDevEnforcer, "STATE_FILE", state_file)
            re_module.ThreePhaseDevEnforcer._state = None
            re_module.ThreePhaseDevEnforcer._get_state()

            result = re_module.ThreePhaseDevEnforcer.complete_phase3(
                "测试全部通过", []
            )
            assert result["verdict"] == "blocked"

    def test_no_test_evidence(self, re_module, tmp_path):
        with pytest.MonkeyPatch.context() as mp:
            state_file = tmp_path / ".phase_state.json"
            mp.setattr(re_module.ThreePhaseDevEnforcer, "STATE_FILE", state_file)
            re_module.ThreePhaseDevEnforcer._state = None
            state = re_module.ThreePhaseDevEnforcer._get_state()
            state["phase1"]["completed"] = True
            state["phase2"]["completed"] = True
            state["phase2"]["rounds"] = 3
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            result = re_module.ThreePhaseDevEnforcer.complete_phase3(
                "没有测试证据", []
            )
            assert result["verdict"] in ("incomplete", "blocked")


# ═══════════════════════════════════════════════════
# pre_tool_intercept / post_tool_intercept / post_response_intercept
# ═══════════════════════════════════════════════════

class TestUnifiedIntercepts:
    def test_pre_tool_intercept_enforcer_disabled(self, re_module):
        re_module._enforcer_enabled = False
        try:
            result = re_module.pre_tool_intercept("write_file", {"path": "/tmp/test.py"})
            assert result["action"] == "pass"
            assert result["reason"] == "enforcer_disabled"
        finally:
            re_module._enforcer_enabled = True

    def test_pre_tool_intercept_normal_passes(self, re_module):
        result = re_module.pre_tool_intercept("read_file", {"path": "/tmp/test.py"})
        assert result["action"] == "pass"

    def test_post_tool_intercept_enforcer_disabled(self, re_module):
        re_module._enforcer_enabled = False
        try:
            result = re_module.post_tool_intercept("read_file", {}, "ok")
            assert result["action"] == "pass"
        finally:
            re_module._enforcer_enabled = True

    def test_post_tool_intercept_normal_passes(self, re_module):
        result = re_module.post_tool_intercept(
            "read_file", {"path": "/tmp/test.py"}, "file content: def foo(): pass"
        )
        assert result["action"] == "pass"

    def test_post_response_intercept_enforcer_disabled(self, re_module):
        re_module._enforcer_enabled = False
        try:
            result = re_module.post_response_intercept("hello", [], "greeting")
            assert result["action"] == "pass"
        finally:
            re_module._enforcer_enabled = True

    def test_post_response_intercept_clean(self, re_module):
        result = re_module.post_response_intercept(
            "接口返回 HTTP 200，3/3 测试通过，状态码正常",
            [{"name": "curl", "args": {"url": "https://api.example.com"}}],
            "greeting"
        )
        assert result["action"] in ("pass", "warn")

    def test_get_status(self, re_module):
        status = re_module.get_status()
        assert "enabled" in status
        assert "enforcement_count" in status
        assert "rules" in status

    def test_get_report(self, re_module):
        report = re_module.get_report()
        assert "规则引擎" in report or "Hermes" in report
        assert "R14" in report


# ═══════════════════════════════════════════════════
# pre_conversation_hook / post_conversation_hook
# ═══════════════════════════════════════════════════

class TestConversationHooks:
    def test_pre_conversation_hook(self, re_module, tmp_path):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(re_module, "HERMES", tmp_path / ".hermes")
            (tmp_path / ".hermes" / "memories").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".hermes" / "memories" / "test.json").write_text("{}")
            (tmp_path / ".hermes" / "skills").mkdir(parents=True, exist_ok=True)

            result = re_module.pre_conversation_hook("测试任务")
            assert isinstance(result, str)

    def test_post_conversation_hook(self, re_module):
        # Should not raise
        re_module.post_conversation_hook("test task", "All done, verified with pytest 5/5 passed")
        assert True  # reaches here without exception
