"""
Hermes Plugin System - Plugin Registry
Handles plugin discovery, registration, and lifecycle management.
"""

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .plugin_base import Plugin, PluginConfig, PluginManifest

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all plugins.
    Handles discovery, loading, and tracking of plugins.
    """

    def __init__(self, plugins_dir: str = "~/.hermes/plugins"):
        self.plugins_dir = Path(plugins_dir).expanduser()
        self.plugins: dict[str, Plugin] = {}
        self.manifests: dict[str, PluginManifest] = {}
        self.configs: dict[str, PluginConfig] = {}
        self._loaded_plugins: set[str] = set()

    def discover_plugins(self) -> list[str]:
        """
        Discover all plugins in the plugins directory.
        Returns list of plugin names found.
        """
        discovered = []

        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory {self.plugins_dir} does not exist")
            return []

        for plugin_path in self.plugins_dir.iterdir():
            if plugin_path.is_dir() and not plugin_path.name.startswith("_"):
                manifest_file = plugin_path / "plugin.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file) as f:
                            manifest_data = json.load(f)

                        manifest = PluginManifest(
                            name=manifest_data.get("name", plugin_path.name),
                            version=manifest_data.get("version", "0.1.0"),
                            description=manifest_data.get("description", ""),
                            author=manifest_data.get("author", "Unknown"),
                            entry_point=manifest_data.get("entry_point", "__init__.py"),
                            dependencies=manifest_data.get("dependencies", []),
                            capabilities=manifest_data.get("capabilities", []),
                            hooks=manifest_data.get("hooks", []),
                            config_schema=manifest_data.get("config_schema", {})
                        )

                        self.manifests[manifest.name] = manifest

                        # Load config if exists
                        config_file = plugin_path / "config.yaml"
                        if config_file.exists():
                            # Simple YAML-like parser (could use PyYAML if available)
                            config = self._load_config(config_file, manifest)
                            self.configs[manifest.name] = config
                        else:
                            self.configs[manifest.name] = PluginConfig(
                                name=manifest.name,
                                version=manifest.version,
                                description=manifest.description,
                                author=manifest.author
                            )

                        discovered.append(manifest.name)
                        logger.debug(f"Discovered plugin: {manifest.name}")

                    except Exception as e:
                        logger.error(f"Failed to parse plugin {plugin_path.name}: {e}")

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def _load_config(self, config_file: Path, manifest: PluginManifest) -> PluginConfig:
        """Load plugin configuration from file."""
        # Simple parsing - in production use PyYAML
        config = PluginConfig(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author
        )

        try:
            import yaml
            with open(config_file) as f:
                data = yaml.safe_load(f)
                if data:
                    config.enabled = data.get("enabled", True)
                    config.auto_start = data.get("auto_start", False)
                    config.dependencies = data.get("dependencies", [])
                    config.config = {k: v for k, v in data.items()
                                   if k not in ["enabled", "auto_start", "dependencies"]}
        except ImportError:
            logger.warning("PyYAML not installed, using default config")
        except Exception as e:
            logger.error(f"Failed to load config for {manifest.name}: {e}")

        return config

    async def load_plugin(self, plugin_name: str, manager: "PluginManager") -> Plugin | None:
        """
        Load a plugin by name.
        Args:
            plugin_name: Name of plugin to load
            manager: Plugin manager instance to inject into plugin
        Returns:
            Loaded Plugin instance or None on failure
        """
        if plugin_name not in self.manifests:
            logger.error(f"Plugin {plugin_name} not found in registry")
            return None

        if plugin_name in self._loaded_plugins:
            logger.warning(f"Plugin {plugin_name} already loaded")
            return self.plugins.get(plugin_name)

        manifest = self.manifests[plugin_name]
        config = self.configs.get(plugin_name, PluginConfig(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author
        ))

        try:
            # Import plugin module
            plugin_dir = self.plugins_dir / plugin_name
            entry_file = plugin_dir / manifest.entry_point

            if not entry_file.exists():
                logger.error(f"Plugin entry point {entry_file} does not exist")
                return None

            # Add plugin directory to sys.path
            sys.path.insert(0, str(plugin_dir))

            # Import module
            spec = importlib.util.spec_from_file_location(plugin_name, entry_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create spec for plugin {plugin_name}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find Plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    attr.__module__ == plugin_name and
                    hasattr(attr, "__init__") and
                    attr.__name__ != "Plugin"):
                    # Check if it's a Plugin subclass
                    try:
                        if issubclass(attr, Plugin) and attr != Plugin:
                            plugin_class = attr
                            break
                    except TypeError:
                        pass

            if plugin_class is None:
                logger.error(f"No Plugin class found in {plugin_name}")
                return None

            # Instantiate plugin
            plugin = plugin_class(manifest, config)
            plugin.manager = manager
            plugin.event_bus = manager.event_bus

            # Initialize
            await plugin.init()

            self.plugins[plugin_name] = plugin
            self._loaded_plugins.add(plugin_name)

            logger.info(f"Plugin {plugin_name} loaded successfully")
            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}", exc_info=True)
            return None
        finally:
            # Clean up sys.path
            if str(plugin_dir) in sys.path:
                sys.path.remove(str(plugin_dir))

    async def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.
        Args:
            plugin_name: Name of plugin to unload
        Returns:
            True if unloaded successfully
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} not loaded")
            return False

        try:
            plugin = self.plugins[plugin_name]
            await plugin.stop()

            del self.plugins[plugin_name]
            self._loaded_plugins.discard(plugin_name)

            logger.info(f"Plugin {plugin_name} unloaded")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Plugin | None:
        """Get loaded plugin by name."""
        return self.plugins.get(plugin_name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all plugins with their status."""
        result = []
        for name in self.manifests:
            manifest = self.manifests[name]
            config = self.configs.get(name)
            plugin = self.plugins.get(name)

            result.append({
                "name": name,
                "version": manifest.version,
                "description": manifest.description,
                "author": manifest.author,
                "enabled": config.enabled if config else True,
                "loaded": name in self._loaded_plugins,
                "state": plugin.state.value if plugin else "unloaded",
                "capabilities": manifest.capabilities,
                "hooks": manifest.hooks
            })

        return result
