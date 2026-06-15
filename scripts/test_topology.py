#!/usr/bin/env python3
"""Tests for topology_engine.py — 三省六部引擎 core data structures and actors."""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HERMES_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = Path(__file__).parent
if str(HERMES_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from topology_engine import (
    BingBu,
    GongBu,
    HuBu,
    LiBu,
    LiBuRegister,
    MenxiaSheng,
    Ministry,
    MinistryActor,
    TaskDAG,
    TaskNode,
    TaskStatus,
    TopologyEngine,
    XingBu,
    ZhongshuSheng,
)
from synapse_bus import SynapseBus
from actor_base import ActorPriority, Event


@pytest.fixture
def mock_bus():
    """A SynapseBus with all dangerous methods pre-mocked."""
    bus = MagicMock(spec=SynapseBus)
    bus.emit.return_value = {"status": "ok"}
    bus.get_stats.return_value = {"actors": 0}
    return bus


# ======================== Ministry Enum ========================

class TestMinistryEnum:
    def test_six_ministries(self):
        values = [m.value for m in Ministry]
        assert len(values) == 6

    def test_expected_values(self):
        expected = {"gongbu", "hubu", "libu", "bingbu", "xingbu", "libu_reg"}
        assert {m.value for m in Ministry} == expected

    def test_access_by_value(self):
        assert Ministry("gongbu") == Ministry.GONGBU
        assert Ministry("hubu") == Ministry.HUBU


# ======================== TaskStatus Enum ========================

class TestTaskStatusEnum:
    def test_eight_statuses(self):
        assert len(list(TaskStatus)) == 8

    def test_expected_values(self):
        expected = {"planning", "validating", "dispatched", "running",
                     "completed", "failed", "retrying", "cancelled"}
        assert {s.value for s in TaskStatus} == expected


# ======================== TaskNode ========================

class TestTaskNode:
    def test_default_values(self):
        node = TaskNode(id="test-1", description="A test node", event_type="test.run")
        assert node.id == "test-1"
        assert node.description == "A test node"
        assert node.event_type == "test.run"
        assert node.payload == {}
        assert node.depends_on == []
        assert node.status == TaskStatus.PLANNING
        assert node.retry_count == 0
        assert node.max_retries == 3
        assert node.result is None
        assert node.error is None

    def test_custom_payload_and_deps(self):
        node = TaskNode(
            id="n2",
            description="dep node",
            event_type="ev.dep",
            payload={"k": "v"},
            depends_on=["n1"],
            timeout=60.0,
        )
        assert node.payload == {"k": "v"}
        assert node.depends_on == ["n1"]
        assert node.timeout == 60.0

    def test_repr_contains_id(self):
        node = TaskNode(id="repr-test", description="x", event_type="t.x")
        assert "repr-test" in repr(node)


# ======================== TaskDAG ========================

class TestTaskDAG:
    def test_dag_creation(self):
        dag = TaskDAG(id="dag-1", name="Test DAG")
        assert dag.id == "dag-1"
        assert dag.name == "Test DAG"
        assert dag.nodes == {}
        assert dag.status == "created"
        assert dag.created_at != ""

    def test_add_node(self):
        dag = TaskDAG(id="dag-2", name="Test")
        node = TaskNode(id="n1", description="d", event_type="ev.d")
        dag.add_node(node)
        assert "n1" in dag.nodes
        assert dag.nodes["n1"] is node

    def test_get_ready_nodes_none_ready(self):
        # All nodes have unmet dependencies: n3 -> n1 -> n2 -> n3 (cycle, but none COMPLETED)
        dag = TaskDAG(id="dag-3", name="Test")
        n3 = TaskNode("n3", "blocker", "ev.blocker", depends_on=["n1"])
        n3.status = TaskStatus.PLANNING
        dag.add_node(TaskNode("n1", "d1", "ev.d1", depends_on=["n2"]))
        dag.add_node(TaskNode("n2", "dep", "ev.dep", depends_on=["n3"]))
        dag.add_node(n3)
        ready = dag.get_ready_nodes()
        assert len(ready) == 0

    def test_get_ready_nodes_no_deps(self):
        dag = TaskDAG(id="dag-4", name="Test")
        node = TaskNode("n1", "d1", "ev.d1")
        dag.add_node(node)
        ready = dag.get_ready_nodes()
        assert ready == [node]

    def test_get_ready_nodes_dep_satisfied(self):
        dag = TaskDAG(id="dag-5", name="Test")
        n2 = TaskNode("n2", "dep", "ev.dep")
        n2.status = TaskStatus.COMPLETED
        n1 = TaskNode("n1", "main", "ev.main", depends_on=["n2"])
        dag.add_node(n1)
        dag.add_node(n2)
        ready = dag.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "n1"

    def test_completion_empty(self):
        dag = TaskDAG(id="dag-6", name="Test")
        assert dag.get_completion() == 0

    def test_completion_partial(self):
        dag = TaskDAG(id="dag-7", name="Test")
        n1 = TaskNode("n1", "d1", "ev.d1")
        n2 = TaskNode("n2", "d2", "ev.d2")
        n1.status = TaskStatus.COMPLETED
        dag.add_node(n1)
        dag.add_node(n2)
        assert dag.get_completion() == 0.5

    def test_to_dict_structure(self):
        dag = TaskDAG(id="dag-8", name="Test")
        n = TaskNode("n1", "a task node", "ev.n1")
        dag.add_node(n)
        d = dag.to_dict()
        assert d["id"] == "dag-8"
        assert d["name"] == "Test"
        assert "n1" in d["nodes"]
        assert d["progress"] == 0.0
        assert d["status"] == "created"


# ======================== ZhongshuSheng ========================

class TestZhongshuSheng:
    def test_init(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs.id == "zhongshusheng"
        assert zs.priority == ActorPriority.CRITICAL

    def test_detect_intent_analysis(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._detect_intent("分析市场趋势") == "analysis"

    def test_detect_intent_data_collection(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._detect_intent("采集最新数据") == "data_collection"

    def test_detect_intent_generation(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._detect_intent("生成一份报告") == "generation"

    def test_detect_intent_search(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._detect_intent("搜索最新AI论文") == "search"

    def test_detect_intent_monitoring(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._detect_intent("监控竞品动态") == "monitoring"

    def test_detect_intent_default(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._detect_intent("hello world") == "general"

    def test_extract_dimensions(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        dims = zs._extract_dimensions("AI市场分析技术报告图表")
        assert "market_intelligence" in dims
        assert "technology" in dims
        assert "reporting" in dims
        assert "visualization" in dims

    def test_extract_dimensions_fallback(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        dims = zs._extract_dimensions("xyz")
        assert dims == ["general"]

    def test_estimate_complexity(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._estimate_complexity("short") == "low"
        assert zs._estimate_complexity("x" * 90) == "medium"
        assert zs._estimate_complexity("x" * 250) == "high"

    def test_suggest_ministries(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        ministries = zs._suggest_ministries("爬取浏览器页面线程并行重试")
        assert "hubu" in ministries
        assert "gongbu" in ministries
        assert "bingbu" in ministries
        assert "xingbu" in ministries

    def test_suggest_ministries_fallback(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs._suggest_ministries("nothing special") == ["hubu"]

    def test_analyze_requirement(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        result = zs._analyze_requirement({"text": "分析AI市场趋势"})
        assert result["intent"] == "analysis"
        assert isinstance(result["dimensions"], list)
        assert result["complexity"] in ("low", "medium", "high")
        assert isinstance(result["suggested_ministries"], list)

    def test_decompose(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        result = zs._decompose({"text": "test query"})
        assert result["status"] == "decomposed"
        assert len(result["subtasks"]) == 3

    def test_plan_task_analysis(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        dag = zs._plan_task({"text": "分析AI市场趋势"})
        assert isinstance(dag, TaskDAG)
        assert len(dag.nodes) >= 3

    def test_plan_task_caches_dag(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        dag = zs._plan_task({"text": "分析AI市场趋势"})
        cached = zs.get_dag(dag.id)
        assert cached is dag

    def test_handle_unknown_event(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        result = zs.handle(Event(type="unknown.stuff", payload={}))
        assert "error" in result

    def test_get_dag_nonexistent(self, mock_bus):
        zs = ZhongshuSheng(mock_bus)
        assert zs.get_dag("nonexistent") is None


# ======================== MenxiaSheng ========================

class TestMenxiaSheng:
    def test_init(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        assert ms.id == "menxiasheng"
        assert ms.priority == ActorPriority.CRITICAL

    def test_validate_result_none(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._validate_result({"result": None, "node_id": "n1"})
        assert result["valid"] is False
        assert "result_is_none" in result["issues"]

    def test_validate_result_empty_string(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._validate_result({"result": "   ", "node_id": "n1"})
        assert result["valid"] is False
        assert "result_is_empty" in result["issues"]

    def test_validate_result_ok(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._validate_result({"result": "hello world", "node_id": "n1"})
        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_result_expected_missing(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._validate_result({
            "result": "hello",
            "expected": "world",
            "node_id": "n1",
        })
        assert result["valid"] is False
        assert any("expected_content_missing" in i for i in result["issues"])

    def test_validate_schema_ok(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._validate_schema({
            "data": {"a": 1, "b": 2},
            "schema": {"required": ["a", "b"]},
        })
        assert result["valid"] is True
        assert result["missing_fields"] == []

    def test_validate_schema_missing(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._validate_schema({
            "data": {"a": 1},
            "schema": {"required": ["a", "b"]},
        })
        assert result["valid"] is False
        assert "b" in result["missing_fields"]

    def test_estimate_cost_low(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        cost = ms._estimate_cost({"type": "hubu.fetch", "complexity": "low"})
        assert cost["estimated_tokens"] == 100
        assert cost["acceptable"] is True

    def test_estimate_cost_high(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        cost = ms._estimate_cost({"type": "libu.report", "complexity": "high"})
        assert cost["estimated_tokens"] == 12000
        assert cost["acceptable"] is False

    def test_should_retry_under_limit(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._should_retry(
            {"retry_count": 1, "max_retries": 3, "error": "timeout"}
        )
        assert result["should_retry"] is True

    def test_should_retry_exceeded(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._should_retry(
            {"retry_count": 3, "max_retries": 3, "error": "timeout"}
        )
        assert result["should_retry"] is False

    def test_should_retry_non_retryable(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms._should_retry(
            {"retry_count": 0, "max_retries": 3, "error": "schema_mismatch"}
        )
        assert result["should_retry"] is False

    def test_handle_unknown_event(self, mock_bus):
        ms = MenxiaSheng(mock_bus)
        result = ms.handle(Event(type="unknown.stuff", payload={}))
        assert result["valid"] is False


# ======================== Ministry Actors ========================

class TestGongBu:
    def test_init(self):
        gb = GongBu()
        assert gb.id == "ministry:gongbu"
        assert len(gb.capabilities) == 4

    def test_execute_browser(self):
        gb = GongBu()
        result = gb.execute("gongbu", "browser", {"url": "http://example.com"})
        assert result["action"] == "browser_open"
        assert result["url"] == "http://example.com"

    def test_execute_navigate(self):
        gb = GongBu()
        result = gb.execute("gongbu", "navigate", {"url": "http://test.com"})
        assert result["action"] == "navigate"

    def test_execute_unknown(self):
        gb = GongBu()
        result = gb.execute("gongbu", "unknown_action", {"x": 1})
        assert "gongbu.unknown_action" in str(result["action"])


class TestHuBu:
    def test_init(self):
        hb = HuBu()
        assert hb.id == "ministry:hubu"
        assert len(hb.capabilities) == 4

    def test_execute_fetch(self):
        hb = HuBu()
        result = hb.execute("hubu", "fetch", {"query": "AI trends"})
        assert result["status"] == "fetched"

    def test_execute_search(self):
        hb = HuBu()
        result = hb.execute("hubu", "search", {"query": "AI trends"})
        assert result["status"] == "searched"

    def test_cache_starts_empty(self):
        hb = HuBu()
        result = hb.execute("hubu", "fetch", {"query": "AI trends"})
        # _cache is never populated by fetch (design placeholder), so cache_hit is always False
        assert result["status"] == "fetched"
        assert result["cache_hit"] is False


class TestLiBu:
    def test_init(self):
        lb = LiBu()
        assert lb.id == "ministry:libu"

    def test_execute_write(self):
        lb = LiBu()
        result = lb.execute("libu", "write", {"text": "hello world"})
        assert result["status"] == "written"
        assert result["length"] == 11

    def test_execute_report(self):
        lb = LiBu()
        result = lb.execute("libu", "report", {"format": "pdf"})
        assert result["status"] == "report_generated"

    def test_execute_format(self):
        lb = LiBu()
        result = lb.execute("libu", "format", {"format": "html"})
        assert result["status"] == "formatted"


class TestBingBu:
    def test_init(self):
        bb = BingBu()
        assert bb.id == "ministry:bingbu"

    def test_execute_route(self):
        bb = BingBu()
        result = bb.execute("bingbu", "route", {"preferred_model": "gpt-4"})
        assert result["status"] == "routed"
        assert result["model"] == "gpt-4"

    def test_execute_compress(self):
        bb = BingBu()
        result = bb.execute("bingbu", "compress", {"ratio": 0.3})
        assert result["ratio"] == 0.3


class TestXingBu:
    def test_init(self, mock_bus):
        xb = XingBu(mock_bus)
        assert xb.id == "ministry:xingbu"
        assert xb._error_log == []

    def test_execute_retry(self, mock_bus):
        xb = XingBu(mock_bus)
        result = xb.execute("xingbu", "retry", {"backoff": 5})
        assert result["status"] == "retry_scheduled"

    def test_execute_fallback(self, mock_bus):
        xb = XingBu(mock_bus)
        result = xb.execute("xingbu", "fallback", {"alternative": "mock"})
        assert result["status"] == "fallback_activated"

    def test_execute_logs_error(self, mock_bus):
        xb = XingBu(mock_bus)
        xb.execute("xingbu", "retry", {"backoff": 10})
        assert len(xb._error_log) == 1

    def test_get_recent_errors(self, mock_bus):
        xb = XingBu(mock_bus)
        for i in range(5):
            xb.execute("xingbu", "retry", {"backoff": i})
        recent = xb.get_recent_errors(limit=3)
        assert len(recent) == 3

    def test_handle_error_actor_failure(self, mock_bus):
        xb = XingBu(mock_bus)
        result = xb.handle(Event(
            type="error.actor_failure",
            payload={"actor_id": "a1", "error": "timeout"},
        ))
        assert result is not None


class TestLiBuRegister:
    def test_init(self):
        lr = LiBuRegister()
        assert lr.id == "ministry:libu_reg"

    def test_register_skill(self):
        lr = LiBuRegister()
        result = lr.execute("libu_reg", "register", {"name": "test-skill"})
        assert result["status"] == "registered"

    def test_list_skills(self):
        lr = LiBuRegister()
        lr.execute("libu_reg", "register", {"name": "skill-a"})
        lr.execute("libu_reg", "register", {"name": "skill-b"})
        result = lr.execute("libu_reg", "list", {})
        assert "skill-a" in result["skills"]
        assert "skill-b" in result["skills"]

    def test_deregister_skill(self):
        lr = LiBuRegister()
        lr.execute("libu_reg", "register", {"name": "to-remove"})
        result = lr.execute("libu_reg", "deregister", {"name": "to-remove"})
        assert result["status"] == "deregistered"
        list_result = lr.execute("libu_reg", "list", {})
        assert "to-remove" not in list_result["skills"]

    def test_status(self):
        lr = LiBuRegister()
        result = lr.execute("libu_reg", "status", {})
        assert result["status"] == "active"
        assert result["count"] == 0


# ======================== TopologyEngine ========================

class TestTopologyEngine:
    def test_init_with_mock_bus(self, mock_bus):
        with patch("topology_engine.os.path.exists", return_value=False):
            engine = TopologyEngine(bus=mock_bus)
            assert engine.bus is mock_bus
            assert "zhongshu" in engine.zhongshu.id
            assert "menxia" in engine.menxia.id
            assert len(engine.ministries) == 6

    def test_load_yaml_defaults(self, mock_bus):
        with patch("topology_engine.os.path.exists", return_value=False):
            engine = TopologyEngine(bus=mock_bus)
            config = engine._config
            assert "planning" in config
            assert "validation" in config
            assert "ministries" in config
            assert config["validation"]["auto_retry"] is True
            assert config["validation"]["max_retries"] == 3

    def test_get_status(self, mock_bus):
        with patch("topology_engine.os.path.exists", return_value=False):
            engine = TopologyEngine(bus=mock_bus)
            status = engine.get_status()
            assert "config" in status
            assert "actors" in status
            assert "ministries" in status

    def test_hot_reload(self, mock_bus):
        with patch("topology_engine.os.path.exists", return_value=False):
            engine = TopologyEngine(bus=mock_bus)
            engine.hot_reload()
            assert engine._config is not None
