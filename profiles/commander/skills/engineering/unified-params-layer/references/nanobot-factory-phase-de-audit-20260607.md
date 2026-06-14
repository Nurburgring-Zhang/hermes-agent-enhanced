# NanoBot Factory — Phase D+E Session Reference (2026-06-07)

## Overview

Continued development on NanoBot Factory, adding Runway/Pika Providers + Infinite Canvas Engine + Frontend CanvasEditor. Full audit found 7 P0-P2 bugs. All fixed.

## New Bug Patterns Found & Fixed

### Bug #5: RateLimiter Double Definition (P0)
`server.py` had TWO `class RateLimiter` definitions (~lines 40 and 441) with incompatible constructors. First also included dead RedisRateLimiter + zombie middleware.
**Fix:** Remove first definition entirely (237 lines).

### Bug #6: Provider Recognition Missing (P0)
`generate_content_async` had `has_video` tuple missing `"hunyuan"`, `is_3d` tuple missing `"hunyuan"`. Caused misclassification of video/3D requests.
**Fix:** Add `"hunyuan"` to both tuples.

### Bug #7: Story Scene Splitting (P1)
`_split_story_into_scenes` used Chinese-only punctuation regex, breaking on English prompts. Single long sentences produced identical scenes.
**Fix:** 3-level cascade: punctuation → word-split → char-equal.

### Bug #8: Frontend-Backend Provider Mismatch (P0)
Frontend `UnifiedParamsPanel` listed 10 providers; backend had 11; only 6 overlapped. Selected providers would silently fail.
**Fix:** Update frontend list to 15 entries matching all backend providers.

### Bug #9: CanvasGenRequest.prompt Required Field (P1)
`prompt: str` (no default) caused 422 when short drama/book endpoints received `story_prompt` without `prompt`.
**Fix:** `prompt: str = ""`, routes use `request.story_prompt or request.prompt`.

## Provider Integration Pattern

When adding to `unified_generation_service.py`:

```python
class NewProvider(BaseProvider):
    "Documentation"
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.example.com/v1"
        self.api_key = config.api_key or os.getenv("NEW_API_KEY", "")

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.validate_request(request):
            return GenerationResult(..., status="failed")
        if not self.api_key:
            return GenerationResult(..., status="failed", error="KEY not configured")
        payload = {"prompt": request.prompt, "duration": request.duration, ...}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    return GenerationResult(status="processing", ...)
                return GenerationResult(status="failed", error=f"API error {resp.status}")

    async def get_status(self, task_id: str) -> GenerationResult: ...
    async def cancel(self, task_id: str) -> bool: ...

# Register:
_unified_service.register_provider(NewProvider(ProviderConfig(
    provider="newprovider", enabled=True, models=["v1"], default_model="v1"
)))
```

Then update:
1. Frontend `PROVIDERS` list in `UnifiedParamsPanel.tsx`
2. `has_video` / `is_3d` tuples in `generate_content_async`
3. API docs

## Infinite Canvas Engine Summary

### Backend
- `backend/infinite_canvas_engine.py` — CanvasEngine class with 8 operations
- 8 API routes under `/api/canvas/*`
- CanvasState: layer stack + undo/redo (50-step history)

### Frontend
- `CanvasEditor.tsx` — Canvas area + toolbar (7 tools) + layer panel
- `UnifiedParamsPanel.tsx` — 12 sections, 72+ params
- `CanvasStudio.tsx` — Integration with 3 modes (canvas/drama/book)
- Route: `/canvas`, sidebar: 创作工具 → 画布工作室

### Key Design Decisions
- base64 image data in layers (enables instant undo without server roundtrip)
- Gradient alpha mask for seam blending (lighter than ML-based)
- 3-level scene splitting (punctuation → word → char)
- Grid layout for dramas, vertical stack for picture books
