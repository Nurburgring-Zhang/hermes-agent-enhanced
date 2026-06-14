# Subagent HTML Template Injection Pitfalls

## Why Subagents Break Inline HTML Templates

When multiple subagents inject JS code into a Python `r"""..."""` HTML template string (like IMDF's `HTML_TEMPLATE`), they routinely cause:

### 1. JS Object Literal `//` Comments
JS object literals (`const OBJ = {...}`) do NOT support `//` line comments. The `//` is parsed as value content, causing the next token to be misinterpreted (e.g., `3D` → `invalid decimal literal`).

**Fix:** Use `/* ... */` block comments inside object literals.

### 2. Bracket Mismatch from Line-Number Edits
Deleting Python source lines (via `sed '100,120d'`) that fall inside a `r"""..."""` string removes characters from the HTML output. If `{` and `}` counts diverge, the entire `<script>` block fails to parse.

**Fix:** Use Python string manipulation (find/replace within the HTML content), not line-number-based deletion.

### 3. Function Not in Global Scope
Subagents may inject `function fn(){}` inside `if{}`, `try{}`, `setTimeout(()=>{}, 0)` blocks. These functions are not hoisted to global scope, so `onclick="fn()"` in HTML can't find them.

**Fix:** Ensure all onclick-referenced functions are at `<script>` top level, outside any block.

### 4. Cascading Function Overwrites
Subagents overwrite existing functions (e.g., `execNode`) with enhanced versions that reference the original. After multiple overwrites, one layer references a function that was deleted in a later edit, breaking the chain.

**Fix:** Use new function names for enhancements, don't overwrite originals.

### 5. Cascading `let`/`const` Redeclaration  
When subagents reuse existing variable names (e.g., `const __origExec=execNode;` in a patched overwrite of `execNode`), the original `const` in the outer scope prevents re-declaration. `const` declarations also have no TDZ hoisting to `window`, so inline `onclick=` attributes can't reach them.

**Fix:** Use unique variable names per injection layer. Never reuse `__origExec`, `_orig`, or `_prev` as variable names across separate subagent injections.

### 6. False-Positive JS Validation — Python `compile()` vs Node.js  
Python's `compile(js, '<script>', 'exec')` is NOT a reliable JS validator. It fails on valid JS like `/* 3D/布局 */` (block comments with non-ASCII) and succeeds on invalid JS with bracket mismatches.

**Fix:** Use `node --check file.js` for JS syntax validation, or Python's `ast.parse()` from the `ast` module as a second-opinion check:
```bash
node --check /tmp/check.js && echo "JS OK" || echo "JS FAIL"
```

### 7. Bracket Rebalance Recovery  
When bracket mismatch is detected (`{` vs `}` count differs), isolate the excess brackets from the injection point:

```python
with open("file.py", "r") as f:
    lines = f.readlines()
# Delete isolated } on their own line near edit point
for i in range(len(lines)-1, -1, -1):
    if lines[i].strip() == '}':
        lines.pop(i)
        # Recheck
        new_content = ''.join(lines)
        if new_content.count('{') == new_content.count('}'):
            break
with open("file.py", "w") as f:
    f.writelines(lines)
```

### 8. Browser-Side Error Location  
To find the exact syntax error position in the browser's JS, use `new Function()` to compile progressively:
```javascript
const text = document.querySelector('script').textContent;
for(let i=0; i<text.length; i+=1000) {
  try { new Function(text.slice(0, i+1000)); }
  catch(e) { console.log('Error near char', i+1000, e.message); break; }
}
```
Then extract that segment with `text.slice(start-200, start+200)` to see the failing code.

## Detection Script

Run after any subagent modifies an HTML template:

```python
import re
with open('api/canvas_web.py') as f:
    content = f.read()
match = re.search(r'HTML_TEMPLATE = r\"\"\"(.*?)\"\"\"', content, re.DOTALL)
if match:
    html = match.group(1)
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    if scripts:
        js = scripts[0]
        opens = js.count('{')
        closes = js.count('}')
        print(f'Brackets: {opens}:{closes} {"OK" if opens==closes else "MISMATCH"}')
        
        # Check object literal comments (// inside {...} but not in strings)
        in_obj = False
        for line in js.split('\n'):
            stripped = line.strip()
            if stripped.startswith('//') and '{' in js.split(stripped)[0][-50:]:
                print(f'WARN: possible // comment inside object literal: {stripped}')
        
        # Check globals
        for fn in ['switchTab', 'execNode', 'addLog']:
            print(f'  {"OK" if fn in js else "MISSING"}: {fn}')
```
