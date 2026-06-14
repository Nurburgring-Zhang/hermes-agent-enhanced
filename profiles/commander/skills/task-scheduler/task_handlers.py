"""
Task Handlers Registry
Global registry for task function handlers.
"""

from collections.abc import Callable

# Global registry
_handlers: dict[str, Callable] = {}


def register(name: str, handler: Callable):
    """Register a task handler."""
    _handlers[name] = handler


def unregister(name: str):
    """Unregister a task handler."""
    _handlers.pop(name, None)


def get(name: str) -> Optional[Callable]:
    """Get handler by name."""
    return _handlers.get(name)


def list_handlers() -> dict[str, Callable]:
    """List all registered handlers."""
    return dict(_handlers)


def clear():
    """Clear all handlers."""
    _handlers.clear()
