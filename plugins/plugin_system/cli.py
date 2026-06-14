"""
Hermes Plugin System - CLI Interface
Provides commands: /plugins, /plugin_install, /plugin_enable, /plugin_disable, /plugin_start, /plugin_stop
"""

import json
import logging
import shutil
import tarfile
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginCLI:
    """CLI command handler for plugin management."""

    def __init__(self, manager):
        self.manager = manager
        self.plugins_dir = Path("~/.hermes/plugins").expanduser()

    async def cmd_plugins(self, args: list[str] = None) -> str:
        """List all plugins."""
        plugins = self.manager.list_plugins()

        if not plugins:
            return "No plugins discovered."

        lines = ["PLUGINS:", "=" * 60]
        for p in plugins:
            status_icon = "✓" if p["enabled"] else "✗"
            loaded_icon = "●" if p["loaded"] else "○"
            lines.append(f"{status_icon} {loaded_icon} {p['name']:25} v{p['version']:8} {p['state']:10} {p['description']}")
            if p["capabilities"]:
                lines.append(f"    Capabilities: {', '.join(p['capabilities'])}")
            if p["hooks"]:
                lines.append(f"    Hooks: {', '.join(p['hooks'])}")
            lines.append("")

        return "\n".join(lines)

    async def cmd_plugin_install(self, args: list[str]) -> str:
        """Install a plugin from a path or URL."""
        if not args:
            return "Usage: /plugin_install <plugin_path_or_url>\n\nExamples:\n  /plugin_install /path/to/plugin\n  /plugin_install https://example.com/plugin.tar.gz"

        source = args[0]

        # Determine source type
        if source.startswith("http://") or source.startswith("https://"):
            # Download from URL
            return await self._install_from_url(source)
        # Copy from local path
        return await self._install_from_path(source)

    async def _install_from_url(self, url: str) -> str:
        """Install plugin from URL (tar.gz)."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session, session.get(url) as resp:
                if resp.status != 200:
                    return f"Download failed: HTTP {resp.status}"

                # Download to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
                    tmp.write(await resp.read())
                    tmp_path = tmp.name

            # Extract
            return await self._extract_plugin(tmp_path)

        except ImportError:
            return "Error: aiohttp required for URL installation. pip install aiohttp"
        except Exception as e:
            return f"Installation failed: {e}"

    async def _install_from_path(self, path: str) -> str:
        """Install plugin from local directory or archive."""
        src = Path(path).expanduser()

        if not src.exists():
            return f"Path does not exist: {path}"

        if src.is_dir():
            # Copy directory
            return await self._copy_plugin_dir(src)
        if src.suffix in [".tar.gz", ".tgz", ".zip"]:
            # Extract archive
            return await self._extract_plugin(src)
        return "Unsupported file type. Provide a directory or .tar.gz archive."

    async def _copy_plugin_dir(self, src_dir: Path) -> str:
        """Copy plugin directory."""
        try:
            # Validate plugin structure
            plugin_json = src_dir / "plugin.json"
            if not plugin_json.exists():
                return "Invalid plugin: missing plugin.json"

            with open(plugin_json) as f:
                manifest = json.load(f)
                plugin_name = manifest["name"]

            # Destination
            dest_dir = self.plugins_dir / plugin_name

            if dest_dir.exists():
                return f"Plugin {plugin_name} already exists. Remove first or use /plugin_update."

            # Copy
            shutil.copytree(src_dir, dest_dir)

            # Discover
            self.manager.registry.discover_plugins()

            return f"✓ Installed plugin {plugin_name} to {dest_dir}"
        except Exception as e:
            return f"Copy failed: {e}"

    async def _extract_plugin(self, archive_path: Path) -> str:
        """Extract plugin from archive."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(tmpdir)

                    # Find plugin directory (should be top-level)
                    tmpdir_path = Path(tmpdir)
                    items = list(tmpdir_path.iterdir())

                    # If single directory, use it
                    if len(items) == 1 and items[0].is_dir():
                        plugin_dir = items[0]
                    else:
                        # Use tmpdir as plugin dir
                        plugin_dir = tmpdir_path

                    return await self._copy_plugin_dir(plugin_dir)

        except Exception as e:
            return f"Extraction failed: {e}"

    async def cmd_plugin_enable(self, args: list[str]) -> str:
        """Enable a plugin."""
        if not args:
            return "Usage: /plugin_enable <plugin_name>"

        plugin_name = args[0]

        if plugin_name not in self.manager.registry.manifests:
            return f"Plugin {plugin_name} not found. Available: {', '.join(self.manager.registry.manifests.keys())}"

        success = await self.manager.enable_plugin(plugin_name)

        if success:
            return f"✓ Plugin {plugin_name} enabled"
        return f"✗ Failed to enable {plugin_name}"

    async def cmd_plugin_disable(self, args: list[str]) -> str:
        """Disable a plugin."""
        if not args:
            return "Usage: /plugin_disable <plugin_name>"

        plugin_name = args[0]

        success = await self.manager.disable_plugin(plugin_name)

        if success:
            return f"✓ Plugin {plugin_name} disabled"
        return f"✗ Failed to disable {plugin_name}"

    async def cmd_plugin_start(self, args: list[str]) -> str:
        """Start a plugin (if stopped)."""
        if not args:
            return "Usage: /plugin_start <plugin_name>"

        plugin_name = args[0]

        if plugin_name in self.manager.loaded_plugins:
            return f"Plugin {plugin_name} already running"

        if plugin_name not in self.manager.enabled_plugins:
            return f"Plugin {plugin_name} is disabled. Enable it first."

        try:
            plugin = await self.manager.load_and_start(plugin_name)
            if plugin:
                return f"✓ Plugin {plugin_name} started"
            return f"✗ Failed to start {plugin_name}"
        except Exception as e:
            return f"✗ Error: {e}"

    async def cmd_plugin_stop(self, args: list[str]) -> str:
        """Stop a running plugin."""
        if not args:
            return "Usage: /plugin_stop <plugin_name>"

        plugin_name = args[0]

        if plugin_name not in self.manager.loaded_plugins:
            return f"Plugin {plugin_name} not running"

        try:
            plugin = self.manager.loaded_plugins[plugin_name]
            await plugin.stop()
            del self.manager.loaded_plugins[plugin_name]
            return f"✓ Plugin {plugin_name} stopped"
        except Exception as e:
            return f"✗ Error: {e}"

    async def cmd_plugin_reload(self, args: list[str]) -> str:
        """Reload plugin configuration."""
        if not args:
            return "Usage: /plugin_reload <plugin_name>"

        plugin_name = args[0]

        success = await self.manager.reload_plugin_config(plugin_name)

        if success:
            return f"✓ Configuration for {plugin_name} reloaded"
        return f"✗ Failed to reload config for {plugin_name}"

    async def cmd_plugin_info(self, args: list[str]) -> str:
        """Show detailed plugin information."""
        if not args:
            return "Usage: /plugin_info <plugin_name>"

        plugin_name = args[0]

        if plugin_name not in self.manager.registry.manifests:
            return f"Plugin {plugin_name} not found"

        manifest = self.manager.registry.manifests[plugin_name]
        config = self.manager.registry.configs.get(plugin_name)
        plugin = self.manager.loaded_plugins.get(plugin_name)

        lines = [
            f"PLUGIN: {manifest.name}",
            "=" * 60,
            f"Version: {manifest.version}",
            f"Description: {manifest.description}",
            f"Author: {manifest.author}",
            f"Entry Point: {manifest.entry_point}",
            f"Dependencies: {', '.join(manifest.dependencies) if manifest.dependencies else 'none'}",
            f"Capabilities: {', '.join(manifest.capabilities)}",
            f"Hooks: {', '.join(manifest.hooks)}",
            "",
            "Status:",
            f"  Enabled: {config.enabled if config else 'unknown'}",
            f"  Loaded: {plugin is not None}",
            f"  State: {plugin.state.value if plugin else 'unloaded'}",
            "",
            "Configuration:"
        ]

        if config:
            for k, v in config.config.items():
                lines.append(f"  {k}: {v}")

        if plugin:
            health = await plugin.health_check()
            lines.append("")
            lines.append("Health:")
            for k, v in health.items():
                lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    async def cmd_plugin_uninstall(self, args: list[str]) -> str:
        """Uninstall a plugin."""
        if not args:
            return "Usage: /plugin_uninstall <plugin_name>"

        plugin_name = args[0]

        if plugin_name not in self.manager.registry.manifests:
            return f"Plugin {plugin_name} not found"

        # Stop if running
        if plugin_name in self.manager.loaded_plugins:
            await self.cmd_plugin_stop([plugin_name])

        # Disable if enabled
        if plugin_name in self.manager.enabled_plugins:
            await self.cmd_plugin_disable([plugin_name])

        # Remove directory
        plugin_dir = self.plugins_dir / plugin_name
        try:
            shutil.rmtree(plugin_dir)
            self.manager.registry.discover_plugins()
            return f"✓ Plugin {plugin_name} uninstalled"
        except Exception as e:
            return f"✗ Failed to remove: {e}"

    async def cmd_plugin_update(self, args: list[str]) -> str:
        """Update a plugin from source (reinstall)."""
        if not args:
            return "Usage: /plugin_update <plugin_path_or_url>"

        source = args[0]
        plugin_name = None

        # Get name from source
        if source.startswith("http"):
            # Extract name from URL/archive
            return "URL updates not yet implemented. Use /plugin_uninstall then /plugin_install."
        src = Path(source)
        if src.exists():
            plugin_json = src / "plugin.json"
            if plugin_json.exists():
                with open(plugin_json) as f:
                    manifest = json.load(f)
                    plugin_name = manifest["name"]

        if not plugin_name:
            return "Could not determine plugin name"

        # Uninstall then install
        if plugin_name in self.manager.registry.manifests:
            await self.cmd_plugin_uninstall([plugin_name])

        return await self._install_from_path(Path(source)) if not source.startswith("http") else await self._install_from_url(source)

    async def cmd_plugin_config(self, args: list[str]) -> str:
        """Show or modify plugin configuration."""
        if not args:
            return "Usage: /plugin_config <plugin_name> [key] [value]"

        plugin_name = args[0]

        if plugin_name not in self.manager.registry.configs:
            return f"Plugin {plugin_name} not found or has no config"

        config = self.manager.registry.configs[plugin_name]

        if len(args) == 1:
            # Show full config
            lines = [f"Configuration for {plugin_name}:", "=" * 40]
            for k, v in config.config.items():
                lines.append(f"  {k}: {v}")
            lines.append("")
            lines.append("To modify: /plugin_config <plugin> <key> <value>")
            return "\n".join(lines)

        if len(args) == 2:
            key = args[1]
            value = config.config.get(key, "KEY_NOT_FOUND")
            return f"{key}: {value}"

        # Set value
        key = args[1]
        value = args[2]
        # Try to parse as JSON, fallback to string
        try:
            value = json.loads(value)
        except:
            pass

        config.config[key] = value

        # Save to file
        config_file = self.plugins_dir / plugin_name / "config.yaml"
        try:
            import yaml
            # Load existing
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            # Update
            data[key] = value
            # Write back
            with open(config_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False)

            # Emit reload hook
            await self.manager.reload_plugin_config(plugin_name)

            return f"✓ Set {key} = {value} for {plugin_name}"
        except ImportError:
            return "Error: PyYAML required for config modification. pip install pyyaml"
        except Exception as e:
            return f"Error: {e}"

    async def cmd_plugin_logs(self, args: list[str]) -> str:
        """Show plugin logs (if available)."""
        if not args:
            return "Usage: /plugin_logs <plugin_name> [tail]"

        plugin_name = args[0]
        tail = 50
        if len(args) > 1:
            try:
                tail = int(args[1])
            except:
                pass

        log_file = Path(f"~/.hermes/logs/{plugin_name}.log").expanduser()

        if not log_file.exists():
            return f"No log file found at {log_file}"

        try:
            with open(log_file) as f:
                lines = f.readlines()
                recent = lines[-tail:] if len(lines) > tail else lines
                return "".join(recent)
        except Exception as e:
            return f"Error reading log: {e}"


# ============ Command Registration ============

def register_commands(manager) -> dict[str, callable]:
    """Register CLI commands with Hermes."""
    cli = PluginCLI(manager)

    return {
        "plugins": cli.cmd_plugins,
        "plugin_install": cli.cmd_plugin_install,
        "plugin_uninstall": cli.cmd_plugin_uninstall,
        "plugin_enable": cli.cmd_plugin_enable,
        "plugin_disable": cli.cmd_plugin_disable,
        "plugin_start": cli.cmd_plugin_start,
        "plugin_stop": cli.cmd_plugin_stop,
        "plugin_reload": cli.cmd_plugin_reload,
        "plugin_info": cli.cmd_plugin_info,
        "plugin_update": cli.cmd_plugin_update,
        "plugin_config": cli.cmd_plugin_config,
        "plugin_logs": cli.cmd_plugin_logs
    }
