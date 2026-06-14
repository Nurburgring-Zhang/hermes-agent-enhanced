# Large/Python File Reconstruction via Multi-Part + cat

When `write_file` truncates or corrupts a large Python file (>500 lines), use this proven recovery pattern.

## Success Pattern (used in V17.0 recovery, 1229 lines restored)

```bash
# 1. Save the corrupted file as backup
cp /path/to/corrupted.py /path/to/corrupted.py.broken

# 2. Do NOT use write_file for large patches — use terminal with heredoc
cat > /tmp/part1.py << 'PYEOF'
# ... complete code section ...
PYEOF

cat > /tmp/part2.py << 'PYEOF'
# ... next code section ...
PYEOF

# 3. Concatenate with preserved leading portion
head -500 /path/to/corrupted.py > /tmp/combined.py
cat /tmp/part1.py >> /tmp/combined.py
cat /tmp/part2.py >> /tmp/combined.py

# 4. Syntax check + import test
python3 -c "import ast; ast.parse(open('/tmp/combined.py').read()); print('SYNTAX OK')"
python3 -c "import sys; sys.path.insert(0,'/path/to/'); from module import Class; print(Class.RETURN_TYPES)"

# 5. Only then replace original
cp /tmp/combined.py /path/to/file.py
```

## Why write_file fails on large Python files

- `write_file` with `offset`/`limit` pagination creates a read-modify-write cycle that can drop the tail of the file
- When the file has been double-patched across multiple tools, concatenation metadata gets confused
- The file on disk may have line-number prefixes injected (`     1|import os`) from a previous bad write

## Recovery: strip line-number prefixes

```bash
python3 << 'PYEOF'
import re
with open("file.py", "r") as f:
    lines = f.readlines()
fixed = []
for line in lines:
    m = re.match(r'^\s*\d+\|(.*)$', line)
    if m: fixed.append(m.group(1))
    else: fixed.append(line)
with open("file.py", "w") as f:
    f.writelines(fixed)
PYEOF
```

## Verification checklist after reconstruction

1. `python3 -c "import ast; ast.parse(open('file.py').read())"` — AST syntax pass
2. `python3 -c "import sys; sys.path.insert(0,'.'); from module import Class"` — import pass
3. Count def statements match expected count
4. All return statements verified via AST (see `references/ast-return-audit.md`)
5. Run full test suite
