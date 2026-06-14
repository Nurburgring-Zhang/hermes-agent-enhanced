# File Safety & Recovery During Multi-Edit Sessions

## The Risk

When editing a single Python file (especially 1000+ line ComfyUI nodes) across multiple tool calls in one session, the file is at risk of:

1. **Double line numbers** — `read_file` displays lines as `"  NNN|content"`. If `write_file` writes this back, every line gets a prefix like `"     1|"`.
2. **Truncation** — if `write_file` was given an incomplete snapshot, the file loses everything after that point.
3. **Concurrent corruption** — `delegate_task` sub-agents calling `read_file` + `write_file` on the same file as the main agent's `patch` calls.

## Proven Recovery (V17.0 Session, 2026-05-21)

### Symptom
File `/mnt/d/ComfyUI/custom_nodes/PromptLibraryNode/__init__.py`:
- Every line started with `"     1|"` or `"   122|"` 
- `wc -l` = 501 (was 1377)
- `tail -20` showed content truncated mid-function

### Recovery Steps

**Step 1: Preserve the broken file**
```bash
cp __init__.py __init__.py.broken
```

**Step 2: Fix double line numbers**
```python
import re
with open("__init__.py.broken", "r") as f:
    raw = f.read()
fixed = []
for line in raw.split("\n"):
    m = re.match(r'^\s*\d+\|(.*)$', line)
    if m:
        fixed.append(m.group(1))
    else:
        fixed.append(line)
with open("__init__.py", "w") as f:
    f.write("\n".join(fixed))
```

**Step 3: Verify what's still there**
```bash
python3 -c "import ast; ast.parse(open('__init__.py').read())"
# If this fails, the file is still truncated
```

**Step 4: Reconstruct missing suffix**

If the file is truncated (e.g., ends at line 500 instead of 1377):
1. Know what was in the original file (from previously reading the complete version)
2. Split the missing part into logical chunks:
   - **Part 1**: get_prompt body remainder (batch AI loop → translation → multi-output split → scoring → output return)
   - **Part 2**: AI call + error tools + keywords parse
   - **Part 3**: File scan + line loading + filters (smart_filter, subject_filter, whitelist, lifeless)
   - **Part 4**: Storyboard generator (system prompts, user prompts, layout, names, styles)
3. Write each chunk as a separate temp file
4. Concatenate and verify:
   ```bash
   head -N __init__.py > combined.py
   cat combined.py part1.txt part2.txt part3.txt part4.txt > combined.py
   cp combined.py __init__.py
   python3 -c "import ast; ast.parse(open('__init__.py').read())"
   ```

**Step 5: Verify import works**
```python
import sys
sys.path.insert(0, '/mnt/d/ComfyUI/custom_nodes/PromptLibraryNode')
from __init__ import PromptLibraryNodePro
# Check: RETURN_TYPES, RETURN_NAMES, INPUT_TYPES, all methods
```

## Prevention Rules

| Rule | Why |
|------|-----|
| `cp f.py f.py.safe` before any multi-edit session | Physical backup survives tool failures |
| `python3 -c "import ast; ast.parse(...)"` after EVERY write | Catches corruption immediately |
| NEVER use `write_file` on same file as `patch` in same turn | Race condition guarantees corruption |
| delegate_task sub-agents must NOT touch the main file | Concurrent writes = guaranteed loss |
| When in doubt, use `terminal` with heredoc for precision | `cat > f << 'EOF'` is atomic |

## NEW TRAP: Empty write_file Truncates to 0 Bytes

**Discovered:** 2026-05-22, V17.0 session.

**Symptom:** `file __init__.py` returns `empty`. File size = 0. The Python file that was 1650 lines is suddenly blank. Import fails with `SyntaxError`.

**Root cause:** `write_file` with empty `content` parameter — either a mistake in the tool call or passing a variable that resolves to empty string. `write_file` treats empty content as a valid write, truncating the file to 0 bytes.

**Recovery workflow that worked (V17.0 session):**

1. **Find backups immediately:**
   ```bash
   ls -la __init__.py*  # check .bak, .safe, .broken files
   find . -name "*.bak" -o -name "*.safe" 2>/dev/null
   git stash list  # check git stashes if in git repo
   ```
   
2. **Restore nearest backup:**
   ```bash
   cp __init__.py.bak __init__.py  # 500-line old version
   python3 -c "import ast; ast.parse(open('__init__.py').read()); print('✅')"
   # If backup is truncated/old, proceed to rebuild
   ```

3. **Rebuild missing code via delegate_task (NOT manual write):**
   - delegate_task have full session context and can reconstruct the missing logic
   - Use multiple chained delegate_task for different code sections
   - After all blocks are written, merge and verify:
   ```bash
   cat __init__.py.v17_b1 > combined.py
   cat part2.py >> combined.py
   cp combined.py __init__.py
   python3 -c "import ast; ast.parse(open('__init__.py').read()); print('✅')"
   ```

4. **Verify NODE_CLASS_MAPPINGS** — without this, ComfyUI silently ignores the node:
   ```bash
   grep "NODE_CLASS_MAPPINGS" __init__.py
   ```

5. **Run full functional test** — don't just check import, run all tests:
   ```python
   from __init__ import PromptLibraryNodePro
   node = PromptLibraryNodePro()
   # Test all critical paths
   ```

**Prevention:**
```python
# SAFER: validate content before write_file
if not content or len(content.strip()) == 0:
    raise ValueError("Refusing to write empty content — this would truncate the file")

# SAFEST: use terminal with heredoc for critical files
content = open('__init__.py').read()  # re-read from file, don't pass raw string
```

## Prevention Rules

For files over 500 lines being modified across multiple edits:

```
read_file → [know structure] → 
  write_file (backup.safe) → 
  patch (change 1) → AST verify → 
  patch (change 2) → AST verify → 
  ... → 
  full import test → 
  full functional test
```

Each `patch` or `write_file` call must be followed by an AST check. If AST fails, restore from `.safe` and retry with smaller changes.
