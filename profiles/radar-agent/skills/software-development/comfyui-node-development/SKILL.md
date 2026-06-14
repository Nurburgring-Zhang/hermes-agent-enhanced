---
name: comfyui-node-development
description: "ComfyUI custom node development — registration, parameter patterns, ensemble upscale fusion, AuraSR, 5-round audit cycle, Prompt Library Node (V17→V20.5: 统一编号总纲/五维度变化追踪/分镜头顺序标准化, V20.5+故事弧引擎+DirectorPromptPro), and common failure modes"
version: 1.28.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: ["comfyui", "custom-nodes", "python", "image-processing", "frequency-decomposition", "residual-injection", "upscale-ensemble", "prompt-engineering", "prompt-library-node", "chinese-prompt", "child-content", "universal-settings", "总纲-extraction", "professional-design-prompts", "thumbnail-preview", "js-extension", "unified-mode-selector", "output-format-standards", "story-arc-engine", "director-pro", "shot-constraints", "batch-shot-output"]
    related_skills: [systematic-debugging, writing-plans, autonomous-ai-agents]
---

# ComfyUI Node Development

### Absorbed Skills (consolidated from narrow sibling)

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `comfyui-custom-node` | Subsection — full JS extension, multi-file upload, DOM widget, content density rules | `references/comfyui-custom-node-skill.md` |

The absorbed skill `comfyui-custom-node` was focused on JS frontend extensions (addDOMWidget, addCustomWidget, image upload, thumbnail grids) and content density / 格林主人 format rules. All content preserved in the reference file listed above. See also its linked references under `references/PromptLibraryNode-*` for format-specific guidance.

## Core Concepts

### Node Registration

Every custom node needs:

```python
NODE_CLASS_MAPPINGS = {"RegistryName": NodeClass}
NODE_DISPLAY_NAME_MAPPINGS = {"RegistryName": "Display Name"}
```

**Common pitfalls:**
- `NODE_CLASS_MAPPINGS` key vs class name mismatch (e.g. `"UUU_ImageUpscale": UUU_ImageUpscale` works, but `"FU_ImageUpscale_v4": UUU_ImageUpscale_v4` will fail with `NameError`)
- CATEGORY and DISPLAY_NAME must match exact spelling used by ComfyUI
- `RETURN_TYPES` and `RETURN_NAMES` must be same-length tuples
- `FUNCTION` name must match an actual class method
- `IS_CHANGED` must accept `**kwargs` — ComfyUI passes widget params as keyword arguments. Using `(self, kwargs)` causes `TypeError: unexpected keyword argument 'xxx'`

### Parameter Patterns

**Widget layout order:** Parameters appear in the order defined in `INPUT_TYPES()`. Use the `optional` dict for less-frequently-used params to keep the UI clean.

**Conditional visibility:** ComfyUI doesn't natively support conditional widgets. Use `BOOLEAN` toggles + clear naming conventions.

**STRING multiline:** Use `"multiline": True` for longer text inputs. Use `"multiline": False` for single-line paths/names.

**Dropdown defaults:** Always provide a `"default"` in dropdown options.

### Reference Image System

The `参考图列表` pattern uses a JS extension (`web/PromptLibraryNode.js`) that uploads images to ComfyUI's input directory and stores file info in a STRING widget as JSON:

```json
[{"filename": "img1.png", "subfolder": "", "type": "input"}]
```

Key points:
- Max 9 reference images
- Image resolution filtered at 4096px
- JS extension registers before the node loads — use `ComfyApp.onNodeCreated`
- Reference images influence system prompt (not direct image input to AI)
- The JS file must be in `web/` subdirectory and `WEB_DIRECTORY = "web"` must be set (not `"./web"` — some ComfyUI versions reject the leading `./`)

## 格林主人输出格式核心规则（2026-06-02 第五轮修正 + 2026-06-03 故事弧引擎+模板一致性铁律）

### 儿童模式完整重写（2026-06-02）
四种儿童模式（儿童视频格式一/二、儿童微动视频/GIF、儿童绘本格式）的 `_build_child_*` 方法已在2026-06-02全部重写。

**关键发现：** 原来的 `_build_child_v2` 和 `_build_child_gif` 方法**完全缺失输出格式维度定义**，只有创作原则。这导致LLM自由发挥成连贯叙事。修复后所有4个模式都有完整的输出格式定义。

### 总纲格式 — 纯文字标题，无编号无符号，禁止【】。内容行不缩进。
注意：代码中所有总纲硬编码的 `1、整体视觉风格：` `2、角色物品设定：` `3、道具/武器：` `4、场景设定：` `5、氛围与画质标准：` `6、声音设定：` `7、核心叙事设定：` 以及 `【{mode}总纲】`（带方括号的标题）已在2026-06-02全部清理为纯文字无符号形式。

### 角色特征维度定义（2026-06-02 精确化） 
**角色特征 = 仅在外貌/服装/状态有实质性变化时输出（换装/变脏/受伤/新增饰品等可见变化）。禁止写角色动作叙事（那是画面维度的事）。无变化时此行整行不出现。**

### 变化标注规则（最终版）
核心原则：只有分镜场景和角色特征这两个字段参与变化标注。其他字段标题始终正常输出。无变化时这两行整行不出现（包括标题本身）。

### 6. 新节点模板不一致（2026-06-03 新增 — 经格林主人审查修复）

**症状**: 格林主人在质量审查中发现 DirectorPromptPro 的输出模板与 PromptLibraryNodePro 不一致
**根因**: `director_pro.py` 中的 `_get_format_templates()` 直接复制了模板但精简了字段描述
**修复**: 逐行对比两个文件对应模式的角色特征行/创作原则/铁律条目，用脚本提取关键文本验证

**验证脚本**（2026-06-03 session中用过的模式）：
```python
# 提取两个文件中所有角色特征行进行对比
with open('modes_storyboard.py','r') as f: s = f.read()
with open('director_pro.py','r') as f: d = f.read()
for fname, text in [('modes_storyboard', s), ('director_pro', d)]:
    for line in text.split(chr(10)):
        if '角色特征' in line and '输出格式' not in line:
            print(fname, line.strip()[:120])
```

**已知的容易遗漏点**（格林主人验证过的完整清单）：
- **角色特征字段**：必须包含 `"禁止写角色在做什么（那是画面维度的事）"` 和 `"换装/变脏/受伤/新增饰品等可见变化"` 这句禁令
- **画面铁律第5条（变化标注规则）**：必须写完整版，包括 `"分镜场景：完整场景描述（地点、时间、光线、环境氛围，2-4句）"`、`"角色特征：仅在外貌/服装/状态有实质性变化时输出（换装/变脏/受伤/新增饰品等可见变化），描述变化了什么，2-3句"`、`"禁止写角色动作叙事（那是画面维度的事）"`、`"无变化时这两行不出现"`、`"其他字段正常输出"`
- **画面铁律第7条（时空锚定）**：必须包含 `"（如「清晨·森林小屋厨房」「傍晚·湖边小码头」）"` 示例，以及标注推进的措辞
- **画面铁律第8条（180度不越轴）**：必须写 `"（左侧机位/右侧机位锁定），禁止突然镜像翻转"`
- **画面铁律第9条（单格凝固动作）**：必须写 `"禁止连续动作（如「跑向…然后跳起来」会导致画面鬼影）"`
- **画面铁律第11条（风格统一）**：必须写 `"（除非场景转换有明确交代）。每格开头重复主风格词"`
- **画面铁律第12条（对话框绑定）**：必须写 `"（如「指向[角色名]的对话框」「[角色名]头顶的气泡对话框」），禁止模糊的「有对话框」。旁白不加对话框"`
- **各模式的创作原则部分**：广告/动画/漫画/MV/教程/短视频/品牌/剧情每种的创作原则都必须保留完整版，不能消除或精简

**正确做法**：不要手动精简复制，直接从原节点模块复制完整模板字符串。

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

## Prompt Library Node 开发指南

### 版本演进

The Prompt Library Node has evolved through many versions. Key milestones:
- **V17**: Storyboard mode with 9 sub-modes
- **V18**: Picture book mode + short drama mode + child content (4 sub-modes)
- **V19**: Unified mode selector + professional design prompts (8 modes) + JS thumbnail preview
- **V20**: Header extraction restructuring + universal settings
- **V20.5**: 12 iron rules for storyboard, 15 creation principles for picture book, five-dimension change tracking, dialogue binding, style locking, integration of 儿童绘本生图规则(1).txt
- **V20.5 重构（2026-06-03）**: 1916行单文件拆分为11个模块 + **故事弧引擎(StoryArc)** + **DirectorPromptPro 新节点**

### 故事弧引擎（engine_story_arc.py）

将25个故事感总纲从"写在prompt里的文本"变成"Python代码可计算的结构化数据"。

**核心类：**

`StoryArc` — 读取一条故事感总纲文本，解析为结构化的节拍序列。提供 `get_beat_for_shot(shot_index, total_shots)` 返回当前镜头所属节拍的结构化数据（beat_name, emotion_value, pace, intensity, recommended_shot_types, emotion_tags, is_final等）。情绪值范围0.0恐惧-1.0高涨，从中文"情感节奏"行自动解析。

`ShotConstraints` — 追踪镜头连续性状态（景别/运镜/角色/场景），提供 `get_constraints_text()` 生成对下一镜头的约束（如"连续3个同景别⚠️"）

`PromptSegmenter` — 批次输出工具，`join_outputs(segments)` / `split_output(combined)`，分隔符 `===SEGMENT_BREAK===`

**接入方式**：`PromptLibraryNodePro` 的故事板模式自动创建StoryArc并传入 — system prompt不再写"要有情绪曲线"，而是注入精确的结构化数据（节拍序列+情绪值+推荐景别）。旧路径（无story_arc时）保持原样作为fallback。

### DirectorPromptPro 节点（V1.0，23种模式全覆盖）

新节点（V1.0），与PromptLibraryNodePro共存于同一 `__init__.py`。

**核心差异**：传统节点一次性输出所有分镜 → DirectorPromptPro 按块数逐块调用LLM，每次输出 = 完整总纲 + 单个内容块，用 `===SEGMENT_BREAK===` 分隔。内部用 `ShotConstraints` 追踪连续性状态。

**23种模式全覆盖**（2026-06-03补齐）：

| 类别 | 模式 | 批处理函数 | 分段单位 |
|------|------|------------|----------|
| 故事板 | 电影/广告/动画/漫画/MV/教程/短视频/品牌/剧情 | `process_storyboard_batched` | 逐镜头 |
| 绘本 | 绘本模式 | `process_picture_book_batched` | 逐页 |
| 短剧 | 短剧模式 | `process_short_drama_batched` | 逐镜头 |
| 儿童 | 格式一/二/微动GIF/绘本格式 | `process_child_batched` | 逐片段/逐页 |
| 设计 | 电商/海报/品牌/PPT/逻辑图/三视图/爆炸图/流水线 | `process_design_batched` | 逐张/逐组 |

14种非故事板模式的完整架构详见 `references/director-pro-14-mode-batch-full.md`

**输出**：2个端口 — 批次输出(STRING, 含 `===SEGMENT_BREAK===` 分隔) + 元数据JSON

**新增模块注意事项**：
- `director_pro.py` 顶部需要 `sys.path.insert(0, _node_dir)` 确保ComfyUI加载模式下的导入路径正确
- 新节点在 `__init__.py` 底部注册，和现有 `NODE_CLASS_MAPPINGS` 放在一起
- `RETURN_TYPES` 和 `RETURN_NAMES` 为 (`"STRING"`, `"STRING"`) / (`"批次输出"`, `"元数据JSON"`)

### 代码架构

**V20.5 重构（2026-06-03）：从1916行单文件拆分为11个模块**

```
PromptLibraryNodePro/
├── __init__.py                          # 节点注册 + 主类（~510行，减少70%）
├── story_sense_data.py                  # 25个故事感总纲常量
├── llm_client.py                        # AI API调用封装（指数退避+抖动重试）
├── utils.py                             # 工具函数
├── random_content.py                    # 随机主题/角色/环境生成
├── modes_storyboard.py                  # 9种故事板模式
├── modes_book.py                        # 绘本模式
├── modes_drama.py                       # 短剧模式
├── modes_child.py                       # 4种儿童内容模式
├── modes_design.py                      # 8种专业设计模式
├── director_pro.py                      # NEW: DirectorPromptPro批次输出
├── engine_story_arc.py                  # NEW: 故事弧引擎
├── web/PromptLibraryNode.js             # 参考图上传UI
└── story_sense_library_complete.md      # 保留作为参考
```

**主类调用链**：所有 `self._xxx()` 转模块级函数调用，外部依赖通过参数回调注入。

### Prompt Library Node 的输出格式

**总纲（所有模式统一）**：纯文字标题，无符号无编号。

**分镜头的字段顺序**：
| 字段 | 规则 |
|------|------|
| 景别 | 始终输出，放在第一行 |
| 分镜场景 | 仅在场景变化时输出 |
| 角色特征 | 仅在角色特征变化时输出 |
| 画面 | 始终输出 |
| 叙事功能 | 仅在必要时输出 |

### 故事板模式（9种）

All storyboard modes share the `_build_storyboard_system_prompt()` method which contains:
1. **12 iron rules** (画面铁律十二条) — shared across all 9 sub-modes
2. **format_templates** — one per sub-mode for individual output structure
3. **mode_style** + **layout_desc** — per-mode references

Common pitfalls:
- Editing a format_template requires updating the correct entry in the `format_templates` dict
- The 12 iron rules are in the f-string — changes here affect ALL 9 storyboard modes
- Always search for parallel locations when modifying output format (grep for the pattern across all modes)

### 绘本模式

Built by `_build_picture_book_system_prompt()`:
- **7-dimensional output format**
- **15 creation principles**

### 短剧模式

Built by `_build_short_drama_system_prompt()`:
- Vertical 9:16 format
- 12 iron rules adapted for short drama

### 儿童内容模式（4种子模式）

- **儿童视频格式一**: 片段式(time·space / scene / dynamic / changes / dialogue / FX)
- **儿童视频格式二**: 起承转合四幕
- **儿童微动视频/GIF**: 每页一个核心动作
- **儿童绘本格式**: 每页(画面/文字)，不适用分镜场景/角色特征

### 专业设计模式（8种）

Each design mode has its own `_build_*_prompt()` method with world-class expert role-playing. Design modes do NOT use change tracking.

### AI API 集成

`call_ai()` handles OpenAI-compatible API:
- 3 retries with exponential backoff + jitter ((2^n + random(0,1)) seconds)
- 300s timeout
- Returns (content, error) tuple — error string on failure

### 参考图集成

- JS uploads to ComfyUI `input/` directory
- Parsed from JSON string widget
- Up to 9 images, 4096px resolution cap

## 常见故障模式

### 1. `IS_CHANGED` 签名错误

**症状**: ComfyUI报错 `TypeError: unexpected keyword argument 'xxx'`
**根因**: `IS_CHANGED(self, kwargs)` → 应改为 `IS_CHANGED(self, **kwargs)`

### 2. 语言混合问题

Old code mixed English and Chinese strings in prompt templates. Keep output prompts in Chinese for Chinese-language scenes.

### 3. 参考图解析失败

If `参考图列表` contains empty strings or malformed JSON, `_parse_ref_image_list()` degrades gracefully (returns `[]`).

### 4. 输出格式不一致

**症状**: 某个模式的输出格式与其他模式不一致
**根因**: 修改某个模式的format_template时忘了更新其他模式
**修复**: grep搜索所有format_templates中对应的字段，检查总纲header中隐藏的硬编码字符串

### 5. `patch`工具反斜杠转义问题

**症状**: `patch` tool报 `Escape-drift detected` 或 `Could not find a match`
**原因**: Python多行字符串中的 `\n` 会被patch工具误判
**缓解**: 优先使用精确的单行匹配，减少old_string长度，使用sed作为fallback

### 6. 新节点模板不一致（2026-06-03 新增）

**症状**: 格林主人在质量审查中发现 DirectorPromptPro 的输出模板与 PromptLibraryNodePro 不一致
**根因**: `director_pro.py` 中的 `_get_format_templates()` 直接复制了模板但精简了字段描述
**修复**: 逐行对比两个文件对应模式的角色特征行/创作原则/铁律条目，用脚本提取关键文本验证

### 7. 跨模块导入路径问题（2026-06-03 新增 — 重要通用模式）

**症状**: ComfyUI加载时 `ModuleNotFoundError: No module named 'xxx'`
**根因**: ComfyUI的custom_nodes加载机制不自动把节点目录加入Python模块搜索路径。即使 `__init__.py` 和 `xxx.py` 在同一目录下，`from xxx import YYY` 也可能失败。这与ComfyUI版本和Python加载方式有关（有些版本用importlib加载不继承搜索路径）。

**对所有多文件节点的要求**（通用规则，不只是director_pro.py）：
1. **`__init__.py` 顶部必须加**：
```python
import os, sys
_node_dir = os.path.dirname(os.path.abspath(__file__))
if _node_dir not in sys.path:
    sys.path.insert(0, _node_dir)
```
2. **被 `__init__` 间接导入的子模块中**（如 `engine_story_arc.py` 有 `from story_sense_data import` 的），**也必须加同样的代码**。因为ComfyUI是先执行 `__init__.py`，`__init__` 再触发子模块加载，但子模块的import解析发生在自己的作用域里，不会继承 `__init__` 的 `sys.path` 修改。

   **正确的检测方法**：模拟ComfyUI的加载方式测试——不在节点目录下启动python：
   ```python
   # 从/tmp启动，不把节点目录加入sys.path
   import importlib.util
   spec = importlib.util.spec_from_file_location('test', '/path/to/__init__.py')
   mod = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(mod)  # 如果这里不报错，说明修复ok
   ```

3. **所有同级模块间的导入必须用绝对导入**（`from xxx import YYY`），不用相对导入（`from .xxx import YYY`）。ComfyUI的custom_nodes不是包（package），`.`相对导入会炸。

**已验证的修复模式**（PromptLibraryNode V20.5重构后的经验）：
- `__init__.py`：需要 `sys.path.insert` + 所有`from xxx import` 改为同级绝对导入
- `engine_story_arc.py`：有 `from story_sense_data import` 也需要 `sys.path.insert`
- `modes_child.py`：如果被独立导入也需要加
- `director_pro.py`：已经有 `sys.path.insert` 在顶部

**不需要加的地方**：只使用标准库（`import os`, `import json`）且被其他模块间接导入的工具模块。它们不会被ComfyUI直接importlib加载。

### 8. 文件命名与ComfyUI内置模块冲突（2026-06-03 新增）

**症状**: `ImportError: cannot import name 'parse_keywords' from 'utils' (D:\ComfyUI\utils\__init__.py)`
**根因**: ComfyUI自己有一个 `D:\ComfyUI\utils\__init__.py` 包。当节点写 `from utils import ...` 时，Python搜索路径优先找到了ComfyUI的 `utils` 包，而不是本地的 `utils.py`。

**修复**: 将所有可能与ComfyUI内置模块冲突的文件名改掉，加独特前缀：
- `utils.py` → `pln_utils.py`（冲突文件: `D:\ComfyUI\utils\`）
- `llm_client.py` → `pln_llm.py`（"client"是常见名词，但不是直接冲突）
- `random_content.py` → `pln_random.py`（"random"不冲突，但统一风格）

**经验法则**: 在多文件节点中，**避免使用任何与ComfyUI目录/文件名重叠的简短的通用名**。ComfyUI本身包含 `utils/`、`nodes/`、`server.py`、`execution.py` 等。安全的命名策略：加项目唯一前缀（如 `pln_`）、或者用长且具体的名字。

**改名后必须同步更新的位置**：
1. `__init__.py` 中的 `from xxx import` — 对应改
2. `director_pro.py` 中的 `from xxx import` — 对应改（如果它也导入被改名的模块）
3. **被改名文件内部的 `from xxx import`** — 如果被改名文件依赖同级模块，也需要改
4. 执行完整测试验证

### 9. call_ai_fn 闭包签名不匹配（2026-06-03 新增）

**症状**: `TypeError: Xxx.get_prompt.<locals>._call_ai() takes 2 positional arguments but 7 were given`
**根因**: 当重构代码将AI调用从 `self._call_ai(api_url, api_key, model_name, sys_p, user_prompt, temperature, max_tokens)` 改为闭包 `def _call_ai(system_prompt, user_message)` 时，没有同步更新所有下游调用方。

**根本原因模式**: 在大型重构中，**函数签名的变更必须追踪所有调用点**。在重构 `PromptLibraryNodePro` 的 `_call_ai` 从7参数方法变为2参数闭包时，以下3个文件中的下游调用未被更新：
- `modes_storyboard.py:378` — 7参数调用
- `modes_book.py:27` — 7参数调用
- `modes_drama.py:45-49` — 7参数调用（多行）

**避免方案**：
1. 变更任何函数签名后，立即用 `grep -rn "old_call_pattern" *.py` 搜索所有调用方
2. 对闭包型 refactor（把方法变成闭包），尤其注意模块间调用——方法按 `self.method(args)` 调用，但闭包只传业务参数
3. 用 Python 的模拟加载测试（importlib方法）验证所有路径不报错

**正确做法**：`__init__.py` 中定义的 `_call_ai` 闭包应该只接受 `(system_prompt, user_message)`，因为API地址/密钥/模型/温度等都已被外层闭包捕获。下游模块只需要传prompt内容。

### 10. README 写作偏好 — 用"规则与思考"叙事取代表格对比（2026-06-03 格林主人校正）

**症状**: 第一次写的两个节点对比是表格（定位/输出/API需求/场景 7行表格）。格林主人纠正："主要写规则与思考的区别，这才是有价值的"

**根因**: 表格对比适合功能清单，但两个节点的真正区别不在于功能多寡，而在于设计哲学的不同——一个是一次生成全出（靠LLM），一个是逐段生成引擎控制（代码在追踪约束）。

**正确做法**：
- 用"PromptLibraryNodePro 的规则：一次生成，全部输出。/ DirectorPromptPro 的规则：逐段生成，引擎控制。" 开头
- 然后解释每种的思考方式：Pro 告诉LLM"你是个好导演，好好干"；Director 告诉LLM"这是情绪曲线，这是当前节拍，这是约束——现在输出第3个镜头"
- 用具体的技术差异（故事弧引擎、ShotConstraints追踪、批次独立）来支撑叙事，而不是列功能清单

**通用原则**：向格林主人解释技术架构时，优先用"规则与思考"的叙事，避免表格对比。表格只适合做快速概览，真正的价值在于解释为什么这样做。

### 故事感总纲（2026-06-01 新增 — 25种随机抽取）

核心机制：每个`_build_xxx_system_prompt()`中调用 `_pick_story_sense()`，从 `STORY_SENSE_LIBRARY` 常量中随机抽取一个。25个独立的故事模式，每个有独特的情感曲线、开场钩子、冲突模式、高潮方式。

**V20.5 重构变更**：改为Python常量 `story_sense_data.STORY_SENSE_LIBRARY`（内联列表），不再读md文件。类级缓存确保只加载一次。

### GitHub发布检查清单

1. **脱敏检查** — grep 个人信息/路径/密钥
2. **符号清理** — 确认输出不含 ## ** - 1. --- 【】
3. **README风格** — 说人话，禁止符号装饰
4. **commit** — 极简
5. **推送** — credential store 配置好

## 验证步骤

修改后必须执行：
1. 语法检查：`python3 -c "import ast; ast.parse(open('__init__.py').read()); print('OK')"`
2. grep确认旧格式无残留
3. grep确认新格式已到位
4. 在ComfyUI中加载节点测试实际输出
5. **符号清理验证**：grep检查输出中是否含 ** - 1. --- 【】 等装饰符号
6. **平行位置检查**：修改任何字段定义时，必须用grep搜索所有模式中相同字段并全部修改
7. **新节点模板一致性验证**（2026-06-03 新增）：用脚本提取两个节点对应模式的模板字符串逐行对比

## 参考文档

- `references/story-arc-engine-director-node.md` — 故事弧引擎 + DirectorPromptPro 架构详解
- `references/director-pro-14-mode-batch.md` — DirectorPromptPro 14种非故事板模式批处理架构详解
- `references/session-20260601-storysense-final.md` — 2026-06-01最终版：故事感总纲+格式规则清零
- `references/prompt-library-node-output-format-standards.md` — 输出格式标准化规范
- `references/module-split-refactoring.md` — 单文件→多模块拆分模式
- 及其他 references/ 下的各子主题文档
