# ComfyUI 节点单文件 → 多模块拆分模式

## 场景

ComfyUI 自定义节点发展到 V10+ 后，`__init__.py` 达到 1000-3000 行，单个类包揽所有逻辑（system prompt 构建、AI 调用、文件扫描、随机生成、设计模式等）。需要拆分为可维护的模块化结构。

## 前提条件

- ComfyUI 只认 `NODE_CLASS_MAPPINGS` 和 `NODE_DISPLAY_NAME_MAPPINGS` 这两个顶层字典
- 节点类中的方法之间全部是 `self.xxx()` 调用，没有跨文件依赖
- JS 前端扩展在 `web/` 目录下，不受 Python 文件拆分影响

## 拆分策略：混入模式（Mixin Pattern）

不继承，不改变类层次结构。将辅助方法提取到独立模块作为普通函数，主类通过参数注入调用它们。

### 步骤

1. **分析调用链**：列出所有 `self._xxx()` 调用，按功能域分组（AI调用、文件扫描、故事板模式、设计模式等）

2. **提取为普通函数**：每个模块中的函数去掉 `self` 参数，改为独立函数

3. **依赖通过参数注入**：主类中的 `self._random_topic(mode)` → 模块函数 `random_topic(mode)`。主类通过闭包或函数引用传给子模块：
   ```python
   def _call_ai(system_prompt, user_message):
       result, last_error = call_ai(api_url, api_key, ...)
       return result
   
   from modes_storyboard import _process_storyboard_mode
   mode_output = _process_storyboard_mode(
       ..., 
       random_topic_fn=random_topic,
       random_character_fn=random_character,
       call_ai_fn=_call_ai,
       pick_story_sense_fn=self._pick_story_sense,
   )
   ```

4. **数据常量内联**：如果子模块依赖外部数据文件（如故事感总纲的md文件），将其提取为Python常量模块：
   ```python
   # story_sense_data.py
   STORY_SENSE_LIBRARY = [
       """【故事感总纲01：灰烬里的星星】...""",
       ...
   ]
   ```
   
   优势：类级缓存，无IO开销，无文件缺失风险。

### 模块划分原则

| 功能域 | 提取为独立模块 | 原因 |
|--------|---------------|------|
| AI API 调用 | `llm_client.py` | 独立重试逻辑，可独立测试 |
| 工具函数 | `utils.py` | 纯函数，无状态，可复用 |
| 随机内容 | `random_content.py` | 大量静态数据（pools字典），污染主文件 |
| 故事板模式 | `modes_storyboard.py` | 9个子模式，system prompt超长 |
| 绘本模式 | `modes_book.py` | 独立格式规范 |
| 短剧模式 | `modes_drama.py` | 独立输出格式 |
| 儿童内容 | `modes_child.py` | 4个子模式，每个有完整格式定义 |
| 设计模式 | `modes_design.py` | 8个子模式，带世界级角色扮演文本 |

### 不拆的部分

- **主调度器**（`get_prompt`）留在 `__init__.py` — 这是节点入口，负责参数提取和模式路由
- **传统模式**（提示词库读取/AI生成）— 依赖于主类的 `_cache` 和 `_cache_lock`，拆分会引入复杂的状态传递

## 常见陷阱

### 1. ⚠️ 子Agent生成模块的命名不一致

使用 `delegate_task` 并行提取多个模块时，不同子Agent可能产生不一致的命名约定：
- 有的用 `process_storyboard_mode`（无下划线前缀），有的用 `_process_storyboard_mode`（有下划线）
- 有的参数名用 `random_topic`，有的用 `random_topic_fn`，有的用 `random_topic_fn=`

**解决方法**：在所有并行子任务完成后，统一检查所有模块的函数签名和 `__init__.py` 中的调用参数，确保完全匹配。不要假设所有子Agent遵循相同命名约定。

### 2. 故事感总纲引用

`_build_xxx_system_prompt` 函数在原始代码中通过 `self._pick_story_sense()` 调用故事感总纲。提取到独立模块后，需要通过 `pick_story_sense_fn` 参数传入这个回调。

**错误做法**：在子模块中重新实现文件读取逻辑（导致重复IO和文件路径硬编码）

### 3. 缓存状态迁移

`_pick_n_lines` 和 `history_dedup` 依赖 `self._cache` 字典和 `self._cache_lock`。提取到 `utils.py` 后，需要将 `cache` 和 `cache_lock` 作为参数传入/传出。

### 4. 未使用的import清理

拆分后检查原 `__init__.py` 中的 import 语句，很多原来的 import（如 `io`, `base64`, `pathlib`, `urllib.request` 等）会变得不再需要，应手动清理。

### 5. 死函数检测

有些类方法可能在重构前就未被调用（如原代码中的 `_error_result`）。拆分前用 grep 全局搜索确认每个私有方法的调用点。

## 验证清单

拆分后必须验证：

- [ ] `NODE_CLASS_MAPPINGS` 仍能正确导入主类
- [ ] 所有子模块能独立 import
- [ ] `关闭` 模式（不使用AI）返回空字符串
- [ ] 所有故事板模式（无API）返回空字符串
- [ ] 所有设计模式（无API）返回空字符串
- [ ] 所有儿童模式（无API）返回空字符串
- [ ] 绘本/短剧模式（无API）返回空字符串
- [ ] 负面词生成功能正常
- [ ] 元数据JSON输出正常
- [ ] `IS_CHANGED` 每次返回不同值
- [ ] 故事感总纲随机抽取功能正常
- [ ] `__pycache__` 清理后重启 ComfyUI 仍能加载节点
