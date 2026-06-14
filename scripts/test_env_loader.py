#!/usr/bin/env python3
"""Tests for env_loader.py — Hermes 环境变量安全加载器"""

import os
import sys
from pathlib import Path

import pytest

# Ensure scripts dir is in path
sys.path.insert(0, str(Path.home() / ".hermes"))


@pytest.fixture(autouse=True)
def reset_env_loader():
    """Reset env_loader module state between tests"""
    import scripts.env_loader as el
    el._HERMES_HOME = None
    # Clean up any test env vars we set
    for k in list(os.environ.keys()):
        if k.startswith("TEST_HERMES_"):
            del os.environ[k]


class TestGetHermesHome:
    """get_hermes_home() — 返回 HERMES_HOME 或默认值"""

    def test_default_when_no_env(self):
        """未设置 HERMES_HOME 时返回 ~/.hermes"""
        if "HERMES_HOME" in os.environ:
            del os.environ["HERMES_HOME"]
        from scripts.env_loader import get_hermes_home
        expected = Path.home() / ".hermes"
        assert get_hermes_home() == expected

    def test_uses_env_var(self):
        """设置 HERMES_HOME 时使用环境变量值"""
        os.environ["HERMES_HOME"] = "/tmp/test_hermes_home"
        from scripts.env_loader import get_hermes_home
        assert get_hermes_home() == Path("/tmp/test_hermes_home")

    def test_returns_path_object(self):
        """返回类型为 Path"""
        from scripts.env_loader import get_hermes_home
        assert isinstance(get_hermes_home(), Path)

    def test_caching(self):
        """第二次调用返回相同对象（不走环境变量）"""
        from scripts.env_loader import get_hermes_home
        h1 = get_hermes_home()
        os.environ["HERMES_HOME"] = "/tmp/different"
        h2 = get_hermes_home()
        assert h1 == h2


class TestLoadEnvFile:
    """load_env_file() — 加载 .env 文件并设置 os.environ"""

    def test_loads_simple_vars(self, tmp_path):
        """加载简单 key=value"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_HERMES_KEY=hello\nTEST_HERMES_NUM=42\n")
        from scripts.env_loader import load_env_file
        loaded = load_env_file(env_file)
        assert "TEST_HERMES_KEY" in loaded
        assert "TEST_HERMES_NUM" in loaded
        assert os.environ.get("TEST_HERMES_KEY") == "hello"

    def test_skips_comments_and_blanks(self, tmp_path):
        """跳过 # 注释行和空行"""
        env_file = tmp_path / ".env"
        env_file.write_text("# this is a comment\n\nTEST_HERMES_A=1\n")
        from scripts.env_loader import load_env_file
        loaded = load_env_file(env_file)
        assert "TEST_HERMES_A" in loaded
        assert len(loaded) == 1

    def test_skips_lines_without_equals(self, tmp_path):
        """跳过没有 = 的行"""
        env_file = tmp_path / ".env"
        env_file.write_text("NOTANENV\nTEST_HERMES_B=2\n")
        from scripts.env_loader import load_env_file
        loaded = load_env_file(env_file)
        assert "TEST_HERMES_B" in loaded
        assert "NOTANENV" not in loaded

    def test_strips_quotes(self, tmp_path):
        """去掉值两端的引号"""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_HERMES_Q='quoted'\nTEST_HERMES_DQ=\"dquoted\"\n")
        from scripts.env_loader import load_env_file
        loaded = load_env_file(env_file)
        assert os.environ.get("TEST_HERMES_Q") == "quoted"
        assert os.environ.get("TEST_HERMES_DQ") == "dquoted"

    def test_strips_api_keys_but_sets_os_environ(self, tmp_path):
        """API_KEY/TOKEN/SECRET 变量被设置到 os.environ"""
        env_file = tmp_path / ".env"
        env_file.write_text("MY_API_KEY=sk-test123\nMY_TOKEN=tok-abc\nMY_SECRET=secret-x\n")
        from scripts.env_loader import load_env_file
        loaded = load_env_file(env_file)
        assert "MY_API_KEY" in loaded
        assert "MY_TOKEN" in loaded
        assert "MY_SECRET" in loaded
        assert os.environ.get("MY_API_KEY") == "sk-test123"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        """文件不存在时返回空 dict"""
        from scripts.env_loader import load_env_file
        result = load_env_file(tmp_path / "nonexistent.env")
        assert result == {}

    def test_default_path_is_hermes_home_dot_env(self, monkeypatch):
        """不传参数时默认路径为 HERMES_HOME/.env"""
        import scripts.env_loader as el
        monkeypatch.setattr(el, "get_hermes_home", lambda: Path("/tmp/fake_hermes"))
        # Should not crash, just return empty since file doesn't exist
        result = el.load_env_file()
        assert result == {}


class TestResolveEnvRefs:
    """resolve_env_refs() — 替换 ${ENV_VAR} 引用"""

    def test_basic_replacement(self):
        """基础 ${VAR} 替换"""
        os.environ["TEST_HERMES_NAME"] = "HermesAI"
        from scripts.env_loader import resolve_env_refs
        result = resolve_env_refs("Hello ${TEST_HERMES_NAME}")
        assert result == "Hello HermesAI"

    def test_missing_var_keeps_placeholder(self):
        """未设置的环境变量保留 ${VAR} 原样"""
        from scripts.env_loader import resolve_env_refs
        result = resolve_env_refs("${NONEXISTENT_VAR_XYZ}")
        assert result == "${NONEXISTENT_VAR_XYZ}"

    def test_multiple_replacements(self):
        """多个变量同时替换"""
        os.environ["TEST_HERMES_A"] = "foo"
        os.environ["TEST_HERMES_B"] = "bar"
        from scripts.env_loader import resolve_env_refs
        result = resolve_env_refs("${TEST_HERMES_A}-${TEST_HERMES_B}")
        assert result == "foo-bar"

    def test_no_refs(self):
        """没有引用时原样返回"""
        from scripts.env_loader import resolve_env_refs
        result = resolve_env_refs("plain text")
        assert result == "plain text"

    def test_empty_string(self):
        """空字符串返回空"""
        from scripts.env_loader import resolve_env_refs
        result = resolve_env_refs("")
        assert result == ""


class TestResolveConfigEnv:
    """resolve_config_env() — 递归替换配置 dict"""

    def test_replaces_in_dict_values(self):
        """替换 dict 中的 ${VAR}"""
        os.environ["TEST_HERMES_API"] = "https://api.test"
        from scripts.env_loader import resolve_config_env
        config = {"url": "${TEST_HERMES_API}", "name": "test"}
        result = resolve_config_env(config)
        assert result["url"] == "https://api.test"
        assert result["name"] == "test"

    def test_replaces_in_nested_dict(self):
        """嵌套 dict 递归替换"""
        os.environ["TEST_HERMES_KEY"] = "secret123"
        from scripts.env_loader import resolve_config_env
        config = {"outer": {"inner": "${TEST_HERMES_KEY}"}}
        result = resolve_config_env(config)
        assert result["outer"]["inner"] == "secret123"

    def test_replaces_in_list(self):
        """替换列表中的 ${VAR}"""
        os.environ["TEST_HERMES_HOST"] = "localhost"
        from scripts.env_loader import resolve_config_env
        config = {"hosts": ["${TEST_HERMES_HOST}", "backup"]}
        result = resolve_config_env(config)
        assert result["hosts"][0] == "localhost"
        assert result["hosts"][1] == "backup"

    def test_full_var_replacement(self):
        """整个字符串就是 ${VAR} 时特别处理"""
        os.environ["TEST_HERMES_VAL"] = "full_value"
        from scripts.env_loader import resolve_config_env
        config = "${TEST_HERMES_VAL}"
        result = resolve_config_env(config)
        assert result == "full_value"

    def test_non_string_types_unchanged(self):
        """非字符串类型（int、bool、None）保持不变"""
        from scripts.env_loader import resolve_config_env
        config = {"count": 42, "active": True, "data": None}
        result = resolve_config_env(config)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["data"] is None


class TestInitEnv:
    """init_env() — 初始化环境变量"""

    def test_returns_true_on_success(self, tmp_path, monkeypatch):
        """正常返回 True"""
        import scripts.env_loader as el
        monkeypatch.setattr(el, "load_env_file", lambda p=None: {"TEST": "ok"})
        assert el.init_env() is True

    def test_returns_false_on_exception(self, monkeypatch):
        """异常时返回 False"""
        import scripts.env_loader as el
        def _broken(*a, **kw):
            raise RuntimeError("broken")
        monkeypatch.setattr(el, "load_env_file", _broken)
        assert el.init_env() is False

    def test_alt_path_fallback(self, tmp_path, monkeypatch):
        """第一次无内容时尝试备用路径"""
        import scripts.env_loader as el
        calls = []
        def _track(p=None):
            calls.append(p)
            return {"key": "val"} if len(calls) > 1 else {}
        monkeypatch.setattr(el, "load_env_file", _track)
        monkeypatch.setattr(el, "get_hermes_home", lambda: tmp_path)
        # Create alt path file
        alt = tmp_path / ".env"
        alt.write_text("X=1\n")
        result = el.init_env()
        assert result is True
        assert len(calls) >= 2
