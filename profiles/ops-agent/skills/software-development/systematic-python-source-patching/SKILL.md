---
name: systematic-python-source-patching
description: Safely modify Python source files by replacing whole function/method blocks without breaking indentation or introducing syntax errors. Use when you need to edit existing Python code programmatically.
---

## When to Use

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Use this skill when you need to:
- Patch or extend an existing Python file (especially multi-method classes)
- Replace function bodies to change behavior
- Add new methods to existing classes
- Avoid string escaping hell when embedding code in code
- **Write large multi-block Python files** where a single `write_file` call would exceed context limits, or where the file needs to be assembled from multiple parts

**Do NOT use** for simple sed/awk replacements — use `patch` tool directly for those.

## ⚠️ CRITICAL: write_file OVERWRITES — It Does NOT Append

`write_file` **destructively overwrites** the entire file every time it's called. This is the #1 footgun in this session. If you call `write_file` 4 times for 4 code blocks, **only the 4th call's content survives.** The first 3 blocks are gone.

**This is NOT like `cat >> file` or `echo ... >> file`. It is `>` not `>>`.**

### The Three Safe Patterns for Multi-Block Files

#### Pattern A: Write Parts to Temp Files, Combine at End (Preferred for 3+ blocks)

```python
from hermes_tools import terminal

# Step 1: Write each block to a separate temp file via write_file
# write_file("/tmp/part_header.py", "...")
# write_file("/tmp/part_engine.py", "...")

# Step 2: Use execute_code (not terminal) to combine them
from pathlib import Path
parts = []
for name in ['header', 'engine', 'nodes']:
    parts.append(Path(f"/tmp/part_{name}.py").read_text())
full = '\n\n'.join(parts)
Path("/output/final_file.py").write_text(full)

# Step 3: Verify syntax
import ast
ast.parse(full)  # raises SyntaxError if bad
```

**Use this when:** the file is large (300+ lines), has clear structural sections, and each section is independently testable.

#### Pattern B: Batch Append via execute_code (2-3 blocks)

```python
from hermes_tools import execute_code

# Write first block via write_file
# Then in execute_code, load, append, rewrite:
execute_code(code="""
content = open("/target/file.py").read()
content += "\\n# === NEW SECTION ===\\n"
content += open("/tmp/new_section.py").read()
open("/target/file.py", "w").write(content)
""")
```

**Use this when:** you already wrote the first block and only need to add 1-2 more.

#### Pattern C: Single write_file with compressed single-string (Simple files)

Write the entire file as one `write_file` call. Keep it under ~10,000 chars. Use minimal comments and concise code.

**Use this when:** the file is < 200 lines and straightforward.

### When to Use Each Pattern

| Scenario | Pattern | Why |
|----------|---------|-----|
| 3+ blocks, 600+ lines, complex logic | **A** (temp files + merge) | Each piece independently verifiable; no escape hell |
| 2 blocks, 300+ lines | **B** (append) | Fast, no temp file juggling |
| Single block, <200 lines | **C** (one write) | Simplest |
| Green master's 4-part ultra-detailed node | **A** (temp files + merge) | Code is big, structured, needs syntax check

## The Pattern (Step-by-Step)

### Step 1: Extract Patch Content to External Files
Write your new/changed code to separate files first (not embedded strings). This avoids triple-quote escaping nightmares.

```python
from pathlib import Path
patches_dir = Path("/tmp/patches")
patches_dir.mkdir(exist_ok=True)

# Write each function/method to its own file
(patches_dir / "new_method.txt").write_text('''    def new_method(self):
        """Do something"""
        pass
''')
```

**Key:** Keep the file content exactly as it should appear in the target file (with proper indentation).

### Step 2: Locate Exact Boundaries in Target File
Before replacing anything, find where the code lives:

```python
content = target_file.read_text()

# For functions/methods: find exact def line
start_marker = "    def method_name(self"  # adjust spaces for class level (4) or nested (8)
start_idx = content.find(start_marker)
if start_idx == -1:
    # Try alternative indent if corrupted
    start_marker = f"        def method_name(self"
    start_idx = content.find(start_marker)
```

### Step 3: Find the End of the Block
Search for the next method or class definition at the same indentation level:

```python
search_from = start_idx + 1
next_method = content.find("\n    def ", search_from)   # same level: 4 spaces before def
next_class = content.find("\n\nclass ", search_from)   # class definition
candidates = [p for p in [next_method, next_class] if p > start_idx]
end_idx = min(candidates) if candidates else len(content)
```

### Step 4: Replace the Whole Block
Replace exactly from `start_idx` to `end_idx`:

```python
old_block = content[start_idx:end_idx]
new_block = (patches_dir / "new_method.txt").read_text()
new_content = content.replace(old_block, new_block, 1)  # replace first match only
```

### Step 5: Fix Indentation if Needed
If you discover the target file has inconsistent indentation, **dedent or indent consistently** before final write:

```python
lines = new_content.split('\n')
# Check a sample of method def lines
for line in lines:
    if 'def _handler_' in line:
        spaces = len(line) - len(line.lstrip())
        print(f"Indent: {spaces} | {line[:80]}")
```

**Standard:** Class body methods: def at 4 spaces, body at 8 spaces.

Fix by dedenting entire affected sections:
```python
fixed_lines = []
for line in lines:
    if line.startswith('        '):  # 8 spaces, should be 4?
        fixed_lines.append(line[4:])
    else:
        fixed_lines.append(line)
target_file.write_text('\n'.join(fixed_lines))
```

### Step 6: Verify Syntax
```python
import subprocess, sys
result = subprocess.run([sys.executable, "-m", "py_compile", str(target_file)],
                       capture_output=True, text=True)
assert result.returncode == 0, f"Syntax error: {result.stderr}"
```

## Common Pitfalls & How to Avoid Them

| Pitfall | Fix |
|---------|-----|
| `SyntaxError: unexpected character after line continuation` | Don't use `'''` inside `'''`. Write patches to files first, then read. |
| `IndentationError: expected an indented block` | The def line has wrong spaces. Ensure def is 4 spaces (class-level), body is 8. |
| Old block not found by `replace()` | Print `old_block[:100]` and compare to actual file content — whitespace differences matter. |
| Patch replaces wrong function | Use unique surrounding context in old_block, or search+replace by position (slicing). |
| `patch` tool warns "file was read with offset/limit" | This is **not an error**. It happens when you used `read_file(offset=N)` to view a snippet. The patch still applies correctly as long as the `old_string` is unique and present in the file. **Ignore the warning** — just verify with syntax check after. |
| Using `patch` on a file read with offset/limit — tool says re-read the whole file | Don't re-read the whole file. The tool uses grep internally to find the old_string. As long as old_string is truly present, it works. The warning is a conservative guard. **Preferred workflow: `grep -n` to locate line numbers, write old_string/new_string with unique surrounding context, then `patch`.** |

## Verification Checklist

- [ ] Patch files written to disk before loading (no triple-quoted string hell)
- [ ] `start_idx` locating includes the leading whitespace of the def line
- [ ] `end_idx` is the character just before the next method/class at same level
- [ ] Replacement uses `replace(old, new, 1)` — only first occurrence
- [ ] After all patches: run `python -m py_compile` on modified file
- [ ] Spot-check method def lines to ensure 4-space indent (class level)

## Example: Patching Multiple Handlers

```python
from pathlib import Path

target = Path("executor.py")
content = target.read_text()
patches = Path("/tmp/patches")

for method in ["_handler_backend", "_handler_frontend", "_handler_deploy"]:
    # 1. Find function block
    start = content.find(f"    def {method}(self")
    # 2. Find end
    next_def = content.find("\n    def ", start+1)
    end = next_def if next_def > start else len(content)
    old = content[start:end]
    # 3. Replace
    new = (patches / f"{method}.txt").read_text()
    content = content.replace(old, new, 1)

target.write_text(content)
```

---

## Lessons from Real Use

This skill was developed while patching `agents_company_executor.py` where:
- Initial attempts embedded code as triple-quoted strings inside Python strings → caused escape hell
- Replacement introduced extra indentation (8 spaces instead of 4) because the search pattern didn't include original indentation properly
- Solution: Extract patches to files, read as raw strings, and ensure replacement blocks preserve the exact leading whitespace structure of methods
- Critical: Always verify with `py_compile` after patching and visually inspect indentation levels

### write_file Overwrite Warning — Live in This Session

**Every session will hit this.** The tool's overwrite semantics (`>` not `>>`) caught out the author **four times** in one session while building a 522-line ComfyUI node:
1. Wrote header → overwritten by engine section
2. Wrote engine → overwritten by tiling section  
3. Wrote tiling → overwritten by nodes section
4. Finally realized: combine temp files in execute_code

**Rule of thumb:** If the file exceeds 200 lines OR contains 3+ logical sections, do NOT use sequential `write_file` calls. Use the temp-file + merge pattern (see `references/multi-block-delivery-patterns.md` for the full worked example).

**Pro tip:** If you find yourself with a partial file after writing, don't rewrite — use execute_code to load each temp part and reassemble:

```python
from pathlib import Path
sections = []
for name in ['header', 'engine', 'tiling', 'nodes']:
    p = Path(f"/tmp/part_{name}.py")
    if p.exists():
        sections.append(p.read_text())
full = '\n\n'.join(sections)
# Verify then write
import ast; ast.parse(full)
Path("/target/file.py").write_text(full)
```

### NumPy np.diff Broadcast Trap

When computing edge maps with `np.diff`, the result shapes differ:
- `np.diff(arr, axis=1)` → shape `(h, w-1)`
- `np.diff(arr, axis=0)` → shape `(h-1, w)`

Adding them directly **crashes with broadcast error**. Always crop to the minimum common dimensions:

```python
diff_h = np.abs(np.diff(arr, axis=1))  # (h, w-1)
diff_w = np.abs(np.diff(arr, axis=0))  # (h-1, w)
min_s = min(diff_h.shape[0], diff_w.shape[0], diff_h.shape[1], diff_w.shape[1])
edges = diff_h[:min_s,:min_s] + diff_w[:min_s,:min_s]
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
