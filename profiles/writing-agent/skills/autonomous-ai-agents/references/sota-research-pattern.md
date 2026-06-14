# SOTA Research-Then-Implement Pattern for Code Improvement

## When to Use

User says: "Research the latest SOTA in [domain] and integrate it into this [existing codebase/node]."

## Flow

### Step 1: Research (Exhaustive)

Try in order until one succeeds:

1. **Browser directly**: navigate to PapersWithCode or specific arXiv search
2. **`delegate_task` with `toolsets=["browser", "terminal", "web"]`**: pass the research goal in `context` and `goal` params. The sub-agent gets multiple attempts and retries with different tools.
3. **Fallback to knowledge**: if no tool works, use your existing knowledge but clearly label which data is verified vs estimated

**What to collect per model:**
- Model name, architecture type, paper year
- PSNR/SSIM on standard benchmarks (Set5, Urban100, Manga109)
- Parameter count and inference speed
- Where to download pretrained weights (GitHub Release, HuggingFace)
- Whether existing ComfyUI infrastructure can load it

### Step 2: Prioritize

From the research, pick **3-5 concrete improvements** ordered by impact:

1. **Architecture upgrade** (e.g., generic wrapper → real HAT/SwinIR/DAT) — highest impact
2. **Processing pipeline** (e.g., tiling with sinusoidal blend instead of linear)
3. **Post-processing** (e.g., FFT sharpen, adaptive sharpen, deringing)
4. **Ensemble methods** (e.g., self-ensemble via flip/rotate)
5. **Content-adaptive strategies** (e.g., anime vs. photo detection → different model)

### Step 3: Implement in Priority Order

Each improvement must:
- Be **fully implemented** (no stubs, no "core only")
- Be **tested immediately** before moving to the next
- Preserve backward compatibility with the existing interface

### Pitfalls

- **Don't try to implement all findings from research.** Pick 2-3 that directly address the user's complaint.
- **Don't skip research if browser fails once.** delegate_task with multi-tool fallback often succeeds where direct browser calls don't.
- **Don't include model architectures you cannot actually load.** Real weights must exist at a downloadable URL.
- **Don't promise performance numbers you can't verify.** State "based on the paper's reported metrics" not "our model achieves X dB".

## Real Architecture vs Generic Wrapper

When loading pretrained weights, prefer **real architecture definitions** (class SwinIRModel with nn.Module layers) over generic wrappers that try to brute-force conv2d layers from arbitrary state_dicts.

| Approach | Pros | Cons |
|----------|------|------|
| Generic wrapper (conv2d loop matching) | Works with any .pth | ~50% weight utilization, can't use actual attention |
| Real architecture + `load_state_dict(strict=False)` | Full weight utilization, correct attention | Must define each architecture class |

**Fallback**: If you can't determine the architecture type, try loading as HAT first, then SwinIR, then RRDB — HAT's attention pattern is most general.

## File Structure for SOTA Nodes

```
node_name/
├── __init__.py          # ComfyUI node class + all logic (load, process, output)
├── download_models.py   # Pretrained weight downloader (optional, standalone)
├── install.py           # One-click install (optional)
├── requirements.txt     # Dependencies
└── models/              # Local model storage fallback
```
