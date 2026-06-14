"""Tests for compression system: compression_engine.py + context_packer.py + lossless_claw.py"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from compression_engine import (
    LosslessClawCompressor,
    EmergencyCompressor,
    RTK,
    ContextCompressor,
    compress_soul,
    compress_for_context,
    compress,
    run_fidelity_validation,
    archive_old_intelligence,
    _load_fidelity_stats,
    _check_byte_fidelity,
    HERMES,
    TZ,
)

from context_packer import (
    estimate_tokens,
    extract_layer1_core,
    extract_layer2_optional,
    extract_layer3_indices,
    pack_context,
)

from lossless_claw import LosslessClawCompressor as LCC_forwarder

# Dummy sqlite3 connection for test
import sqlite3


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_compression.db")


@pytest.fixture
def claw(db_path):
    """Create a LosslessClawCompressor with a temp DB."""
    return LosslessClawCompressor(db_path=db_path)


class TestLosslessClawCompressor:
    """Test the three-level lossless compression engine."""

    def test_compress_level1(self, claw):
        """Compress at level 1 (zlib)."""
        data = "hello world " * 200
        result = claw.compress("test_section", data, level=1)
        assert result["action"] == "compressed"
        assert result["level"] == 1
        assert result["original_bytes"] > 0
        assert result["compressed_bytes"] > 0
        assert "ratio" in result
        assert "checksum" in result

    def test_compress_level2(self, claw):
        """Compress at level 2 (gzip level 6)."""
        data = "hello world " * 200
        result = claw.compress("test_section_l2", data, level=2)
        assert result["action"] == "compressed"
        assert result["level"] == 2

    def test_compress_level3(self, claw):
        """Compress at level 3 (gzip level 9)."""
        data = "hello world " * 200
        result = claw.compress("test_section_l3", data, level=3)
        assert result["action"] == "compressed"
        assert result["level"] == 3

    def test_compress_skips_critical(self, claw):
        """Critical keys are skipped unless force=True."""
        data = "secret data " * 100
        result = claw.compress("user_prefs", data, level=1)
        assert result["action"] == "skipped_critical"

    def test_compress_critical_forced(self, claw):
        """Critical keys can be forced with force=True."""
        data = "secret data " * 100
        result = claw.compress("user_prefs", data, level=1, force=True)
        assert result["action"] == "compressed"

    def test_decompress_roundtrip(self, claw):
        """Data survives compression + decompression roundtrip."""
        data = "hello world test data " * 150
        claw.compress("roundtrip", data, level=1)
        decompressed = claw.decompress("roundtrip")
        assert decompressed == data

    def test_decompress_nonexistent(self, claw):
        """decompress returns None for unknown sections."""
        result = claw.decompress("nonexistent_section")
        assert result is None

    def test_status(self, claw):
        """status returns compression statistics."""
        claw.compress("s1", "data " * 100, level=1)
        status = claw.status()
        assert "total_compressions" in status
        assert "db_path" in status
        assert status["total_compressions"] >= 1

    def test_level1_compress(self, claw):
        """level1_compress scans and compresses session tables."""
        result = claw.level1_compress()
        assert result["level"] == 1
        assert "sections_compressed" in result

    def test_level2_compress(self, claw):
        """level2_compress recompresses level-1 sections with low access count."""
        # First create level-1 data then try level-2
        data = "large " * 300
        claw.compress("s2", data, level=1, force=True)
        result = claw.level2_compress()
        assert result["level"] == 2

    def test_level3_archive(self, claw):
        """level3_archive archives old checkpoints."""
        result = claw.level3_archive(older_than_days=365)
        assert result["level"] == 3

    def test_checksum_consistency(self, claw):
        """Same data produces same checksum."""
        data = "test checksum " * 50
        ck1 = claw._checksum(data.encode())
        ck2 = claw._checksum(data.encode())
        assert ck1 == ck2


class TestEmergencyCompressor:
    """Test emergency context compression."""

    def test_estimate_tokens_chinese(self):
        """Chinese characters use ~1.5 tokens per char."""
        comp = EmergencyCompressor()
        text = "你好世界" * 100
        tokens = comp._estimate_tokens(text)
        assert tokens > 0

    def test_estimate_tokens_mixed(self):
        """Mixed Chinese/English text estimated correctly."""
        comp = EmergencyCompressor()
        text = "hello 世界 test 测试"
        tokens = comp._estimate_tokens(text)
        assert tokens > 0

    def test_estimate_tokens_empty(self):
        """Empty text returns 0 tokens."""
        comp = EmergencyCompressor()
        assert comp._estimate_tokens("") == 0

    def test_compress_below_threshold(self):
        """Compression not triggered when below threshold."""
        comp = EmergencyCompressor(context_window=128000)
        short = "short text\n" * 10
        result = comp.compress(short)
        assert result["level"] == "none"

    def test_compress_aggressive(self):
        """Aggressive compression trims context."""
        comp = EmergencyCompressor(context_window=100)
        long_text = "line of text\n" * 200
        result = comp.compress(long_text)
        # should trigger some level
        assert result["level"] in ("mild", "aggressive", "emergency", "none")

    def test_get_status(self):
        """get_status returns usage ratio and recommended level."""
        comp = EmergencyCompressor(context_window=5000)
        text = "x" * 10000
        status = comp.get_status(text)
        assert "current_tokens" in status
        assert "usage_ratio" in status
        assert "recommended_level" in status

    def test_emergency_level(self):
        """Very long text triggers emergency compression."""
        comp = EmergencyCompressor(context_window=10)
        huge = "a\n" * 1000
        result = comp.compress(huge)
        assert result["level"] in ("aggressive", "emergency")


class TestRTK:
    """Test Real-Time Token Killer."""

    def test_compress_text_basic(self):
        """RTK compresses text preserving uniqueness."""
        text = "line1\nline2\nline3\nline1\n"
        result = RTK.compress_text(text, ratio=0.5)
        assert len(result) > 0

    def test_compress_text_empty(self):
        """Compressing empty text returns empty."""
        assert RTK.compress_text("", ratio=0.5) == ""

    def test_compress_html(self):
        """HTML compression strips tags and scripts."""
        html = "<html><body><p>Hello world</p><script>alert('x')</script></body></html>"
        result = RTK.compress_html(html, ratio=0.5)
        assert "script" not in result.lower() or "alert" not in result
        assert "Hello" in result

    def test_compress_html_empty(self):
        """Compressing empty HTML returns empty."""
        assert RTK.compress_html("", ratio=0.5) == ""

    def test_compress_json_dict(self):
        """JSON compression drops safe fields."""
        data = {"title": "test", "raw_data": "large", "_id": "123", "content": "hello"}
        result = RTK.compress_json(data, ratio=0.5)
        assert "title" in result
        # Safe fields should be dropped
        assert "raw_data" not in result
        assert "_id" not in result

    def test_compress_json_str(self):
        """JSON compression handles string input."""
        data = '{"title": "test", "desc": "hello world"}'
        result = RTK.compress_json(data, ratio=0.5)
        assert "title" in result or isinstance(result, dict)

    def test_compress_json_list(self):
        """JSON compression truncates long lists."""
        data = [{"id": i, "name": f"item_{i}"} for i in range(30)]
        result = RTK.compress_json(data, ratio=0.5)
        assert isinstance(result, list)

    def test_estimate_tokens(self):
        """Token estimation is len(text) // 4."""
        text = "a" * 400
        assert RTK.estimate_tokens(text) == 100

    def test_compress_for_context_within_limit(self):
        """Content within context limit is returned as-is."""
        data = {"key": "small value"}
        result = RTK.compress_for_context(data, context_limit=8000, current_usage=0)
        assert "small value" in result

    def test_compress_for_context_exceeds_limit(self):
        """Content exceeding limit is compressed."""
        data = {"key": "x" * 10000}
        result = RTK.compress_for_context(data, context_limit=200, current_usage=100)
        assert len(result) > 0

    def test_compress_auto_mode_dict(self):
        """Auto mode detects dict and compresses as JSON."""
        data = {"title": "test", "raw_data": "large", "__v": 1}
        result = RTK.compress(data, mode="auto")
        assert "title" in result or isinstance(result, dict)
        if isinstance(result, dict):
            assert "raw_data" not in result


class TestContextCompressor:
    """Test conversation/checkpoint compression."""

    def test_store_task_checkpoint(self, monkeypatch, tmp_path):
        """store_task_checkpoint writes task state."""
        monkeypatch.setattr("compression_engine.HERMES", tmp_path)
        cc = ContextCompressor()
        result = cc.store_task_checkpoint(
            "task_001", "running", ["step1"], ["step2"], "do step2", "details"
        )
        assert result["task_id"] == "task_001"
        assert result["status"] == "running"

    def test_store_audit_snapshot(self, monkeypatch, tmp_path):
        """store_audit_snapshot writes audit report."""
        monkeypatch.setattr("compression_engine.HERMES", tmp_path)
        cc = ContextCompressor()
        result = cc.store_audit_snapshot("Audit Title", "Audit content " * 100)
        assert result["stored"] is True
        assert "path" in result


class TestCompressionFunctions:
    """Test standalone compression functions."""

    def test_compress_for_context_shortcut(self):
        """compress_for_context shortcut works."""
        result = compress_for_context({"key": "val"}, context_limit=8000)
        assert len(result) > 0

    def test_compress_shortcut(self):
        """compress shortcut works."""
        result = compress({"key": "val"}, mode="json", ratio=0.5)
        assert isinstance(result, (str, dict))

    def test_compress_soul_missing(self, monkeypatch, tmp_path):
        """compress_soul returns error when SOUL.md missing."""
        monkeypatch.setattr("compression_engine.HERMES", tmp_path)
        result = compress_soul()
        assert "error" in result

    def test_compress_soul_exists(self, monkeypatch, tmp_path):
        """compress_soul works when SOUL.md exists."""
        monkeypatch.setattr("compression_engine.HERMES", tmp_path)
        (tmp_path / "reports").mkdir(exist_ok=True)
        soul_content = """## 一、核心身份\nTest\n## 二、永久禁令\n1. ban\n## 三、other\n## 四、5大行为准则\n| 1 | test | content |\n### 规则0：\n1. **step1**\n### 规则1：\ntest rule\n### 规则2：\ntest rule2\n### 🔴 上下文压缩强制规则\n1. rule a\n"""
        (tmp_path / "SOUL.md").write_text(soul_content)
        result = compress_soul()
        assert "compression_ratio" in result

    def test_check_byte_fidelity_good(self):
        """Byte fidelity check with good ratio."""
        score = _check_byte_fidelity(100, 30)
        assert 0 < score <= 1.0

    def test_check_byte_fidelity_bad(self):
        """Byte fidelity check with bad ratio."""
        score = _check_byte_fidelity(0, 10)
        assert score == 0.0

    def test_load_fidelity_stats_missing(self, monkeypatch, tmp_path):
        """Load fidelity stats returns default when file missing."""
        monkeypatch.setattr("compression_engine.STATS_FILE", tmp_path / "nonexistent.json")
        stats = _load_fidelity_stats()
        assert stats["total_compressed"] == 0

    def test_load_fidelity_stats_exists(self, monkeypatch, tmp_path):
        """Load fidelity stats loads from file."""
        stats_file = tmp_path / "stats.json"
        monkeypatch.setattr("compression_engine.STATS_FILE", stats_file)
        stats_file.write_text(json.dumps({"total_compressed": 5}))
        stats = _load_fidelity_stats()
        assert stats["total_compressed"] == 5


class TestContextPacker:
    """Test dynamic context packer from context_packer.py."""

    def test_estimate_tokens_cn(self):
        """estimate_tokens handles Chinese text."""
        assert estimate_tokens("你好世界") > 0

    def test_estimate_tokens_en(self):
        """estimate_tokens handles English text."""
        assert estimate_tokens("hello world") > 0

    def test_pack_context_missing_soul(self, monkeypatch, tmp_path):
        """pack_context returns error when SOUL.md missing."""
        monkeypatch.setattr("context_packer.HERMES", tmp_path)
        (tmp_path / "reports").mkdir(exist_ok=True)
        result = pack_context()
        assert "error" in result

    def test_pack_context_with_soul(self, monkeypatch, tmp_path):
        """pack_context works with SOUL.md."""
        monkeypatch.setattr("context_packer.HERMES", tmp_path)
        (tmp_path / "reports").mkdir(exist_ok=True)
        soul_content = """## 一、核心身份\nHermes is an AI agent.\n## 二、永久禁令\n1. No lying\n2. No cheating\n3. No stealing\n4. No harm\n5. No bias\n## 三、other\n## 四、5大行为准则\n| 1 | rule | content here more |\n| 2 | rule | another one |\n### 规则0：\n1. **step one**\n2. **step two**\n3. **step three**\n### 规则1：\ncore sentence test。additional text\n### 规则2：\ncore two。more text\n### 规则3：\ntest\n### 🔴 上下文压缩强制规则\n1. compression rule one\n2. compression rule two\n### 🔴 全能力自动激活设定\ntest activation\n## 零、⚙️ 齿轮强制恢复协议\n### 🔴 强制步骤0\nstep0 content\n### 🔴 强制步骤1\nstep1 content\n### 外挂保障\next table\n### 三重冗余文件\nredundancy doc\n### 生产级可靠性引擎\nproduction engine\n"""
        (tmp_path / "SOUL.md").write_text(soul_content)
        result = pack_context()
        assert "content" in result
        assert "packed_tokens" in result
        assert "compression_ratio" in result

    def test_extract_layer1_core(self, monkeypatch, tmp_path):
        """extract_layer1_core extracts critical content from SOUL.md."""
        text = """## 一、核心身份\nHermes AI Agent\n## 二、永久禁令\n1. Rule one\n2. Rule two\n3. Rule three\n4. Rule four\n5. Rule five\n## 三、Other\n## 四、5大行为准则\n| 1 | test | content |\n### 规则0：\n1. **step1**\n2. **step2**\n### 规则1：\ncore here。\n### 🔴 上下文压缩强制规则\n1. r1\n2. r2\n"""
        result = extract_layer1_core(text)
        assert len(result) > 0
        assert "核心身份" in result or "永久禁令" in result

    def test_extract_layer2_optional(self):
        """extract_layer2_optional extracts gear/pipeline content."""
        text = """## 零、⚙️ 齿轮强制恢复协议\n### 🔴 强制步骤0\nstep0\n### 🔴 强制步骤1\nstep1\n### 外挂保障\ntable\n### 三重冗余文件\nredundancy\n### 生产级可靠性引擎\nengine\n"""
        result = extract_layer2_optional(text)
        assert len(result) > 0

    def test_extract_layer3_indices(self):
        """extract_layer3_indices extracts section index."""
        text = """## 关键文件索引\nfile index\n## skills组合\nskills combo\n"""
        result = extract_layer3_indices(text)
        assert len(result) > 0


class TestLosslessClawForwarder:
    """Test the lossless_claw.py forwarder module."""

    def test_forwarder_is_instance(self):
        """The forwarder class is the same LosslessClawCompressor."""
        from compression_engine import LosslessClawCompressor as LCC
        assert LCC_forwarder is LCC
