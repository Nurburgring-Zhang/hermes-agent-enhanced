#!/usr/bin/env python3
"""
quick-reference: print the v10.1 engine architecture summary
"""
import os

ENGINE_PATH = "/mnt/d/Hermes/1000000提示词/高质量模板/维度库/combine_engine_v10_1.py"

if os.path.exists(ENGINE_PATH):
    with open(ENGINE_PATH) as f:
        content = f.read()

    # Extract key sections
    lines = content.split("\n")
    print(f"v10.1 Engine ({ENGINE_PATH})")
    print(f"Total lines: {len(lines)}")
    print(f"File size: {os.path.getsize(ENGINE_PATH)} bytes")
    print()

    # Show gen_one()
    for i, line in enumerate(lines, 1):
        if "def gen_one" in line:
            print(f"--- gen_one() starts at line {i} ---")
            for j in range(i, min(i+80, len(lines))):
                print(lines[j])
            break

    # Show FEMALE_ONLY list
    print()
    print("--- FEMALE_ONLY (gender filter words) ---")
    for line in lines:
        if "FEMALE_ONLY" in line and "=" in line:
            print(line)
        if "FEMALE_WORDS" in line and "=" in line:
            print(line)

    # Show pick() function
    print()
    print("--- pick() function ---")
    for i, line in enumerate(lines, 1):
        if "def pick" in line:
            for j in range(i, min(i+20, len(lines))):
                print(lines[j])
            break
else:
    print(f"ERROR: {ENGINE_PATH} not found")
