#!/usr/bin/env python3
"""
RAG Memory Plugin for Hermes

This plugin registers RAG memory management commands and ensures the
memory_search and memory_get tools are available in all expert agents.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def ensure_skill_loaded():
    """Ensure RAG skill is loaded and tools are registered."""
    try:
        # Import the RAG tool module to trigger registration
        skill_path = Path.home() / ".hermes" / "skills" / "rag-memory-enhanced"
        if skill_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("rag_memory_tool", skill_path / "rag_memory_tool.py")
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logger.info("[RAG] RAG memory tools registered successfully")
                return True
    except Exception as e:
        logger.error(f"[RAG] Failed to load RAG tools: {e}")
    return False

def register_commands():
    """Register CLI commands for RAG memory management."""
    try:
        from hermes_cli.commands import CommandDef, register_plugin_command

        commands = [
            CommandDef(
                name="memory_index",
                description="Index workspace files into RAG memory (manual trigger)",
                category="Memory",
                cli_only=True,
                args_hint="[--force] [--extensions py,js,md]"
            ),
            CommandDef(
                name="memory_search_test",
                description="Test RAG search quality and recall rate",
                category="Memory",
                cli_only=True,
                args_hint="[query] [--limit 10]"
            ),
            CommandDef(
                name="memory_stats",
                description="Show detailed RAG memory statistics",
                category="Memory",
                cli_only=True,
                args_hint="[--format json|text]"
            ),
            CommandDef(
                name="memory_compress",
                description="Compress memory database by removing old chunks",
                category="Memory",
                cli_only=True,
                args_hint="[--execute]"
            ),
            CommandDef(
                name="memory_watch",
                description="Control file watcher (start/stop/status)",
                category="Memory",
                cli_only=True,
                args_hint="[start|stop|status]"
            ),
        ]

        for cmd in commands:
            register_plugin_command(cmd)

        logger.info(f"[RAG] Registered {len(commands)} CLI commands")
        return True

    except Exception as e:
        logger.error(f"[RAG] Failed to register commands: {e}")
        return False

# ---------------------------------------------------------------------------
# Hermes Plugin Interface
# ---------------------------------------------------------------------------

def on_load():
    """Called when plugin is loaded by Hermes."""
    logger.info("[RAG] RAG Memory Plugin loading...")

    # Register commands
    cmd_success = register_commands()

    # Ensure RAG tools are available
    tool_success = ensure_skill_loaded()

    if cmd_success and tool_success:
        logger.info("[RAG] Plugin loaded successfully - RAG system ready")
        return True
    logger.warning("[RAG] Plugin loaded with warnings")
    return False

def on_unload():
    """Called when plugin is unloaded."""
    logger.info("[RAG] RAG Memory Plugin unloaded")
    return True

# Auto-initialize when imported
if __name__ != "__main__":
    try:
        on_load()
    except Exception as e:
        logger.error(f"[RAG] Plugin initialization failed: {e}")
