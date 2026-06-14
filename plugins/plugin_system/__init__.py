"""
Hermes Plugin System - Core plugin infrastructure.
Provides base classes, registry, manager, and event bus.
"""

from .cli import register_commands
from .core.event_bus import Event, EventBus
from .core.plugin_base import Plugin, PluginConfig, PluginManifest, PluginState
from .core.plugin_manager import HookType, PluginManager
from .core.plugin_registry import PluginRegistry

__all__ = [
    "Event",
    "EventBus",
    "HookType",
    "Plugin",
    "PluginConfig",
    "PluginManager",
    "PluginManifest",
    "PluginRegistry",
    "PluginState",
    "register_commands"
]
