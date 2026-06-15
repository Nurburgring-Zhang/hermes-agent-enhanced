"""Tests for pipeline system: pipeline_orchestrator.py + production_chain.py + full_auto_pipeline.py"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def temp_production_db(tmp_path):
    """Create a temporary products database."""
    db_path = str(tmp_path / "products.sqlite")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            source TEXT DEFAULT 'intelligence',
            status TEXT DEFAULT 'collecting',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            collection_ref TEXT,
            collection_data TEXT,
            requirement_doc TEXT,
            market_analysis TEXT,
            target_users TEXT,
            design_doc TEXT,
            ui_ux_spec TEXT,
            tech_architecture TEXT,
            code_repo TEXT,
            build_status TEXT,
            build_log TEXT,
            test_report TEXT,
            qa_score REAL,
            known_issues TEXT,
            release_notes TEXT,
            deployment_url TEXT,
            delivery_status TEXT
        )
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_intel_db(tmp_path):
    """Create a temporary intelligence database."""
    db_path = str(tmp_path / "intelligence.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cleaned_intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            platform TEXT,
            summary TEXT,
            content TEXT,
            source TEXT,
            importance_score REAL DEFAULT 0,
            cleaned_at TEXT DEFAULT (datetime('now','localtime')),
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS raw_intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS push_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT
        )
    """)
    # Insert some test data
    c.execute(
        "INSERT INTO cleaned_intelligence (title, platform, summary) VALUES (?, ?, ?)",
        ("Test Intel 1", "weibo", "Summary of test intel 1"),
    )
    c.execute(
        "INSERT INTO cleaned_intelligence (title, platform, summary) VALUES (?, ?, ?)",
        ("Test Intel 2", "toutiao", "Summary of test intel 2"),
    )
    c.execute("INSERT INTO raw_intelligence (title) VALUES ('raw1')")
    c.execute("INSERT INTO push_records (title) VALUES ('push1')")
    # Also create the 'intelligence' table for phase_collect
    c.execute("""
        CREATE TABLE IF NOT EXISTS intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            summary TEXT,
            source TEXT,
            score REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute(
        "INSERT INTO intelligence (title, summary, source, score) VALUES (?, ?, ?, ?)",
        ("Intel 1", "Summary 1", "weibo", 95),
    )
    conn.commit()
    conn.close()
    return db_path


class TestPipelineOrchestrator:
    """Test pipeline_orchestrator.py functions."""

    def test_load_intelligence_no_db(self, monkeypatch, tmp_path):
        """load_intelligence returns empty when no DB."""
        from pipeline_orchestrator import load_intelligence

        monkeypatch.setattr("pipeline_orchestrator.Path.home",
                           lambda: tmp_path)
        result = load_intelligence()
        assert isinstance(result, list)

    def test_load_intelligence_with_db(self, monkeypatch, tmp_path, temp_intel_db):
        """load_intelligence loads from DB."""
        from pipeline_orchestrator import load_intelligence

        db_dir = Path(temp_intel_db).parent
        monkeypatch.setattr("pipeline_orchestrator.Path.home",
                           lambda: db_dir)
        (db_dir / ".hermes").mkdir(parents=True, exist_ok=True)
        # symlink or copy the db
        target = db_dir / ".hermes" / "intelligence.db"
        if not target.exists():
            import shutil
            shutil.copy(temp_intel_db, target)
        result = load_intelligence()
        assert isinstance(result, list)

    def test_get_employees(self, monkeypatch, tmp_path):
        """get_employees scans employee directories."""
        from pipeline_orchestrator import get_employees

        emp_dir = tmp_path / ".hermes" / "skills" / "agents-company" / "employees"
        emp_dir.mkdir(parents=True)
        (emp_dir / "01_marketing_emp1").mkdir()
        (emp_dir / "02_design_emp2").mkdir()
        monkeypatch.setattr("pipeline_orchestrator.Path.home",
                           lambda: tmp_path)
        result = get_employees()
        assert isinstance(result, list)
        # Should have entries for 12 departments
        assert len(result) == 12

    def test_read_identity(self, monkeypatch, tmp_path):
        """read_identity reads identity.yaml if it exists."""
        from pipeline_orchestrator import read_identity

        emp_dir = tmp_path / ".hermes" / "skills" / "agents-company" / "employees" / "01_test_emp"
        emp_dir.mkdir(parents=True)
        yaml_content = "agent:\n  name: Test Emp\n  role: Tester\n  personality: Curious\n"
        (emp_dir / "identity.yaml").write_text(yaml_content)
        monkeypatch.setattr("pipeline_orchestrator.Path.home",
                           lambda: tmp_path)
        name, role, personality = read_identity("01_test_emp")
        assert name == "Test Emp"
        assert role == "Tester"

    def test_read_identity_missing(self, monkeypatch, tmp_path):
        """read_identity returns emp_id when identity.yaml missing."""
        from pipeline_orchestrator import read_identity

        monkeypatch.setattr("pipeline_orchestrator.Path.home",
                           lambda: tmp_path)
        name, role, personality = read_identity("nonexistent_emp")
        assert name == "nonexistent_emp"
        assert role == ""

    def test_build_summary(self):
        """build_summary creates department execution summary."""
        from pipeline_orchestrator import build_summary

        summary = build_summary("Test Dept", ["emp1", "emp2"], "emp1 success")
        assert "Test Dept" in summary
        assert "emp1" in summary


class TestProductionChain:
    """Test production_chain.py pipeline phases."""

    def test_init_databases(self, monkeypatch, tmp_path):
        """init_databases creates the products database."""
        company_dir = tmp_path / "agents_company" / "data"
        company_dir.mkdir(parents=True)

        import production_chain
        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           company_dir / "products.sqlite")
        production_chain.init_databases()
        assert (company_dir / "products.sqlite").exists()

    def test_phase_collect_with_db(self, monkeypatch, tmp_path, temp_production_db, temp_intel_db):
        """phase_collect collects from an intelligence DB."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        # Create product entry
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute("INSERT INTO products (name, description) VALUES (?, ?)",
                  ("Test Product", "Test"))
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_collect(product_id, temp_intel_db)
        assert result is True

    def test_phase_collect_no_db(self, monkeypatch, tmp_path, temp_production_db):
        """phase_collect uses mock data when no intel DB."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute("INSERT INTO products (name) VALUES (?)", ("Mock Product",))
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_collect(product_id, None)
        assert result is True

    def test_phase_analyze(self, monkeypatch, tmp_path, temp_production_db):
        """phase_analyze does requirement analysis."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute(
            "INSERT INTO products (name, collection_data, status) VALUES (?, ?, ?)",
            ("Analyze Product", json.dumps([{"title": "t1"}]), "collected"),
        )
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_analyze(product_id)
        assert result is True

    def test_phase_analyze_no_data(self, monkeypatch, tmp_path, temp_production_db):
        """phase_analyze fails when no collection data."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute("INSERT INTO products (name) VALUES (?)", ("NoData Product",))
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_analyze(product_id)
        assert result is False

    def test_phase_design(self, monkeypatch, tmp_path, temp_production_db):
        """phase_design creates product design."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        req_doc = json.dumps({"product_name": "Test", "core_features": ["f1"]})
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute(
            "INSERT INTO products (name, requirement_doc, status) VALUES (?, ?, ?)",
            ("Design Product", req_doc, "analyzed"),
        )
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_design(product_id)
        assert result is True

    def test_phase_design_no_requirements(self, monkeypatch, tmp_path, temp_production_db):
        """phase_design fails without requirement doc."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute("INSERT INTO products (name) VALUES (?)", ("NoReq Product",))
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_design(product_id)
        assert result is False

    def test_phase_build(self, monkeypatch, tmp_path, temp_production_db):
        """phase_build creates product directory structure."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        design_doc = json.dumps({
            "ui_framework": "React",
            "architecture": {"backend": "FastAPI"},
        })
        tech_arch = json.dumps({"backend": "FastAPI", "frontend": "React"})
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute(
            "INSERT INTO products (name, design_doc, tech_architecture, status) VALUES (?, ?, ?, ?)",
            ("Build Product", design_doc, tech_arch, "designed"),
        )
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        output_dir = str(tmp_path / "output")
        result = production_chain.phase_build(product_id, output_dir)
        assert result is True

    def test_phase_build_no_design(self, monkeypatch, tmp_path, temp_production_db):
        """phase_build creates structure even without design doc (row exists)."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute("INSERT INTO products (name) VALUES (?)", ("NoDesign Product",))
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        output_dir = str(tmp_path / "output")
        result = production_chain.phase_build(product_id, output_dir)
        # Row exists so it proceeds — builds structure
        assert result is True

    def test_phase_test(self, monkeypatch, tmp_path, temp_production_db):
        """phase_test creates test report."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute(
            "INSERT INTO products (name, code_repo) VALUES (?, ?)",
            ("Test Product", "/tmp/test"),
        )
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        result = production_chain.phase_test(product_id)
        assert result is True

    def test_phase_test_no_product(self, monkeypatch, tmp_path, temp_production_db):
        """phase_test fails for nonexistent product."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        result = production_chain.phase_test(99999)
        assert result is False

    def test_phase_deliver(self, monkeypatch, tmp_path, temp_production_db):
        """phase_deliver creates delivery artifacts."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        conn = sqlite3.connect(temp_production_db)
        c = conn.cursor()
        c.execute(
            "INSERT INTO products (name, status, qa_score) VALUES (?, ?, ?)",
            ("Deliver Product", "tested", 92.5),
        )
        product_id = c.lastrowid
        conn.commit()
        conn.close()

        output_dir = str(tmp_path / "delivery_output")
        result = production_chain.phase_deliver(product_id, output_dir)
        assert result is True

    def test_phase_deliver_no_product(self, monkeypatch, tmp_path, temp_production_db):
        """phase_deliver fails for nonexistent product."""
        import production_chain

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        output_dir = str(tmp_path / "output")
        result = production_chain.phase_deliver(99999, output_dir)
        assert result is False

    def test_run_full_pipeline(self, monkeypatch, tmp_path, temp_production_db):
        """run_full_pipeline runs all 6 phases."""
        import production_chain

        company_dir = tmp_path / "agents_company" / "data"
        company_dir.mkdir(parents=True)
        company_root = tmp_path / "agents_company"

        monkeypatch.setattr(production_chain, "PRODUCT_DB",
                           Path(temp_production_db))
        monkeypatch.setattr(production_chain, "COMPANY_DIR", company_root)
        output_dir = str(tmp_path / "pipeline_output")

        result = production_chain.run_full_pipeline(
            "Full Pipeline Product", intelligence_db=None, output_dir=output_dir
        )
        assert result is True


class TestFullAutoPipeline:
    """Test full_auto_pipeline.py functions."""

    def test_get_db_stats_empty(self, monkeypatch, tmp_path):
        """get_db_stats returns zeros when no DB."""
        from full_auto_pipeline import get_db_stats

        monkeypatch.setattr("full_auto_pipeline.HERMES", tmp_path)
        # No DB file -> should return zeros
        stats = get_db_stats()
        assert isinstance(stats, dict)
        assert "raw" in stats
        assert "cleaned" in stats
        assert "pushed" in stats

    def test_get_db_stats_with_data(self, monkeypatch, tmp_path):
        """get_db_stats returns counts from DB."""
        from full_auto_pipeline import get_db_stats

        db_path = tmp_path / "intelligence.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE raw_intelligence (id INTEGER)")
        conn.execute("CREATE TABLE cleaned_intelligence (id INTEGER)")
        conn.execute("CREATE TABLE push_records (id INTEGER)")
        conn.execute("INSERT INTO raw_intelligence VALUES (1)")
        conn.execute("INSERT INTO raw_intelligence VALUES (2)")
        conn.execute("INSERT INTO cleaned_intelligence VALUES (1)")
        conn.execute("INSERT INTO push_records VALUES (1)")
        conn.execute("INSERT INTO push_records VALUES (2)")
        conn.execute("INSERT INTO push_records VALUES (3)")
        conn.commit()
        conn.close()

        monkeypatch.setattr("full_auto_pipeline.HERMES", tmp_path)
        stats = get_db_stats()
        assert stats["raw"] == 2
        assert stats["cleaned"] == 1
        assert stats["pushed"] == 3

    def test_log_function(self):
        """log function prints colored output."""
        from full_auto_pipeline import log
        # Just verify it doesn't crash
        log("test message", "INFO")
        log("test ok", "OK")
        log("test err", "ERR")
        log("test wrn", "WRN")


def test_pipeline_orchestrator_main(monkeypatch, tmp_path):
    """pipeline_orchestrator main runs without errors."""
    from pipeline_orchestrator import main
    import io
    import contextlib

    emp_dir = tmp_path / ".hermes" / "skills" / "agents-company" / "employees"
    emp_dir.mkdir(parents=True)
    (emp_dir / "01_marketing_emp1").mkdir()
    monkeypatch.setattr("pipeline_orchestrator.Path.home",
                       lambda: tmp_path)
    monkeypatch.setattr("pipeline_orchestrator.OUTPUT_DIR",
                       tmp_path / "exports")

    # Capture stdout to avoid noise
    f = io.StringIO()
    with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        try:
            result = main()
        except SystemExit as e:
            result = e.code
    # Should exit cleanly
    assert result == 0
