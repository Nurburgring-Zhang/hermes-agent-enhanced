# Full-API Depth Test Protocol (30-item)

## When to Use

When the user demands "极细粒度的功能测试" / "所有功能逐项细粒度验证" after a round of bug fixes or feature additions. This protocol systematically exercises every API endpoint group with realistic parameter payloads, not just health check pings.

## The 30-Item Test Matrix

Organize into logical groups that correspond to the backend's API endpoint organization:

### Group 1: Core System (tests 1-3)
| # | Test | What it validates |
|---|------|------------------|
| 1 | GET /health | All subsystem status (DB/GPU/Nanobot/Queue/AIRI) |
| 2 | GET / | HTML template serving |
| 3 | GET/POST /api/config | Config read/write persistence |

### Group 2: Agent Cluster (tests 4-8)
| # | Test | What it validates |
|---|------|------------------|
| 4 | GET /api/agents | Agent count (33), provider diversity |
| 5 | POST/GET/PUT/DELETE /api/agents | Full CRUD lifecycle |
| 6 | GET /api/skills | Skill count (18), toggle enabled/disabled |
| 7 | GET /api/cluster/stats + /agents | Cluster state |
| 8 | POST /api/cluster/tasks + GET list | Task submission + query |

### Group 3: Asset System (test 9)
| # | Test | What it validates |
|---|------|------------------|
| 9 | POST/GET/LIST/DELETE /api/assets | Full CRUD with tags/metadata/quality scores |

### Group 4: Generation API (tests 10-17) — THE CRITICAL GROUP
Each test sends a different generation type with ITS SPECIFIC parameter set:

| # | Generator | Type | Key Parameters |
|---|-----------|------|----------------|
| 10 | comfyui | txt2img | width/height/steps/cfg/seed/sampler/scheduler/batch/model/clip_skip/style_preset/lora/controlnet/vae |
| 11 | kling | txt2vid | duration/fps/width/height/seed/cfg/camera_type/loop/motion_bucket |
| 12 | seedance | first-last-frame | first_frame/last_frame/duration/fps |
| 13 | comfyui | img2img | source_image/strength/edit_type |
| 14 | seedance | multi-ref video | reference_images[]/duration/fps |
| 15 | triposr | img2text | export_format/texture_resolution/remove_bg |
| 16 | runway | txt2vid (new provider) | duration/fps/resolution/style_preset/camera |
| 17 | pika | txt2vid (new provider) | duration/motion_intensity/camera |

Each generation test must return `{"task_id": "...", "status": "pending"}` — not an error.

### Group 5: Infinite Canvas (tests 18-26)
| # | Test | What it validates |
|---|------|------------------|
| 18 | POST /api/canvas/create | Canvas creation with ID |
| 19 | POST /api/canvas/gen-image | Positioned image generation |
| 20 | POST /api/canvas/outpaint | Canvas expansion (right direction) |
| 21 | POST /api/canvas/edit | Region editing |
| 22 | POST /api/canvas/drama | Story split into N distinct scenes |
| 23 | POST /api/canvas/picture-book | Story split into N distinct pages |
| 24 | POST /api/canvas/undo + redo | Undo/redo history stack |
| 25 | POST /api/canvas/export | Full composite export |
| 26 | GET /api/canvas/list | Canvas listing |

**Validation:** Test 22+23 must assert `len(scenes) == scene_count` and `len(pages) == page_count`, not just that the endpoint returns 200.

### Group 6: Database Management (tests 27)
| # | Test | What it validates |
|---|------|------------------|
| 27 | verify/cleanup/export | DB maintenance endpoints |

### Group 7: Digital Human (tests 28)
| # | Test | What it validates |
|---|------|------------------|
| 28 | status/animations/expressions | AIRI subsystem |

### Group 8: LLM & GPU (tests 29-30)
| # | Test | What it validates |
|---|------|------------------|
| 29 | providers/models/routing | 10+ providers, 35 models, 4 routing strategies |
| 30 | gpu/system/metrics | RTX 4090 stats, Prometheus metrics |

## Execution Pattern

Use `terminal()` with inline Python assertions, not separate curl+python calls:

```bash
curl -s http://localhost:8001/api/... | python3 -c "
import sys,json
d = json.load(sys.stdin)
assert d['status'] == 'healthy', f'Expected healthy, got {d}'
"
```

Pro tip: group multiple small tests into one terminal() call to reduce context overhead. Only separate when a test is expected to take significant time.

## Common Failure Patterns to Test For

| Pattern | What to send | Expected Response | Failure Signal |
|---------|-------------|------------------|----------------|
| Missing prompt | `{"prompt":""}` | 200 with error in body | ✗ crash/500 |
| Negative seed | `{"settings":{"seed":-1}}` | 200 with random seed | ✗ validation error |
| Wrong generator | `{"generator":"invalid"}` | 200 with error (falls back) | ✗ crash/500 |
| Oversized params | `{"width":8192}` | 200 (accepts, engine may clamp) | ✗ crash/500 |
| Empty settings | `{"prompt":"test","generator":"comfyui","settings":{}}` | 200 with defaults | ✗ crash/500 |
