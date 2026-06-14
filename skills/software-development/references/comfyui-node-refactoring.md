# ComfyUI Node Refactoring Patterns

## The If/Elif/Else → Independent If Blocks Pattern

ComfyUI nodes often have `get_prompt` methods with deeply nested if/elif/else chains that create mutual exclusion between features. When users want all output ports to be independently executable, convert:

```python
# BEFORE: mutual exclusion
if 开启AI生成 or 故事板模式 != "关闭":
    if 故事板模式 != "关闭":
        # storyboard logic
        final_prompt = ai_result  # ❌ pollutes "提示词" port
    elif 开启AI生成:
        # AI gen logic
        final_prompt = ai_result
else:
    # prompt library logic (skipped if storyboard enabled)
    final_prompt = ...
```

To:

```python
# AFTER: independent if blocks
if 故事板模式 != "关闭":
    # storyboard logic — NO final_prompt assignment ✅
    storyboard_prompt = ...

if 开启AI生成:
    # AI gen logic — only for "提示词" port
    final_prompt = ai_result

if 文件夹路径:
    # prompt library — independent, not skipped
    final_prompt = ...
```

### Key rules:
1. Change `elif` → `if` to break mutual exclusion
2. Remove outer wrapper conditions (e.g. `if 开启AI生成 or 故事板模式 != "关闭"`)
3. Remove early `return` statements that would kill subsequent ports — use silent failure instead
4. Each port's output variable gets assigned independently; `final_prompt` belongs only to the "提示词" port

## Multi-Port Output Assembly

ComfyUI nodes with `RETURN_TYPES = ("STRING", "STRING", ...)` need each variable declared at function start:

```python
final_prompt = ""
negative_prompt = ""
storyboard_prompt = ""

# Each port gets assembled independently
if 输出绘本提示词:
    picture_book_prompt = header + ai_result

if 输出短剧提示词:
    short_drama_prompt = header + ai_result

return (
    final_prompt,          # port 0: 提示词
    picture_book_prompt,   # port 1: 绘本
    short_drama_prompt,    # port 2: 短剧
    storyboard_prompt,     # port 3: 故事
    negative_prompt,       # port 4: 负面
)
```

## System Prompt + Header Dual Maintenance

ComfyUI nodes that prepend a "总纲" (summary header) to AI output have TWO places that describe the output format:

1. **system prompt** — sent to AI as instruction (defines what AI should output)
2. **总纲/header** — prepended to output (describes what was generated)

Both must be updated in sync when dimensions change. Strategy:
- Change system prompt first (the AI will follow new format)
- Change header to match (describes the new format)
- Verify no "orphan" dimension references

## AST Return Audit for ComfyUI Nodes

After refactoring, audit all return paths in `get_prompt` to ensure every `return` produces a 5-element tuple:

```python
import ast

with open(path, 'r') as f:
    tree = ast.parse(f.read())

for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and n.name == 'get_prompt':
        returns = [s for s in ast.walk(n) 
                   if isinstance(s, ast.Return) and s.value is not None]
        for r in returns:
            if isinstance(r.value, ast.Tuple):
                n_elts = len(r.value.elts)
                assert n_elts == 5, f"Line {r.lineno}: {n_elts} elements"
```

## f-string in system prompts

When building system prompts that span multiple f-string lines:

```python
# Use implicit string concatenation with f-prefix on each line
sys_prompt = (
    f"line one {variable}\n"
    f"line two {other_var}\n"
)
```

No `\n` escapes between strings — just close/open quotes. Put `\n` inside each string to avoid indentation issues with the linter.

## Silent Failure Pattern

When one port's API call fails, it should NOT `return` early (killing all ports). Instead:

```python
if 故事板模式 != "关闭":
    if not API地址:
        storyboard_prompt = ""  # silent skip
        # NO return here — other ports continue
    ai_result = self._call_ai(...)
    if ai_result:
        storyboard_prompt = sb_header + ai_result
    else:
        storyboard_prompt = ""  # silent failure
```
