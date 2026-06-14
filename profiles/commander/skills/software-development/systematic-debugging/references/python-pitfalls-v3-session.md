# Python Pitfalls Found in Hermes Self-Enhancement V3 Session

## 1. Enum vs String Comparison

`DriftLevel.MILD == 'mild'` returns **False**. Python enums compare by identity, not value.

```python
# WRONG - never matches
if drift_level in ['severe', 'moderate', 'mild']:  # drift_level is a DriftLevel enum

# RIGHT - use .value
if drift_level.value in ['severe', 'moderate', 'mild']:

# RIGHT - convert to string first
if str(drift_level) in ['severe', 'moderate', 'mild']:
```

**When to suspect:** Conditional logic that looks correct but never triggers. The values are enums but the comparison uses strings.

## 2. Silent `except Exception: pass` Masks Real Bugs

5 instances found in one codebase session. One masked a missing variable initialization (`experiences = []`) that caused ALL 5+ step tasks to silently fail.

```python
# DANGEROUS - masks every bug
try:
    dangerous_operation()
except Exception:
    pass

# SAFE - records errors without blocking
try:
    dangerous_operation()
except Exception as e:
    metadata.setdefault('errors', []).append(str(e)[:100])
```

**Rule:** Every `except` that doesn't log or propagate is a defect waiting to happen.

## 3. Truncated Context in Diagnostic Functions

Passing only a step name as the "context" parameter (instead of goal + step name) caused drift detection to always detect "severe drift" on step 0 of every multi-step task.

```python
# WRONG - only step name
drift = detect_drift(goal, current_step)  # goal="重构JWT", step="需求分析" -> severe drift

# RIGHT - full context
drift_context = f"{goal} 当前步骤: {current_step}"
drift = detect_drift(goal, drift_context)  # "重构JWT 当前步骤: 需求分析" -> ok
```

**When to suspect:** A diagnostic function consistently returns negative/wrong results, and its "context" parameter is a single short field.

## 4. Missing Variable Initialization After Patch

A patch to `extract_step_experience()` accidentally deleted the `experiences = []` line. Every subsequent call threw `NameError`, caught by `except Exception: pass`. The symptom was "task.execute_plan returns 0 steps" — not a crash.

**Prevention:** After ANY patch, check that all local variables referenced in the function are still initialized. Run the function in its full calling context.
