# Model Prompt Format Specifications — V17.0 Update (2026-05-22)

## Source: ComfyUI Blueprints + HuggingFace Model Cards + GitHub Research

### 1. Z-Image-Turbo / Z-Image-Base (ByteDance)

**Text Encoder:** Qwen3 4B  
**Blueprints:** `blueprints/Text to Image (Z-Image-Turbo).json`, `Text to Image (Z-Image-Base).json`

**Format Rules:**
- **Chinese support:** ✅ YES — Qwen3 4B is a Chinese-native LLM. Removing Chinese DEGRADES quality.
- **SD ()/[] syntax:** NOT supported — Qwen treats `((word))` as literal characters, not weight modifiers
- **Quality prefixes (masterpiece, best quality):** NOT needed — these are SD/CLIP-era patterns. Qwen architecture doesn't interpret them as quality signals.
- **Recommended:** Natural language descriptions, comma-separated elements
- **Length limit:** ~512-1024 tokens (Qwen architecture max)

**Community practice:** Z-Image users write prompts in natural English or Chinese, with quality emerging from the model's training, not from prompt incantations.

**Testing:**
```python
# Z image must preserve Chinese
assert any('\u4e00' <= c <= '\u9fff' for c in result)
# NO SD quality prefix
assert not result.startswith(("masterpiece", "best quality"))
# SD bracket syntax removed
assert "((" not in result and "[[" not in result
```

### 2. Qwen-Image (Alibaba / 通义千问)

**Text Encoder:** 通义千问 (Qwen architecture)  
**Blueprints:** `Text to Image (Qwen-Image).json`, `Text to Image (Qwen-Image 2512).json`, `Image Outpainting (Qwen-Image).json`, `Image to Layers (Qwen-Image-Layered).json`

**Format Rules:**
- **Chinese support:** ✅ YES — primary language
- **SD ()/[] syntax:** NOT supported — Qwen treats as literal chars
- **Quality prefixes:** NOT needed
- **Recommended:** Complete natural language paragraphs. Qwen can follow complex compositional instructions.
- **Length limit:** ~256-512 tokens

**Key insight:** Qwen-Image excels at following intricate natural language descriptions. A prompt like "一只橘猫蹲在窗台上，夕阳从窗外照进来，影子拉得很长，猫的毛在逆光中闪着金色光晕" works better than comma-separated keyword lists.

**Testing:**
```python
# Chinese preserved
assert any('\u4e00' <= c <= '\u9fff' for c in result)
# Bracket syntax removed
assert "((" not in result
```

### 3. Flux.2 Dev (Black Forest Labs)

**Text Encoder:** Mistral 3 Small  
**Blueprints:** `Text to Image (Flux.2 Dev).json` (48KB), `Image Edit (Flux.2 Dev).json` (53KB)

**Format Rules:**
- **Chinese support:** ❌ NO — Mistral 3 Small is English-centric. Chinese input degrades or creates gibberish.
- **SD ()/[] syntax:** NOT supported — Mistral treats as literal characters
- **Quality prefixes:** NOT needed — Flux's rectified flow transformer doesn't interpret "masterpiece" as a quality instruction
- **Recommended:** Concise English description, comma-separated
- **Length limit:** ~256 tokens (Mistral 3 Small context)
- **Special:** Supports reference images as optional inputs

**Testing:**
```python
# English only
assert all(ord(c) < 128 for c in result)
# No bracket syntax
assert "((" not in result and "[[" not in result
# No SD prefix added
assert not result.startswith(("masterpiece", "best quality"))
```

### 4. Flux.2 Klein 4B (Black Forest Labs)

**Text Encoder:** Mistral 3 Small (FP8, 4B parameters)  
**Blueprints:** `Image Edit (Flux.2 Klein 4B).json` (47KB) — only Image Edit variant found

**Format Rules:**
- **Same as Flux.2 Dev** with one extra constraint:
- **Prompt length:** More sensitive to long prompts. Keep under 150 words / ~200 tokens.
- **Optimized for image editing:** Uses "instruction" style prompts rather than pure descriptions

**Testing:**
```python
# Same as Flux 2 + length check
assert len(result.split()) <= 150
```

## Summary: What NOT to do

| Incorrect Pattern | Why It's Wrong | Correct Approach |
|------------------|----------------|------------------|
| Remove Chinese from Z-Image/Qwen | Their Qwen encoder is Chinese-native | Keep Chinese, only remove SD bracket syntax |
| Add "masterpiece, best quality" to Z-Image | Qwen treats as literal, not quality signal | Write natural language description |
| Add "cinematic shot" to Flux 2 | Mistral treats as literal, not quality signal | Write clear English description |
| Use SD ()/[] weighting on any of these 4 models | None of them use CLIP-based attention modulation | Natural language only |
| Generate "ugly, deformed" negative for Flux/Qwen | Their encoders don't interpret these | Minimal negative (blurry, watermark only) |
