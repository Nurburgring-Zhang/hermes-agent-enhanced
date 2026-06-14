# Python Try/Except Scoping Trap: Mock Class in Wrong Except Block

## The Pattern

When a file has multiple `try/except` blocks for importing optional dependencies, and the **second** block's `except` defines mock classes that the **first** block's failure needs...

## Symptom

```
File "omni_gen.py", line 498, in OmniGenState
    def get_engine(self) -> DiffuserEngine:
                        ^^^^^^^^^^^^^^
NameError: name 'DiffuserEngine' is not defined
```

The class `DiffuserEngine` does exist in the file — it's defined at line 165 inside `except ImportError` of the **video generator** import (block 2). But `OmniGenState` at line 270 references it, and when the **diffuser engine** import (block 1) fails while the **video generator** import (block 2) succeeds, the mock classes in block 2's except body are never executed.

## Root Cause

```python
# Block 1 - Diffuser Engine import
try:
    from .diffuser_engine import DiffuserEngine, ...  # FAILS
    DIFFUSER_ENGINE_AVAILABLE = True
except ImportError:
    logger.warning("not available")
    DIFFUSER_ENGINE_AVAILABLE = False
    # ⚠️ NO MOCK CLASSES HERE ← the bug

# Block 2 - Video Generator import  
try:
    from video_generation_backend import VideoGenerationBackend  # SUCCEEDS
    VIDEO_GENERATOR_AVAILABLE = True
except ImportError:
    VIDEO_GENERATOR_AVAILABLE = False
    
    # Mock classes are HERE — only runs if Block 2 fails
    class DiffuserEngine: ...   # Never defined if Block 2 succeeds
    class ModelType(Enum): ...
    class GenerationResult: ...
    
# Line 270 — uses DiffuserEngine
class OmniGenState:
    def get_engine(self) -> DiffuserEngine:  # NameError!
```

## The Fix

Move mock classes into the **same** except block that needs them:

```python
try:
    from .diffuser_engine import DiffuserEngine, ...
    DIFFUSER_ENGINE_AVAILABLE = True
except ImportError:
    logger.warning("not available, using mock mode")
    DIFFUSER_ENGINE_AVAILABLE = False
    
    # Mock classes HERE — always defined when the import fails
    class DiffuserEngine: ...
    class ModelType(Enum): ...
    class GenerationResult: ...
```

## Diagnosis Checklist

- [ ] Are there multiple `try/except` blocks in the same file for different imports?
- [ ] Are mock/fallback classes defined in an `except` block of a **different** import?
- [ ] Does the class that uses the mock reference come **after** both import blocks in the file?
- [ ] Check the execution path: what happens when Block 1 fails but Block 2 succeeds?

## Prevention

1. Mock classes should be in the **immediately following** except block of the failed import, not in a sibling or nested except.
2. Or define all mock/fallback classes unconditionally at module level before any import try/except, then the imports override them on success.
3. After fixing, clear stale `.pyc` caches — the old bytecode may mask the fix.

## Related

- See `python-pitfalls-v3-session.md` for other Python traps (silent except: pass, enum vs string comparison)
