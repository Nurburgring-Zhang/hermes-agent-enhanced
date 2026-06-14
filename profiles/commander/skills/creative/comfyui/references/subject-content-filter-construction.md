# ComfyUI 自定义节点：主体内容过滤 — 增强集构建方法论

> 来源：PromptLibraryNode V17.0 开发（2026-05-22）
> 核心经验：四个增强集（LIFELESS/WHITELIST/FALSE_POSITIVE/STRONG_SUBJECT）需要精确保留下效果、防止误杀。

## 架构：两阶段过滤

```
输入行 → _smart_filter（智能过滤，先判主体再判LIFELESS）→ _filter_by_subject（正则主体检测）→ 有效行
```

### _smart_filter 逻辑（关键）
1. **先查STRONG_SUBJECT_SIGNALS** — 有主体信号直接放行。即使包含LIFELESS词（如"少女品尝马卡龙"）
2. **无主体时查LIFELESS_KEYWORDS** — 命中则过滤。纯产品/食物/室内等
3. 不返回None → 过滤后行数不变时返回None（表示无过滤发生）
4. 返回None → 上层检查并跳过smart_filter统计

### _filter_by_subject 逻辑（第二道防线）
- 正则匹配中英文主体词（人物/动物/风景/动漫等）
- 仅检测到明确主体词才放行
- 纯LIFELESS内容已经_smart_filter过滤过，但_fiLter_by_subject作为第二道防线

## 增强集构建原则

### LIFELESS_KEYWORDS — 纯无生命内容检测词

**角色**: 在没有STRONG_SUBJECT时，判断是否纯无生命
**阈值**: 每行如果匹配到任意一个LIFELESS词，且无主体，则过滤

```
❌ 错误："风景""日落""自然""山川"在LIFELESS中
    → "壮丽的日落山脉全景"会被过滤（4个LIFELESS命中，无STRONG_SUBJECT命中——如果忘记加"日落"到STRONG_SUBJECT）

✅ 正确: LIFELESS只放真正无生命的：
    - 食物类（红烧肉、马卡龙、披萨等全部具体菜名）
    - 珠宝首饰类
    - 器皿餐具类
    - 家具类
    - 电子产品类
    - 车辆类
    - 服饰箱包平铺类
    - UI/设计类
```

**食物分类示例**（约100词，覆盖中/西/日/糕点/饮料/水果）：
```
中餐: 红烧肉/宫保鸡丁/麻婆豆腐/北京烤鸭/小笼包/火锅/烧烤
西餐: 牛排/披萨/意面/汉堡/三明治/沙拉/培根
日料: 寿司/刺身/拉面/天妇罗/味噌汤
糕点: 马卡龙/提拉米苏/蛋挞/蛋糕/曲奇/布丁
饮料: 拿铁/卡布奇诺/奶茶/珍珠奶茶/果汁
水果: 苹果/草莓/芒果/榴莲/西瓜
食材: 土豆/西红柿/黄瓜/鸡蛋/豆腐
```

### WHITELIST_WORDS — 强烈主体信号（跳过smart_filter）

**角色**: 有这些词就必定有主体，直接放行
**作用范围**: _smart_filter之前（先查白名单→有就放行→不执行LIFELESS检查）

**分类示例**（约100词）：
```
人物身份: 公主/王子/女王/骑士/忍者/武士/女仆/修女
人物职业: 舞者/歌手/画家/诗人/学生/教师/医生
动物: 猫咪/小狗/兔子/鹦鹉/海豚/蝴蝶/熊猫
风格: 宫崎骏/吉卜力/古风/汉服/赛博朋克
```

### STRONG_SUBJECT_SIGNALS — 强主体信号（_smart_filter内部使用）

**角色**: 先查这个set，有则直接放行（不执行LIFELESS检查）
**关键**: 必须包含所有可能的有效主体词——否则会被LIFELESS误杀

```
✅ 必须覆盖:
  - 中英文人物词（woman/man/girl/boy/human/people）
  - 中文自然词（日落/日出/山脉/瀑布/峡谷）
  - 英文自然词（mountain/ocean/beach/sunset/forest）
  - 动物（cat/dog/bird/butterfly/horse/dragon）
  - 身体动作词（站立/端坐/行走/微笑/holding/standing）
```

### FALSE_POSITIVE_COMPOUNDS — 假阳性复合词排除

**角色**: 当命中LIFELESS关键词时，先检查是否属于"有主体的复合词"
**例如**: "产品设计"含LIFELESS"产品"但有主体的设计场景应放行

## 数字统计参考（V17.0最终版）

| 增强集 | 条目数 | 新增内容特点 |
|--------|--------|-------------|
| LIFELESS_KEYWORDS | 498 | 中餐100+/西餐30+/日料15+/糕点30+/饮料25+/水果30+/食材35+/珠宝15+/餐具30+/家具40+/电子产品20+/车辆10+/服饰30+ |
| WHITELIST_WORDS | 249 | 人物100+/动物80+/风格30+/英文词30+ |
| FALSE_POSITIVE_COMPOUNDS | 52 | 设计类20+/英文复合10+/语句10+ |
| STRONG_SUBJECT_SIGNALS | 236 | 人像80+/动物50+/自然60+/花朵20+/动作词26+ |

## 关键陷阱

### 1. 不要把有效主体词放进LIFELESS
```
❌ "风景""日落""自然"在LIFELESS → "壮丽的日落山脉全景"除非STRONG_SUBJECT也有这些词否则被过滤
✅ LIFELESS只放"产品""食物""珠宝""家具"等真正无生命的
```

### 2. _filter_by_subject的正则需要英文覆盖
```
❌ 只有中文词 → "A beautiful sunset over mountains"被滤掉
✅ 增加r"sunset", r"mountain", r"woman", r"cat", r"bird", r"landscape"等
```

### 3. 食物+主体的混合prompt不应被过滤
```
✅ "一位优雅的女性在品尝马卡龙" — STRONG_SUBJECT中"女性"先命中→放行
✅ "a woman drinking coffee" — _filter_by_subject中"woman"命中→放行
❌ "一盘红烧肉" — 无STRONG_SUBJECT命中→LIFELESS命中→过滤
```

### 4. ComfyUI节点注册必不可少
```
NODE_CLASS_MAPPINGS = {
    "PromptLibraryNodePro": PromptLibraryNodePro,
}
```
没有这行代码，ComfyUI加载目录时报 `(IMPORT FAILED)`——即使Python import正常。
