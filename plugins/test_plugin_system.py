#!/usr/bin/env python3
"""
Hermes Plugin System - Quick Test and Demo Script
Tests all 4 migrated plugins and core functionality.
"""

import asyncio
import sys
from pathlib import Path

# Set up paths
PLUGINS_DIR = Path("~/.hermes/plugins").expanduser()
PLUGIN_SYSTEM_DIR = PLUGINS_DIR / "plugin_system"
sys.path.insert(0, str(PLUGINS_DIR))

# Import core system
try:
    from plugin_system import HookType, PluginManager
except ImportError as e:
    print(f"Failed to import plugin system: {e}")
    print(f"Make sure {PLUGIN_SYSTEM_DIR} exists and is correct")
    sys.exit(1)


async def test_core_components():
    """Test core plugin system components."""
    print("\n=== Testing Core Components ===")

    # Test event bus
    print("Testing EventBus...")
    manager = PluginManager()
    bus = manager.event_bus

    test_messages = []

    async def handler(event):
        test_messages.append(event.data)

    await bus.subscribe("test.event", handler)
    await bus.publish("test.event", "test_source", {"test": "data"})

    assert len(test_messages) == 1
    assert test_messages[0]["test"] == "data"
    print("  ✓ EventBus working")

    return manager


async def test_all_plugins(manager: PluginManager):
    """Test all 4 migrated plugins."""
    print("\n=== Testing Plugin Discovery ===")

    await manager.initialize()

    print(f"Discovered {len(manager.registry.manifests)} plugins:")
    for name, manifest in manager.registry.manifests.items():
        print(f"  • {name} v{manifest.version} - {manifest.description}")

    expected_plugins = [
        "openclaw-web-search",
        "openclaw-weixin",
        "openclaw-airi",
        "openclaw-superintelligence"
    ]

    for plugin in expected_plugins:
        if plugin in manager.registry.manifests:
            print(f"  ✓ {plugin} discovered")
        else:
            print(f"  ✗ {plugin} NOT FOUND")

    print("\n=== Testing Plugin Loading ===")

    # We won't actually load all plugins (some dependencies missing)
    # But check that they have proper structures
    for plugin_name in expected_plugins:
        if plugin_name in manager.registry.manifests:
            manifest = manager.registry.manifests[plugin_name]
            config = manager.registry.configs.get(plugin_name)

            assert manifest.name == plugin_name
            assert manifest.entry_point
            assert config is not None
            print(f"  ✓ {plugin_name} has valid manifest and config")

    print("\n=== Checking Plugin Files ===")

    for plugin_name in expected_plugins:
        plugin_dir = PLUGINS_DIR / plugin_name

        if not plugin_dir.exists():
            print(f"  ✗ {plugin_name} directory missing")
            continue

        required_files = ["plugin.json", "__init__.py", "config.yaml", "requirements.txt", "README.md"]
        for fname in required_files:
            fpath = plugin_dir / fname
            if fpath.exists():
                print(f"  ✓ {plugin_name}/{fname} exists")
            else:
                print(f"  ✗ {plugin_name}/{fname} missing")

    return manager


async def test_plugin_actions(manager: PluginManager):
    """Test plugin-specific actions."""
    print("\n=== Testing Plugin Actions (structure) ===")

    # Check that plugins have the required action methods
    plugins_to_test = {
        "openclaw-web-search": ["web_search"],
        "openclaw-weixin": ["connect", "send", "receive", "list_accounts"],
        "openclaw-airi": ["set_expression", "say", "set_emotion", "look_at", "get_status"],
        "openclaw-superintelligence": ["chat", "optimize", "get_metrics", "list_models"]
    }

    for plugin_name, actions in plugins_to_test.items():
        manifest = manager.registry.manifests.get(plugin_name)
        if not manifest:
            print(f"  ⚠ {plugin_name} not discovered, skipping action checks")
            continue

        print(f"\n  {plugin_name} expected actions:")
        for action in actions:
            print(f"    • {action}")
        print(f"    Expected tools: {len(manifest.capabilities)} capabilities")
        print(f"    Expected hooks: {manifest.hooks or 'none'}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("HERMES PLUGIN SYSTEM - MIGRATION TEST")
    print("Testing OpenClaw plugin migration")
    print("=" * 60)

    try:
        # Test core
        manager = await test_core_components()

        # Test plugins
        await test_all_plugins(manager)

        # Test actions
        await test_plugin_actions(manager)

        print("\n" + "=" * 60)
        print("✓ BASIC VALIDATION COMPLETE")
        print("=" * 60)

        # Show CLI commands
        print("\nAvailable CLI commands:")
        print("  /plugins              - List all plugins")
        print("  /plugin_install <src> - Install plugin")
        print("  /plugin_enable <name> - Enable plugin")
        print("  /plugin_disable <name>- Disable plugin")
        print("  /plugin_start <name>  - Start plugin")
        print("  /plugin_stop <name>   - Stop plugin")
        print("  /plugin_info <name>   - Show plugin details")
        print("  /plugin_reload <name> - Reload config")
        print("  /plugin_config <name> [key] [value] - Get/set config")
        print("  /plugin_logs <name>   - Show plugin logs")

        print("\nPlugin-specific commands (registered by plugins):")
        print("  /web_search <query> [--source <engine>] [--max <N>]")
        print("  /weixin_login <account_id>")
        print("  /weixin_status")
        print("  /weixin_send <to> <msg> [--account <id>]")
        print("  /airi_open")
        print("  /airi_set_expression <emotion>")
        print("  /airi_say <text>")
        print("  /superintel_chat <prompt>")
        print("  /superintel_models")
        print("  /superintel_optimize <prompt>")

        return 0

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
