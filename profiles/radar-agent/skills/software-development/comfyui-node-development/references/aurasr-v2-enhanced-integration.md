# AuraSR v2 Enhanced Integration — UltraUltimateUpscale V7.1

## Architecture (4 files, ~2183 lines total)

```
UltraUltimateUpscale/
├── __init__.py                    (1210 lines) — main node, 5 quality modes
├── uau_module1_loader.py          (242 lines)  — overlap tiling + dual-pass fusion + gaussian/checkerboard
├── uau_module2_compensation.py    (290 lines)  — dark/highlight compensation + frequency + wavelet + denoise
├── uau_module3_detail_preserve.py (182 lines)  — HAT/DRCT pre-detail + 3-zone injection + strategy analysis
└── uau_module4_node.py            (259 lines)  — EnhancedAuraSR engine (replaces original tile method)
```

## Original AuraSR Defects

### Defect 1: Non-overlapping Tiles
`tile_image(image, chunk_size)` cuts tiles with ZERO overlap. Each tile starts exactly at `i * chunk_size`. Tile edges have no context from neighboring regions.

**Fix:** `tile_image_overlapped(image_tensor, chunk_size, overlap=16)` — stride = chunk_size - overlap, ensuring adjacent tiles share `overlap` pixels of context.

### Defect 2: Weak Dual-Pass Fusion
`upscale_4x_overlapped` runs two passes (original + offset) then blends with a simple checkerboard weight. The checkerboard uses sigma=0.5, then applies `**8` power saturation, making the transition zone too narrow (~10% of tile).

**Fix 3-way:**
- `dual_pass_fusion` with `gaussian` mode — smoother sigma, proper checkboard weight distribution
- `dual_pass_fusion` with `laplacian` mode — multi-frequency band blending (energy-aware per-band weighting)
- `dual_pass_fusion` with `constant` mode — simple average (baseline)

### Defect 3: Dark/Highlight Texture Loss
GAN generators learn to produce "clean" outputs by suppressing low-amplitude texture in dark and bright regions. This is a GAN hallucination artifact — not noise, but real texture that gets treated as "imperfection" and smoothed away.

**Fix cascade (5 stages):**
1. dark_highlight_compensation() — threshold-based mask extraction (dark < 60, bright > 200), then local contrast stretching in dark regions + laplacian texture injection in bright regions
2. frequency_compensation() — multi-scale bandpass: (blur1 - blur2) * 0.7 + (blur2 - blur4) * 0.3, adaptive gain based on local std
3. wavelet_texture_boost() — Haar 2D decomposition, boost LH/HL/HH subbands independently, inverse Haar reconstruction. Energy-adaptive gain: weaker texture subbands get more boost
4. adaptive_noise_reduction() — detects over-sharp regions via high-pass energy / local std ratio, applies selective Gaussian blur only where ratio exceeds threshold
5. Pipeline order: dark/highlight -> frequency -> wavelet -> denoise

## New in V7.1 (Round 2-5 Upgrades)

### Wavelet Domain Enhancement
Inspired by SUPIR's wavelet_reconstruction concept. Uses forward/inverse Haar 2D transform. Enhancement: compute energy (std) of each subband. Lower-energy subbands get more boost. This prevents over-amplifying already-noisy high-frequency bands.

### Edge-Aware Gaussian Weights for Tile Merging
Distribute the Gaussian kernel sigma based on tile position relative to image center: edge tiles get sharper falloff (sigma_factor up to 1.3x). Sine edge fade on weights for extra smoothness at overlap boundaries.

### 3-Zone Detail Injection
Classify each pixel into flat zone (strong injection), normal texture zone (moderate), or edge zone (weak/no injection to prevent artifacts). Flat zone weight = 1 - local_std/0.12, edge protect = 1 - edge_smooth/0.08, combined by multiplication.

### Multi-Dimension Image Analysis (v2)
Added texture_richness to strategy dict — computed via high-frequency energy ratio after Lanczos downscale/resize cycle. Higher richness -> less frequency compensation needed.

## ComfyUI Integration

### Quality Mode Entry
"优化版AuraSR放大" added as 5th quality mode in the dropdown list.

### Fallback Chain (3 levels)
1. Import uau_module4_node -> if ImportError, fall through to regular path
2. run_enhanced_aurasr() returns None -> fallback to single model
3. No models loaded -> Lanczos resize

### Model Info String
Normal: "优化版AuraSR" or "优化版AuraSR+前置细节" if HAT/DRCT model active. Fallback: "回退单模型"

## Known Issues
1. Laplacian blend: use interpolate mode='area' at fixed 1/4 reduction instead of avg_pool2d to avoid size mismatch
2. Import ordering: ImageFilter import must be inside functions, not at module level
3. Test scripts frequently misspell aurasr_compensation_pipeline as auasr (missing one 'r')

## Comparison vs Original AuraSR
- Tile overlap: none -> 32px overlap with gaussian fusion
- Tile fusion: hard stitch / checkerboard avg -> dual-pass offset + optional laplacian
- Dark detail: lost -> wavelet recovery + local contrast stretch
- Bright detail: lost -> laplacian texture injection
- Pre-detail: none -> HAT/DRCT 3-zone adaptive injection
- Over-sharpening: visible -> adaptive noise reduction
- Adaptive tuning: none -> auto-analyze input
- Fallback: crash -> 3-level fallback chain
