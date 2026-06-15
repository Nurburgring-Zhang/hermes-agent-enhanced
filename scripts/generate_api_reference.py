#!/usr/bin/env python3
"""
generate_api_reference.py -- 自动生成 Hermes API 参考文档
===========================================================
扫描 scripts/ 目录下所有 .py 文件，提取所有 public class/function
的定义、docstring、参数签名，生成 API_REFERENCE.md。

输出: ~/.hermes/API_REFERENCE.md

用法:
    python3 generate_api_reference.py
    python3 generate_api_reference.py --output /tmp/api.md
    python3 generate_api_reference.py --check-deprecated
"""

import ast
import glob
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

HERMES_HOME = os.path.expanduser("~/.hermes")
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
MONITORING_DIR = os.path.join(HERMES_HOME, "monitoring")
DEFAULT_OUTPUT = os.path.join(HERMES_HOME, "API_REFERENCE.md")

# Modules that are part of the public API
PUBLIC_MODULES = [
    "actor_base.py",
    "synapse_bus.py",
    "loop_engine.py",
    "loop_checkpoint.py",
    "resilience_patterns.py",
    "memory_federation.py",
    "hermes_utils.py",
    "hermes_skill_evolver.py",
    "hermes_self_evolve_cluster.py",
    "l3_persona_scheduler.py",
    "product_evolve.py",
    "production_chain_v2.py",
    "fabric_heartbeat.py",
    "unified_collector.py",
]

MONITORING_MODULES = [
    "__init__.py",
    "telemetry.py",
    "health.py",
    "metrics.py",
    "alerts.py",
    "dashboard.py",
]


def extract_module_doc(filepath: str) -> Optional[str]:
    """Extract the module docstring."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        return ast.get_docstring(tree)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return None


def extract_classes(filepath: str) -> List[Dict[str, Any]]:
    """Extract all public classes with docstrings and methods."""
    classes = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                cls_info = {
                    "name": node.name,
                    "doc": ast.get_docstring(node) or "",
                    "methods": [],
                    "line": node.lineno,
                    "bases": [b.id for b in node.bases if isinstance(b, ast.Name)],
                    "decorators": [],
                }
                # Check for @deprecated decorator
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == "deprecated":
                        cls_info["deprecated"] = True
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Name) and dec.func.id == "deprecated":
                            cls_info["deprecated"] = True
                            cls_info["deprecated_since"] = (
                                dec.args[0].value if dec.args else "unknown"
                            )
                    cls_info["decorators"].append(ast.unparse(dec))

                # Extract public methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name.startswith("_") and item.name != "__init__":
                            continue
                        method = extract_function_info(item, content)
                        cls_info["methods"].append(method)

                classes.append(cls_info)

    except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
        print(f"  Warning: Could not parse {filepath}: {e}", file=sys.stderr)

    return classes


def extract_functions(filepath: str) -> List[Dict[str, Any]]:
    """Extract all public standalone functions."""
    functions = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue
                func = extract_function_info(node, content)
                # Filter out methods (handled in class extraction)
                if func["name"] != "__init__":
                    functions.append(func)

    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        pass

    return functions


def extract_function_info(node: ast.FunctionDef, source: str) -> Dict[str, Any]:
    """Extract function metadata."""
    info = {
        "name": node.name,
        "doc": ast.get_docstring(node) or "",
        "line": node.lineno,
        "args": [],
        "returns": None,
        "async": isinstance(node, ast.AsyncFunctionDef),
        "deprecated": False,
        "deprecated_since": None,
        "decorators": [],
    }

    # Check decorators
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "deprecated":
            info["deprecated"] = True
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name) and dec.func.id == "deprecated":
                info["deprecated"] = True
                info["deprecated_since"] = (
                    dec.args[0].value if dec.args else "unknown"
                )
        info["decorators"].append(ast.unparse(dec))

    # Extract args
    for arg in node.args.args:
        arg_info = {"name": arg.arg}
        if arg.annotation:
            arg_info["type"] = ast.unparse(arg.annotation)
        info["args"].append(arg_info)

    # Extract return type
    if node.returns:
        info["returns"] = ast.unparse(node.returns)

    return info


def generate_md(
    output_path: str,
    check_deprecated: bool = False,
) -> str:
    """Generate the full API_REFERENCE.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    deprecated_count = 0

    lines = []
    lines.append("# Hermes Agent Enhanced -- API Reference")
    lines.append("")
    lines.append(f"> Auto-generated: {now}")
    lines.append(f"> Version: v0.17.0 (Round 11)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")

    # Scan scripts/
    all_modules = {}
    for pyfile in PUBLIC_MODULES:
        path = os.path.join(SCRIPTS_DIR, pyfile)
        if not os.path.exists(path):
            continue
        classes = extract_classes(path)
        functions = extract_functions(path)
        if classes or functions:
            mod_name = pyfile.replace(".py", "")
            all_modules[f"scripts/{pyfile}"] = {
                "name": mod_name,
                "doc": extract_module_doc(path) or "No description.",
                "classes": classes,
                "functions": functions,
            }
            lines.append(f"- [{mod_name}](#{mod_name})")

    # Scan monitoring/
    for pyfile in MONITORING_MODULES:
        path = os.path.join(MONITORING_DIR, pyfile)
        if not os.path.exists(path):
            continue
        classes = extract_classes(path)
        functions = extract_functions(path)
        if classes or functions:
            mod_name = f"monitoring/{pyfile.replace('.py', '')}"
            display_name = f"monitoring_{pyfile.replace('.py', '')}"
            all_modules[f"monitoring/{pyfile}"] = {
                "name": display_name,
                "doc": extract_module_doc(path) or "No description.",
                "classes": classes,
                "functions": functions,
            }
            lines.append(f"- [{display_name}](#{display_name})")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Generate per-module sections
    for filepath, mod in sorted(all_modules.items()):
        lines.append(f"## {mod['name']}")
        lines.append("")
        lines.append(f"**File:** `{filepath}`")
        lines.append("")
        if mod["doc"]:
            lines.append(f">{mod['doc'].split(chr(10))[0]}")
            lines.append("")

        # Classes
        for cls in mod["classes"]:
            cls_id = f"{mod['name']}-{cls['name']}".lower()
            status = ""
            if cls.get("deprecated"):
                deprecated_count += 1
                since = cls.get("deprecated_since", "unknown")
                status = f" [DEPRECATED since {since}]"

            lines.append(f"### `class {cls['name']}`{status}")
            if cls["bases"]:
                lines.append(f"*Inherits from: {', '.join(cls['bases'])}*")
            lines.append("")
            if cls["doc"]:
                for docline in cls["doc"].split("\n"):
                    lines.append(f"  {docline}")
                lines.append("")

            # Public methods
            for method in cls["methods"]:
                lines.append(f"#### `{method['name']}(...)`")
                if method.get("deprecated"):
                    deprecated_count += 1
                    lines.append(f"  **Deprecated** since {method.get('deprecated_since', 'unknown')}")
                if method["args"]:
                    for arg in method["args"]:
                        type_hint = f": {arg['type']}" if arg.get("type") else ""
                        lines.append(f"  - `{arg['name']}`{type_hint}")
                if method["returns"]:
                    lines.append(f"  - Returns: `{method['returns']}`")
                if method["doc"]:
                    lines.append(f"  {method['doc'].split(chr(10))[0]}")
                lines.append("")

        # Standalone functions
        for func in mod["functions"]:
            func_id = f"{mod['name']}-{func['name']}".lower()
            status = ""
            if func.get("deprecated"):
                deprecated_count += 1
                since = func.get("deprecated_since", "unknown")
                status = f" [DEPRECATED since {since}]"

            lines.append(f"### `def {func['name']}(...)`{status}")
            if func["args"]:
                for arg in func["args"]:
                    type_hint = f": {arg['type']}" if arg.get("type") else ""
                    lines.append(f"  - `{arg['name']}`{type_hint}")
            if func["returns"]:
                lines.append(f"  - Returns: `{func['returns']}`")
            if func["doc"]:
                lines.append(f"  {func['doc'].split(chr(10))[0]}")
            lines.append("")

    # Deprecated summary
    if deprecated_count > 0:
        lines.append("---")
        lines.append("")
        lines.append("## Deprecated API Summary")
        lines.append("")
        lines.append(f"Total deprecated items: **{deprecated_count}**")
        lines.append("")
        if check_deprecated:
            lines.append("> Run `--check-deprecated` to see this summary.")
        else:
            for filepath, mod in sorted(all_modules.items()):
                for cls in mod["classes"]:
                    if cls.get("deprecated"):
                        lines.append(f"- `{cls['name']}` in {mod['name']}")
                    for m in cls["methods"]:
                        if m.get("deprecated"):
                            lines.append(f"- `{cls['name']}.{m['name']}()` in {mod['name']}")
                for f in mod["functions"]:
                    if f.get("deprecated"):
                        lines.append(f"- `{f['name']}()` in {mod['name']}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by `generate_api_reference.py` on {now}*")

    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate Hermes API Reference"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--check-deprecated",
        action="store_true",
        help="Include deprecated API summary",
    )
    args = parser.parse_args()

    print(f"Scanning modules...")
    content = generate_md(args.output, check_deprecated=args.check_deprecated)
    print(f"Generated: {args.output}")
    print(f"  Size: {len(content)} bytes")
    print(f"  Deprecated items: {content.count('[DEPRECATED')}")
    print("Done.")


if __name__ == "__main__":
    main()
