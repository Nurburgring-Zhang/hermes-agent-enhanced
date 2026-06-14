# LLM-Generated Code Bug: Object Method Confusion

## Pattern

LLMs sometimes write `.method()` calls on primitive types as if they were objects with methods.

**Wrong:**
```python
return (1 - (t * 3.14159 / 2).cos())
```

**Correct:**
```python
import math
return (1 - math.cos(t * 3.14159 / 2))
```

## Why It Happens

Python `float` has no `.cos()` method. In numpy, `np.cos(array)` works, and numpy arrays have methods like `.mean()`, `.sum()`. LLMs sometimes conflate `math.cos(t)` with `t.cos()`.

## Detection

Search for these patterns in any Python codebase:
- `).cos(` / `).sin(` / `).tan(` — the dot after a parenthesized expression
- `).sqrt(` / `).exp(` / `).log(` — any math function called as a method
- `.cos()` / `.sin()` called on a variable that is a plain Python float (not np.ndarray)

```bash
# Find all occurrences
grep -rn ').cos\|).sin\|).tan\|).sqrt\|).exp\|).log' backend/ --include="*.py"
```

## Real-World Instance

**File:** `backend/airi_digital_human.py` line 873 (2026-06-06)
```python
# Before (BUG):
return (1 - (t * 3.14159 / 2).cos()) if t < 0.5 else (1 + (t * 3.14159 / 2 - 3.14159 / 2).cos())

# After (FIX):
import math
return (1 - math.cos(t * 3.14159 / 2)) if t < 0.5 else (1 + math.cos(t * 3.14159 / 2 - 3.14159 / 2))
```

## Prevention

When reviewing AI-generated math code:
1. Search for `.cos(`, `.sin(`, `.sqrt(` called on anything that's not a numpy array
2. If the function uses `import math` at the top, look for places that DON'T use `math.` prefix
3. When in doubt, use `math.*` functions — they are always correct for float operations
