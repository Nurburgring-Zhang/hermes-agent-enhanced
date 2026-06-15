"""Tests for hermes_tools.py + tool_wrapper.py — 工具系统"""
import json
import os
import sys
import time
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from hermes_tools import (
    read_file,
    write_file,
    terminal,
    search_files,
    patch,
)


class TestHermesToolsReadFile:
    """Test hermes_tools.read_file."""

    def test_read_file_content(self, tmp_path):
        """Read file returns content and metadata."""
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")
        result = read_file(str(f))
        assert "content" in result
        assert result["total_lines"] == 5
        assert result["truncated"] is False

    def test_read_file_offset(self, tmp_path):
        """Read file with offset starts at correct line."""
        f = tmp_path / "test.txt"
        f.write_text("a\nb\nc\nd\ne\n")
        result = read_file(str(f), offset=3)
        assert "c" in result["content"]
        assert "a" not in result["content"]

    def test_read_file_limit(self, tmp_path):
        """Read file with limit returns at most that many lines."""
        f = tmp_path / "test.txt"
        f.write_text("\n".join(str(i) for i in range(100)))
        result = read_file(str(f), offset=1, limit=5)
        content = result["content"]
        assert content.strip().count("\n") <= 5

    def test_read_file_not_found(self, tmp_path):
        """Read non-existent file returns error."""
        result = read_file(str(tmp_path / "nonexistent.txt"))
        assert "error" in result
        assert result["total_lines"] == 0

    def test_read_file_tilde_path(self, monkeypatch, tmp_path):
        """Read file expands ~/ paths."""
        monkeypatch.setattr("hermes_tools.HOME", str(tmp_path))
        f = tmp_path / "test.txt"
        f.write_text("content")
        result = read_file("~/test.txt")
        assert "content" in result["content"]

    def test_read_file_utf8(self, tmp_path):
        """Read file handles UTF-8 encoding."""
        f = tmp_path / "utf8.txt"
        f.write_text("你好世界 🌍 test")
        result = read_file(str(f))
        assert "你好世界" in result["content"]


class TestHermesToolsWriteFile:
    """Test hermes_tools.write_file."""

    def test_write_file_creates(self, tmp_path):
        """Write file creates content."""
        f = tmp_path / "output.txt"
        result = write_file(str(f), "hello world")
        assert result["bytes_written"] > 0
        assert f.read_text() == "hello world"

    def test_write_file_creates_dirs(self, tmp_path):
        """Write file creates parent directories."""
        f = tmp_path / "deep" / "nested" / "dir" / "out.txt"
        result = write_file(str(f), "nested content")
        assert result["bytes_written"] > 0
        assert f.exists()

    def test_write_file_tilde_path(self, monkeypatch, tmp_path):
        """Write file expands ~/ paths."""
        monkeypatch.setattr("hermes_tools.HOME", str(tmp_path))
        result = write_file("~/hermes_output.txt", "test")
        assert result["bytes_written"] > 0
        assert (tmp_path / "hermes_output.txt").exists()

    def test_write_file_empty(self, tmp_path):
        """Write empty content."""
        f = tmp_path / "empty.txt"
        result = write_file(str(f), "")
        assert result["bytes_written"] == 0


class TestHermesToolsTerminal:
    """Test hermes_tools.terminal."""

    def test_terminal_echo(self):
        """terminal runs a simple echo command."""
        result = terminal("echo hello")
        assert result["exit_code"] == 0
        assert "hello" in result["output"]

    def test_terminal_with_workdir(self, tmp_path):
        """terminal uses specified working directory."""
        result = terminal("pwd", workdir=str(tmp_path))
        assert result["exit_code"] == 0

    def test_terminal_failure(self):
        """terminal captures exit code for failing commands."""
        result = terminal("ls /nonexistent_path_xyz")
        assert result["exit_code"] != 0

    def test_terminal_timeout(self):
        """terminal handles command timeout."""
        result = terminal("sleep 5", timeout=1)
        assert result["exit_code"] == -1
        assert "timed out" in result.get("error", "").lower()

    def test_terminal_invalid_command(self):
        """terminal handles invalid commands."""
        result = terminal("nonexistent_command_xyz")
        assert result["exit_code"] != 0


class TestHermesToolsSearchFiles:
    """Test hermes_tools.search_files."""

    def test_search_files_by_name(self, tmp_path):
        """Search files by glob pattern."""
        (tmp_path / "test_file.py").write_text("content")
        (tmp_path / "other.txt").write_text("other")
        result = search_files("*.py", target="files", path=str(tmp_path))
        assert "matches" in result
        assert any("test_file.py" in m for m in result["matches"])

    def test_search_files_by_content(self, tmp_path):
        """Search files by content pattern."""
        (tmp_path / "code.py").write_text("def hello_world():\n    return 'secret_key'\n")
        result = search_files("secret_key", target="content", path=str(tmp_path),
                             file_glob="*.py")
        assert "matches" in result

    def test_search_files_tilde_path(self, monkeypatch, tmp_path):
        """Search files expands ~/ paths."""
        monkeypatch.setattr("hermes_tools.HOME", str(tmp_path))
        (tmp_path / "myfile.py").write_text("special_content")
        result = search_files("special_content", target="content", path="~",
                             file_glob="*.py")
        assert "matches" in result

    def test_search_files_no_match(self, tmp_path):
        """Search returns empty when no matches."""
        result = search_files("nonexistent_pattern_xyz", target="content",
                             path=str(tmp_path))
        assert len(result.get("matches", [])) == 0


class TestHermesToolsPatch:
    """Test hermes_tools.patch."""

    def test_patch_replace_single(self, tmp_path):
        """patch replaces single occurrence of old string."""
        f = tmp_path / "to_patch.py"
        f.write_text("hello world\nhello again\n")
        result = patch(str(f), "hello world", "hi there")
        assert result["success"] is True
        content = f.read_text()
        assert "hi there" in content
        assert "hello again" in content  # only first replaced

    def test_patch_replace_all(self, tmp_path):
        """patch replaces all occurrences with replace_all=True."""
        f = tmp_path / "to_patch.py"
        f.write_text("foo bar\nfoo baz\n")
        result = patch(str(f), "foo", "qux", replace_all=True)
        assert result["success"] is True
        content = f.read_text()
        assert content.count("qux") == 2
        assert "foo" not in content

    def test_patch_not_found(self, tmp_path):
        """patch returns error when old_string not found."""
        f = tmp_path / "to_patch.py"
        f.write_text("only this")
        result = patch(str(f), "not found", "replacement")
        assert "error" in result

    def test_patch_file_not_found(self, tmp_path):
        """patch returns error for missing file."""
        result = patch(str(tmp_path / "nonexistent.py"), "a", "b")
        assert "error" in result

    def test_patch_tilde_path(self, monkeypatch, tmp_path):
        """patch expands ~/ paths."""
        monkeypatch.setattr("hermes_tools.HOME", str(tmp_path))
        f = tmp_path / "tilde_test.txt"
        f.write_text("original content")
        result = patch("~/tilde_test.txt", "original", "modified")
        assert result["success"] is True
        assert "modified" in f.read_text()


class TestToolWrapper:
    """Test tool_wrapper.py classes."""

    def test_tool_unloader_init(self):
        """ToolUnloader initializes with refs directory."""
        from tool_unloader import ToolUnloader
        unloader = ToolUnloader()
        assert unloader is not None

    def test_tool_unloader_intercept_small(self, tmp_path):
        """Small results are returned as-is."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_refs = tmp_path / "refs"
        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload
        monkeypatch_refs.mkdir()

        unloader = ToolUnloader()
        result = unloader.intercept_tool_result("test_tool", {}, "short result")
        assert "short result" in result

    def test_tool_unloader_intercept_large_v1(self, tmp_path):
        """Large results without LLM follow v1 fallback."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_refs = tmp_path / "refs"
        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload
        monkeypatch_refs.mkdir()

        unloader = ToolUnloader()
        # Mock _evaluate_with_llm to return None (v1 fallback)
        unloader._evaluate_with_llm = lambda tool_name, result: None
        large = "x" * 3000
        result = unloader.intercept_tool_result("read_file", {"path": "test"}, large)
        assert "[ref:" in result

    def test_tool_unloader_make_ref_id(self, tmp_path):
        """_make_ref_id generates unique IDs."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_refs = tmp_path / "refs"
        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload
        monkeypatch_refs.mkdir()

        unloader = ToolUnloader()
        ref_id1 = unloader._make_ref_id("tool_a")
        ref_id2 = unloader._make_ref_id("tool_b")
        assert ref_id1 != ref_id2
        assert "tool_a" in ref_id1

    def test_tool_unloader_write_ref_file(self, tmp_path):
        """_write_ref_file creates .md ref file."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_refs = tmp_path / "refs"
        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload
        monkeypatch_refs.mkdir()

        unloader = ToolUnloader()
        ref_path = unloader._write_ref_file("ref123", "test_tool", {"a": 1}, "content", "summary")
        assert ref_path.exists()
        content = ref_path.read_text()
        assert "test_tool" in content
        assert "ref123" in content

    def test_tool_unloader_summarize_read_file(self):
        """_summarize for read_file generates file summary."""
        from tool_unloader import ToolUnloader
        unloader = ToolUnloader()
        summary = unloader._summarize("read_file", {"path": "/tmp/test.py"}, "content" * 1000)
        assert "/tmp/test.py" in summary

    def test_tool_unloader_summarize_terminal(self):
        """_summarize for terminal generates command summary."""
        from tool_unloader import ToolUnloader
        unloader = ToolUnloader()
        summary = unloader._summarize("terminal", {"command": "python test.py"}, "output" * 1000)
        assert "python" in summary or "test" in summary

    def test_tool_unloader_get_compressed_context_empty(self, tmp_path):
        """get_compressed_context returns empty when no entries."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_offload = tmp_path / "offload_empty.jsonl"
        tu.OFFLOAD_DB = monkeypatch_offload

        unloader = ToolUnloader()
        ctx = unloader.get_compressed_context()
        assert ctx == ""

    def test_tool_unloader_get_compressed_context(self, tmp_path):
        """get_compressed_context returns recent entries."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.OFFLOAD_DB = monkeypatch_offload

        entries = [
            {"ref_id": "a_1", "tool_name": "read_file", "summary": "read x",
             "result_size": 5000, "ref_path": "/tmp/x", "timestamp": time.time() - 100},
            {"ref_id": "a_2", "tool_name": "terminal", "summary": "ran cmd",
             "result_size": 3000, "ref_path": "/tmp/y", "timestamp": time.time()},
        ]
        monkeypatch_offload.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        unloader = ToolUnloader()
        ctx = unloader.get_compressed_context(max_entries=5)
        assert "read x" in ctx or "ran cmd" in ctx

    def test_tool_unloader_cleanup(self, tmp_path):
        """cleanup_expired removes old refs."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_refs = tmp_path / "refs"
        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload
        monkeypatch_refs.mkdir()

        # Create an old ref file
        old_ref = monkeypatch_refs / "old_ref.md"
        old_ref.write_text("# old")
        # Set mtime to 30 days ago
        old_time = time.time() - 30 * 86400
        os.utime(str(old_ref), (old_time, old_time))

        # Create offload entry for it
        entry = {
            "ref_id": "old_ref",
            "tool_name": "test",
            "summary": "old",
            "result_size": 100,
            "ref_path": str(old_ref),
            "timestamp": old_time,
            "keep_days": 7,
        }
        monkeypatch_offload.write_text(json.dumps(entry) + "\n")

        unloader = ToolUnloader()
        cleaned = unloader.cleanup_expired(max_age_days=7)
        assert cleaned >= 1

    def test_tool_unloader_cleanup_empty(self, tmp_path):
        """cleanup_expired returns 0 with no refs."""
        from tool_unloader import ToolUnloader
        import tool_unloader as tu

        monkeypatch_refs = tmp_path / "refs_empty"
        monkeypatch_offload = tmp_path / "offload_empty.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload

        unloader = ToolUnloader()
        cleaned = unloader.cleanup_expired()
        assert cleaned == 0

    def test_t_wrapper_class_exists(self):
        """T wrapper class is importable."""
        from tool_wrapper import T
        assert hasattr(T, "read_file")
        assert hasattr(T, "terminal")
        assert hasattr(T, "search_files")
        assert hasattr(T, "get_compressed_context")
        assert hasattr(T, "cleanup")

    def test_wrap_func(self):
        """wrap_func wraps a regular function."""
        from tool_wrapper import wrap_func

        def original(a, b=0):
            return f"result: {a} {b}"

        wrapped = wrap_func("test_func", original)
        result = wrapped("hello", b=42)
        assert "result: hello 42" in result

    def test_install_hooks(self):
        """install_hooks runs without error."""
        from tool_wrapper import install_hooks
        # Should not crash
        install_hooks()

    def test_t_read_file_small(self, tmp_path):
        """T.read_file returns content for small files."""
        from tool_wrapper import T
        import tool_unloader as tu

        # Redirect refs to temp
        monkeypatch_refs = tmp_path / "refs"
        monkeypatch_offload = tmp_path / "offload.jsonl"
        tu.REFS_DIR = monkeypatch_refs
        tu.OFFLOAD_DB = monkeypatch_offload
        monkeypatch_refs.mkdir()

        f = tmp_path / "small.txt"
        f.write_text("small content")
        result = T.read_file(str(f))
        assert "small content" in result
