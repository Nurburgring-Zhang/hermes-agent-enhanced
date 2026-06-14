---
name: mass-syntax-fix
description: Systematically scan and fix syntax errors across large codebases — batch Python compilation checking, pattern-based error diagnosis, and targeted repair for patterns like double-shebang, docstring-inlined SQL, and mismatched brackets
---

# Mass Syntax Fix Workflow

Use this skill when you need to audit and fix syntax errors across hundreds of files, especially AI-generated codebases with structural fractures. For TypeScript/JavaScript projects, see `references/ai-code-salvage-ts.md`.

## Diagnosis Phase

## 触发条件
- 用户提及调试、修复、分析代码问题时
- 需要系统性排查复杂Bug时
- 执行架构分析或代码审核时


### 1. Batch Syntax Scan
```bash
# Count PASS vs FAIL across a directory
for f in /path/to/dir/*.py; do
  python3 -m py_compile "$f" 2>/dev/null && echo "OK: $(basename $f)" || echo "FAIL: $(basename $f)"
done

# Get summary counts
fails=0; for f in /path/to/dir/*.py; do
  python3 -m py_compile "$f" 2>/dev/null || ((fails++))
done; echo "$fails failures"
```

### 2. Get Detailed Error Messages
```bash
for f in /path/to/dir/*.py; do
  python3 -m py_compile "$f" 2>&1 | head -3
  echo "---"
done
```

### 3. Identify Common Patterns
```python
with open(file_path) as f:
    content = f.read()
# Triple-quote balance (must be EVEN)
print(f'Triple quotes: {content.count(chr(34)*3)}')  # Must be even!
# Known corruption patterns
for p in ['!/usr/bin/env python3"""', '!/usr/bin/env python3']:
    if p in content: print(f'FOUND: {p}')
```

## Common Corruption Patterns & Fixes

### Pattern 1: "Double Shebang" (most common)
Lines 1-3 are repeated with trailing `"""`:
```
#!/usr/bin/env python3
!/usr/bin/env python3"""
#!/usr/bin/env python3
"""
```
**Fix:** Remove lines 2-3 entirely → keep clean `#!/usr/bin/env python3` + `"""`

### Pattern 2: Docstring-Inlined SQL
A `class` docstring never closes, then raw SQL code is embedded inside it:
```python
@dataclass  
class ExecutionResult:
    中文工作流程描述文字
        conn = sqlite3.connect(...)
        conn.execute("""CREATE TABLE...""")
```
**Fix:** Close docstring at end of prose, then restructure as proper method body. If structure too broken, reconstruct using neighboring module patterns.

### Pattern 3: Parentheses Mismatch
`SyntaxError: closing parenthesis '}' does not match opening parenthesis '('`
**Fix:** Check bracket balance:
```bash
python3 -c "c=open('file.py').read(); print(f'{{:{c.count(chr(123))} }}:{c.count(chr(125))}')"
```

## Recovery After Accidental Overwrite
1. Check `__pycache__/*.pyc` for bytecode salvage
2. Check git/backup location for originals
3. Look at sibling modules in same directory for architectural patterns
4. Use `grep -n "class\|def \|^@"` on truncated file to see what's left
5. Rebuild using standard patterns from similar files

## Verification
```bash
errors=0
for f in /path/to/dir/*.py; do
  python3 -m py_compile "$f" 2>/dev/null || { echo "FAIL: $(basename $f)"; ((errors++)); }
done
echo "Total: $(ls /path/to/dir/*.py | wc -l) files, $errors failures"
```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
