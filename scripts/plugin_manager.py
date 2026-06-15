#!/usr/bin/env python3
"""
Hermes Plugin Manager v1.0
===========================
Plugin registration, discovery, lifecycle hooks, configuration management, and hot-reload.

Core features:
  1. Plugin registration & discovery — scan directories, load Python modules dynamically
  2. Lifecycle hooks — on_load, on_unload, on_tool_call (pre/post)
  3. Plugin configuration — per-plugin YAML/JSON config with validation
  4. Hot-reload support — watch for file changes and reload plugins

Architecture:
  Plugins are Python modules implementing the HermesPlugin base class.
  They live in ~/.hermes/plugins/<name>/plugin.py and are auto-discovered.

Usage:
  from scripts.plugin_manager import PluginManager, HermesPlugin
  pm = PluginManager()
  pm.discover()
  pm.load_all()
  pm.call_hook("on_tool_call", tool_name="write_file", args={...})
"""

import importlib
import importlib.util
import inspect
import json
import logging
import sys
import threading
import time
from abc import ABC
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

HERMES_HOME = Path.home() / ".hermes"
DEFAULT_PLUGIN_DIR = HERMES_HOME / "plugins"
DEFAULT_PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Exceptions
# ============================================================================


class PluginError(Exception):
    """Base exception for plugin errors."""


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""


class PluginHookError(PluginError):
    """Raised when a plugin hook fails."""


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin is not found."""


# ============================================================================
# HermesPlugin Base Class
# ============================================================================


class HermesPlugin(ABC):
    """Base class for all Hermes plugins.

    Plugins subclass this and override lifecycle hooks.
    Each plugin must define:
      - name: str        — Unique plugin identifier
      - version: str     — Semantic version string
      - description: str — Human-readable description
    """

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._loaded = False

    @property
    def config(self) -> Dict[str, Any]:
        """Plugin configuration dictionary."""
        return self._config

    @config.setter
    def config(self, value: Dict[str, Any]) -> None:
        self._config = value

    # ---- Lifecycle hooks ----

    def on_load(self) -> None:
        """Called when the plugin is loaded.

        Override to perform initialization: open connections, register handlers, etc.
        """
        pass

    def on_unload(self) -> None:
        """Called when the plugin is unloaded.

        Override to perform cleanup: close connections, flush buffers, etc.
        """
        pass

    def on_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Optional[Dict]:
        """Called before a tool is executed.

        Args:
            tool_name: Name of the tool being called (e.g., 'write_file')
            args: Arguments passed to the tool

        Returns:
            None to allow the call, or a dict to short-circuit with a response.
        """
        return None

    def on_tool_result(
        self, tool_name: str, args: Dict[str, Any], result: Any
    ) -> Any:
        """Called after a tool is executed.

        Args:
            tool_name: Name of the tool that was called
            args: Arguments that were passed
            result: The result returned by the tool

        Returns:
            Possibly modified result.
        """
        return result

    def on_shutdown(self) -> None:
        """Called during system shutdown."""
        pass


# ============================================================================
# Plugin Info
# ============================================================================


@dataclass
class PluginInfo:
    """Metadata for a discovered/loaded plugin."""

    name: str
    version: str
    description: str
    path: Path
    module_name: str = ""
    loaded: bool = False
    instance: Optional[HermesPlugin] = None
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    enabled: bool = True
    load_time: float = 0.0


# ============================================================================
# Plugin Manager
# ============================================================================


class PluginManager:
    """Central plugin manager for Hermes.

    Handles discovery, loading, unloading, configuration, and hot-reload of plugins.

    Features:
      - Auto-discovery from plugin directories
      - Dependency ordering (load plugins in dependency order)
      - Lifecycle hook dispatch
      - Per-plugin JSON configuration
      - Hot-reload via file watcher thread
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self._plugin_dirs = plugin_dirs or [DEFAULT_PLUGIN_DIR]
        self._plugins: OrderedDict[str, PluginInfo] = OrderedDict()
        self._hook_registry: Dict[str, Dict[str, Callable]] = {}
        self._lock = threading.RLock()
        self._watcher_thread: Optional[threading.Thread] = None
        self._watcher_stop = threading.Event()
        self._file_mtimes: Dict[Path, float] = {}
        self._config_dir = HERMES_HOME / "config" / "plugins"
        self._config_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self, plugin_dirs: Optional[List[Path]] = None) -> List[PluginInfo]:
        """Discover all plugins in the configured directories.

        A plugin directory must contain a plugin.py file with a HermesPlugin subclass.

        Returns:
            List of discovered PluginInfo objects.
        """
        dirs = plugin_dirs or self._plugin_dirs
        discovered: List[PluginInfo] = []

        for base_dir in dirs:
            if not base_dir.exists():
                continue
            for entry in sorted(base_dir.iterdir()):
                if not entry.is_dir():
                    continue
                plugin_file = entry / "plugin.py"
                if not plugin_file.exists():
                    continue

                # Try to extract metadata without full import
                meta = self._extract_metadata(plugin_file)
                info = PluginInfo(
                    name=meta.get("name", entry.name),
                    version=meta.get("version", "0.1.0"),
                    description=meta.get("description", ""),
                    path=entry,
                    module_name=f"plugins.{entry.name}.plugin",
                )
                discovered.append(info)

                # Track file mtimes for watch
                self._file_mtimes[plugin_file] = plugin_file.stat().st_mtime

        return discovered

    def _extract_metadata(self, plugin_file: Path) -> Dict[str, str]:
        """Extract plugin metadata from file without executing it."""
        meta = {}
        try:
            content = plugin_file.read_text(encoding="utf-8")
            import re

            name_match = re.search(r'^\s*name\s*[:=]\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            ver_match = re.search(r'^\s*version\s*[:=]\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            desc_match = re.search(
                r'^\s*description\s*[:=]\s*["\']([^"\']+)["\']', content, re.MULTILINE
            )

            if name_match:
                meta["name"] = name_match.group(1)
            if ver_match:
                meta["version"] = ver_match.group(1)
            if desc_match:
                meta["description"] = desc_match.group(1)
        except Exception:
            pass
        return meta

    # ------------------------------------------------------------------
    # Loading / Unloading
    # ------------------------------------------------------------------

    def load(self, plugin_name: str) -> Optional[HermesPlugin]:
        """Load a single plugin by name.

        First discovers if not already known, then imports the module,
        instantiates the plugin class, and calls on_load().

        Returns:
            The plugin instance, or None if loading failed.
        """
        with self._lock:
            # Check already loaded
            if plugin_name in self._plugins and self._plugins[plugin_name].loaded:
                return self._plugins[plugin_name].instance

            # Discover if not known
            if plugin_name not in self._plugins:
                discovered = self.discover()
                found = [d for d in discovered if d.name == plugin_name]
                if not found:
                    raise PluginNotFoundError(f"Plugin '{plugin_name}' not found")
                self._plugins[plugin_name] = found[0]

            info = self._plugins[plugin_name]

            if not info.enabled:
                logger.info(f"Plugin '{plugin_name}' is disabled, skipping load")
                return None

            # Load plugin configuration
            info.config = self._load_plugin_config(plugin_name)

            # Import the module
            try:
                spec = importlib.util.spec_from_file_location(
                    f"hermes_plugin_{plugin_name}",
                    str(info.path / "plugin.py"),
                )
                if spec is None or spec.loader is None:
                    raise PluginLoadError(f"Cannot create module spec for '{plugin_name}'")
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)
                info.module_name = spec.name
            except Exception as e:
                raise PluginLoadError(
                    f"Failed to import plugin '{plugin_name}': {e}"
                ) from e

            # Find the HermesPlugin subclass
            plugin_class = None
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, HermesPlugin)
                    and obj is not HermesPlugin
                    and obj.__module__ == module.__name__
                ):
                    plugin_class = obj
                    break

            if plugin_class is None:
                raise PluginLoadError(
                    f"No HermesPlugin subclass found in '{plugin_name}'"
                )

            # Update metadata from class attributes
            info.name = getattr(plugin_class, "name", info.name)
            info.version = getattr(plugin_class, "version", info.version)
            info.description = getattr(plugin_class, "description", info.description)
            info.depends_on = getattr(plugin_class, "depends_on", [])

            # Resolve dependencies
            for dep in info.depends_on:
                if dep not in self._plugins or not self._plugins[dep].loaded:
                    self.load(dep)

            # Instantiate and call on_load
            start_time = time.monotonic()
            try:
                instance = plugin_class(config=info.config)
                instance.on_load()
            except Exception as e:
                raise PluginLoadError(
                    f"Plugin '{plugin_name}' on_load failed: {e}"
                ) from e

            info.loaded = True
            info.instance = instance
            info.load_time = time.monotonic() - start_time

            logger.info(
                f"Loaded plugin '{plugin_name}' v{info.version} "
                f"in {info.load_time:.3f}s"
            )

            # Register hooks
            self._register_hooks(plugin_name, instance)

            return instance

    def load_all(self) -> Dict[str, Optional[HermesPlugin]]:
        """Discover and load all plugins. Returns {name: instance} mapping."""
        discovered = self.discover()
        results: Dict[str, Optional[HermesPlugin]] = {}
        for info in discovered:
            try:
                instance = self.load(info.name)
                results[info.name] = instance
            except PluginError as e:
                logger.error(f"Failed to load plugin '{info.name}': {e}")
                results[info.name] = None
        return results

    def unload(self, plugin_name: str) -> bool:
        """Unload a plugin: calls on_unload(), removes from registry.

        Returns True if successfully unloaded, False if not loaded.
        """
        with self._lock:
            if plugin_name not in self._plugins:
                return False

            info = self._plugins[plugin_name]

            if not info.loaded or info.instance is None:
                return False

            # Call on_unload
            try:
                info.instance.on_unload()
            except Exception as e:
                logger.error(f"Plugin '{plugin_name}' on_unload failed: {e}")

            # Remove from hook registry
            self._unregister_hooks(plugin_name)

            # Remove module from sys.modules
            if info.module_name and info.module_name in sys.modules:
                del sys.modules[info.module_name]

            info.loaded = False
            info.instance = None
            logger.info(f"Unloaded plugin '{plugin_name}'")
            return True

    def unload_all(self) -> None:
        """Unload all loaded plugins in reverse dependency order."""
        with self._lock:
            for name in reversed(list(self._plugins.keys())):
                self.unload(name)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Load per-plugin configuration from JSON/YAML file."""
        config_path = self._config_dir / f"{plugin_name}.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load config for '{plugin_name}': {e}")
            return {}

    def set_plugin_config(
        self, plugin_name: str, config: Dict[str, Any]
    ) -> None:
        """Save per-plugin configuration to disk."""
        config_path = self._config_dir / f"{plugin_name}.json"
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Update in-memory if loaded
        with self._lock:
            if plugin_name in self._plugins:
                self._plugins[plugin_name].config = config
                if self._plugins[plugin_name].instance:
                    self._plugins[plugin_name].instance.config = config

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get current plugin configuration."""
        with self._lock:
            if plugin_name in self._plugins:
                return dict(self._plugins[plugin_name].config)
        return self._load_plugin_config(plugin_name)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def _register_hooks(self, plugin_name: str, instance: HermesPlugin) -> None:
        """Register a plugin's hook methods in the hook registry."""
        hook_methods = ["on_tool_call", "on_tool_result", "on_shutdown"]
        for hook_name in hook_methods:
            method = getattr(instance, hook_name, None)
            if method is not None and callable(method) and method.__func__ is not getattr(HermesPlugin, hook_name):
                if hook_name not in self._hook_registry:
                    self._hook_registry[hook_name] = {}
                self._hook_registry[hook_name][plugin_name] = method

    def _unregister_hooks(self, plugin_name: str) -> None:
        """Remove a plugin's hooks from the registry."""
        for hook_name in list(self._hook_registry.keys()):
            self._hook_registry[hook_name].pop(plugin_name, None)
            if not self._hook_registry[hook_name]:
                del self._hook_registry[hook_name]

    def call_hook(
        self,
        hook_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Call a hook on all loaded plugins that implement it.

        For 'on_tool_call' hook: if any plugin returns a non-None value,
        that value short-circuits and is returned. The first non-None
        return value wins.

        Returns:
            List of {plugin_name, result} dicts, or a single short-circuit value.
        """
        results = []
        with self._lock:
            hooks = dict(self._hook_registry.get(hook_name, {}))

        for plugin_name, hook_fn in hooks.items():
            try:
                result = hook_fn(*args, **kwargs)
                if hook_name == "on_tool_call" and result is not None:
                    # Short-circuit: plugin wants to intercept
                    return [{"plugin": plugin_name, "intercepted": True, "result": result}]
                results.append({"plugin": plugin_name, "result": result})
            except Exception as e:
                logger.error(f"Hook '{hook_name}' in plugin '{plugin_name}' failed: {e}")
                results.append({"plugin": plugin_name, "error": str(e)})

        return results

    # ------------------------------------------------------------------
    # Hot Reload
    # ------------------------------------------------------------------

    def start_hot_reload(self, poll_interval: float = 2.0) -> None:
        """Start a background thread that watches for plugin file changes.

        When a plugin.py file changes, the plugin is automatically reloaded.

        Args:
            poll_interval: Seconds between filesystem checks.
        """
        if self._watcher_thread and self._watcher_thread.is_alive():
            logger.warning("Hot-reload watcher already running")
            return

        self._watcher_stop.clear()
        self._watcher_thread = threading.Thread(
            target=self._watch_loop,
            args=(poll_interval,),
            daemon=True,
            name="plugin-hot-reload",
        )
        self._watcher_thread.start()
        logger.info(f"Hot-reload watcher started (poll={poll_interval}s)")

    def stop_hot_reload(self) -> None:
        """Stop the hot-reload watcher thread."""
        if self._watcher_thread is None:
            return
        self._watcher_stop.set()
        self._watcher_thread.join(timeout=5.0)
        self._watcher_thread = None
        logger.info("Hot-reload watcher stopped")

    def _watch_loop(self, poll_interval: float) -> None:
        """Background loop that checks plugin files for changes."""
        while not self._watcher_stop.is_set():
            try:
                self._check_and_reload()
            except Exception as e:
                logger.error(f"Hot-reload check error: {e}")
            self._watcher_stop.wait(poll_interval)

    def _check_and_reload(self) -> None:
        """Check all tracked plugin files and reload changed ones."""
        for plugin_name, info in list(self._plugins.items()):
            plugin_file = info.path / "plugin.py"
            if not plugin_file.exists():
                continue

            current_mtime = plugin_file.stat().st_mtime
            last_mtime = self._file_mtimes.get(plugin_file, 0)

            if current_mtime > last_mtime:
                logger.info(
                    f"Detected change in plugin '{plugin_name}', reloading..."
                )
                self._file_mtimes[plugin_file] = current_mtime
                try:
                    self.unload(plugin_name)
                    self.load(plugin_name)
                    logger.info(f"Plugin '{plugin_name}' reloaded successfully")
                except PluginError as e:
                    logger.error(f"Hot-reload of '{plugin_name}' failed: {e}")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all known plugins and their status."""
        result = []
        with self._lock:
            for info in self._plugins.values():
                result.append(
                    {
                        "name": info.name,
                        "version": info.version,
                        "description": info.description,
                        "loaded": info.loaded,
                        "enabled": info.enabled,
                        "load_time": info.load_time,
                        "depends_on": info.depends_on,
                    }
                )
        return result

    def get_plugin(self, name: str) -> Optional[HermesPlugin]:
        """Get a loaded plugin instance by name."""
        with self._lock:
            info = self._plugins.get(name)
            if info and info.loaded:
                return info.instance
        return None

    def is_loaded(self, name: str) -> bool:
        """Check if a plugin is loaded."""
        with self._lock:
            info = self._plugins.get(name)
            return info is not None and info.loaded

    def enable_plugin(self, name: str) -> None:
        """Enable a plugin (does not load it)."""
        with self._lock:
            if name in self._plugins:
                self._plugins[name].enabled = True

    def disable_plugin(self, name: str) -> None:
        """Disable a plugin (unloads if loaded)."""
        self.unload(name)
        with self._lock:
            if name in self._plugins:
                self._plugins[name].enabled = False

    def shutdown(self) -> None:
        """Shutdown hook: unload all plugins and stop watcher."""
        self.stop_hot_reload()

        with self._lock:
            for info in self._plugins.values():
                if info.loaded and info.instance:
                    try:
                        info.instance.on_shutdown()
                    except Exception as e:
                        logger.error(f"Shutdown hook failed for '{info.name}': {e}")

        self.unload_all()
        logger.info("Plugin manager shut down")


# ============================================================================
# Standalone test
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    pm = PluginManager()
    print("Plugin directories:", pm._plugin_dirs)

    # Discover plugins
    discovered = pm.discover()
    print(f"Discovered {len(discovered)} plugin(s):")
    for d in discovered:
        print(f"  - {d.name} v{d.version}: {d.description} ({d.path})")

    # Try loading all
    loaded = pm.load_all()
    print(f"\nLoaded plugins: {loaded}")

    # List
    print("\nPlugin status:")
    for p in pm.list_plugins():
        print(f"  [{('LOADED' if p['loaded'] else 'not loaded')}] {p['name']} v{p['version']}")

    # Shutdown
    pm.shutdown()
