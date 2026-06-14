---
name: "plugin-system-architecture"
title: "Complete Plugin System Architecture"
description: "Design and implement a production-ready plugin system with lifecycle management, dependency resolution, event bus, hot-reload, and inter-plugin communication"
difficulty: "advanced"
prerequisites: ["Python async/await", "OOP patterns", "dependency injection", "event-driven architecture"]
---

## Stages

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### 1. Architecture Design
Define core abstractions: Plugin base class, PluginRegistry, PluginManager, EventBus. Plan lifecycle states (UNLOADED → LOADED → RUNNING → STOPPED). Design hook system integration points.

**Deliverables**: plugin_base.py, plugin_registry.py, plugin_manager.py, event_bus.py

**Verification**: Unit tests for EventBus publish/subscribe, PluginRegistry discovery logic

### 2. Core Implementation
Implement Plugin abstract base class with lifecycle methods (init, start, stop, execute). Build PluginRegistry with JSON manifest parsing, config loading (YAML), and dynamic module import. Create PluginManager with dependency graph resolution using topological sort and batch loading. Implement EventBus with async handlers, wildcard subscriptions, and history tracking.

**Deliverables**: Core classes with full type hints, DependencyGraph class, Hook emission system

**Verification**: All plugins can be discovered; dependency resolution produces correct load order; circular dependencies raise errors

### 3. CLI and Management
Build CLI interface for plugin lifecycle: list, install (from path/URL/unarchive), enable/disable, start/stop, reload config, info, uninstall. Integrate with Hermes command system via register_commands().

**Deliverables**: cli.py, Command handler functions, Error handling for all edge cases

**Verification**: All /plugin_* commands work, can install a test plugin, hot-reload config

### 4. Plugin Structure Definition
Standardize plugin directory layout: `{plugin_name}/{__init__.py, plugin.json, config.yaml, requirements.txt, README.md}`. Define plugin.json schema: name, version, description, entry_point, dependencies, capabilities, hooks, config_schema. Implement YAML config loading with PyYAML fallback.

**Deliverables**: Template structure, Manifest validator, Config loader with defaults

**Verification**: Sample plugin with all fields validates; missing required fields give clear errors

### 5. Advanced Features
Add hot configuration reload without restarting plugin (reload_plugin_config). Implement inter-plugin communication via EventBus publish/subscribe. Add hook registration system where plugins declare hooks they need and manager calls them at appropriate times (hermes.start, message.receive, ai.before_generate, etc.). Build tool discovery: plugins expose tools via get_tools(); manager aggregates for LLM integration.

**Deliverables**: Hot reload mechanism, HookType constants and emission points, PluginManager.get_plugin_tools()

**Verification**: Changing config.yaml triggers reload hook; plugins can communicate via custom events; tools appear in main Hermes system

### 6. Testing and Validation
Write comprehensive tests: EventBus synchronous and async handlers, wildcard subscriptions, history limits. Test PluginRegistry discovery with manifest validation errors. Test PluginManager dependency resolution (including circular dependency detection). Test plugin load/stop/unload with mock plugins. Integration tests: all 4 migrated plugins discover and have valid structures.

**Deliverables**: tests/test_plugin_system.py, Mock plugins for testing, Smoke test script

**Verification**: pytest suite passes; smoke test shows all 4 migrated plugins discovered with complete file structure

### 7. Real Plugin Implementation Examples
Migrate 4 complex OpenClaw plugins to demonstrate system:
1. **Web Search**: multi-engine adapters (Brave, DuckDuckGo, Tavily, Perplexity), caching, deduplication
2. **Weixin**: dual backend (itchat/wxauto), multi-account management, message handling, filters
3. **AirI**: Live2D integration, lip-sync engine with librosa, WebSocket server, emotion control
4. **SuperIntelligence**: multi-model orchestration, synthesis strategies (voting/consensus/cascade), self-critique loop, performance optimization

Each shows different plugin patterns: tool providers, channel adapters, long-running services, AI enhancers.

**Deliverables**: 4 full plugin implementations, README for each, config.yaml with detailed comments

**Verification**: Each plugin can be enabled/disabled; their tools are discoverable; they use event bus where appropriate

---

## Key Patterns & Decisions

### Plugin Lifecycle States
UNLOADED → LOADING → LOADED → STARTING → RUNNING → STOPPING → STOPPED. State transitions enforced, can't start unloaded.

### Dependency Resolution
Directed acyclic graph (DAG) with topological sort produces load batches. Circular dependencies raise clear error. Allows plugins to declare dependencies for proper initialization order.

### Dynamic Module Loading
Uses importlib.util with explicit sys.path manipulation, cleaned up after. Finds Plugin subclass by checking issubclass(). Safe unloading by removing from registry.

### Configuration Management
YAML files with PyYAML optional. Config merged with defaults from manifest.schema. Hot reload re-reads file and emits `hermes.config.reload` hook without restarting plugin.

### Event Bus
Central async pub/sub. Handlers can be sync or async (run in thread pool). Wildcard subscriptions. Thread-safe with asyncio locks. History buffer for debugging.

### Hook System
Declarative hooks in manifest (e.g., ["message.receive", "ai.before_generate"]). PluginManager._emit_hook calls methods named with dots replaced by underscores (message_receive). Allows plugins to integrate at key points without tight coupling.

### Tool Discovery
Plugins implement get_tools() returning OpenAI-style tool schemas. PluginManager aggregates all tools, adds plugin name. Enables seamless LLM integration - tools auto-discovered.

### Threading for Blocking Operations
Plugins like weixin (itchat) and wxauto use blocking code. We isolate in separate threads with asyncio thread pool integration. Lifecycle methods remain async but offload blocking calls.

### Graceful Degradation
Plugin dependencies listed in manifest but not enforced at install time - manager warns but continues. Optional features (API keys) configured; plugin starts with reduced capability if missing.

### Error Isolation
Plugin load failures logged but don't stop other plugins. Individual plugin exceptions caught in hooks and tool calls. Manager keeps running even if one plugin crashes.

## Common Pitfalls Addressed

1. **Import errors**: Added explicit try/except and clear error messages when dependencies missing
2. **Circular dependencies**: Topological sort detection with detailed error message showing cycle path
3. **Thread safety**: EventBus uses asyncio locks; plugin state mutations guarded by manager._lock
4. **Configuration races**: Hot reload acquires lock, prevents concurrent modifications
5. **Memory leaks**: Plugin unloading removes from sys.path and deletes references
6. **Blocking event loops**: Offload blocking I/O to threads; use asyncio.to_thread for sync handlers

## When to Use This Architecture

- Building extensible applications with third-party plugins
- Need runtime plugin enable/disable without restart
- Want dependency management between plugins
- Require inter-plugin communication (events)
- Want to expose plugin capabilities as tools for AI agents
- Need hot configuration reload

## Integration Steps

1. Copy plugin_system/ to your project's plugin directory
2. Initialize PluginManager with plugins_dir path
3. Call manager.initialize() at startup
4. Call manager.start_all() to auto-start enabled plugins
5. Register CLI commands via register_commands(manager)
6. Plugins can now call manager.get_plugin('name') to interact
7. Use manager.get_plugin_tools() to aggregate tools for LLM

## Minimal Plugin Template

```python
from plugin_system import Plugin, PluginManifest, PluginConfig

manifest = PluginManifest(
    name="my-plugin",
    version="1.0.0",
    description="My plugin",
    author="Me",
    entry_point="__init__.py",
    capabilities=["my_capability"],
    hooks=[]
)

config = PluginConfig(
    name="my-plugin",
    version="1.0.0",
    description="My plugin",
    author="Me",
    config={"setting": "value"}
)

class MyPlugin(Plugin):
    async def init(self):
        self.data = {}
    
    async def start(self):
        pass
    
    async def stop(self):
        pass
    
    async def my_action(self, param: str) -> str:
        return f"Hello {param}"
    
    def get_tools(self):
        return [{
            "name": "my_tool",
            "description": "My tool",
            "parameters": {"type": "object", "properties": {"param": {"type": "string"}}}
        }]
```

## Testing Script

```python
# test_plugin_system.py - quick validation
import asyncio
from plugin_system import PluginManager, EventBus

async def test():
    manager = PluginManager()
    await manager.initialize()
    print(f"Discovered {len(manager.registry.manifests)} plugins")
    
    # Test event bus
    results = []
    await manager.event_bus.subscribe("test", lambda e: results.append(e.data))
    await manager.event_bus.publish("test", "src", {"value": 42})
    assert len(results) == 1
    print("✓ All checks passed")

asyncio.run(test())
```
## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
