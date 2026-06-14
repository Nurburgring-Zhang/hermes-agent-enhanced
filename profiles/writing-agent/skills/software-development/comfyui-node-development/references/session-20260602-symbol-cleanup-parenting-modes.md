# 2026-06-02 会话：总纲硬编码符号清零 + 儿童模式重写 + GitHub发布

## 背景

格林主人多次因符号标记问题发火（"妈说了很多次去掉**和-""操你妈""去掉所有无用符号"）。本次会话做了四轮修正：

1. 角色特征维度定义精准化
2. 儿童视频格式二格式修正（从编号1~7改成起承转合四幕）
3. 所有4种儿童模式输出格式定义补齐
4. 所有总纲硬编码符号清零（4处header）
5. 所有system prompt末尾加输出约束

## 修改清单

### 文件
`/mnt/d/ComfyUI/custom_nodes/PromptLibraryNode/__init__.py`（1916行）

### 一、角色特征定义修改（14处统一）

旧：`角色特征：有角色特征变化时输出完整角色描述（外貌、服装、表情变化，2-3句）。无变化时不出现`

新：`角色特征：仅在角色外貌/服装/状态有实质性变化时输出（换装/变脏/受伤/新增饰品等可见变化）。禁止写角色动作叙事（那是画面维度的事）。无变化时此行整行不出现。`

位置：
- 5处输出格式定义（L1087/L1104/L1120/L1139/L1373）
- 3处变化标注规则旧版（L1245/L1440/L1449）
- 1处画面铁律#10（L1250）
- 1处变化必须可见（L1383）
- 1处单引号格式（L1515）
- 1处选项格式（L1540）
- 1处变化必须可见单引号（L1523）

### 二、总纲硬编码符号清零

共4处header，统一去掉 【】、数字编号、道具/武器斜杠：

旧：`f"【绘本总纲】\n"` + `f"1、整体视觉风格：\n"` ... `f"7、核心叙事设定：\n"`
新：`f"绘本总纲\n"` + `f"整体视觉风格：\n"` ... `f"核心叙事设定：\n"`

- 故事板总纲（L583-600）
- 绘本总纲（L632-646）
- 短剧总纲（L675-689）
- 儿童视频总纲（L722-738）

"格林主人"字样脱敏为"定制版"

### 三、`_build_child_v2` 从编号1~7改为四幕结构

旧（被我上一轮错改的编号格式）：
```
1.时间·空间锚定
2.画面描述
3.动态描述【动态】
4.分镜场景
5.角色特征
6.旁白/对话
7.特效/TIPS
```

新（格林主人实际需求的格式）：
```
第一幕起
【场景】地点·天气·时间·内外
画面描述：场景氛围、光线、色彩情绪，2-3句
旁白：叙事旁白文字
对话：角色名（表情动作标注）：对话内容
TIPS：叙事功能或关键提示
（分镜场景和角色特征仅在变化时输出，无变化时不出现）
动态描述【动态】：动效和运动方式（可选，有动效变化时必出）
```

末尾加了输出示例参考。

### 四、`_build_child_gif` 重写

旧：只有4行 `- 每页只表达1个核心动作\n- 画面简洁\n- 动效标注循环方式\n- 首帧等于末帧`

新：
```
角色设定：儿童动画编剧兼分镜师
输出格式：第N页，核心动作/画面/动效三维度
变化维度：分镜场景和角色特征仅在变化时输出
创作原则：7条
输出约束：禁止一切符号标记
```

### 五、`_build_child_book` 重写

旧：7行零散规则，无输出格式定义

新：
```
角色设定：儿童绘本编剧兼插画师
输出格式：第N页，画面/文案/旁白对话/视觉连续性提示/构图与景别五维度
变化维度：分镜场景和角色特征仅在变化时输出
创作原则：8条（包括不说教公式/角色一致性/视觉节奏/负空间构图/八大红线/情绪正向等）
输出约束：禁止一切符号标记
```

### 六、输出约束统一

所有4个儿童模式末尾统一加：
```
输出约束：严禁使用任何符号标记——禁止#、禁止**、禁止-开头、禁止→、禁止1. 2. 3.编号、禁止---分隔线。直接用纯文字叙述。各维度之间用换行分隔，不要用符号装饰维度名称。
```

## GitHub发布流程

### 脱敏
- `grep -in '格林\|administrator\|password\|token\|secret\|D:\\\\\|/mnt/d'` 
- 替换"（格林主人定制）" → "（定制版）"
- 替换"（格林主人最高指令）" → 空字符串
- 确认无API密钥/路径硬编码（默认 `localhost:1234` 安全）

### 初始化仓库
```bash
cd /mnt/d/ComfyUI/custom_nodes/PromptLibraryNode
git init
git branch -m main
git add .
git commit -m "初始提交：..."
git remote add origin https://github.com/Nurburgring-Zhang/ComfyUI-PromptLibraryNode.git
```

### token配置
```bash
# classic token，勾选repo全部权限
git remote set-url origin https://USER:TOKEN@github.com/USER/REPO.git
git push -u origin main
git remote set-url origin https://github.com/USER/REPO.git  # push完立即去掉URL中的token

# credential store
git config --global credential.helper store
echo "https://USER:TOKEN@github.com" > ~/.git-credentials
```

### 成果
仓库：https://github.com/Nurburgring-Zhang/ComfyUI-PromptLibraryNode
6文件：__init__.py(1916行) + web/PromptLibraryNode.js(190行) + 3个故事感文库 + .gitignore + README.md
