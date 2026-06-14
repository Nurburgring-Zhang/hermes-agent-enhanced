# Chinese-System-Prompt ComfyUI Node Patterns

## The Chinese Colon F-String Problem

When editing ComfyUI custom nodes that have Chinese parameter names/descriptions in Python string literals:

**Problem:** Full-width colon `：` (U+FF1A) inside escaped quotes within f-strings triggers Python parser errors:
```python
# BROKEN — lint error
f"...\"文字：\"..."
f"...\"对话：\"..."
```

**Fix:** Use bracket notation `【文字】` or keep the colon outside the quote boundary:
```python
# WORKS
f"...【文字】..."
f"...文字：{value}..."  # colon in string literal, not in quote
```

## RETURN_TYPES Expansion

When going from N to N+1 output ports, every return path must be updated:
1. `RETURN_TYPES` tuple in class definition
2. `RETURN_NAMES` tuple in class definition
3. Main `return (...)` in `get_prompt`
4. `_error_result()` method
5. All early-return error paths (storyboard failure, API failure, folder missing, etc.)

ComfyUI silently accepts wrong tuple lengths — missing ports render as empty strings with no error.

## Multi-method System Prompt Dispatch

For nodes with multiple output formats:
```python
def _build_child_system_prompt(self, mode, style, age):
    if mode == "format_a":
        return self._build_format_a_prompt(style_text, age_text)
    elif mode == "format_b":
        return self._build_format_b_prompt(style_text, age_text)
    
def _build_format_a_prompt(self, style_text, age_text):
    return (
        "# 角色设定\n"
        "..."
        "# 输出格式（严格遵循）\n"
        "..."
        "# 创作原则\n"
        "..."
        "请直接输出xxx内容，不要额外解释。"
    )
```

Each format method returns a complete system prompt with 4-6 sections: role, output format, principles, age guidance, style guidance, closing instruction.

## Optional Section Marking

Mark sections as `"(可选，不是每个xxx都有，需要时才有)"` in the system prompt. LLMs reliably respect this framing and omit sections when narrative context doesn't call for them.

## Backup Before Batch Edits

Chinese-parameter ComfyUI nodes grow 100-200 lines per development session. Always:
```bash
cp __init__.py __init__.py.bak.$(date +%Y%m%d_%H%M)
```
