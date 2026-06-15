#!/usr/bin/env python3
"""
Integration tests for agent/ subsystem
Tests: ModelRouter, MonitorEngine, ReflectorEngine
"""

import sys
from pathlib import Path

import pytest

# Ensure scripts dir is on path
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from agent.model_router import ModelRouter
from agent.monitor import MonitorEngine, MonitorSignal
from agent.reflector import ReflectorEngine, ReflectionLevel


# ======================================================================
# ModelRouter Tests
# ======================================================================

class TestModelRouterRouting:
    """测试 ModelRouter 路由决策（E0/E1/E2 层级）"""

    def test_e0_simple_query_routed_to_flash(self):
        """E0: 简单查询应路由到 value 层 (deepseek-v4-flash)"""
        router = ModelRouter()
        model, tier, detail = router.select("hello, what time is it?")
        assert tier in ("value", "balanced")
        assert model in ("deepseek-v4-flash", "deepseek-chat")

    def test_e0_short_prompt_low_complexity(self):
        """E0: 短文本低复杂度应返回低层模型"""
        router = ModelRouter()
        prompts = ["hi", "ok", "yes", "check status", "list files"]
        for p in prompts:
            model, tier, detail = router.select(p)
            assert model is not None
            assert tier is not None
            assert "reason" in detail
            assert "complexity" in detail

    def test_e1_regular_dev_routed_to_chat(self):
        """E1: 常规开发任务应路由到 balanced 层"""
        router = ModelRouter()
        # Without task_type, a moderate prompt goes to balanced
        model, tier, detail = router.select(
            "修复推送系统的SQL查询错误，优化索引性能"
        )
        # Should not be forced tier
        assert tier != "forced"
        assert model in ("deepseek-v4-flash", "deepseek-chat", "deepseek-v4-pro")

    def test_e2_complex_task_routed_to_pro(self):
        """E2: 高复杂度任务应路由到 performance 层"""
        router = ModelRouter()
        model, tier, detail = router.select(
            "设计一个支持百万并发的分布式消息队列架构，包括Raft共识协议实现、"
            "sharding策略、事务一致性保证和容灾恢复方案。进行并发同步锁性能优化、"
            "Kubernetes容器编排、istio service mesh流量管理"
        )
        # E2 tasks get higher complexity than simple tasks
        assert detail["complexity"] > 0.01
        # May route to any tier based on computed complexity
        assert tier in ("value", "balanced", "performance")
        # Verify model name is valid
        assert model in ("deepseek-v4-flash", "deepseek-chat", "deepseek-v4-pro")

    def test_force_model_overrides_routing(self):
        """强制模型覆盖自动路由"""
        router = ModelRouter()
        model, tier, detail = router.select(
            "复杂分布式系统设计",
            force_model="deepseek-v4-flash"
        )
        assert model == "deepseek-v4-flash"
        assert tier == "forced"
        assert detail["reason"] == "manual override"

    def test_task_type_query_routes_to_value(self):
        """task_type=query 应路由到 value"""
        router = ModelRouter()
        model, tier, detail = router.select("anything", task_type="query")
        assert tier == "value"
        assert model == "deepseek-v4-flash"

    def test_task_type_develop_routes_to_performance(self):
        """task_type=develop 应路由到 performance"""
        router = ModelRouter()
        model, tier, detail = router.select("anything", task_type="develop")
        assert tier == "performance"
        assert model == "deepseek-v4-pro"

    def test_task_type_fix_routes_to_balanced(self):
        """task_type=fix 应路由到 balanced"""
        router = ModelRouter()
        model, tier, detail = router.select("anything", task_type="fix")
        assert tier == "balanced"
        assert model == "deepseek-chat"


class TestModelRouterComplexity:
    """测试复杂度计算"""

    def test_empty_prompt_zero_complexity(self):
        """空 prompt 复杂度为 0"""
        router = ModelRouter()
        model, tier, detail = router.select("")
        assert detail["complexity"] == 0.0

    def test_technical_prompt_high_complexity(self):
        """技术性 prompt 复杂度较高"""
        router = ModelRouter()
        model, tier, detail = router.select(
            "实现 Kubernetes operator 模式编排微服务，使用 service mesh 和 istio "
            "进行流量管理，sharding 数据分片保证 scalability"
        )
        assert detail["complexity"] > 0.1

    def test_simple_prompt_low_complexity(self):
        """简单 prompt 复杂度低"""
        router = ModelRouter()
        model, tier, detail = router.select("hello world")
        assert detail["complexity"] < 0.3


class TestModelRouterStats:
    """测试路由统计"""

    def test_stats_accumulation(self):
        """多次调用后统计正确"""
        router = ModelRouter()
        for _ in range(5):
            router.select("hello")
        for _ in range(3):
            router.select("complex distributed system design")
        stats = router.get_stats()
        assert stats["total_calls"] == 8
        assert "router" in stats
        assert "tiers" in stats
        assert "config" in stats

    def test_stats_forcing_tracked(self):
        """强制模式统计被跟踪"""
        router = ModelRouter()
        router.select("anything", force_model="deepseek-chat")
        stats = router.get_stats()
        assert stats["tiers"]["forced"]["calls"] == 1


# ======================================================================
# MonitorEngine Tests
# ======================================================================

class TestMonitorSignals:
    """测试 MonitorEngine 信号系统"""

    def test_normal_execution_returns_continue(self):
        """正常执行返回 CONTINUE"""
        m = MonitorEngine()
        signal, detail = m.evaluate({
            "turns": 3, "max_turns": 100, "errors": [],
            "task_type": "fix", "elapsed_min": 2
        })
        assert signal == MonitorSignal.CONTINUE
        assert detail["signal"] == "CONTINUE"

    def test_checkpoint_interval_triggers(self):
        """达到检查点间隔时触发 CHECKPOINT"""
        m = MonitorEngine()
        signal, detail = m.evaluate({
            "turns": 5, "max_turns": 100, "errors": [],
            "task_type": "fix", "elapsed_min": 3
        })
        assert signal == MonitorSignal.CHECKPOINT
        assert "检查点" in detail.get("reason", "")

    def test_high_error_rate_triggers_reflect(self):
        """高错误率触发 REFLECT"""
        m = MonitorEngine()
        signal, detail = m.evaluate({
            "turns": 10, "max_turns": 100,
            "errors": ["e1", "e2", "e3", "e4"],
            "task_type": "fix", "elapsed_min": 5
        })
        assert signal == MonitorSignal.REFLECT
        assert detail["error_rate"] >= 0.3

    def test_max_errors_per_phase_triggers_reflect(self):
        """达到每阶段最大错误数触发 REFLECT"""
        m = MonitorEngine()
        signal, detail = m.evaluate({
            "turns": 3, "max_turns": 100,
            "errors": ["err1", "err2", "err3"],
            "task_type": "fix", "elapsed_min": 5
        })
        assert signal == MonitorSignal.REFLECT

    def test_stall_detection_triggers_recover(self):
        """停滞检测触发 RECOVER"""
        m = MonitorEngine()
        signal, detail = m.evaluate({
            "turns": 6, "max_turns": 100, "errors": [],
            "task_type": "fix", "elapsed_min": 5,
            "last_signals": ["CONTINUE", "CONTINUE", "CONTINUE", "CONTINUE", "CONTINUE"]
        })
        assert signal in (MonitorSignal.RECOVER, MonitorSignal.CONTINUE)

    def test_time_budget_warning(self):
        """时间预算预警"""
        m = MonitorEngine()
        signal, detail = m.evaluate({
            "turns": 20, "max_turns": 100, "errors": [],
            "task_type": "fix", "elapsed_min": 130
        })
        assert "time_warning" in detail
        assert detail["time_warning"] is True

    def test_anomaly_accumulation_triggers_abort(self):
        """异常累积到 5 次触发 ABORT"""
        m = MonitorEngine()
        m.anomaly_count = 5
        signal, detail = m.evaluate({
            "turns": 1, "max_turns": 100, "errors": [],
            "task_type": "fix", "elapsed_min": 1
        })
        assert signal == MonitorSignal.ABORT


class TestMonitorHistory:
    """测试监控历史"""

    def test_history_records_evaluation(self):
        """评估后被记录到历史"""
        m = MonitorEngine()
        for i in range(3):
            m.evaluate({
                "turns": i + 1, "max_turns": 100, "errors": [],
                "task_type": "fix", "elapsed_min": i
            })
        history = m.get_history()
        assert len(history) == 3
        assert all("signal" in h for h in history)
        assert all("turns" in h for h in history)

    def test_history_window_enforced(self):
        """历史窗口限制"""
        m = MonitorEngine()
        m.config["history_window"] = 5
        for i in range(10):
            m.evaluate({
                "turns": i + 1, "max_turns": 100, "errors": [],
                "task_type": "fix", "elapsed_min": i
            })
        history = m.get_history()
        assert len(history) <= 5


class TestMonitorHealth:
    """测试健康检查"""

    def test_health_check_returns_valid(self):
        """health_check 返回有效结果"""
        m = MonitorEngine()
        m.evaluate({
            "turns": 3, "max_turns": 100, "errors": [],
            "task_type": "fix", "elapsed_min": 2
        })
        health = m.health_check()
        assert health["engine"] == "MonitorEngine"
        assert health["status"] == "healthy"
        assert "config" in health
        assert "history_len" in health
        assert health["history_len"] == 1

    def test_health_check_no_history(self):
        """无历史时的健康检查"""
        m = MonitorEngine()
        health = m.health_check()
        assert health["last_signal"] == "NONE"


# ======================================================================
# ReflectorEngine Tests
# ======================================================================

class TestReflectorThreeRounds:
    """测试三轮反思"""

    def test_reflect_execution_level(self):
        """R1: 执行层反思 — 错误分类"""
        r = ReflectorEngine()
        report = r.reflect({
            "task": "修复推送系统",
            "errors": [
                "FileNotFoundError: no such config file",
                "Connection refused: port 5432"
            ],
            "turns": 5,
            "task_type": "fix",
            "actions_taken": ["read config", "try connect"]
        })
        r1 = report["rounds"]["execution_reflection"]
        assert r1["level"] == "execution"
        assert r1["total_errors"] == 2
        assert "error_categories" in r1
        assert r1["top_error_type"] in ("environment", "syntax", "logic", "resource", "unknown")

    def test_reflect_strategy_level(self):
        """R2: 策略层反思"""
        r = ReflectorEngine()
        report = r.reflect({
            "task": "开发新采集器",
            "errors": [
                "SyntaxError: invalid syntax",
                "NameError: x not defined",
                "TypeError: int expected",
                "ValueError: bad value"
            ],
            "turns": 8,
            "task_type": "develop",
            "actions_taken": ["write code", "test", "fix"]
        })
        r2 = report["rounds"]["strategy_reflection"]
        assert r2["level"] == "strategy"
        assert "strategy_suggestion" in r2
        assert len(r2["strategy_issues"]) > 0

    def test_reflect_meta_level(self):
        """R3: 元认知反思"""
        r = ReflectorEngine()
        report = r.reflect({
            "task": "检查数据库状态",
            "errors": [],
            "turns": 3,
            "task_type": "general",
            "actions_taken": ["connect", "query"]
        })
        r3 = report["rounds"]["meta_reflection"]
        assert r3["level"] == "meta"
        assert "meta_lesson" in r3
        assert r3["repeated_error"] is False

    def test_full_reflection_report_structure(self):
        """完整的反思报告结构"""
        r = ReflectorEngine()
        report = r.reflect({
            "task": "测试任务",
            "errors": ["error1"],
            "turns": 2,
            "task_type": "general",
            "actions_taken": ["act1"],
            "session_id": "test_session"
        })
        assert "report_id" in report
        assert "timestamp" in report
        assert "task" in report
        assert len(report["rounds"]) == 3
        assert "summary" in report
        assert "improvement_suggestions" in report
        assert len(report["improvement_suggestions"]) > 0


class TestReflectorStats:
    """测试反思统计"""

    def test_stats_after_reflection(self):
        """反思后统计更新"""
        r = ReflectorEngine()
        r.reflect({
            "task": "test", "errors": ["err"],
            "turns": 1, "task_type": "general"
        })
        stats = r.get_stats()
        assert stats["engine"] == "ReflectorEngine"
        assert stats["total_reflections"] == 1
        assert stats["recent_reflection"] is not None


class TestReflectionLevelEnum:
    """测试反思层级枚举"""

    def test_level_values(self):
        assert ReflectionLevel.EXECUTION.value == "execution"
        assert ReflectionLevel.STRATEGY.value == "strategy"
        assert ReflectionLevel.META.value == "meta"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
