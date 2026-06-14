---
name: comfyui
description: "Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for workflow execution."
version: 5.0.1
author: [kshitijk4poor, alt-glitch]
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli (auto-installed via pipx/uvx by the setup script)."
prerequisites:
  commands: ["python3"]
setup:
  help: "Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh auto-installs locally (or use Cloud API key for platform.comfy.org)."
metadata:
  hermes:
    tags:
      - comfyui
      - image-generation
      - stable-diffusion
      - flux
      - sd3
      - wan-video
      - hunyuan-video
      - creative
      - generative-ai
      - video-generation
    related_skills: [stable-diffusion-image-generation, image_gen]
    category: creative
---

# ComfyUI

Generate images, video, audio, and 3D content through ComfyUI using the
official `comfy-cli` for setup/lifecycle and direct REST/WebSocket API
for workflow execution.

## What's in this skill

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


**Reference docs (`references/`):**

- `unified-params-comfyui-mapping.md` — full 13-node end-to-end workflow builder from `UnifiedGenerationParams`: CheckpointLoader → LoRA chain → CLIPSkip → ControlNetApply → IPAdapter → KSampler → AnimateDiff → VAE → SaveImage/VHS. Covers seed/params/strength routing, conditioning chain topology, inpaint path, and video output. Produced by `backend/unified_params.py:params_to_comfyui()`.

- `official-cli.md` — every `comfy ...` command, with flags
- `rest-api.md` — REST + WebSocket endpoints (local + cloud), payload schemas
- `workflow-format.md` — API-format JSON, common node types, param mapping
- `comfyui-node-architecture-patterns.md` — custom node authoring: file-based prompt library architecture, multi-extension scanning, semantic filtering with safe-word exemption, filter categories (369 entries), weight syntax, **super-resolution node architecture (1119 lines, 9 algorithms, 9 attention mechanisms, tiled processing, image adjustments, 79 tests 100%)**, testing methodology, ComfyUI constraints (PromptLibraryNode PRO rewrite + FinalUltraFusion, 2026-05-18/19), **v7.3 efficiency optimizations** (Gaussian pyramid precompute, smooth-tile skip, overlap bounds fix, AuraSR integration)

**Scripts (`scripts/`):**

| Script | Purpose |
|--------|---------|
| `_common.py` | Shared HTTP, cloud routing, node catalogs (don't run directly) |
| `hardware_check.py` | Probe GPU/VRAM/disk → recommend local vs Comfy Cloud |
| `comfyui_setup.sh` | Hardware check + comfy-cli + ComfyUI install + launch + verify |
| `extract_schema.py` | Read a workflow → list controllable params + model deps |
| `check_deps.py` | Check workflow against running server → list missing nodes/models |
| `auto_fix_deps.py` | Run check_deps then `comfy node install` / `comfy model download` |
| `run_workflow.py` | Inject params, submit, monitor, download outputs (HTTP or WS) |
| `run_batch.py` | Submit a workflow N times with sweeps, parallel up to your tier |
| `ws_monitor.py` | Real-time WebSocket viewer for executing jobs (live progress) |
| `health_check.py` | Verification checklist runner — comfy-cli + server + models + smoke test |
| `fetch_logs.py` | Pull traceback / status messages for a given prompt_id |

**Example workflows (`workflows/`):** SD 1.5, SDXL, Flux Dev, SDXL img2img,
SDXL inpaint, ESRGAN upscale, AnimateDiff video, Wan T2V. See
`workflows/README.md`.

## When to Use

- User asks to generate images with Stable Diffusion, SDXL, Flux, SD3, etc.
- User wants to run a specific ComfyUI workflow file
- User wants to chain generative steps (txt2img → upscale → face restore)
- User needs ControlNet, inpainting, img2img, or other advanced pipelines
- User asks to manage ComfyUI queue, check models, or install custom nodes
- User asks to **develop/write/debug/modify a custom ComfyUI node** — load this skill and check `references/comfyui-node-architecture-patterns.md` for architecture patterns including:
  - File-based prompt library architecture (PromptLibraryNode PRO, 808 lines)
  - **Real-weight upscaling with Spandrel** — three-generation evolution (GenericUpscaler rejected, Real Architectures preferred, Spandrel autoloader recommended). Detail enhancement pipeline (FFT/USM/Adaptive/CLAHE/De-ring). Chinese-parameter naming constraints. CATEGORY discoverability.
  - Multi-extension scanning, semantic filtering with safe-word exemption
  - 9 attention mechanisms (CA/ECA/SA/WA/OCA/CAL/SAL/PA/NLA)
  - Tiled processing for large images, weight fusion for seam elimination
  - Filter categories (369 entries), weight syntax, testing methodology
  - **Subject Content Filter (V14)** (`references/comfyui-node-subject-filter-v14.md`)
  - **Children's content module architecture** (`references/comfyui-node-children-content-formats.md`) — 4 output formats (video1/video2/GIF/book) with structured system prompts, multi-port RETURN_TYPES, f-string construction patterns, age-group/style dispatch
  - **Chinese-system-prompt ComfyUI node patterns** (`references/comfyui-chinese-node-patterns.md`) — f-string colon pitfalls, RETURN_TYPES expansion across all return paths, dispatch pattern, optional section marking
  - **Ensemble Fusion v2→v3 evolution** — spatial adaptive fusion, Laplacian-of-Variance clarity maps, softmax spatial weighting, tiled fusion, 5 bug patterns, dilution trap, 44-test validation, **v7.3 efficiency: Gaussian pyramid precompute, smooth-tile skip via variance threshold, overlap bound fix, AuraSR unified post-processing**
  - ComfyUI constraints (NHWC format, NODE_CLASS_MAPPINGS, OUTPUT_NODE)
- User wants video/audio/3D generation via AnimateDiff, Hunyuan, Wan, AudioCraft, etc.

## 回滚方案
### 内容回退
1. 恢复到上一个版本的文件
2. 确认生成内容无退化
3. 必要时重启生成流程

### 恢复步骤
1. 从备份目录恢复原始文件
2. 验校内容完整性
3. 对比前后差异确认回退成功
