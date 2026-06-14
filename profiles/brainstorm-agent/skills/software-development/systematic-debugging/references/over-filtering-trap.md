# Over-Filtering Root Cause — Common Mistakes

## The Trap

When debugging "items missing from a dataset", the instinct is to suspect:
1. The random/selection logic is broken
2. The loop has a dead zone or index bug
3. The pool/shuffle isn't working

**In reality, the most common cause is a filter that's too aggressive.**

## Questions to Ask Immediately

Before investigating any random/loop logic:

1. **What filters exist between the raw data and the output?**
   - Keyword filters
   - Blacklist filters (category, content, length)
   - Tag filters
   - History/dedup filters
   - Any "skip if" conditions

2. **Can I run without filters to get a baseline count?**
   - If filtered = 50 and unfiltered = 500, the filter is the problem
   - Do this BEFORE touching any selection logic

3. **What words are in the blacklist?**
   - Are there common neutral words like `chair`, `table`, `window`, `door`, `cup`?
   - Are there single-letter words like `a` that would match everything?
   - Are there substring matches that would catch unintended content?

4. **Does the filter check context?**
   - A prompt saying "a woman sitting on a chair in a garden" should not be filtered for "chair"
   - Check if the filter has "safe context" words (person, animal, landscape) that bypass blocking

## The Fix Pattern

```python
# BAD: filter first, no context check
for keyword in BLACKLIST:
    if keyword in text_lower:
        is_blocked = True  # too aggressive

# FIXED: context-aware
HAS_SAFE_CONTEXT = any(safe_word in text_lower for safe_word in SAFE_CONTEXT_WORDS)

for keyword in BLACKLIST:
    if keyword in text_lower:
        if HAS_SAFE_CONTEXT:
            continue  # don't block if context is appropriate
        is_blocked = True
```

## Metrics to Collect

When investigating missing items, always log:
- Raw count (before any filter)
- Per-stage pass/block counts
- Top-10 blocking keywords (what's catching the most items)
- A sample of blocked items (to verify they should be blocked)
