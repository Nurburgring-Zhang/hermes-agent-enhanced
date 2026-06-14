---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, writing-plans, subagent-driven-development]
---

# Systematic Debugging

## Overview

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

### Automated Code Audit Pattern

**WHEN debugging system-level issues (not single-bug), use an automated audit script
that scans ALL files for common bug patterns.** This is faster than reading each file
manually and catches issues you wouldn't think to look for.

**The audit script checks:**
- **Bare excepts** (`except:`) — should be `except Exception:` — catches SystemExit/KeyboardInterrupt ⚡ this was the #1 finding in the Hermes self-enhancement session, 23 occurrences across 10 files
- **Bare `except Exception: pass` (no logging)** — silently swallows bugs. The V3 session found 5 instances, one of which masked a missing variable initialization that silently killed all 5+ step tasks (see `references/python-pitfalls-v3-session.md`)
- **SQL injection** — `execute(f"...")` with string formatting
- **Hardcoded passwords** — `password="xxx"` not from env
- **Missing subprocess timeout** — `subprocess.run()` without `timeout=`
- **Unprotected file I/O** — `open()` not inside try block
- **Nested loops (O(n²) risk)** — `for` inside `for`
- **Placeholder code** — `TODO`/`FIXME`/`pass`/`...`/`NotImplementedError`
- **Functions over 100 lines** — suggests it needs splitting
- **Empty files** — exist but 0 bytes

### The "Over-Filtering" Trap

**When debugging "why only N items show up from a dataset of M":** check the FILTER LOGIC first, not the RANDOMNESS logic. This was the root cause in a content-filtering system:

1. Symptom: 500+ prompts in folder, only ~50 ever appear
2. Wrong hypothesis: "Random distribution is broken" / "Loop has dead zone"
3. Actual root cause: A 200-word blacklist containing common neutral words (`chair`, `table`, `window`, `door`, `cup`, `glass`) was silently discarding 90% of valid prompts
4. Fix path: Count items before/after each filter stage. Check if filter keywords are too broad. Add "safe context" detection (if prompt contains person/animal/landscape words, skip filter entirely)

**Checklist for "missing items" bugs:**
- [ ] Count items before and after EACH filter stage (log pass/block counts)
- [ ] Review filter keywords for overly broad terms
- [ ] Check if filter accounts for safe/category context
- [ ] Verify with a raw "no filter" run to establish baseline count

**Implementation pattern** (Python):

```python
import ast, re, os
from pathlib import Path

def audit_file(path: str) -> list[dict]:
    issues = []
    content = Path(path).read_text()
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*except\s*:\s*$', line):
            issues.append({"line": i, "type": "bare_except", "severity": "high"})
        # ... more patterns
    return issues
```

**⚠️ Critical heuristic: "Is this a real failure or a test matching problem?"**

When an automated test reports a failure, ALWAYS verify manually before spending
time on a fix. Many automated test failures are text-matching issues:

| Test Pattern | Typical False Positive | How to Verify |
|-------------|----------------------|---------------|
| `"ok" in stdout` | Script outputs `"status=ok"` but test expects exact string | Run script manually, check last 3 lines |
| `file in list` | Test looks for wrong path (e.g. `scripts/` vs `agents_company/`) | `ls -la` the actual path |
| `pattern in crontab` | Test uses wrong regex for cron line format | `crontab -l \| grep <pattern>` |
| `== 0` exit code | Script returns non-zero but produced correct output | Run it and check output manually |

**Always check**: run the actual script, look at the last 3 lines of stdout.
If the output looks correct, it's a test problem, not a system problem.

### The "Test Failure Noise" Trap

**When automated tests report failures on what looks like correct code:**

Session pattern: You write a test that runs 70 checks. 9 fail. You fix the obvious issues, rerun, now a different set of 9 fail in a clean workspace. This usually means the tests are sensitive to **workspace contamination** or **timing assumptions**, not that the code is broken.

#### Debugging Test Failure Noise (not code bugs)

**When an isolated manual test passes but the full suite fails:**

| Symptom | Likely Root Cause | Fix |
|---------|-------------------|-----|
| Test passes in new tmpdir, fails in shared tmpdir | Leftover files from prior test (big.txt, 50k rows, etc.) contaminate this test's file listing | Create a fresh tmpdir for EACH test group |
| "Women in garden" filtered out in clean run but passes in debug | Different test file content (<8 chars lines get silently dropped) | Ensure ALL test lines are >= 8 chars |
| Classification prefix test fails | Test passes with manual probe but fails in suite because prior test mutated `_cache` state | Test in order that accounts for cache, or clear cache between test groups |
| Empty path test returns wrong error | The error tuple changed shape (7-tuple vs 5-tuple) but the test checks the old format | Match tests to current RETURN_TYPES (7 elements) |

**Rules for writing robust tests:**

1. **Each test group gets its own `tempfile.mkdtemp()`** — never share tmpdirs between test groups
2. **Check test assertions against known-valid output**, not against guesses — print the actual output first
3. **If assertion `X == True` fails**, print `X` to see what it actually is
4. **Test one thing per assertion** — `assert A and B` masks which one failed
5. **Count items before and after each filter pipeline stage** — logging is debugging
6. **For ComfyUI nodes specifically**, test through Python import (not through ComfyUI) — direct tests catch logic bugs faster

#### Distinguishing Real Bug from Test Bug

```
Test says X fails -> Does manual invocation of the same function with the same inputs produce a correct result?
  -> YES: test is wrong, not the code. Fix the test.
  -> NO: code is wrong. Debug the code.
```

Real example from session: `assert '女性' in prompts` failed. Manual test showed "女性" passed both filters correctly. Root cause: the tmpdir had a 50000-line "big.txt" from a prior performance test that matched "女性" but was counted as passing -- the 6-line test file had only 3 lines with bodies matching the filter, not 4, because one line was 7 chars and got dropped by the min-line filter. The **test** was wrong, not the filter.

### Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

### Visual Artifacts Debugging — Tile Stitch Weight Bug

See `references/tile-stitch-weight-bug-pattern.md` for full pattern.

**Key symptom:** Image upscale produces "top half darker, bottom half pure white" with a horizontal dividing line.

**Diagnosis:** `wt[:, :, :ah, ...]` instead of `wt[:, :, oys:oye, ...]` in tiled inference.

**Always check both `tiled_upscale_v2` and `ensemble_upscale_v2_tiled`** — same bug duplicates in both.

## Python Pitfalls from Hermes V3 Session (2026-05-20)

The reference file `references/python-pitfalls-v3-session.md` documents four class-level bugs found across a ~6500-line Python codebase during a single deep-dive session. Read it before debugging multi-step task execution, diagnostic functions, or enum-based logic.

Key signal: if a task executes 0 steps despite correct loop logic, check for silent `except Exception: pass` masking an exception in an unrelated function called from within the loop. This was the root cause in 3 separate instances during the V3 audit.

**Mock class scoping trap:** When investigating `NameError: name 'X' is not defined` on a class that IS defined in the file, check whether the mock/fallback classes live in the `except` block of a **different** import than the one that failed. See `references/python-mock-class-scoping-trap.md` for the full pattern. Also see: `references/python-pitfalls-v3-session.md` for enum-vs-string, silent pass, and variable initialization traps.

### Object Method Confusion Bug

LLMs sometimes write `.method()` on Python primitive types as if they had methods (confusing numpy array methods with plain Python math). See `references/object-method-confusion-bug.md` for detection and the fix pattern.

**Quick check:** Search for `).cos(`, `).sin(`, `).tan(`, `).sqrt(` — these are never valid on plain Python floats.

**No shortcuts. No guessing. Systematic always wins.**

## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
