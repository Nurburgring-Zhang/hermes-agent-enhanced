"""
Hermes Plugin System - Plugin Manager
Central manager for plugin lifecycle, dependencies, and hooks.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any

from .event_bus import EventBus
from .plugin_base import Plugin
from .plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class HookType:
    """Hook point constants."""
    # System hooks
    HERMES_START = "hermes.start"
    HERMES_STOP = "hermes.stop"
    HERMES_CONFIG_LOAD = "hermes.config.load"
    HERMES_CONFIG_RELOAD = "hermes.config.reload"

    # Message hooks
    MESSAGE_RECEIVE = "message.receive"
    MESSAGE_BEFORE_SEND = "message.before_send"
    MESSAGE_SENT = "message.sent"

    # Command hooks
    COMMAND_EXECUTE = "command.execute"
    COMMAND_BEFORE = "command.before"
    COMMAND_AFTER = "command.after"

    # AI hooks
    AI_BEFORE_GENERATE = "ai.before_generate"
    AI_AFTER_GENERATE = "ai.after_generate"
    AI_TOOL_USE = "ai.tool_use"


class DependencyGraph:
    """Simple dependency resolver."""

    def __init__(self):
        self.dependencies: dict[str, set[str]] = defaultdict(set)
        self.dependents: dict[str, set[str]] = defaultdict(set)

    def add_dependency(self, plugin: str, depends_on: list[str]):
        """Add a dependency relationship."""
        self.dependencies[plugin] = set(depends_on)
        for dep in depends_on:
            self.dependents[dep].add(plugin)

    def resolve(self) -> list[list[str]]:
        """
        Resolve dependencies using topological sort.
        Returns list of plugin batches in load order.
        """
        visited = set()
        temp = set()
        result: list[list[str]] = []

        def visit(plugin: str, path: set[str]) -> list[str]:
            if plugin in temp:
                cycle = " -> ".join(path) + " -> " + plugin
                raise ValueError(f"Circular dependency detected: {cycle}")
            if plugin in visited:
                return []

            temp.add(plugin)
            path.add(plugin)

            batch = []
            for dep in sorted(self.dependencies.get(plugin, [])):
                batch.extend(visit(dep, path.copy()))

            temp.remove(plugin)
            visited.add(plugin)
            batch.append(plugin)
            return batch

        all_plugins = set(self.dependencies.keys()) | set(self.dependents.keys())

        for plugin in sorted(all_plugins):
            if plugin not in visited:
                result.append([])
                for p in visit(plugin, set()):
                    # Find which batch this belongs to (avoid duplicates)
                    if p not in [item for batch in result for item in batch]:
                        result[-1].append(p)

        # Deduplicate and flatten
        final = []
        seen = set()
        for batch in result:
            clean_batch = [p for p in batch if p not in seen]
            if clean_batch:
                final.append(clean_batch)
                seen.update(clean_batch)

        return final

    def get_missing_dependencies(self, plugin: str) -> set[str]:
        """Get dependencies that are not in the graph."""
        missing = set()
        for dep in self.dependencies.get(plugin, []):
            if dep not in self.dependencies and dep not in self.dependents:
                missing.add(dep)
        return missing


class PluginManager:
    """
    Main plugin manager orchestrating lifecycle, hooks, and communication.
    """

    def __init__(self, plugins_dir: str = "~/.hermes/plugins"):
        self.registry = PluginRegistry(plugins_dir)
        self.event_bus = EventBus()
        self.loaded_plugins: dict[str, Plugin] = {}
        self.enabled_plugins: set[str] = set()
        self.hooks: dict[str, list[str]] = defaultdict(list)
        self._running = False
        self._lock = asyncio.Lock()
        self._dependency_graph = DependencyGraph()

    async def initialize(self) -> None:
        """Initialize plugin manager."""
        logger.info("Initializing plugin manager...")

        # Discover all plugins
        discovered = self.registry.discover_plugins()

        # Build dependency graph
        for name, manifest in self.registry.manifests.items():
            if manifest.dependencies:
                self._dependency_graph.add_dependency(name, manifest.dependencies)

        # Load enabled plugins from config
        for name, config in self.registry.configs.items():
            if config.enabled:
                self.enabled_plugins.add(name)

        logger.info(f"Plugin manager initialized, {len(discovered)} plugins discovered")

    async def start_all(self, auto_start_only: bool = True) -> None:
        """Start all enabled plugins."""
        self._running = True
        logger.info("Starting plugins...")

        try:
            # Resolve dependency order
            load_order = self._dependency_graph.resolve()

            # Flatten and filter to enabled plugins
            plugins_to_load = []
            for batch in load_order:
                for plugin_name in batch:
                    if plugin_name in self.enabled_plugins:
                        if not auto_start_only or self.registry.configs.get(plugin_name, PluginConfig).auto_start:
                            plugins_to_load.append(plugin_name)

            # Load and start plugins in order
            for plugin_name in plugins_to_load:
                try:
                    await self.load_and_start(plugin_name)
                except Exception as e:
                    logger.error(f"Failed to start plugin {plugin_name}: {e}")

            # Emit startup hook
            await self._emit_hook(HookType.HERMES_START, {"manager": self})

            logger.info(f"Started {len(self.loaded_plugins)} plugins")

        except Exception as e:
            logger.error(f"Error during plugin startup: {e}")
            raise

    async def load_and_start(self, plugin_name: str) -> Plugin | None:
        """Load and start a plugin."""
        async with self._lock:
            if plugin_name in self.loaded_plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return self.loaded_plugins[plugin_name]

            # Check dependencies
            missing = self._dependency_graph.get_missing_dependencies(plugin_name)
            if missing:
                logger.warning(f"Plugin {plugin_name} has missing dependencies: {missing}")

            # Load the plugin
            plugin = await self.registry.load_plugin(plugin_name, self)
            if plugin is None:
                return None

            # Register hooks
            await self._register_plugin_hooks(plugin)

            self.loaded_plugins[plugin_name] = plugin

            # Start if enabled
            if plugin_name in self.enabled_plugins:
                await plugin.start()

            return plugin

    async def stop_all(self) -> None:
        """Stop all loaded plugins."""
        logger.info("Stopping plugins...")
        self._running = False

        # Emit shutdown hook (before stopping)
        await self._emit_hook(HookType.HERMES_STOP, {"manager": self})

        # Stop plugins in reverse order
        for plugin_name in reversed(list(self.loaded_plugins.keys())):
            try:
                plugin = self.loaded_plugins[plugin_name]
                await plugin.stop()
                logger.debug(f"Stopped plugin {plugin_name}")
            except Exception as e:
                logger.error(f"Error stopping plugin {plugin_name}: {e}")

        self.loaded_plugins.clear()
        logger.info("All plugins stopped")

    async def reload_plugin_config(self, plugin_name: str) -> bool:
        """Reload configuration for a specific plugin."""
        try:
            # Re-discover to reload manifest
            self.registry.discover_plugins()

            # Reload config from file
            config_file = self.registry.plugins_dir / plugin_name / "config.yaml"
            if config_file.exists():
                self.registry._load_config(config_file, self.registry.manifests[plugin_name])

            # Emit config reload hook
            await self._emit_hook(HookType.HERMES_CONFIG_RELOAD, {
                "plugin": plugin_name,
                "config": self.registry.configs.get(plugin_name)
            })

            logger.info(f"Plugin {plugin_name} config reloaded")
            return True
        except Exception as e:
            logger.error(f"Failed to reload config for {plugin_name}: {e}")
            return False

    async def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin."""
        if plugin_name not in self.registry.manifests:
            logger.error(f"Plugin {plugin_name} not found")
            return False

        # Update config
        config = self.registry.configs.get(plugin_name)
        if config:
            config.enabled = True

        self.enabled_plugins.add(plugin_name)

        # Load and start if not already
        if plugin_name not in self.loaded_plugins:
            await self.load_and_start(plugin_name)

        logger.info(f"Plugin {plugin_name} enabled")
        return True

    async def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin."""
        if plugin_name not in self.enabled_plugins:
            logger.warning(f"Plugin {plugin_name} already disabled")
            return False

        # Stop if running
        if plugin_name in self.loaded_plugins:
            await self.loaded_plugins[plugin_name].stop()
            del self.loaded_plugins[plugin_name]

        # Update config
        config = self.registry.configs.get(plugin_name)
        if config:
            config.enabled = False

        self.enabled_plugins.discard(plugin_name)

        logger.info(f"Plugin {plugin_name} disabled")
        return True

    def get_plugin(self, plugin_name: str) -> Plugin | None:
        """Get a loaded plugin by name."""
        return self.loaded_plugins.get(plugin_name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all plugins with status."""
        result = self.registry.list_plugins()
        for item in result:
            item["enabled"] = item["name"] in self.enabled_plugins
        return result

    def get_plugins_by_capability(self, capability: str) -> list[Plugin]:
        """Get all plugins that have a specific capability."""
        result = []
        for plugin in self.loaded_plugins.values():
            if capability in plugin.manifest.capabilities:
                result.append(plugin)
        return result

    def get_plugins_by_hook(self, hook: str) -> list[Plugin]:
        """Get all plugins registered for a hook."""
        result = []
        for plugin in self.loaded_plugins.values():
            if hook in plugin.manifest.hooks:
                result.append(plugin)
        return result

    async def emit_hook(self, hook_type: str, data: Any) -> list[Any]:
        """
        Emit a hook to all plugins registered for it.
        Args:
            hook_type: Hook type constant
            data: Data to pass to handlers
        Returns:
            List of results from all handlers
        """
        return await self._emit_hook(hook_type, data)

    async def _emit_hook(self, hook_type: str, data: Any) -> list[Any]:
        """Internal hook emission."""
        results = []
        plugins = self.get_plugins_by_hook(hook_type)

        for plugin in plugins:
            try:
                if hasattr(plugin, hook_type.replace(".", "_")):
                    handler = getattr(plugin, hook_type.replace(".", "_"))
                    if callable(handler):
                        result = await handler(data) if asyncio.iscoroutinefunction(handler) else handler(data)
                        results.append(result)
            except Exception as e:
                logger.error(f"Error in hook {hook_type} for plugin {plugin.name}: {e}")

        return results

    async def call_plugin_action(self, plugin_name: str, action: str, **kwargs) -> Any:
        """Call an action on a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_name} not loaded")
        return await plugin.execute(action, **kwargs)

    def get_plugins_providing_capability(self, capability: str) -> list[Plugin]:
        """Get all plugins that provide a specific capability."""
        return [
            plugin for plugin in self.loaded_plugins.values()
            if capability in plugin.manifest.capabilities
        ]

    def get_plugin_tools(self) -> list[dict[str, Any]]:
        """Aggregate tools from all plugins."""
        tools = []
        for plugin in self.loaded_plugins.values():
            plugin_tools = plugin.get_tools()
            for tool in plugin_tools:
                tool["plugin"] = plugin.name
                tools.append(tool)
        return tools
