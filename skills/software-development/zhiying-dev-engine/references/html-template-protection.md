# HTML_TEMPLATE 保护与验证指南

## 问题场景

IMDF项目的前端代码存放在Python `r"""..."""` 字符串变量 `HTML_TEMPLATE` 中（约3万字，2800+行Python文件中的内联HTML/CSS/JS）。

多子Agent并发注入前端功能时，经常破坏代码。

## 常见破坏模式

### 1. 花括号不匹配
子Agent删除代码块时删了`{`但保留了`}`，导致JS解析器在遇到多余`}`时报语法错误，整个`<script>`块被丢弃。

**检测：**
```python
js.count('{') == js.count('}')
```

### 2. 对象字面量内的`//`注释
```javascript
const NT={
text:{...},
// 图片处理  ← 非法！
imgedit:{...},
};
```
`//`注释在对象字面量内是语法错误。必须用`/* ... */`。

### 3. 函数定义在script末尾被丢弃
如果script块在加载初期就抛异常（如`preReview`未定义），后面的所有`function`声明都不会被执行。

## 验证脚本

## Browser-side diagnosis

When the browser loads but no JS functions are defined (`typeof switchTab === 'undefined'` despite `function switchTab` in the script source):

```javascript
// 1. Check if the script source contains the function
document.querySelector('script').textContent.includes('function switchTab')

// 2. Find exact syntax error location 
const text = document.querySelector('script').textContent;
for(let i=0; i<text.length; i+=1000) {
  try { new Function(text.slice(0, i+1000)); }
  catch(e) { 
    console.log('Error near char', i+1000, e.message);
    const ctx = text.slice(Math.max(0,i-200), i+200);
    console.log('Context:', ctx);
    break; 
  }
}

// 3. Extract failing segment
// const segment = text.slice(start, start+200); // then look for syntax issues
```

## JS validation (Node.js vs Python)

Python's `compile(js, '<script>', 'exec')` is NOT reliable for JS validation. It false-positives on valid code like `/* 3D/布局 */` (block comments with non-ASCII characters).

Use `node --check` instead:

```bash
node --check /tmp/test.js && echo "JS OK" || echo "JS FAIL"
```

Without Node.js, the bracket check + comment scan + backtick count (must be even) is sufficient — real JS engines handle more syntax variations than Python's `compile()`.

## Verification script

```python
import re, sys

with open("api/canvas_web.py") as f:
    content = f.read()

match = re.search(r'HTML_TEMPLATE = r"""(.*?)"""', content, re.DOTALL)
if not match:
    print("HTML_TEMPLATE not found")
    sys.exit(1)

html = match.group(1)
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
if not scripts:
    print("No script tag in HTML_TEMPLATE")
    sys.exit(1)

js = scripts[0]

# 1. 括号匹配
errors = []
if js.count('{') != js.count('}'):
    errors.append(f"花括号: {js.count('{')}:{js.count('}')}")
if js.count('[') != js.count(']'):
    errors.append(f"中括号: {js.count('[')}:{js.count(']')}")
if js.count('(') != js.count(')'):
    errors.append(f"圆括号: {js.count('(')}:{js.count(')')}")

# 2. 对象字面量内的//注释
if 'const NT={' in js:
    nt_body = js.split('const NT={')[1].split('};')[0]
    for i, line in enumerate(nt_body.split('\n')):
        stripped = line.strip()
        if stripped.startswith('//'):
            errors.append(f"NT对象内//注释 行{i+1}: {stripped[:50]}")

# 3. 关键函数存在性
for fn in ['function switchTab', 'async function execNode', 'function addLog',
           'function _cv_api', 'function updateZoom']:
    if fn not in js:
        errors.append(f"缺失关键函数: {fn}")

if errors:
    print("❌ HTML_TEMPLATE 验证失败:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("✅ HTML_TEMPLATE 验证通过")
```

## 修复命令速查

```bash
# 修复对象字面量内的//注释
python3 -c "
with open('api/canvas_web.py') as f: lines = f.readlines()
in_nt = False
for i, line in enumerate(lines):
    if 'const NT={' in line: in_nt = True
    if in_nt and line.strip() == '};': break
    if in_nt and line.strip().startswith('//'):
        lines[i] = line.replace('//', '/*', 1).rstrip('\n') + ' */\n'
with open('api/canvas_web.py', 'w') as f: f.writelines(lines)
"

# 验证JS语法(需要Node.js)
node --check /tmp/nt_test.js
```
