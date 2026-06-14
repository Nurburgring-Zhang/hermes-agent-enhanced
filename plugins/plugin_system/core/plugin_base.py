"""
Hermes Plugin System - Base Plugin Class
Defines the lifecycle and interface for all Hermes plugins.
"""

import logging
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """Plugin lifecycle states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginConfig:
    """Plugin configuration data."""
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True
    auto_start: bool = False
    dependencies: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginManifest:
    """Plugin manifest parsed from plugin.json."""
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """
    Abstract base class for all Hermes plugins.
    Plugins must inherit from this class and implement the required methods.
    """

    def __init__(self, manifest: PluginManifest, config: PluginConfig):
        self.manifest = manifest
        self.config = config
        self.state = PluginState.UNLOADED
        self.manager: PluginManager | None = None
        self.event_bus: EventBus | None = None
        self._logger = logging.getLogger(f"hermes.plugin.{manifest.name}")

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    async def init(self) -> None:
        """
        Initialize plugin resources.
        Called once when plugin is first loaded.
        Override for custom initialization logic.
        """
        self.state = PluginState.LOADED
        self._logger.info(f"Plugin {self.name} initialized")

    async def start(self) -> None:
        """
        Start the plugin.
        Called when plugin is enabled or auto-started.
        Override for custom startup logic.
        """
        self.state = PluginState.RUNNING
        self._logger.info(f"Plugin {self.name} started")

    async def stop(self) -> None:
        """
        Stop the plugin.
        Called when plugin is disabled or system shutdown.
        Override for custom cleanup logic.
        """
        self.state = PluginState.STOPPED
        self._logger.info(f"Plugin {self.name} stopped")

    async def execute(self, action: str, **kwargs) -> Any:
        """
        Execute a plugin-specific action.
        Args:
            action: Action name to execute
            **kwargs: Action parameters
        Returns:
            Result of the action
        """
        method = getattr(self, action, None)
        if method and callable(method):
            return await method(**kwargs)
        raise NotImplementedError(f"Action '{action}' not implemented in plugin {self.name}")

    def get_tools(self) -> list[dict[str, Any]]:
        """
        Return list of tools/exposed functions this plugin provides.
        Used for integration with main Hermes system.
        """
        return []

    def on_event(self, event: str, data: Any) -> None:
        """
        Handle events from other plugins.
        Override to react to plugin events.
        """

    async def health_check(self) -> dict[str, Any]:
        """
        Return plugin health status.
        Used for monitoring and diagnostics.
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "healthy": self.state in [PluginState.RUNNING, PluginState.LOADED]
        }

    def __repr__(self) -> str:
        return f"<Plugin {self.name} v{self.version} state={self.state.value}>"
