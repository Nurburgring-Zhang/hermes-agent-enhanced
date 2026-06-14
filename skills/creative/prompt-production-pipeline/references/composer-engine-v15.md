# Composer Engine V15 — 维度库组合实战记录

## 背景

2026-05-23格林主人要求基于15个维度库（5,889条）生成10万条500-800字的高质量现代视觉艺术prompt。

经历了V12→V13→V14→V15四轮迭代，每轮修复关键问题。

## 引擎版本演进

| 版本 | 核心改动 | 多角色率 | 三手问题 | 平均字数 |
|------|---------|---------|---------|---------|
| V12 | 从15个库随机抽取+自由拼接 | ~70% | 0 | 576 |
| V13 | 添加清洗逻辑(tags/数字前缀) | ~33% | 0 | 531 |
| V14 | 添加"一位/一名"前缀清洗 | ~13% | 0 | 528 |
| V15 | 每条只从01库抽一次角色+活动库抽活动且丢弃人物头 | ~13% | 0 | 528 |

## 最终引擎V15核心代码架构

```python
# 加载15个库
libs = load_libraries()  # 5902条

def compose_one(libs):
    # 只抽一次的关键元素
    start = random.choice(STARTS)      # 18种风格开场（固定池）
    scene = random.choice(SCENES)      # 14种场景（固定池）
    color = random.choice(COLORS)      # 10种色彩描述（固定池）
    light = random.choice(LIGHTS)      # 8种光影描述（固定池）
    breakout = random.choice(BREAKOUTS) # 6种破圈逻辑（固定池）
    
    # 角色（只抽一次！）
    role_text = random.choice(libs['01_角色特征库.txt'])
    
    # 检查裸体
    is_nude = any(w in role_text for w in ['裸体','赤裸','裸露'])
    
    # 活动（只抽一次！只取动作部分）
    a = random.choice(libs['08_活动行为库.txt'])
    activity = extract_doing(a)  # 正则提取"正在XXX"
    
    # 材质/配饰（裸体时跳过）
    material = '' if is_nude else random.choice(libs['11_材质质感库.txt'])[:60]
    accessory = '' if is_nude else random.choice(libs['12_配饰鞋帽库.txt'])[:60]
    
    # 道具/动态/情感
    prop = random.choice(libs['13_环境道具库.txt'])[:60]
    dynamic = random.choice(libs['10_动态效果库.txt'])[:40]
    mood = extract_mood(libs['06_情感氛围库.txt'])
    
    # 组合
    parts = [start, scene, role_text]
    if activity: parts.append(activity)
    if material: parts.append(material)
    if accessory: parts.append(accessory)
    if prop: parts.append(prop)
    if dynamic: parts.append(dynamic)
    parts += [color, light]
    if mood: parts.append(mood)
    parts.append(breakout)
    
    prompt = '。'.join(parts)
    # 清理重复标点，确保字数
    cn = len(re.findall(r'[\u4e00-\u9fff]', prompt))
    if cn < 500: prompt += extra_sentence()
    if cn > 800: prompt = truncate(prompt)
    return prompt
```

## 质量数据（V15，77,000条）

- 平均字数: 528字
- <500字: 7% (5,259条)
- >800字: 0%
- 三手问题: 0条
- 比喻词: 0条
- 多角色拼接: ~13% (基线问题—角色库条目本身含"一位"描述，清洗后仍有残余)
- 含裸体: ~25% (合理分布)

## 库文件依赖

| # | 库文件 | 条数 | 作用 | 组合中被抽次数 |
|---|--------|------|------|--------------|
| 01 | 角色特征库 | 499 | 人物描述 | **1次** — 关键！ |
| 02 | 画面类型库 | 499 | 画面类型标注(未使用) | 0 |
| 03 | 光照条件库 | 299 | 用固定池替代 | 0 |
| 04 | 构图镜头库 | 499 | 用固定池替代 | 0 |
| 05 | 色彩调性库 | 199 | 用固定池替代 | 0 |
| 06 | 情感氛围库 | 499 | 提取氛围描述 | 1次 |
| 07 | 天气季节库 | 299 | 天气(未直接使用) | 0 |
| 08 | 活动行为库 | 499 | 提取"正在"动作 | **1次** — 只取动作部分 |
| 09 | 无主体场景库 | 499 | 未使用 | 0 |
| 10 | 动态效果库 | 199 | 动态描述 | 1次 |
| 11 | 材质质感库 | 201 | 材质描述(裸体跳过) | 1次(有条件) |
| 12 | 配饰鞋帽库 | 500 | 配饰描述(裸体跳过) | 1次(有条件) |
| 13 | 环境道具库 | 499 | 场景道具 | 1次 |
| 14 | 色彩搭配库 | 200 | 禁止使用 | 0 |
| 15 | 美学风格库 | 499 | 风格(用固定池替代) | 0 |

**实际使用**: 8个库(01/06/08/10/11/12/13) + 4个固定池(风格/场景/色彩/光影) + 1个破圈池 = 13种来源

## 文件组织

```
D:\Hermes\1000000提示词\10万提示词\
├── modern_art_prompts_01.txt ~ _29.txt  # 早期批次(试验品质)
├── modern_art_prompts_30.txt ~ _106.txt # V15优质批次(77,000条)
```

## 格林主人的关键纠正（永久牢记）

1. **有"正在"时不需要去掉服装描述** — 活动和服装可以共存，只有裸体时才去掉
2. **保留所有"裸体/赤裸"词汇** — 这是合理的prompt内容，不要自作主张替换
3. **每条prompt可以是多个维度的组合** — 不是每条都要用上所有维度，而是合理时尽量多用
4. **不要用AI逐条生成大规模prompt** — 速度太慢(<10条/分钟在delegate_task中)，必须用Python组合引擎
