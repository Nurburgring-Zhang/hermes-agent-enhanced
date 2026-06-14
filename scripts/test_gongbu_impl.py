#!/usr/bin/env python3
"""Tests for gongbu_impl.py — 工部（工程建设）Playwright async API"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".hermes"))


class TestGongbu:
    """工部初始化和基本结构"""

    def test_import_available(self):
        """模块可导入"""
        from scripts.gongbu_impl import Gongbu
        assert Gongbu is not None

    def test_init_defaults(self):
        """默认参数初始化"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        assert gb._headless is True
        assert gb._browser_type == "chromium"
        assert gb._default_timeout == 30.0
        assert gb._browser is None
        assert gb._page is None

    def test_init_custom(self):
        """自定义参数初始化"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu(headless=False, browser_type="firefox", default_timeout=60.0)
        assert gb._headless is False
        assert gb._browser_type == "firefox"
        assert gb._default_timeout == 60.0

    def test_ministry_name(self):
        """工部名称正确"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        assert gb.ministry_name == "工部"

    def test_get_handler_known_actions(self):
        """已知 action 返回对应 handler"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        assert gb._get_handler("browser_navigate") is not None
        assert gb._get_handler("browser_screenshot") is not None
        assert gb._get_handler("browser_evaluate") is not None

    def test_get_handler_unknown_action(self):
        """未知 action 返回 None"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        assert gb._get_handler("nonexistent_action") is None

    def test_playwright_available_flag(self):
        """Playwright 可用性标志"""
        from scripts.gongbu_impl import _PLAYWRIGHT_AVAILABLE
        assert isinstance(_PLAYWRIGHT_AVAILABLE, bool)

    def test_get_gongbu_singleton(self):
        """get_gongbu() 返回全局实例"""
        from scripts.gongbu_impl import get_gongbu
        gb1 = get_gongbu()
        gb2 = get_gongbu()
        assert gb1 is gb2

    def test_get_gongbu_custom_params(self):
        """get_gongbu() 首次调用时使用自定义参数"""
        # Reset
        import scripts.gongbu_impl as gi
        from scripts.gongbu_impl import get_gongbu
        gi._default_gongbu = None
        gb = get_gongbu(headless=False, browser_type="firefox")
        assert gb._headless is False
        assert gb._browser_type == "firefox"
        gi._default_gongbu = None

    def test_ensure_browser_raises_without_playwright(self, monkeypatch):
        """Playwright 未安装时 ensure_browser 抛出 RuntimeError"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        monkeypatch.setattr("scripts.gongbu_impl._PLAYWRIGHT_AVAILABLE", False)
        import asyncio
        with pytest.raises(RuntimeError, match="Playwright 未安装"):
            asyncio.run(gb.ensure_browser())

    def test_close_browser_cleanup_safe(self):
        """close_browser 在未初始化时安全调用"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        import asyncio
        # Should not raise even though nothing is initialized
        asyncio.run(gb.close_browser())
        assert gb._page is None
        assert gb._browser is None
        assert gb._playwright is None

    def test_execute_unknown_action_raises(self):
        """execute() 未知 action 抛出或返回错误"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        # Mock ensure_browser to avoid Playwright dependency
        import asyncio
        async def fake_ensure():
            pass
        gb.ensure_browser = fake_ensure
        result = asyncio.run(gb.execute({"task_id": "test", "action": "unknown_action", "args": {}}))
        assert "error" in str(result) or "unknown" in str(result).lower()

    def test_handle_navigate_missing_url_raises(self):
        """browser_navigate 缺少 url 参数抛出异常"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        import asyncio
        with pytest.raises(Exception, match="url"):
            asyncio.run(gb._handle_browser_navigate({}))

    def test_handle_evaluate_missing_script_raises(self):
        """browser_evaluate 缺少 script 参数抛出异常"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()
        import asyncio
        with pytest.raises(Exception, match="script"):
            asyncio.run(gb._handle_browser_evaluate({}))

    def test_navigate_convenience_method(self, monkeypatch):
        """navigate() 便捷方法正确创建任务"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()

        called = []
        async def fake_execute(task):
            called.append(task)
            return {"status": "success", "data": {"url": task["args"]["url"]}, "task_id": "test", "error": None}

        monkeypatch.setattr(gb, "execute", fake_execute)
        import asyncio
        result = asyncio.run(gb.navigate("https://example.com"))
        assert len(called) == 1
        assert called[0]["action"] == "browser_navigate"
        assert called[0]["args"]["url"] == "https://example.com"
        assert result["url"] == "https://example.com"

    def test_screenshot_convenience_method(self, monkeypatch):
        """screenshot() 便捷方法创建正确任务"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()

        called = []
        async def fake_execute(task):
            called.append(task)
            return {"status": "success", "data": b"fake_image", "task_id": "test", "error": None}

        monkeypatch.setattr(gb, "execute", fake_execute)
        import asyncio
        result = asyncio.run(gb.screenshot(full_page=False))
        assert len(called) == 1
        assert called[0]["action"] == "browser_screenshot"
        assert result == b"fake_image"

    def test_evaluate_convenience_method(self, monkeypatch):
        """evaluate() 便捷方法创建正确任务"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()

        called = []
        async def fake_execute(task):
            called.append(task)
            return {"status": "success", "data": 42, "task_id": "test", "error": None}

        monkeypatch.setattr(gb, "execute", fake_execute)
        import asyncio
        result = asyncio.run(gb.evaluate("1+1"))
        assert len(called) == 1
        assert called[0]["action"] == "browser_evaluate"
        assert called[0]["args"]["script"] == "1+1"
        assert result == 42

    def test_navigate_convenience_raises_on_failure(self, monkeypatch):
        """navigate() 执行失败时抛出 TaskExecutionError"""
        from scripts.gongbu_impl import Gongbu
        gb = Gongbu()

        async def fake_execute(task):
            return {"status": "error", "data": None, "task_id": "test", "error": "failed"}

        monkeypatch.setattr(gb, "execute", fake_execute)
        import asyncio
        with pytest.raises(Exception):
            asyncio.run(gb.navigate("https://example.com"))

    def test_demo_navigate_importable(self):
        """demo_navigate 函数可导入"""
        from scripts.gongbu_impl import demo_navigate
        assert callable(demo_navigate)
