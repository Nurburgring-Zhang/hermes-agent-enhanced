# Bug: IndentationError after replacing methods

## Symptom
After patching methods in a class, Python reports:
```
IndentationError: expected an indented block after function definition on line N
```

even though the function body visibly has content.

## Root Cause
During replacement, the search pattern (`start_marker`) didn't include the original method's leading indentation, so the replacement text was inserted with correct indentation but relative to wrong base — effectively indenting everything by an extra 4 spaces.

Example:
- Original in file: `    def method(self):` (4 spaces)
- Replacement text: `    def method(self):` (also 4 spaces in string)
- But search found `def method(self:` without those 4 spaces, so replacement inserted at position where a 4-space indent on def line should have been 4, became 8.

## Detection
1. Compile check fails with IndentationError on function def line (not body)
2. Inspect lines: `line.replace(' ', '·')` to visualize spaces
3. Compare with a known-good method's indentation

## Fix
**Option A: Dedent the entire function after patch**
```python
# Remove 4 spaces from each line of the replaced function
for i in range(func_start, func_end):
    if lines[i].startswith('        '):  # 8 spaces
        lines[i] = lines[i][4:]
```

**Option B: Ensure search pattern includes original whitespace**
```python
# If original def line has 4 spaces, search for exactly "    def name("
start_marker = "    def method_name(self"
start_idx = content.find(start_marker)
```
Then replacement text must also start with exactly 4 spaces on the def line.

**Option C: Use position-based replacement (safest)**
```python
# Find start index, find end index, slice and concatenate
new_content = content[:start_idx] + new_method_code + content[end_idx:]
```
No `str.replace()` ambiguity — direct string surgery.

## Prevention
- Always print `old_block[:100]` and its repr to verify exactly what you're matching
- After patch, run `python -m py_compile` immediately
- If error on def line, suspect indentation corruption
- Use the "Position-based replacement" pattern (Option C) instead of `replace()` when replacing blocks by content