# V19 Widget Layout + Parameter Limit Session (2026-05-27)

## Session Summary

User rebuilt PromptLibraryNode V19 over 3 layout attempts. 3 critical design corrections.

## Attempt 1: Wrong Section Order

Put "文件夹路径→翻译方向" at bottom. User: "这他妈的没理解？？？"

**Correct order:**
1. 文件夹路径→翻译方向 (top)
2. API地址→AI最大Token数 (after translation)
3. 载入参考图 (after AI settings)
4. 模式选择→运镜风格
5. 镜头数量→背景类型 (bottom, optional)

## Attempt 2: Reference Image in optional block

Put "参考图列表" in optional → rendered at bottom, invisible between required sections. User: "为什么没有显示载入参考图这个功能？？"

**Fix:** Move to required block, hide original string widget, replace with DOM widget.

## Attempt 3: Node grows on image deletion

Used `this.setSize()` to resize node for thumbnail grid. Each deletion recalculated height → node got progressively taller. User: "删一张，整个提示词节点就变长一节"

**Fix:** Use `domWidget.computeSize` instead — only affects the reference image widget's height, not the entire node.

## Parameter Over-Detail Fix

User provided 8-shot sample storyboard full of numerical parameters (cm, dB, Hz, 色相, 饱和度). Rejected entirely: "太他妈的复杂了！！！没有任何AIGC模型能理解这样的描述"

**Fix applied in _build_global_context:**
"禁止使用数值参数（毫米/厘米/dB/色相值/密度等），用视觉化语言描述。禁止微观生物学细节（毛细血管、毛密度、肌肉名称等）"

**Also fixed storyboard template:**
- Removed "800字以上" requirement
- Removed "色相饱和度明度参数" 
- Removed "关节角度和肌群状态"
- Removed "相机焦距和光圈参数"
- Replaced with: "角色肢体动作+面部微表情+场景环境+光源方向/色彩氛围+构图方式"

**All 21 prompt templates need this audit** — the global context fix propagates to all modes, but individual mode templates may still contain their own numerical parameter requirements.
