# 故事弧引擎 + DirectorPromptPro 节点架构

## 2026-06-03 新增

## 问题

PromptLibraryNodePro 在 V20.5 重构之后，所有模式仍然是"构建system prompt → 一次性调LLM → 返回全部内容"的模式。故事感总纲写在prompt里，LLM输出啥就是啥，节点不做任何结构约束。

格林主人要求：
1. 在代码层面实现真正的导演级功能（不是写prompt让LLM假装）
2. 新节点 DirectorPromptPro：每次输出总纲+一个分镜，按镜头数批次输出

## 方案

### 一层引擎 + 一个新节点

**不替换原有节点**，新增 `engine_story_arc.py` 引擎层，改造 `modes_storyboard.py` 接入，新建 `director_pro.py` 为 DirectorPromptPro 提供批次输出。

### 引擎架构

```
engine_story_arc.py/
├── EMOTION_MAP              → 中文情绪词→数值映射表（70+词条）
├── EMOTION_EN_MAP           → 中文情绪→英文标签映射
├── SHOT_TYPE_PRIORITY       → 景别优先级（极远景1→极特写7）
├── SHOT_TYPE_NAMES          → 景别列表
├── StoryBeat class          → 单个叙事节拍（name, emotion_value, pace, intensity, narrative_func）
├── StoryArc class           → 讲故事感总纲文本解析为结构化节拍序列
├── ShotConstraints class    → 镜头连续性追踪器
└── PromptSegmenter class    → 批次输出合并/拆分
```

### StoryArc 工作流

1. 接收一条完整的 `【故事感总纲N：XXX】` 文本
2. 正则提取：标题 / 一句话核心 / 情感节奏行 / 情节结构步骤
3. 情感节奏行（如"开场-压抑微痛 → 前段-希望又破灭 → ..."）被拆分为6-7个节拍
4. 每个节拍通过 `EMOTION_MAP` 映射到数值（0.0-1.0）
5. 根据节拍位置（开场/前段/中段/转折/高潮/结尾）分配节奏(pace)和强度(intensity)
6. `get_beat_for_shot(shot_index, total_shots)` 将镜头序号映射到节拍序号，返回结构化的节拍数据

### ShotConstraints 连续性追踪

记录每镜头的 `shot_type / duration / camera / transition / characters / scene`。每次生成下一镜头前调用 `get_constraints_text()` 返回：
- 景别变换检测：连续3个同景别 → 强制切换警告
- 连续2个同景别 → 建议切换提示
- 运镜/转场参考
- 角色/场景一致性提示

### DirectorPromptPro 批次输出

**逐镜头循环**：不是一次性让LLM输出全部，而是每个镜头一次LLM调用：

```python
for shot_idx in range(shot_count):
    beat = story_arc.get_beat_for_shot(shot_idx, shot_count)  # 当前节拍
    constraints = constraints_tracker.get_constraints_text()    # 连续性约束
    
    system_prompt = 总纲 + 节拍数据 + 铁律 + 格式模板 + 约束
    user_prompt = 主题 + "只输出第N个镜头"
    
    raw = call_ai(system_prompt, user_prompt)
    shot_data = parse_shot_data(raw)          # 提取结构化数据
    constraints_tracker.record_shot(shot_data) # 更新追踪器
    
    segments.append(header + raw)
    
return PromptSegmenter.join_outputs(segments)  # 用 ===SEGMENT_BREAK=== 连接
```

### 测试验证

- 全部25个故事感总纲解析正确：6-7节拍，情绪范围0.05-0.88
- 现有 `PromptLibraryNodePro` 19种模式全部回归通过
- `DirectorPromptPro` 9种故事板模式批次输出格式验证通过
