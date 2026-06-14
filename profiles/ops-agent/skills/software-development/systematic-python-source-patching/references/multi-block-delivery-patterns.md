# Multi-Block Code Delivery Patterns

## Context

This reference captures the technique developed during the FinalUltraFusion v4 build (600+ line ComfyUI node) and the PromptLibraryNode V12 rewrite (200+ line fix). Both suffered from the same recurring problem: `write_file` overwrites rather than appends, and sequential calls to write different parts of the same file destroyed earlier parts.

## The Root Cause

`write_file` is a **destructive overwrite** — it truncates the file before writing. This is `>` not `>>` in shell terms. When you need to deliver a large codebase across multiple assistant turns (due to context length limits), you cannot simply call `write_file` 4 times.

## Pattern A: Temp Files + Merge (Proven in This Session)

Used for the FinalUltraFusion v4.0 file: 522 lines across 4 logical sections.

### Step 1: Write Each Section to a Temp File

```python
from hermes_tools import terminal
# Call write_file for each section of code
terminal("python3 << 'EOF'", ...)  # legacy approach
```

Better: use `write_file` to send each section to `/tmp/part_<name>.py`, then merge:

```python
from hermes_tools import execute_code

execute_code(code="""
from pathlib import Path

# Write each part using write_file references 
# (Parts are passed as literal code in the assistant's response)
parts = {}

parts["header"] = \"""\
\"\"\"My header\"\"\"
import os
...
\"""

parts["arch"] = \"""\
class MyModel(nn.Module):
    ...
\"""

# Write to temp
for name, content in parts.items():
    Path(f"/tmp/part_{name}.py").write_text(content)

print(f"Written {len(parts)} parts")
""")
```

### Step 2: Combine in a Second Call

```python
from hermes_tools import execute_code

execute_code(code="""
from pathlib import Path

# Read existing last-write content (if any)
# Or just combine all parts fresh:
parts_names = ['header', 'arch', 'engine', 'nodes']
sections = [Path(f"/tmp/part_{n}.py").read_text() for n in parts_names]
full = '\\n\\n'.join(sections)

# Verify syntax before writing
import ast
ast.parse(full)
print(f"Syntax OK, {len(full.split(chr(10)))} lines")

# Write final
Path("/target/final.py").write_text(full)
print("Written!")
""")
```

### Pros/Cons

| Pro | Con |
|-----|-----|
| Each block independently verifiable | Requires 2+ tool rounds |
| No escaping hell (write_file handles encoding) | Temp file cleanup needed |
| Easy reordering/changing sections | More complex than append |

---

## Pattern B: execute_code Append (2-3 blocks only)

Used when you've already written the first block and need to add more.

```python
from hermes_tools import execute_code

execute_code(code="""
from pathlib import Path

target = Path("/target/file.py")
existing = target.read_text() if target.exists() else ""

# Write the new section to a temp file first (via write_file)
# Then load and append here:
new_code = open("/tmp/new_part.py").read()

combined = existing + "\\n\\n" + new_code

# Verify
import ast
ast.parse(combined)

# Write
target.write_text(combined)
print(f"Appended, total: {len(combined.split(chr(10)))} lines")
""")
```

### Pros/Cons

| Pro | Con |
|-----|-----|
| Single round (read + append + write) | Must keep existing file open-compatible |
| Natural extension of existing content | Risk: can't easily reorder sections |

---

## Pattern C: Python `+` String Concatenation in execute_code (Single Round)

Build the entire file as Python string in `execute_code`:

```python
from hermes_tools import execute_code

execute_code(code="""
from pathlib import Path

code = []
code.append(\"\"\"
import os
\"\"\")

code.append(\"\"\"
class MyClass:
    pass
\"\"\")

full = '\\n'.join(code)

import ast
ast.parse(full)
Path("/target/file.py").write_text(full)
""")
```

Best for files with < 5 sections. Section order is explicit.

---

## Pattern D: `write_file` with Maximal Content (Single Block, < 200 lines)

Simplest but most fragile:

```python
write_file(
    path="/target/file.py",
    content="""\
import os

class Foo:
    def bar(self):
        return 42
"""
)
```

Works fine for **small files** (< 200 lines). Beyond that, split into Pattern A.

---

## Verification Checklist for All Patterns

- [ ] Final file read back with `read_file()` to confirm completeness
- [ ] `python3 -c "import ast; ast.parse(open('file').read())"` passes
- [ ] Line count matches sum of parts (no dropped sections)
- [ ] Class/function count matches expected (e.g., `grep -c '^class ' file.py`)
- [ ] Key strings present (`grep 'NODE_CLASS_MAPPINGS' file.py` etc.)
