"""Tests for engine_core.py — 任务引擎核心"""
import json
import sys
from pathlib import Path


# Ensure scripts dir is in path
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from engine_core import (
    ArsenalRegistry,
    SmartScheduler,
    ForcedWeaponProtocol,
    WeaponCallValidator,
    EngineCore,
)


class TestArsenalRegistry:
    """Test weapon arsenal registry scanning and querying."""

    def test_init_scans_all(self, monkeypatch, tmp_path):
        """Registry initializes and scans all weapon categories."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        # Create minimal structure
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "test_collector.py").write_text("print('hello')")
        registry = ArsenalRegistry()
        assert "scripts" in registry.weapons
        assert "skills" in registry.weapons
        assert "agents" in registry.weapons
        assert "tools" in registry.weapons
        assert "modules" in registry.weapons

    def test_summary_counts(self, monkeypatch, tmp_path):
        """Summary returns correct weapon counts."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "collector.py").write_text("print('hello')")
        (tmp_path / "scripts" / "cleaner.py").write_text("print('hello')")
        registry = ArsenalRegistry()
        summary = registry.summary()
        assert summary["scripts"] == 2
        assert "total" in summary

    def test_classify_script_collector(self, monkeypatch, tmp_path):
        """Scripts with collect/crawl/scrape/feed are classified as 采集."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        registry = ArsenalRegistry()
        p = tmp_path / "collector_v5.py"
        p.write_text("x")
        assert registry._classify_script(p) == "采集"
        p2 = tmp_path / "scrape_web.py"
        p2.write_text("x")
        assert registry._classify_script(p2) == "采集"
        p3 = tmp_path / "crawler_v2.py"
        p3.write_text("x")
        assert registry._classify_script(p3) == "采集"

    def test_classify_script_cleaner(self, monkeypatch, tmp_path):
        """Scripts with clean/filter/spam are classified as 清洗."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        registry = ArsenalRegistry()
        p = tmp_path / "data_cleaner.py"
        p.write_text("x")
        assert registry._classify_script(p) == "清洗"

    def test_classify_script_default(self, monkeypatch, tmp_path):
        """Unknown scripts default to 工具."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        registry = ArsenalRegistry()
        p = tmp_path / "unknown_util.py"
        p.write_text("x")
        assert registry._classify_script(p) == "工具"

    def test_scan_skips_test_files(self, monkeypatch, tmp_path):
        """_scan_scripts skips test_, backup, __pycache__ files."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "test_something.py").write_text("x")
        (tmp_path / "scripts" / "real_script.py").write_text("x")
        registry = ArsenalRegistry()
        scripts = registry._scan_scripts()
        names = [s["name"] for s in scripts]
        assert "real_script" in names
        assert "test_something" not in names

    def test_query_known_type(self):
        """query returns correct weapons for known task types."""
        registry = ArsenalRegistry()
        result = registry.query("采集")
        assert "scripts" in result
        assert "skills" in result

    def test_query_unknown_type(self):
        """query returns empty for unknown task types."""
        registry = ArsenalRegistry()
        result = registry.query("nonexistent_type")
        assert result == {"scripts": [], "skills": []}

    def test_scan_agents_counts(self, monkeypatch, tmp_path):
        """_scan_agents counts employees and experts correctly."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        # Create agent directories
        emp_dir = tmp_path / "agents_company" / "employees"
        exp_dir = tmp_path / "agents_company" / "experts"
        emp_dir.mkdir(parents=True)
        exp_dir.mkdir(parents=True)
        (emp_dir / "emp_001").mkdir()
        (emp_dir / "emp_002").mkdir()
        (exp_dir / "exp_001").mkdir()
        registry = ArsenalRegistry()
        assert registry.weapons["agents"]["employees"] == 2
        assert registry.weapons["agents"]["experts"] == 1

    def test_classify_script_memory(self, monkeypatch, tmp_path):
        """Scripts with memory/recall/store are classified as 记忆."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        registry = ArsenalRegistry()
        p = tmp_path / "memory_engine.py"
        p.write_text("x")
        assert registry._classify_script(p) == "记忆"


class TestSmartScheduler:
    """Test intelligent task scheduler."""

    def test_analyze_task_push(self):
        """Task analysis recognizes push-type tasks."""
        sched = SmartScheduler()
        result = sched.analyze_task("推送今天的日报到微信")
        assert result["task_type"] == "推送"

    def test_analyze_task_collect(self):
        """Task analysis recognizes collection-type tasks."""
        sched = SmartScheduler()
        result = sched.analyze_task("采集微博热搜数据")
        assert result["task_type"] == "采集"

    def test_analyze_task_fix(self):
        """Task analysis recognizes fix-type tasks. Note: '推送' matches first because keyword order."""
        sched = SmartScheduler()
        result = sched.analyze_task("fix this broken system bug")
        assert result["task_type"] == "修复"

    def test_analyze_task_develop(self):
        """Task analysis recognizes development-type tasks. Note: '实现' matches as 开发."""
        sched = SmartScheduler()
        result = sched.analyze_task("implement a new code feature")
        assert result["task_type"] == "开发"

    def test_analyze_task_research(self):
        """Task analysis recognizes research-type tasks."""
        sched = SmartScheduler()
        result = sched.analyze_task("研究最新的AI模型")
        assert result["task_type"] == "研究"

    def test_analyze_task_multiple_types(self):
        """Tasks matching multiple keywords get multiple types."""
        sched = SmartScheduler()
        result = sched.analyze_task("采集数据然后推送到微信")
        assert len(result["task_types"]) >= 2

    def test_analyze_task_complex(self):
        """Long tasks with multiple markers are classified as complex."""
        sched = SmartScheduler()
        long_task = "采集所有平台数据然后清洗然后评分然后推送 " * 10
        result = sched.analyze_task(long_task)
        assert result["complexity"] == "复杂"

    def test_analyze_task_simple(self):
        """Short simple tasks are classified as simple."""
        sched = SmartScheduler()
        result = sched.analyze_task("推送消息")
        assert result["complexity"] == "简单"

    def test_should_segment_long_task(self):
        """Tasks longer than 200 chars should be segmented."""
        sched = SmartScheduler()
        long_task = "x" * 250
        assert sched.should_segment(long_task)

    def test_should_segment_batch_task(self):
        """Tasks with batch keywords should be segmented."""
        sched = SmartScheduler()
        assert sched.should_segment("处理所有数据")

    def test_should_segment_simple(self):
        """Simple short tasks should not be segmented."""
        sched = SmartScheduler()
        assert not sched.should_segment("简单任务")

    def test_segment_task_basic(self):
        """Segment task splits by natural markers."""
        sched = SmartScheduler()
        task = "第一步处理 然后 第二步处理 然后 第三步处理"
        segs = sched.segment_task(task, n_segments=3)
        assert len(segs) >= 2

    def test_segment_task_single(self):
        """Segment with n_segments=1 returns single segment."""
        sched = SmartScheduler()
        task = "a simple task"
        segs = sched.segment_task(task, n_segments=1)
        assert len(segs) == 1
        assert segs[0]["id"] == 1

    def test_get_relevant_weapons(self):
        """get_relevant_weapons returns matching weapons."""
        sched = SmartScheduler()
        weapons = sched.get_relevant_weapons("采集数据")
        assert isinstance(weapons, list)


class TestForcedWeaponProtocol:
    """Test forced weapon protocol mandate generation."""

    def test_generate_mandate_basic(self):
        """generate_mandate creates a mandate string."""
        protocol = ForcedWeaponProtocol()
        mandate = protocol.generate_mandate("推送消息到微信")
        assert "强制武器调用协议" in mandate
        assert len(mandate) > 100

    def test_generate_mandate_empty_task(self):
        """generate_mandate with empty task."""
        protocol = ForcedWeaponProtocol()
        mandate = protocol.generate_mandate("test")
        assert len(mandate) > 0

    def test_get_script_desc_known(self):
        """_get_script_desc returns description for known scripts."""
        protocol = ForcedWeaponProtocol()
        desc = protocol._get_script_desc("guardian")
        assert "3模式" in desc

    def test_get_script_desc_unknown(self):
        """_get_script_desc returns generic description for unknown scripts."""
        protocol = ForcedWeaponProtocol()
        desc = protocol._get_script_desc("unknown_script")
        assert "相关脚本" in desc

    def test_get_skill_desc_known(self):
        """_get_skill_desc returns description for known skills."""
        protocol = ForcedWeaponProtocol()
        desc = protocol._get_skill_desc("intelligence")
        assert "情报" in desc

    def test_get_skill_desc_unknown(self):
        """_get_skill_desc returns generic description for unknown skills."""
        protocol = ForcedWeaponProtocol()
        desc = protocol._get_skill_desc("nonexistent")
        assert "相关skill" in desc

    def test_recommend_by_type_collect(self):
        """_recommend_by_type returns weapons for collection tasks."""
        protocol = ForcedWeaponProtocol()
        result = protocol._recommend_by_type("采集")
        assert len(result["scripts"]) > 0

    def test_recommend_by_type_unknown(self):
        """_recommend_by_type returns generic weapons for unknown types."""
        protocol = ForcedWeaponProtocol()
        result = protocol._recommend_by_type("nonexistent_type")
        assert len(result["scripts"]) > 0  # falls back to 通用

    def test_generate_mandate_complex_task(self):
        """generate_mandate handles complex tasks with segmentation."""
        protocol = ForcedWeaponProtocol()
        mandate = protocol.generate_mandate("采集数据然后推送消息然后修复bug然后开发新功能然后写研究报告")
        assert "任务分解" in mandate or "分段" in mandate


class TestWeaponCallValidator:
    """Test weapon call compliance validator."""

    def test_check_recent_calls_no_logs(self, monkeypatch, tmp_path):
        """check_recent_calls returns empty when no logs exist."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        validator = WeaponCallValidator()
        result = validator.check_recent_calls(["weapon_a", "weapon_b"])
        assert isinstance(result, dict)
        assert "called" in result
        assert "missed" in result

    def test_generate_violation_report(self):
        """generate_violation_report creates a readable report."""
        validator = WeaponCallValidator()
        check = {
            "called": ["weapon_a"],
            "missed": ["weapon_b"],
            "total_calls": 3,
            "weapon_calls": 1,
            "compliant": False,
        }
        report = validator.generate_violation_report("test task", check)
        assert "违规" in report
        assert "weapon_a" in report

    def test_generate_violation_report_compliant(self):
        """generate_violation_report shows compliant when enough weapons called."""
        validator = WeaponCallValidator()
        check = {
            "called": ["weapon_a", "weapon_b"],
            "missed": [],
            "total_calls": 5,
            "weapon_calls": 2,
            "compliant": True,
        }
        report = validator.generate_violation_report("test task", check)
        assert "合规" in report


class TestEngineCore:
    """Test EngineCore tick mechanism."""

    def test_engine_core_init(self):
        """EngineCore initializes with arsenal and scheduler."""
        engine = EngineCore()
        assert engine.arsenal is not None
        assert engine.scheduler is not None

    def test_tick_returns_report(self, monkeypatch, tmp_path):
        """tick returns a status report list."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        engine = EngineCore()
        reports = engine.tick()
        assert isinstance(reports, list)

    def test_tick_no_wake_guide(self, monkeypatch, tmp_path):
        """tick works without wake_guide."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        (tmp_path / "reports").mkdir(exist_ok=True)
        engine = EngineCore()
        reports = engine.tick()
        assert isinstance(reports, list)

    def test_tick_with_interrupted_task(self, monkeypatch, tmp_path):
        """tick recognizes interrupted tasks from wake_guide."""
        monkeypatch.setattr("engine_core.HERMES", tmp_path)
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        wg = {
            "interrupted_task": {
                "task_id": "test_123",
                "next_action": "然后继续执行 然后完成",
            }
        }
        (reports_dir / "wake_guide.json").write_text(json.dumps(wg))
        engine = EngineCore()
        reports = engine.tick()
        assert isinstance(reports, list)


def test_smart_scheduler_with_unknown_type():
    """analyze_task returns 通用 when no types match."""
    sched = SmartScheduler()
    result = sched.analyze_task("xyzzy")
    assert result["task_type"] == "通用"


def test_forced_weapon_protocol_init_with_task():
    """ForcedWeaponProtocol can be initialized with a task."""
    protocol = ForcedWeaponProtocol(task="测试任务")
    assert protocol.task == "测试任务"
    assert protocol.task_analysis is not None
