# Deep API Functional Test Template

Use this for thorough API testing of FastAPI backends. Tests each endpoint with complete parameter sets.

## Pattern

```bash
# Test health + all subsystems
curl -s http://localhost:8001/health | python3 -c "
import sys,json; d=json.load(sys.stdin)
assert d['status'] == 'healthy'
assert 'database' in d      # DB health check
assert 'gpu_monitor' in d    # GPU status
assert 'task_queue' in d     # Queue status
assert 'nanobot' in d        # Controller status
"

# Test generation API with all parameters
curl -s -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"test prompt",
    "negative_prompt":"blurry",
    "generator":"comfyui",
    "settings":{
      "width":1024,"height":1024,"steps":30,"cfg_scale":7.5,
      "seed":42,"sampler":"dpm++_2m","scheduler":"karras",
      "batch_count":3,"model":"sd_xl","clip_skip":2,
      "style_preset":"cinematic",
      "lora_model":"detail","lora_strength":0.8,
      "controlnet_model":"canny","controlnet_strength":0.5,
      "vae":"sdxl_vae"
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] == 'pending'"

# Test Provider-specific endpoints (Kling / Seedance / Runway / Pika / triposr)
curl -s -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"sunset beach waves",
    "generator":"kling",
    "settings":{
      "duration":10,"fps":24,"width":1920,"height":1080,
      "seed":123,"cfg_scale":0.8,"model":"kling-1.6",
      "camera_type":"pan_left","loop":true,
      "motion_bucket_id":150,"motion_intensity":0.7
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] == 'pending'"

# Test first-last-frame video
curl -s -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"timelapse","generator":"seedance",
    "settings":{"first_frame":"base64_f","last_frame":"base64_l","duration":5}
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] == 'pending'"

# Test image-to-image
curl -s -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"style transfer","generator":"comfyui",
    "settings":{"source_image":"base64","strength":0.75,"edit_type":"style_transfer"}
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] == 'pending'"

# Test multi-image reference video
curl -s -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"character animation","generator":"seedance",
    "settings":{"reference_images":["img1","img2"],"duration":5}
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] == 'pending'"

# Test 3D generation
curl -s -X POST http://localhost:8001/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"dragon","generator":"triposr",
    "settings":{"export_format":"glb","texture_resolution":2048}
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status'] == 'pending'"

# Test infinite canvas operations
CID=$(curl -s -X POST http://localhost:8001/api/canvas/create -H "Content-Type: application/json" \
  -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('canvas_id',''))")

curl -s -X POST "http://localhost:8001/api/canvas/gen-image" \
  -H "Content-Type: application/json" \
  -d "{\"canvas_id\":\"$CID\",\"prompt\":\"test\",\"x\":0,\"y\":0,\"width\":1024,\"height\":1024}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']"

curl -s -X POST "http://localhost:8001/api/canvas/outpaint" \
  -H "Content-Type: application/json" \
  -d "{\"canvas_id\":\"$CID\",\"prompt\":\"more\",\"direction\":\"right\",\"expand_pixels\":256}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']"

curl -s -X POST "http://localhost:8001/api/canvas/edit" \
  -H "Content-Type: application/json" \
  -d "{\"canvas_id\":\"$CID\",\"prompt\":\"sun\",\"x\":100,\"y\":100,\"width\":256,\"height\":256}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']"

curl -s -X POST "http://localhost:8001/api/canvas/drama" \
  -H "Content-Type: application/json" \
  -d "{\"canvas_id\":\"$CID\",\"story_prompt\":\"a fox and an owl become friends\",\"scene_count\":4}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success'] and len(d['scenes']) == 4"

curl -s -X POST "http://localhost:8001/api/canvas/picture-book" \
  -H "Content-Type: application/json" \
  -d "{\"canvas_id\":\"$CID\",\"story_prompt\":\"a little star learning to shine\",\"page_count\":5}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success'] and len(d['pages']) == 5"

# Test undo/redo
curl -s -X POST "http://localhost:8001/api/canvas/undo?canvas_id=$CID&action=undo" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']"

curl -s -X POST "http://localhost:8001/api/canvas/undo?canvas_id=$CID&action=redo" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']"

# Test export
curl -s -X POST "http://localhost:8001/api/canvas/export" \
  -H "Content-Type: application/json" \
  -d "{\"canvas_id\":\"$CID\",\"output_path\":\"\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['success']"
```

## Common Failure Modes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| 422 Unprocessable | Pydantic model has required field w/o default | Add `= ""` default |
| 500 on async task | `state.active_tasks[task_id]` KeyError | Add task recreation in catch block |
| Provider not found | Provider not registered in unified_generation_service | Add to `get_unified_service()` + register call |
| Wrong generation type | `has_video`/`is_3d` tuples incomplete | Add provider name to the tuple |
| Short drama returns 1 scene | Scene splitter can't handle English | Use 3-level cascade splitter |
