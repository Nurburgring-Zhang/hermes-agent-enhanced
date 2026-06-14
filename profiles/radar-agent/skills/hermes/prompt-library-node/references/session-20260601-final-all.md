# 会话最终版（2026-06-01）

## 本轮完成的所有修改

### 1. 代码结构修复
- `_pick_story_sense()` 方法新建（L156-172）：从story_sense_library_complete.md随机抽取
- 7个system prompt函数加入随机抽取+强制指令+角色设定的三层结构
- 修复儿童v1/v2/gif/book中重复调用和缺失return (的问题
- 所有硬编码故事感总纲替换为随机抽取

### 2. 故事感文库升级
- 25个总纲全部重写为带完整情节结构的版本（7步情节+情感节奏）
- 文件位置：`/mnt/d/ComfyUI/custom_nodes/PromptLibraryNode/story_sense_library_complete.md`
- 大小：33KB，25个条目

### 3. 强制指令
在`_pick_story_sense()`之后紧跟：
```
上述故事感总纲是本故事的结构设计核心。严格按照总纲的情节结构来设计故事的起承转合。
让故事本身的走向有波折有悬念，不要平铺直叙。情感表达在恰当的情节节点出现，配合故事推动。
```

### 4. 修复检查清单
- 语法通过
- `_pick_story_sense` 调用 = 8次（1定义+7调用）
- `上述故事感总纲` 行 = 7处（所有模式各一）
- 所有模式都有 sense = + return ( + {sense} 的正确结构
- 文库25个全部有情节结构
