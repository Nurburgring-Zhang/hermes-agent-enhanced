---
name: unified-params-layer
description: >
  多层参数完整性框架：当AI生成项目有多个独立的生成系统（API层/服务层/引擎层）各自定义参数集时，
  创建统一超集模型并逐层回填，确保所有参数维度在所有层级贯通。
  适用于：FastAPI生成系统审计、参数不完整报告修复、Provider参数映射。
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [parameter-mapping, generation-systems, backend-architecture, code-audit]
    related_skills: [deep-code-architecture-analysis, systematic-debugging]
---

# 多层参数完整性框架 (Unified Params Layer)

## 概述

AI生成项目通常有多个独立的生成系统层，各自定义自己的参数集。典型的分层结构：

```
API层 (server.py) → 服务层 (generation_service.py) → 引擎层 (diffuser_engine.py) → Provider层 (Kling/ComfyUI/...)
```

**核心问题：** 参数在API层定义了但从未到达引擎层。每个层只传递了自己认识的字段。

## 触发条件

- 用户问"所有参数维度都添加到位了吗"或"所有的设置/选择/调整功能都加上了吗"
- 发现多个生成系统文件各有不同的参数数据类
- 需要审计一个大型后端项目的参数传递完整性
- 需要为新Provider编写参数映射

## 方法论

### Pass 1: 字段清单审计

对每一层，读取所有请求/参数数据类，列出所有字段，跨层对比：

```yaml
步骤:
  1. 找到所有定义参数的数据类（dataclass/BaseModel）
  2. 提取每个类的字段名+类型+默认值
  3. 跨层对比矩阵，标记缺失
```

**需要检查的典型文件：**
- `server.py` — GenerationRequest / 路由函数参数
- `unified_generation_service.py` — GenerationRequest
- `production_workbench.py` — GenerationRequest
- `omni_gen.py` — 各generate函数的参数签名
- `diffuser_engine.py` — GenerationParams（本地推理最完整层）
- `aigc.py` / `aigc_adapter.py` — 各Adapter参数

### Pass 2: 参数传递追踪

对每个生成端点，追踪哪些字段实际传递到了 generate() 调用：

```python
# 常见失败模式：
gen_request = GenRequest(
    prompt=request.prompt,
    width=request.settings.get("width", 1024),  # ✅ 从settings提取
    # ❌ seed/cfg_scale/sampler/scheduler 全部丢失
    # ❌ lora/controlnet/clip_skip 全部丢失
)
```

**检查点：** `settings.get()` 调用是否覆盖了所有定义的字段。

### Pass 3: 统一超集模型

创建一个包含所有层所有字段的 UnifiedGenerationParams，然后用转换函数逐层映射：

```
UnifiedGenerationParams (84字段)
    ↓ params_to_diffuser() → diffuser_engine.GenerationParams (32字段映射)
    ↓ params_to_comfyui() → ComfyUI workflow JSON
    ↓ params_to_kling() → Kling API request
    ↓ params_to_seedance() → Seedance API request
    ↓ params_to_unified_service() → unified_generation_service.GenerationRequest
```

### Pass 4: 逐层回填

对每一层：
1. **API层：** 补全请求数据类的字段，确保所有 settings 被提取
2. **服务层：** 补全 GenerationRequest 数据类
3. **引擎层：** 补全 generate() 调用中的参数映射
4. **Provider层：** 编写 Provider-specific 转换函数

## 缺失参数类别（通用清单）

以下是AI生成项目中常见的缺失参数类别，可直接作为检查清单使用：

| 类别 | 关键字段 | 典型缺失率 |
|------|---------|-----------|
| 图像基础 | sampler/scheduler/batch_count/clip_skip/eta/vae/guidance_rescale | 60% |
| LoRA | model/weight/clip_weight/trigger_words/type | 80% |
| ControlNet | type/image/weight/guidance_start/end/preprocessor/mode | 85% |
| 视频 | duration/fps/video_frames/camera(3子字段)/motion_bucket/noise_aug/loop | 70% |
| 编辑 | edit_type/source_image/mask(4子字段)/strength/edit_prompt | 90% |
| 滤镜/色彩 | filter_type/strength/output_format/brightness/contrast/saturation/vibrance/temperature/tint/exposure/highlights/shadows | 75% |
| 放大 | model/scale/face_enhance/tile_size/tile_pad/denoise | 65% |
| 3D | export_format/texture_resolution/mesh_simplification/remove_bg/num_views/shape_resolution | 90% |
| 无限画布 | x/y/w/h/canvas_w_h/context_images/overlap/seam_blend/scene/story | 95% |

## Provider 参数映射模式

每个 Provider 需要自己的转换函数，把统一参数映射为 Provider-specific JSON：

```python
def params_to_kling(params: UnifiedGenerationParams) -> Dict:
    d = {
        "prompt": params.prompt,
        "duration": params.duration,
        "cfg_scale": params.cfg_scale,
        "seed": params.seed if params.seed >= 0 else None,
        "mode": "pro",
    }
    if params.camera.type:
        d["camera_control"] = {"type": params.camera.type}
    if params.loop:
        d["single_loop"] = 0
    return d
```

### 类级别 Provider 实现模式

当在 `unified_generation_service.py` 中添加新Provider时，遵循以下基类契约：

```python
class NewProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.example.com/v1"
        self.api_key = config.api_key or os.getenv("NEW_API_KEY", "")

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        # 1. validate
        if not self.validate_request(request):
            return GenerationResult(..., status="failed", error="Invalid request")
        # 2. check key
        if not self.api_key:
            return GenerationResult(..., status="failed", error="KEY not configured")
        # 3. build payload from request fields
        # 4. call API via aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    return GenerationResult(status="processing", ...)
                return GenerationResult(status="failed", error=f"API error {resp.status}")
        # 5. return GenerationResult

    async def get_status(self, task_id: str) -> GenerationResult: ...
    async def cancel(self, task_id: str) -> bool: ...

# 注册:
_unified_service.register_provider(NewProvider(ProviderConfig(
    provider="newprovider",
    enabled=True,
    models=["model-v1"],
    default_model="model-v1"
)))
```

**关键点：** `GenerationRequest` 已在 `unified_generation_service.py` 扩展为57个字段（包括lora/controlnet/clip_skip/vae/video高级/3D/后处理），新Provider应尽量完整映射这些字段。

### 新增Provider的server.py集成

在 `generate_content_async` 中，确保新Provider名称被加入 `has_video` 或 `is_3d` 检测元组：

```python
has_video = request.generator in ("kling", "seedance", "runway", "pika", "minimax", "doubao", "svd", "animatediff", "hunyuan")
is_3d = request.generator in ("triposr", "trellis", "hunyuan3d", "hunyuan")
```

## 陷阱

### 🕳️ 陷阱1: settings dict 黑洞
API层用 `settings: Dict[str, Any]` 接收参数，但后台只调用了 `settings.get("width")` 和 `settings.get("steps")`，其他参数全部丢失。

**对策：** 显式提取所有 settings 字段，或改用 Pydantic 模型验证。

### 🕳️ 陷阱2: 不同系统用不同字段名
同一参数在不同层叫不同的名字（如 `cfg` vs `cfg_scale` vs `guidance_scale`）。

**对策：** 统一超集模型用标准名，转换函数在各层做名字映射。

### 🕳️ 陷阱3: copy-vs-mutation
`state.assets` property 返回 `self._assets.copy()`，所有写入操作修改的都是 copy。

**对策：** 对 mutations 绕过 property，直接操作 `state._items[key]`。

### 🕳️ 陷阱4: Body vs Query
FastAPI 中 `payload: Dict[str, Any]` 默认为 query 参数，不会从 JSON body 读取。

**对策：** `from fastapi import Body, Query` + `payload: Dict[str, Any] = Body(...)`。

### 🕳️ 陷阱5: RateLimiter 双重定义
同一个文件中有两个同名 `class RateLimiter`，构造函数参数不同，后定义者覆盖前者。同时附带了废弃的 RedisRateLimiter 和死代码中间件。

**对策：** 检查 `server.py` 第40行附近和第441行附近是否有重复的 RateLimiter。删除早期的版本，只保留一个。

### 🕳️ 陷阱6: Provider 识别不完整
`generate_content_async` 中的 `has_video` 和 `is_3d` 检测元组可能会遗漏新加入的 Provider，导致请求类型被误判。

**对策：** 添加新 Provider 后，同时更新 `has_video` 和 `is_3d` 元组。检查时搜索 `request.generator in (""`。

### 🕳️ 陷阱7: 前端 Provider 列表与后端不一致
前端 `UnifiedParamsPanel` 中硬编码的 `PROVIDERS` 列表与后端实际注册的 Provider 容易不同步。

**对策：** 每次新增/移除后端 Provider 后，同步更新前端 PROVIDERS 列表。可用 `intersection` 检查：前端列表 ∩ 后端注册列表 应该等于后端注册列表。

### 🕳️ 陷阱8: Pydantic required 字段阻塞可选 body
当一个 Pydantic 模型同时被多个路由复用时，有些路由不需要全部字段。`prompt: str`（无默认值）导致只传 `story_prompt` 的请求返回 422。

**对策：** `prompt: str = ""`，路由中用 `request.field_a or request.field_b` 策略。不要在一个模型里混合 required 和 optional 逻辑——用默认空值 + 业务层判断代替。

### 🕳️ 陷阱9: health check 扩展时序
向 `/health` 端点添加新子系统检查时，如果子系统在 lifespan 之后初始化，第一次调用会失败。

**对策：** 用 try/except 包裹每个新检查块，失败时 `health_status["subsystem"] = {"available": False, "error": str(e)}` 而非抛异常。

## 实例

NanoBot Factory 项目（2026-06-06）：
- 3个独立生成系统，参数从25→57字段、15→45字段、7→32参数
- 创建84字段统一超集模型，5个Provider转换函数
- 发现并修复3个bug（copy-vs-mutation, Body vs Query, missing Query import）

详见 `deep-code-architecture-analysis/references/nanobot-factory-audit-20260606.md`。

## 验证脚本

`templates/deep-api-test.sh` 提供可复用的深度API功能测试脚本，覆盖：
- 8种生成类型（文生图/视频/首尾帧/图生图/多图参考/3D/Runway/Pika）
- 每个生成类型的完整参数集（15-30个参数）
- 无限画布7种操作（创建/生图/outpaint/编辑/短剧/绘本/导出）
- 常见失败模式速查表

每次修改生成API后运行此脚本验证完整性。
