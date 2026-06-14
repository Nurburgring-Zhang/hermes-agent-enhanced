# Inline HTML Sink — Debugging Pattern

## Problem

When HTML/CSS/JS is embedded in Python `r"""..."""` strings (like `HTML_TEMPLATE`), multiple sub-agent injections accumulate silent bugs that are invisible to Python's compiler:

1. **Bracket mismatch** — sub-agents delete `{` but leave `}`, causing JS parse failure
2. **`//` comments in object literals** — `const NT={...// comment\n...}` silently makes the entire script block unexecutable
3. **Stale function references** — `PAGE_RENDERERS` captures function refs at load time; later-redefined functions aren't picked up

## Debugging Workflow

### Step 1: Extract JS from HTML and check syntax
```bash
curl -s http://127.0.0.1:8765/ | python3 -c "
import sys, re
html = sys.stdin.read()
s = html.find('<script>') + len('<script>')
e = html.find('</script>')
js = html[s:e]
opens = js.count('{')
closes = js.count('}')
print(f'Brackets: {{{opens} }}={closes} diff={opens-closes}')
"
```

### Step 2: Use Node.js `--check` if available
```bash
node --check /tmp/extracted_js.js
```

### Step 3: Check browser console
```javascript
typeof switchTab  // undefined = script never executed
typeof execNode   // undefined = script never executed
```

### Step 4: Isolate the error
```javascript
// Find first parse error by chunking
const text = document.querySelector('script').textContent;
new Function(text); // catches the first syntax error
```

## Root Causes Found in the Wild

1. **`// 3D/布局` inside `const NT={...}`** — object literals do NOT accept `//` comments. Use `/* */` instead. This single line caused ALL JS to fail silently.

2. **Sed deleting Python file lines that cross HTML string boundaries** — `sed -i '1757,1803d'` on canvas_web.py deleted lines inside the `r"""..."""` string, destroying bracket pairing.

3. **`PAGE_RENDERERS` caching stale references** — Fix: navigate() must look up renderer functions from `window` dynamically, not from a frozen dictionary:
```javascript
let renderer = PAGE_RENDERERS[page];
if (!renderer || typeof renderer !== 'function') {
    renderer = window['render' + pageName];
}
```

## Rule: Never Patch Inline HTML Directly

Sub-agents modifying `HTML_TEMPLATE` r"""...""" strings will produce:
- Bracket mismatches
- Duplicate function definitions
- Orphaned `}` closing brackets
- Silent JS parse failures

**Solution**: Use independent frontend files under `frontend/` directory. Each page gets its own `.js` file. No shared mutable string.
