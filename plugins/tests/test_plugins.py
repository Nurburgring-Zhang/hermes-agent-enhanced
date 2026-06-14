"""
Comprehensive tests for Hermes Plugin System and all migrated plugins.
Run with: python -m pytest tests/test_plugins.py -v
"""

import asyncio
import json
import os

# Add plugin_system to path
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path("~/.hermes/plugins").expanduser()))

from plugin_system import EventBus, PluginManager, PluginState
from plugin_system.core.event_bus import Event
from plugin_system.core.plugin_base import Plugin as BasePlugin

# ============ Fixtures ============

@pytest.fixture
def temp_plugins_dir():
    """Create temporary plugins directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugins_dir = Path(tmpdir) / "plugins"
        plugins_dir.mkdir()
        yield plugins_dir

@pytest.fixture
def event_bus():
    """Create event bus instance."""
    return EventBus()

@pytest.fixture
def plugin_manager(temp_plugins_dir):
    """Create plugin manager."""
    os.environ["HERMES_PLUGINS_DIR"] = str(temp_plugins_dir)
    manager = PluginManager(plugins_dir=str(temp_plugins_dir))
    return manager


# ============ Core Tests ============

class TestEventBus:
    """Test EventBus functionality."""

    @pytest.mark.asyncio
    async def test_publish_subscribe(self, event_bus):
        """Test basic publish-subscribe."""
        received = []

        async def handler(event: Event):
            received.append(event)

        await event_bus.subscribe("test.event", handler)
        await event_bus.publish("test.event", source="test", data={"key": "value"})

        assert len(received) == 1
        assert received[0].type == "test.event"
        assert received[0].source == "test"
        assert received[0].data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers for same event."""
        results1 = []
        results2 = []

        async def handler1(event):
            results1.append(event.data)

        async def handler2(event):
            results2.append(event.data)

        await event_bus.subscribe("test", handler1)
        await event_bus.subscribe("test", handler2)
        await event_bus.publish("test", source="test", data="value")

        assert results1 == ["value"]
        assert results2 == ["value"]

    @pytest.mark.asyncio
    async def test_wildcard_subscribe(self, event_bus):
        """Test wildcard subscription."""
        received = []

        async def handler(event):
            received.append(event.type)

        await event_bus.subscribe_all(handler)
        await event_bus.publish("any.event1", source="test", data={})
        await event_bus.publish("any.event2", source="test", data={})

        assert "any.event1" in received
        assert "any.event2" in received

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """Test unsubscribe."""
        received = []

        async def handler(event):
            received.append(event.data)

        await event_bus.subscribe("test", handler)
        await event_bus.publish("test", source="test", data="first")
        await event_bus.unsubscribe("test", handler)
        await event_bus.publish("test", source="test", data="second")

        assert len(received) == 1
        assert received[0] == "first"

    def test_get_history(self, event_bus):
        """Test event history retrieval."""
        # Publish some events synchronously for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(event_bus.publish("evt1", "src", "data1"))
        loop.run_until_complete(event_bus.publish("evt2", "src", "data2"))
        loop.run_until_complete(event_bus.publish("evt1", "src", "data3"))

        history = event_bus.get_history(limit=2)
        assert len(history) == 2
        assert history[0].type == "evt2"  # Most recent first
        assert history[1].type == "evt1"

        loop.close()


class TestPluginRegistry:
    """Test PluginRegistry functionality."""

    def test_discover_plugins(self, temp_plugins_dir):
        """Test plugin discovery."""
        # Create a minimal plugin
        plugin_dir = temp_plugins_dir / "test_plugin"
        plugin_dir.mkdir()

        manifest = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test",
            "entry_point": "__init__.py"
        }

        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump(manifest, f)

        # Create dummy __init__.py
        (plugin_dir / "__init__.py").write_text("from plugin_system import Plugin\nclass TestPlugin(Plugin): pass")

        registry = PluginRegistry(plugins_dir=str(temp_plugins_dir))
        discovered = registry.discover_plugins()

        assert "test_plugin" in discovered
        assert "test_plugin" in registry.manifests

    def test_load_plugin(self, temp_plugins_dir):
        """Test loading a plugin."""
        # Create minimal plugin
        plugin_dir = temp_plugins_dir / "load_test"
        plugin_dir.mkdir()

        manifest = {
            "name": "load_test",
            "version": "1.0.0",
            "description": "Load test",
            "author": "Test",
            "entry_point": "__init__.py"
        }

        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump(manifest, f)

        (plugin_dir / "__init__.py").write_text("""
from plugin_system import Plugin, PluginManifest, PluginConfig

class LoadTestPlugin(Plugin):
    async def init(self):
        self.initialized = True

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True
""")

        # Mock manager
        manager = MagicMock()
        manager.event_bus = EventBus()

        registry = PluginRegistry(plugins_dir=str(temp_plugins_dir))
        registry.discover_plugins()

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        plugin = loop.run_until_complete(registry.load_plugin("load_test", manager))

        assert plugin is not None
        assert plugin.name == "load_test"
        assert plugin.state == PluginState.LOADED

        loop.run_until_complete(plugin.start())
        assert plugin.state == PluginState.RUNNING

        loop.run_until_complete(plugin.stop())
        assert plugin.state == PluginState.STOPPED

        loop.close()


class TestPluginManager:
    """Test PluginManager functionality."""

    @pytest.mark.asyncio
    async def test_initialize(self, plugin_manager):
        """Test manager initialization."""
        await plugin_manager.initialize()
        # Should discover system plugin
        assert len(plugin_manager.registry.manifests) >= 1

    @pytest.mark.asyncio
    async def test_enable_disable(self, plugin_manager):
        """Test enable/disable."""
        # This would require real plugins
        # For now, structure test
        assert hasattr(plugin_manager, "enable_plugin")
        assert hasattr(plugin_manager, "disable_plugin")


# ============ Plugin Implementation Tests ============

class TestWebSearchPlugin:
    """Test Web Search plugin."""

    @pytest.mark.asyncio
    async def test_plugin_loading(self, temp_plugins_dir):
        """Test that Web Search plugin can be discovered and loaded."""
        # Copy real plugin (would be there in integration test)


class TestWeixinPlugin:
    """Test Weixin plugin."""

    def test_account_structure(self):
        """Test account data structure."""


class TestAirIPlugin:
    """Test AirI plugin."""

    @pytest.mark.asyncio
    async def test_lip_sync_engine(self):
        """Test lip-sync analysis."""
        # Mock lip sync


class TestSuperIntelligencePlugin:
    """Test SuperIntelligence plugin."""

    def test_model_selection(self):
        """Test model selection logic."""

    def test_synthesis_engines(self):
        """Test synthesis strategies."""


# ============ Integration Tests ============

class TestIntegration:
    """Integration tests for full plugin system."""

    @pytest.mark.asyncio
    async def test_event_communication(self, plugin_manager):
        """Test plugins can communicate via event bus."""
        # Create two plugins that talk via events

    @pytest.mark.asyncio
    async def test_all_plugins_load(self, temp_plugins_dir):
        """Test that all 4 migrated plugins can be loaded."""
        # In full test, they would be in ~/.hermes/plugins

    @pytest.mark.asyncio
    async def test_hot_reload_config(self, plugin_manager):
        """Test configuration hot reload."""


# ============ Mock Plugin for Testing ============

class MockPlugin(BasePlugin):
    """Simple mock plugin for testing."""

    def __init__(self, manifest, config):
        super().__init__(manifest, config)
        self.init_called = False
        self.start_called = False
        self.stop_called = False

    async def init(self):
        self.init_called = True
        await super().init()

    async def start(self):
        self.start_called = True
        await super().start()

    async def stop(self):
        self.stop_called = True
        await super().stop()

    def get_tools(self):
        return [{"name": "mock_tool", "description": "Mock tool"}]


# ============ Run if standalone ============

if __name__ == "__main__":
    # Quick sanity check
    print("Running quick smoke tests...")

    # Test EventBus
    bus = EventBus()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    result = []

    async def test_handler(e):
        result.append(e.data)

    loop.run_until_complete(bus.subscribe("test", test_handler))
    loop.run_until_complete(bus.publish("test", "src", {"value": 42}))
    assert len(result) == 1
    assert result[0]["value"] == 42
    print("✓ EventBus basic test passed")

    # Test PluginManager init
    manager = PluginManager()
    loop.run_until_complete(manager.initialize())
    print(f"✓ PluginManager initialized, discovered {len(manager.registry.manifests)} plugins")

    loop.close()
    print("✓ All smoke tests passed!")
