# PromptLibraryNode V20.5 — 四项强制格式修正记录

修正日期: 2026-05-30
原文件: /mnt/d/ComfyUI/custom_nodes/PromptLibraryNode/__init__.py
备份: /mnt/d/Hermes/备份/__init__.py.PromptLibraryNode.V20.5.backup.20260529_214400

## 修正1: 总纲去掉#前缀 + 硬编码角色物品和场景

**问题**: 总纲以`# 【xxx总纲】`开头，且总纲header中硬编码了`【角色物品设定】`和`【场景设定】`，直接从用户输入的`character_desc`参数拼接。当用户把场景内容填入角色描述框时，输出就变成了"清晨的阳光下，一片绿油油的菜园里"出现在【角色物品设定】下。

**修改**:
- 去掉`# `前缀：4个总纲从`f"# 【xxx总纲】"`改为`f"【xxx总纲】"`
- 去掉header中`【角色物品设定】`和`【场景设定】`的硬编码拼接
- 总纲只保留风格/色调/画风等元信息
- 在system prompt中加入引导：要求AI在正文开头自行输出`【角色设定】`和`【环境设定】`

**涉及函数**:
- `_process_storyboard_mode` → `storyboard_header`
- `_process_picture_book_mode` → `header`
- `_process_short_drama_mode` → `header`  
- `_process_child_mode` → `header`

**system prompt引导语句**:
```python
# 故事板
f"注意：在故事板正文开头，先输出【角色设定】（列出角色外貌、服装、标志性物品）和【环境设定】（场景地点、时间、氛围）。\n"

# 绘本
"注意：在绘本正文开头，先输出【角色设定】（列出角色外貌、服装、标志性物品）和【环境设定】（场景地点、时间、氛围）。\n"

# 短剧
"注意：在剧本正文开头，先输出【角色设定】（列出角色外貌、服装、标志性物品）和【环境设定】（场景地点、时间、氛围）。\n"

# 儿童  
"注意：在正文开头先输出【角色设定】（角色外貌、服装、物品）和【环境设定】（场景地点、时间、氛围）。场景切换时在新场景首页用孩子能懂的话描述新环境——那里有什么颜色、有什么好玩的东西、光线亮不亮。\n"
```

## 修正2: 用户输入传透补全

**问题**: 绘本和短剧模式的`_build_picture_book_user_prompt`和`_build_short_drama_user_prompt`没有将用户输入的`character_desc`和`env_desc`传递给AI，导致AI只有主题和风格信息，没有角色和场景信息。

**修改**:
- `_build_picture_book_user_prompt`函数签名从`(topic, pages, style, color_tone, text_amount, age_group)`改为`(topic, character_desc, env_desc, pages, style, color_tone, text_amount, age_group)`，添加角色和场景描述输出
- 调用处更新：`book_user = self._build_picture_book_user_prompt(topic, character_desc, env_desc, pages, ...)`
- 短剧system prompt描述从"主题、镜头数"改为"主题、角色、场景、镜头数"
- 儿童user prompt添加`场景描述：{env_desc}`

## 修正3: 场景切换规则按模板类型定制

**问题**: 所有模板的场景切换规则用了同一套描述"布局、光线、氛围"，没有匹配模板类型。

**修改**: 按模板类型定制场景切换时的环境描述规则

| 模板 | 规则描述 |
|------|---------|
| 故事板 | 用镜头语言描述新场景的环境氛围、空间特征和关键视觉元素 |
| 绘本 | 用孩子的视角——有什么颜色、形状、好玩的东西、光线温暖还是神秘 |
| 短剧-场景设定 | 竖屏构图下交代新场景的空间感和光线氛围 |
| 短剧-铁律 | 首镜头用竖屏构图交代空间氛围和光线方向，让观众一眼看懂到了什么地方 |
| 儿童 | 用孩子能懂的话——有什么颜色、有什么好玩的东西、光线亮不亮 |

## 修正4: 去除**和-符号

**问题**: 模板system prompt和输出格式中使用大量`**`粗体和`- `列表符号。

**修改**: 去掉故事板铁律、绘本格式、短剧铁律、儿童4个子模式中的所有`**`和`"- "`前缀。format_templates（9种故事板子模式的输出格式模板）中的字段标记如`**景别**`、`**画面**`等全部改为纯文本。

## 综合检查清单

修改后验证所有模板时检查以下25项：
- 4个总纲无`# `前缀
- 4个总纲无硬编码【角色物品设定】和【场景设定】
- 4个总纲的system prompt有【角色设定】+【环境设定】引导语句
- 绘本user prompt有角色场景描述
- 短剧system prompt有"角色、场景"提示
- 儿童user prompt有场景描述
- 故事板user prompt有【角色描述】和【环境背景】
- 5个场景切换规则按模板类型定制
- 7个模板（故事板铁律、绘本、短剧、儿童v1/v2/gif/绘本）无**和-符号残留
