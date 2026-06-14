# 2026-06-03 模块拆分 + 导入修复 + 故事弧引擎 + DirectorPromptPro

## 本次会话内容

1. PromptLibraryNode 从1916行单文件拆分为11个模块
2. 新增 engine_story_arc.py（故事弧引擎：StoryArc + ShotConstraints + PromptSegmenter）
3. 新增 director_pro.py（DirectorPromptPro批次输出，23种模式全覆盖）
4. 修复 ComfyUI 加载时的 import 路径问题
5. 修复 call_ai_fn 闭包签名不匹配问题
6. 修复文件命名冲突（utils.py → pln_utils.py 等）

## 已嵌入 comfyui-node-development SKILL.md 的核心教训

- **7. 跨模块导入路径问题** — sys.path.insert 修复模式
- **8. 文件命名与ComfyUI内置模块冲突** — pln_前缀命名策略
- **9. call_ai_fn 闭包签名不匹配** — 改签名必须 grep 所有调用点

## 文件冲突检测方法

在重命名 utils.py → pln_utils.py 之前，先用以下方式检查是否有同名冲突：

```bash
# 查看ComfyUI目录下是否存在同名模块
ls D:\ComfyUI\utils\__init__.py  # ComfyUI确实有这个
# 全局搜索也会找到
```

## DirectorPromptPro 23种模式全覆盖清单

```
故事板9种:  process_storyboard_batched()  — 逐镜头
绘本1种:    process_picture_book_batched() — 逐页
短剧1种:    process_short_drama_batched()  — 逐镜头
儿童4种:    process_child_batched()        — 逐片段/逐页
设计8种:    process_design_batched()       — 逐张/逐组
```

## 输出格式

2个端口: 批次输出(STRING, ===SEGMENT_BREAK=== 分隔) + 元数据JSON(STRING)
每个段落 = 完整总纲 + 单个内容块
每个内容块 = 对应模式的标准输出格式（与PromptLibraryNodePro完全一致）

## 恢复备份

所有备份在 /mnt/d/Hermes/备份/ 下:
- PromptLibraryNode_bak_20260603_012053 — 拆分前原始版本
- PromptLibraryNode_bak_20260603_020721_before_director — 拆分后、引擎前的版本
