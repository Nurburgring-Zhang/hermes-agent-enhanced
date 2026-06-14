"""工部（工程建设）真实实现 —— Playwright async API

工部负责页面导航、截图、DOM操作等与浏览器自动化相关的"工程"任务。
"""

from __future__ import annotations

from typing import Any

from scripts.ministry_abc import MinistryBase
from scripts.ministry_exceptions import TaskExecutionError
from scripts.ministry_types import ExecutionResult, ExecutionStatus, TaskPayload

# ── Playwright 导入降级处理 ──────────────────────────────

_PLAYWRIGHT_AVAILABLE: bool = False
async_playwright: Any = None

try:
    from playwright.async_api import async_playwright as _pw
    async_playwright = _pw
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


# ── 工部实现 ─────────────────────────────────────────────

class Gongbu(MinistryBase):
    """工部——浏览器自动化与页面工程。

    支持的能力（注册在 action 字段中）：
    - browser_navigate: 导航到指定 URL 并返回页面基本信息
    - browser_screenshot: 对当前页面截图
    - browser_evaluate: 在页面上下文中执行 JS
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        default_timeout: float = 30.0,
    ) -> None:
        super().__init__(ministry_name="工部")
        self._headless = headless
        self._browser_type = browser_type
        self._default_timeout = default_timeout
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    # ── 生命周期管理 ──────────────────────────────────────

    async def ensure_browser(self) -> None:
        """确保浏览器已启动，若未启动则自动创建。"""
        if self._browser is not None:
            return
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright 未安装。请执行: pip install playwright && playwright install"
            )
        self._playwright = await async_playwright().start()
        browser_launcher = getattr(self._playwright, self._browser_type, None)
        if browser_launcher is None:
            supported = ["chromium", "firefox", "webkit"]
            raise RuntimeError(
                f"不支持的浏览器类型: {self._browser_type}，可选: {supported}"
            )
        self._browser = await browser_launcher.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self._default_timeout * 1000)

    async def close_browser(self) -> None:
        """关闭浏览器，释放资源。"""
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
            self._page = None
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # ── 模板方法实现 ──────────────────────────────────────

    async def _execute_impl(self, task: TaskPayload) -> Any:
        """根据 task['action'] 分发到具体操作。"""
        action: str = task.get("action", "")
        args: dict[str, Any] = task.get("args", {})

        handler = self._get_handler(action)
        if handler is None:
            raise TaskExecutionError(
                ministry="工部",
                task_id=task.get("task_id", ""),
                message=f"不支持的 action: {action}",
            )

        await self.ensure_browser()
        return await handler(args)

    def _get_handler(
        self, action: str
    ) -> Any | None:
        """根据 action 名称查找对应的处理方法。"""
        handlers: dict[str, Any] = {
            "browser_navigate": self._handle_browser_navigate,
            "browser_screenshot": self._handle_browser_screenshot,
            "browser_evaluate": self._handle_browser_evaluate,
        }
        return handlers.get(action)

    # ── 具体操作实现 ──────────────────────────────────────

    async def _handle_browser_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        """真实 Playwright 页面导航。

        必需的 args 参数: url (str)
        可选的 args 参数: wait_until (str), timeout_ms (int)
        """
        url: str = args.get("url", "")
        if not url:
            raise TaskExecutionError(
                ministry="工部",
                message="browser_navigate 缺少必需的参数: url",
                details={"args": args},
            )

        wait_until: str = args.get("wait_until", "load")
        timeout_ms: int | None = args.get("timeout_ms")

        kwargs: dict[str, Any] = {"wait_until": wait_until}
        if timeout_ms is not None:
            kwargs["timeout"] = timeout_ms

        response = await self._page.goto(url, **kwargs)

        title: str = await self._page.title()
        current_url: str = self._page.url
        status_code: int | None = response.status if response else None

        return {
            "url": current_url,
            "title": title,
            "status_code": status_code,
            "final_url": current_url,
        }

    async def _handle_browser_screenshot(self, args: dict[str, Any]) -> bytes:
        """对当前页面截图。

        可选的 args 参数:
            full_page (bool): 是否截取整个页面，默认 True
            path (str): 保存路径，不指定则返回 bytes
            type (str): 图片类型，可选 jpeg/png，默认 png
        """
        full_page: bool = args.get("full_page", True)
        path: str | None = args.get("path")
        screenshot_type: str = args.get("type", "png")

        screenshot: bytes = await self._page.screenshot(
            full_page=full_page,
            path=path,
            type=screenshot_type,  # type: ignore[arg-type]
        )
        return screenshot

    async def _handle_browser_evaluate(self, args: dict[str, Any]) -> Any:
        """在页面上下文中执行 JavaScript。

        必需的 args 参数: script (str)
        """
        script: str = args.get("script", "")
        if not script:
            raise TaskExecutionError(
                ministry="工部",
                message="browser_evaluate 缺少必需的参数: script",
                details={"args": args},
            )

        result: Any = await self._page.evaluate(script)
        return result

    # ── 便捷方法（不经过执行管道） ────────────────────────

    async def navigate(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """便捷方法：直接导航到 URL。"""
        task: TaskPayload = {
            "task_id": "direct_navigate",
            "action": "browser_navigate",
            "args": {"url": url, **kwargs},
        }
        result: ExecutionResult = await self.execute(task)
        if result["status"] != ExecutionStatus.SUCCESS:
            raise TaskExecutionError(
                ministry="工部",
                task_id=result["task_id"],
                message=result["error"] or "导航失败",
            )
        return result["data"]

    async def screenshot(self, **kwargs: Any) -> bytes:
        """便捷方法：直接截图。"""
        task: TaskPayload = {
            "task_id": "direct_screenshot",
            "action": "browser_screenshot",
            "args": dict(kwargs),
        }
        result: ExecutionResult = await self.execute(task)
        if result["status"] != ExecutionStatus.SUCCESS:
            raise TaskExecutionError(
                ministry="工部",
                task_id=result["task_id"],
                message=result["error"] or "截图失败",
            )
        return result["data"]

    async def evaluate(self, script: str) -> Any:
        """便捷方法：直接执行 JS。"""
        task: TaskPayload = {
            "task_id": "direct_evaluate",
            "action": "browser_evaluate",
            "args": {"script": script},
        }
        result: ExecutionResult = await self.execute(task)
        if result["status"] != ExecutionStatus.SUCCESS:
            raise TaskExecutionError(
                ministry="工部",
                task_id=result["task_id"],
                message=result["error"] or "JS 执行失败",
            )
        return result["data"]


# ── 辅助方法：快速获取实例 ────────────────────────────────

_default_gongbu: Gongbu | None = None


def get_gongbu(
    headless: bool = True,
    browser_type: str = "chromium",
) -> Gongbu:
    """获取（或创建）全局默认的工部实例。"""
    global _default_gongbu
    if _default_gongbu is None:
        _default_gongbu = Gongbu(headless=headless, browser_type=browser_type)
    return _default_gongbu


async def demo_navigate(url: str = "https://example.com") -> dict[str, Any]:
    """快速演示：导航到 URL 并返回页面信息。"""
    gb = get_gongbu()
    try:
        result = await gb.navigate(url)
        return result
    finally:
        await gb.close_browser()
