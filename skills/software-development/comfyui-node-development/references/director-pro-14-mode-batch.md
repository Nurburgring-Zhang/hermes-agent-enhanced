# DirectorPromptPro 14种非故事板模式批处理架构

## 背景

DirectorPromptPro 初始只支持9种故事板模式的批次输出。
2026-06-03 session补齐了全部14种非故事板模式的批处理函数。

## 架构

5个批处理函数都在 `PromptLibraryNode/director_pro.py` 中：

| 函数 | 服务模式 | 循环单位 |
|------|----------|----------|
| `process_storyboard_batched` | 9种故事板 | 逐镜头（带故事弧引擎+ShotConstraints） |
| `process_picture_book_batched` | 绘本模式 | 逐页 |
| `process_short_drama_batched` | 短剧模式 | 逐镜头 |
| `process_child_batched` | 4种儿童模式 | 逐片段/逐页 |
| `process_design_batched` | 8种设计模式 | 逐张/逐组 |

共同模式：
- 参数签名尽量与现有节点的入口函数对齐
- 循环N次（count/pages/shot_count）
- 每次构建system prompt + user prompt → call_ai → 组装总纲+单个块 → Append到segments列表
- 最后用 `PromptSegmenter.join_outputs(segments)` 拼接

## 各模式system prompt关键区别

### 绘本（process_picture_book_batched）
- 年龄段指南(age_guide字典 0-3/3-6/6-9/9-12)
- 7维度输出格式
- 创作原则：不说教公式、五感锚定法、情绪始终正向

### 短剧（process_short_drama_batched）
- 竖屏9:16
- 7条画面铁律（不是12条，短剧模式有自己的简化版）
- 输出：镜头N：标题 + 景别/台词/运镜/备注

### 儿童（process_child_batched）
- 4种模式各自不同的格式描述（format_desc字典）
- 年龄段描述(age_desc) + 画风映射(style_map)
- 通用创作原则：不说教、角色一致性、八大红线

### 设计（process_design_batched）
- 复用 `modes_design.py` 中的 `_build_*_prompt` 函数
- builder_map 字典映射模式→构建函数
- 8种设计模式各自不同的角色设定和输出格式

## 注意事项

1. 每种模式的system prompt必须包含"只输出当前块"的明确指令（如"只输出这一个镜头"）
2. `call_ai` 返回 (content, error) 元组
3. 总纲header在每块前重复输出，确保每个块独立可用
4. 所有模式末尾加符号禁令
5. 设计模式不需要总纲header（设计模式输出就是专业设计描述本身）
