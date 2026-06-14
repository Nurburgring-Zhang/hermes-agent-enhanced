# NanoBot Factory — Unified Parameters Implementation Reference

Session: 2026-06-06
Project: NanoBot Factory (FastAPI + React + Electron + 11 AI generation providers)

## Problem

The project had **3 independent generation systems** with incompatible parameter sets:

| System | Layer | Original Fields | After Fix |
|--------|-------|----------------|-----------|
| `server.py` POST /api/generate | API endpoint | 4 (prompt/negative/generator/settings) | 57 (full GenRequest) |
| `production_workbench.py` | Workbench service | 15 | 45 |
| `omni_gen.py` generate_image() | OmniGen engine | 7 | 32 |
| `unified_generation_service.py` | Unified service | 25 | 57 |
| `UnifiedGenerationParams` (new) | Superset model | — | **84** |

## The 4-Step Fix

### Step 1: Create unified_params.py (84 fields)

New file covering ALL generation/edit types with proper dataclasses:
- GenerationType enum (25 types: txt2img/img2img/video/edit/3d/canvas/drama/book)
- SamplerType (20 types), SchedulerType (9 types)
- ControlNetType (14 types), LoraType (5 types)
- FilterType (21 types), StylePreset (16 types)
- Sub-configs: LoraConfig, ControlNetConfig, CameraControl, MaskConfig, CanvasConfig, AnimationConfig, VideoEnhanceConfig

### Step 2: Write Provider conversion functions

```python
params_to_diffuser()    # → 31 diffuser_engine fields
params_to_comfyui()     # → 5+ node workflow JSON
params_to_kling()       # → 8 kling API fields
params_to_seedance()    # → 6 seedance API fields
params_to_unified_service()  # → unified service fields
```

### Step 3: Backfill each layer

In `server.py` POST /api/generate → extract ALL settings fields → build full GenRequest with auto-detection of generation type (text_to_image / text_to_video / image_to_video / first_last_frame / image_edit / text_to_3d).

### Step 4: Fix bugs found during wiring

1. **copy-vs-mutation** — `state.assets` returned copy, writes never persisted
2. **Body vs Query** — `payload: Dict[str, Any]` parsed as query param
3. **Missing import** — `Query` not imported, crash on startup
4. **Pydantic v2** — `skill.dict()` → `skill.model_dump()`

## Key Files Created/Modified

| File | Action | Significance |
|------|--------|-------------|
| `backend/unified_params.py` | **NEW** | 84-field superset model + 5 conversion functions |
| `backend/server.py` | MODIFIED | POST /api/generate maps 4→57 fields |
| `backend/unified_generation_service.py` | MODIFIED | GenerationRequest 25→57 fields |
| `backend/production_workbench.py` | MODIFIED | GenerationRequest 15→45 fields |
| `backend/omni_gen.py` | MODIFIED | 6 functions parameter-completed (7→32, 3→8, 3→9, 6→16, 8→21, 9→23) |

## Verification

```bash
# All 8 generation types accept full parameters
POST /api/generate (txt2img) → 84 params passed
POST /api/generate (txt2vid/Kling) → 15+ video params
POST /api/generate (first-last-frame/Seedance) → first_frame+last_frame
POST /api/generate (img2img) → source_image+strength
POST /api/generate (3d) → export_format+texture_resolution
POST /api/generate (multi-image-ref) → reference_images[]
```
