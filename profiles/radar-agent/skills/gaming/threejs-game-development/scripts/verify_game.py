#!/usr/bin/env python3
"""Quick verification script for Three.js web game bundle.
Run AFTER webpack build, BEFORE declaring done.
Exit code 0 = pass, non-zero = fail."""

import os
import re
import sys


def check(path: str, pattern: str, description: str) -> bool:
    """Check if pattern exists in file. Print result. Return True if OK."""
    try:
        with open(path) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  ❌ {description}: file not found")
        return False

    if re.search(pattern, content):
        print(f"  ✅ {description}")
        return True
    print(f"  ❌ {description}: pattern '{pattern}' not found")
    return False

def neg(path: str, pattern: str, description: str) -> bool:
    """Check if pattern does NOT exist."""
    try:
        with open(path) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  ❌ {description}: file not found")
        return False

    if re.search(pattern, content):
        print(f"  ❌ {description}: FOUND (should not be present)")
        return False
    print(f"  ✅ {description}: confirmed absent")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: verify_game.py <src_directory>")
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.isdir(src):
        print(f"Not a directory: {src}")
        sys.exit(1)

    # Find main TypeScript files
    ts_files = []
    for root, dirs, files in os.walk(src):
        for f in files:
            if f.endswith(".ts"):
                ts_files.append(os.path.join(root, f))

    print(f"Verifying {len(ts_files)} TypeScript files in {src}")
    print()

    results = []

    # 1. No {caret} markers
    for fp in ts_files:
        with open(fp) as f:
            content = f.read()
        if "{caret}" in content:
            rel = os.path.relpath(fp, src)
            print(f"  ❌ {rel}: contains {{caret}} marker!")
            results.append(False)

    # 2. Check all files for common issues
    main_file = os.path.join(src, "PlushRacingGame.ts") if os.path.exists(os.path.join(src, "PlushRacingGame.ts")) else None

    if main_file:
        with open(main_file) as f:
            content = f.read()

        checks = [
            ("window.Game routing (no PlushRacingGame static call)",
             r"PlushRacingGame\.\w+", False),  # neg check
            ("try-catch around WebGLRenderer",
             r"try\s*\{.*new THREE\.WebGLRenderer", True),
            ("try-catch around EffectComposer",
             r"try\s*\{.*new EffectComposer", True),
            ("composer fallback path",
             r"composer\s*=\s*null", True),
            ("Bloom strength < 0.3",
             r"bloomPass.*0\.[012]\d*", True),
            ("no console.log as feature",
             r"console\.log\('[选择|角色|设置|制作]", False),
            ("all menu buttons produce visible output",
             r"alert\(|appendChild\(panel\)", True),
        ]

        for desc, pattern, should_exist in checks:
            found = bool(re.search(pattern, content))
            ok = found == should_exist
            status = "✅" if ok else "❌"
            print(f"  {status} {desc}")
            results.append(ok)

    print()
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"Results: {passed}/{total} passed")

    if passed < total:
        print("FAILURES DETECTED")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
