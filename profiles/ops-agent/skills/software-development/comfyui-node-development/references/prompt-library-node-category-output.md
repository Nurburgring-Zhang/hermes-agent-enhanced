# Prompt Output by Category — V17.1

Added 2026-05-22. Pattern for classifying prompt output by target use case.

## Why

Different downstream workflows (txt2img, img2img, video, storyboard) need prompts in different formats. Rather than making the user manually prefix, the node provides a dropdown.

## Implementation

### INPUT_TYPES addition

```python
"提示词分类": (["通用文生图","图片编辑","视频生成","逻辑图/多格绘图",
                "AI短剧","产品摄影","建筑/室内设计","角色设计",
                "概念艺术","动漫/二次元"], {"default": "通用文生图"}),
```

### Function signature

```python
def get_prompt(self, ..., 提示词分类="通用文生图"):
```

### Prefix injection (before final return)

```python
category_prefixes = {
    "图片编辑": "[图片编辑] ",
    "视频生成": "[视频生成] ",
    "逻辑图/多格绘图": "[多格构图] ",
    "AI短剧": "[AI短剧] ",
    "产品摄影": "[产品摄影] ",
    "建筑/室内设计": "[建筑室内] ",
    "角色设计": "[角色设计] ",
    "概念艺术": "[概念艺术] ",
    "动漫/二次元": "[二次元] ",
}
prefix = category_prefixes.get(提示词分类, "")
if prefix:
    lines = final_prompt.split("\n")
    lines = [prefix + l if l.strip() else l for l in lines]
    final_prompt = "\n".join(lines)
    meta_info["提示词分类"] = 提示词分类
```

### Rules

1. 通用文生图 = no prefix (backward compatible)
2. Prefix added per-line, not as a header
3. Metadata always records the classification
4. Empty lines in multi-line output preserve their structure
