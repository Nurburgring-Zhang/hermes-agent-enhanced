# Unified Params → ComfyUI Workflow Mapping

Generated from `backend/unified_params.py:params_to_comfyui()` — the canonical
translation from the project's unified generation parameter model (84 fields)
into a complete ComfyUI API-format workflow prompt.

## Node Topology (13 node types, auto-numbered)

```
CLIPTextEncode(+) ──┐
CLIPTextEncode(-) ──┤
                     │
CheckpointLoader ────┼──[LoRA Loader chain]──[CLIPSetLastLayer]──┐
                     │                                            │
VAELoader (optional) │                                            │
                     │                                            ▼
              ControlNetLoader ── ControlNetApply ──► conditioning(+)
              IPAdapterApply (if ip_adapter/revision)            │
                                                                ▼
EmptyLatentImage / EmptyLatentVideo / VAEEncode (img2img) ──► KSampler
                                                                │
                                              AnimateDiffLoader (if video)
                                                                │
                                                          VAEDecode ──► SaveImage
                                                                      └── VHS_VideoCombine (if video)
```

## Parameter Mapping Table

| Unified Param | ComfyUI Node | ComfyUI Input |
|---------------|-------------|---------------|
| `prompt` | CLIPTextEncode(1) | `text` |
| `negative_prompt` | CLIPTextEncode(2) | `text` |
| `model` | CheckpointLoaderSimple(3) | `ckpt_name` |
| `vae` | VAELoader(4) | `vae_name` |
| `loras[].model` | LoraLoader(N+) | `lora_name` |
| `loras[].weight` | LoraLoader(N+) | `strength_model` |
| `loras[].clip_weight` | LoraLoader(N+) | `strength_clip` |
| `clip_skip` | CLIPSetLastLayer(N+) | `stop_at_clip_layer` |
| `controlnet[].type` | ControlNetLoader(N+) | `control_net_name` (appends `.safetensors`) |
| `controlnet[].weight` | ControlNetApply(N+) | `strength` |
| `controlnet[].guidance_start/end` | ControlNetApply(N+) | `start_percent`, `end_percent` |
| `width`, `height` | EmptyLatentImage/Video | `width`, `height` |
| `batch_count` | EmptyLatentImage | `batch_size` |
| `video_frames` | EmptyLatentVideo | `batch_size`, `length` |
| `fps` | VHS_VideoCombine | `frame_rate` |
| `loop` | VHS_VideoCombine | `loop_count` (0=loop, 1=once) |
| `seed` | KSampler | `seed` |
| `steps` | KSampler | `steps` |
| `cfg_scale` | KSampler | `cfg` |
| `sampler` | KSampler | `sampler_name` |
| `scheduler` | KSampler | `scheduler` |
| `strength` | KSampler | `denoise` |
| `source_image`/`input_images[0]` | LoadImage → VAEEncode | `image` → replaces EmptyLatentImage |
| `mask.image` | LoadImage → SetLatentNoiseMask | `mask` on latent |
| `animation.motion_module` | AnimateDiffLoaderWithContext | `motion_module` |
| `animation.motion_scale` | AnimateDiffLoaderWithContext | `motion_scale` |
| `animation.context_length` | AnimateDiffLoaderWithContext | `context_length` |
| `animation.context_stride` | AnimateDiffLoaderWithContext | `context_stride` |
| `animation.context_overlap` | AnimateDiffLoaderWithContext | `context_overlap` |
| `animation.closed_loop` | AnimateDiffLoaderWithContext | `closed_loop` |
| `animation.beta_schedule` | AnimateDiffLoaderWithContext | `beta_schedule` |

## Key Design Decisions

1. **Auto-numbered nodes**: Uses an incrementing counter (`nid()`) instead of
   hardcoded IDs, so LoRA/ControlNet count doesn't collide with fixed node numbers.
   The `lora_chain_model` / `lora_chain_clip` variables track the chain tail.

2. **Conditioning routing**: Positive conditioning passes through ControlNetApply
   nodes; negative conditioning goes direct from CLIPTextEncode (or after CLIPSkip).
   When ControlNets are present, the positive cond is the last ControlNetApply output;
   negative cond stays clean.

3. **Batch >1 + video**: EmptyLatentImage handles `batch_size` for multi-image generation;
   EmptyLatentVideo handles both `batch_size` and `length` for video frame count.
   The batch_size parameter in EmptyLatentVideo controls parallel frame generation.

4. **Inpaint path**: LoadImage → VAEEncode (with VAE from VAELoader) → SetLatentNoiseMask
   replaces EmptyLatentImage. The mask comes from a separate LoadImage node.

5. **Video output**: Only added when `video_frames > 1` — uses VHS_VideoCombine with
   h264-mp4 format. The `loop` parameter maps to `loop_count` (0 = infinite loop).

## Using with comfy-cli

```python
# In run_workflow.py or similar:
from unified_params import UnifiedGenerationParams, params_to_comfyui

p = UnifiedGenerationParams(
    prompt="a cat",
    model="sd_xl_base_1.0.safetensors",
    width=1024, height=1024, steps=30, cfg_scale=7.5, seed=42,
    loras=[LoraConfig(model="detail_slider.safetensors", weight=0.8)],
    controlnet=[ControlNetConfig(type="canny", weight=0.5)]
)
workflow = params_to_comfyui(p)
# POST workflow['prompt'] to http://127.0.0.1:8188/prompt
```
