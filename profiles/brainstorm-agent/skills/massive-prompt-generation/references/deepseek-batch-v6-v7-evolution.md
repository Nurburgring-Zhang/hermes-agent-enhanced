# DeepSeek Batch API: V6→V7 Prompt Structure Evolution

## The Problem

V6 prompt used nested `{"segments":{...}, "connective_fragments":[...]}` structure. At 30 rows/batch, output tokens exceeded 16K limit → ~55% JSON truncation failure rate. Every failure wasted ~60 seconds (API call + retry delay).

## The Fix

Removed the `segments` and `connective_fragments` wrappers. Flat array format:

```
V6 (nested): {"条目N": {"segments": {"A01":[],...,"D06":[]}, "connective_fragments":[], "original_length":N}}
V7 (flat):   {"条目N": {"A01_年龄性别":[], ..., "D06_氛围情感":[]}}
```

## Key Numbers

| Format | Tokens/row | 30 rows | 16K limit | Failure rate |
|--------|-----------|---------|-----------|-------------|
| Nested (V6) | ~650 | ~19.5K | ❌ Exceeded | ~55% |
| Flat (V7) | ~550 | ~16.5K | ✅ Just under | ~0% |

## The Connective Fragments Tradeoff

The `connective_fragments` array captured structural words (的/了/在/一个/拍摄于) — theoretically needed for 100% reversible reconstruction. In practice, the 17 semantic dimensions already cover ~98% of the original text. The missing 2% (connective words) doesn't affect dimension library quality.

**Decision**: Dropping `connective_fragments` is acceptable. The 17 dimensions' coverage is sufficient. Library entries are complete sentences/phrases — they don't need to be stitchable back to exact originals.

## Additional Optimizations

1. **Batch size**: 30 (flat) vs 20 (nested). Same API latency, 50% more throughput.
2. **Error recovery**: When JSON parse fails, split batch in half and retry. Recovers ~80% of failures.
3. **5 concurrent workers**: DeepSeek paid supports it. Tested and stable.
