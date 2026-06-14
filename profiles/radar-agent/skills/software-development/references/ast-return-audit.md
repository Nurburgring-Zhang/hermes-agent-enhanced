# AST-Based Return Validation for ComfyUI Nodes

When refactoring ComfyUI nodes that change `RETURN_TYPES`/`RETURN_NAMES` (e.g. adding new output ports), every `return` statement in the class must return the same number of values. Missing even one causes silent runtime errors.

## The Problem: Simple comma-counting fails

Trying to count commas at depth=1 to infer tuple element count gives **false positives** on string literals that contain commas:

```python
json.dumps({"error": "storyboard_failed", "detail": detail}, ensure_ascii=False)
#    ↑      ↑                                   ↑           ↑
# Internal commas fool naive scanners
```

## The Fix: AST-based precise analysis

```python
import ast, sys

with open("/path/to/node.py", "r") as f:
    code = f.read()

tree = ast.parse(code)

# Find the class
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and 'NodePro' in node.name:
        target = node
        break

# Check every Return inside get_prompt  
for node in ast.iter_child_nodes(target):
    if isinstance(node, ast.FunctionDef) and node.name == 'get_prompt':
        for r in ast.walk(node):
            if isinstance(r, ast.Return) and isinstance(r.value, ast.Tuple):
                n = len(r.value.elts)
                if n != EXPECTED_VALUES:
                    print(f"❌ L{r.lineno}: {n} values (expected {EXPECTED_VALUES})")
```

AST only counts Tuple.elts — the actual first-level elements — so string-internal commas are never miscounted.

## Pitfalls

- **`_error_result` helper**: If a helper method returns a partial tuple, it will pass AST check on itself but fail at the caller. Check ALL methods.
- **Conditional early exits**: Storyboard failure, AI generation failure, empty folder — every early `return` must match the new tuple shape.
- **Subclass overrides**: If the node is subclassed with overridden `get_prompt`, check that too.
