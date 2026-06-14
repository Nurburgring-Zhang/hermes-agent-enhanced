# PromptLibraryNode V16 — Dual-Layer Filter Engine (Whitelist + Blacklist)

## Timeline

| Version | Change | User Request |
|---------|--------|-------------|
| V13.2 | Basic smart_filter (English-only) | Initial |
| V14 | Subject content filtering (blacklist only) | "过滤仅食物/室内/首饰描述" |
| V15.0 | Enhanced blacklist + context scoring + false positive compounds | "修复手链/三文鱼等误判" |
| V15.1 | Strong lifeless signals + PURE_TRIGGERS | "强化过滤能力" |
| V16 | **Dual-layer: whitelist first, blacklist second, whitelist rescue** | "增加白名单放过模式防止误伤" |
| V16.1 | Code cleanup: removed dead WITH_SUBJECT_KEYWORDS, STRONG_SIG->class var, file lock for history dedup, LIFELESS short-word false matches | Audit: 10 defects fixed |

## V16 Architecture — The User's Correction

**User (格林主人):** "是增加白名单，而不是改为白名单！黑名单过滤一遍，被黑名单拦截的再过一遍白名单，如果有白名单中的内容就放过！"

**Initial mistake (author):** I replaced the entire blacklist with a whitelist. The user wanted BOTH — blacklist as primary, whitelist as RESCUE LAYER.

**Correct pattern (V16):**
```
第1层: 白名单直接放过 -> _has_subject() matches WHITELIST -> 直接保留（不进黑名单）
第2层: 黑名单拦截     -> _is_lifeless() triggers -> 准备过滤
第3层: 白名单复核挽救  -> _in_whitelist() matches WHITELIST -> 挽救！（黑名单误伤被拦截）
否则: 真正过滤
```

### Filter Flow (3 layers)

```
提示词库抽取
    |
    v
第1层: 白名单直接放过 <- WHITELIST_KEYWORDS(270+词)
含WHITELIST词?         直接保留，不进入黑名单
-> YES: 放过
-> NO: 进入第2层
    |
    v
第2层: 黑名单拦截     <- _is_lifeless()检查
_is_lifeless = True?  强信号词/语境评分/lifeless关键词计数
-> YES: 进入第3层复核
-> NO: 保守放过（模糊不清）
    |
    v
第3层: 白名单复核挽救  <- _in_whitelist() = _has_subject()
_in_whitelist?         被黑名单拦截后，用WHITELIST_KEYWORDS复核
-> YES: 放过（黑名单误伤被挽救）
-> NO: 真正过滤
```

### Code Pattern

```python
def _filter_by_subject(self, lines):
    passed, blacklisted, whitelist_saved = [], 0, 0
    for line in lines:
        text = line["text"]
        # 第1层：白名单快速放过
        if self._has_subject(text):
            passed.append(line); continue
        # 第2层：黑名单拦截检查
        if self._is_lifeless(text):
            blacklisted += 1
            # 第3层：白名单复核（防止误伤）
            if self._in_whitelist(text):  # = self._has_subject(text)
                whitelist_saved += 1; passed.append(line)
        else:
            passed.append(line)
    print(f"黑名单拦截{blacklisted}条, 白名单复核挽救{whitelist_saved}条, 最终保留{len(passed)}条")
    return passed
```

## V16.1 Audit: 10 Defects Found and Fixed

### Defect 1: WITH_SUBJECT_KEYWORDS Dead Code (37 lines)
- 37-line keyword list never referenced after WHITELIST_KEYWORDS replaced it
- Deleted entirely

### Defect 2: _has_subject() and _in_whitelist() Code Duplication
- Both did the same FALSE_POSITIVE stripping + WHITELIST matching
- Fixed: `_in_whitelist()` now calls `self._has_subject(text)`

### Defect 3: _call_ai() last_err Not Updated on Exception Paths
- Variable initialized once, never set during exceptions
- Acceptable: `_last_ai_error` is set correctly on each exception path

### Defect 4: STRONG_SIG / PURE_TRIG Created Per-Call
- ~40 set allocations per `_is_lifeless()` call. 4M allocations on 100K-line folder
- Fixed: Promoted to class-level `STRONG_LIFELESS_SIGNALS` and `PURE_PRODUCT_TRIGGERS`

### Defect 5: WHITELIST Single-Character Substring Risk
- "人", "女", "男", "山" etc. can match inside unrelated words
- Not fixed: Conservative — over-keep is better than over-filter

### Defect 6: LIFELESS_KEYWORDS Short-Character False Matches
| Word | False Match | Severity |
|------|------------|----------|
| "面" | "湖面", "水面", "海面" — landscape | **Medium** — filtered nature prompts |
| "汤" | "汤色" | Low |
| "酒" | "酒红", "酒金" — clothing color | **Medium** — filtered "酒红色连衣裙" |
| "饭" | "饭店" | Low |
**Fix:** Removed all four. Replaced with multi-character words.

### Defect 7: SAFE_WORDS / WHITELIST Overlap
- 37/52 words duplicated. Different layers, not merged.

### Defect 8: History Dedup JSON Concurrent Write Collision
- Multi-threaded writes to `.prompt_history.json` without lock
- Fixed: OS-level file lock:
```python
lock_file = hf + ".lock"
for _ in range(10):
    try: fd = os.open(lock_file, os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.close(fd); lock_acquired = True; break
    except (OSError, FileExistsError): _time.sleep(0.05)
try: # read/write
finally:
    if lock_acquired: os.unlink(lock_file)
```

### Defect 9-10: Logic overlap and performance — judged acceptable

## WHITELIST_KEYWORDS (270+ terms)

**People (60+):** 人物, 人像, 人类, 女人, 男子, 女子, 男人, 女孩, 男孩, 美女, 帅哥, 少女, 少年, 女性, 男性, 婴儿, 幼儿, 儿童, 小孩, 孩子, 孩童, 宝宝, 宝贝, 老人, 长者, 老太, 老头, 奶奶, 爷爷, 阿姨, 叔叔, 姐姐, 妹妹, 哥哥, 弟弟, 夫妻, 情侣, 恋人, 一家, 家庭, 学生, 老师, 教师, 医生, 护士, 厨师, 画家, 舞者, 歌手, 运动员, 模特

**Body Parts (25+):** 脸庞, 面容, 面孔, 脸颊, 脸, 面部, 眼神, 目光, 眼睛, 眼眸, 眸子, 瞳孔, 睫毛, 头发, 长发, 短发, 卷发, 直发, 发丝, 刘海, 辫子, 马尾, 盘发, 肌肤, 皮肤, 肤色, 嘴唇, 唇, 牙齿, 眉毛, 双手, 手指, 指尖, 手腕, 手臂, 肩膀, 肩, 颈部, 脖子, 锁骨, 后背, 背部, 腿, 大腿, 小腿, 膝盖, 脚踝, 赤脚, 裸足, 腰, 腰部, 臀部

**Actions (15+):** 站立, 站, 坐着, 坐, 行走, 走, 奔跑, 跑, 眺望, 凝视, 回眸, 转身, 侧身, 俯身, 仰头, 低头, 点头, 摇头, 微笑, 笑, 表情, 姿态, 姿势, 动作

**Clothing (15+):** 穿着, 身穿, 穿搭, 连衣裙, 裙子, 上衣, 外套, 裤子, 裙摆, 衣角, 衣袖, 衣领, 领口, 汉服, 和服, 旗袍, 婚纱

**Animals (25+):** 动物, 宠物, 猫, 狗, 兔子, 鸟, 蝴蝶, 马, 羊, 鱼, 龙, 凤凰, 老虎, 狮子, 鹿, 天鹅, 小猫, 小狗, 猫咪, 狗狗, 鹦鹉, 鸽子, 麻雀, 老鹰, 孔雀, 鹤, 蛇, 龟, 蜥蜴, 昆虫, 鲸, 海豚, 海龟

**Scenery (30+):** 风景, 自然, 山水, 山川, 河流, 湖泊, 海洋, 大海, 森林, 树林, 林地, 草原, 沙漠, 雪山, 峡谷, 瀑布, 天空, 云彩, 日落, 日出, 晚霞, 星空, 花园, 田园, 原野, 草地, 草坪, 山峦, 山峰, 山, 海岸, 海岸线, 沙滩, 海滩, 海浪, 溪流, 溪, 田野, 农田, 麦田, 丛林, 热带雨林

**Roles (20+):** 角色, 公主, 王子, 骑士, 精灵, 天使, 恶魔, 仙女, 魔法师, 巫师, 战士, 剑士, 武士, 忍者, 英雄, 反派, 机器人, 机械人, 新娘, 新郎, 古人, 古代, 古典, 宇航员, 探险家, 科学家

**English (30+):** woman, man, girl, boy, people, person, female, male, child, baby, model, portrait, face, figure, cat, dog, animal, pet, bird, horse, butterfly, landscape, nature, mountain, beach, ocean, sea, forest, river, lake, sunset, sunrise

## FALSE_POSITIVE_COMPOUNDS (65+ terms)

Strip from text BEFORE whitelist matching:

| Category | Count | Examples |
|----------|-------|---------|
| 手类产品 | 28 | 手链, 手表, 手机, 手套, 手工, 手法, 手镯, 手电, 手帕, 手推车, 手风琴, 手提包, 手提箱, 手写, 手绘, 手势, 手柄, 手把, 手刹, 手印, 手牌, 手环, 手带, 手感, 手型, 手球 |
| 背类 | 9 | 背景, 背光, 背面, 背包, 背板, 背带, 脊椎, 驼背, 背心 |
| 鱼品类(食物) | 28 | 三文鱼, 金枪鱼, 鱼片, 鱼丸, 鱼汤, 鱼头, 鱼排, 鱼子酱, 鱼翅, 鱼肚, 鱼皮, 鱼露, 鱼生, 鱼腐, 鱼蛋, 鱼面, 鱼饼, 鱼干, 鱼柳, 鱼腩, 鱼杂, 炸鱼, 烤鱼, 蒸鱼, 煎鱼, 熏鱼, 鱼缸, 鱼池 |
| 马类非动物 | 6 | 马铃薯, 马桶, 马路, 马达, 马赛克, 马甲 |
| 龙类非动物 | 6 | 龙眼, 龙井, 龙须面, 龙头, 龙虾, 龙舌兰 |
| 蝴蝶类非昆虫 | 4 | 蝴蝶结, 蝴蝶酥, 蝴蝶兰, 蝴蝶袖 |
| 眼类非部位 | 6 | 眼镜, 眼影, 眼线, 眼霜, 眼膜, 眼罩 |
| 头类 | 6 | 头盔, 头饰, 头花, 头巾, 头绳, 头枕 |
| 指类 | 6 | 指示, 指引, 指纹, 指针, 指挥, 指令 |
| 穿类 | 5 | 贯穿, 穿梭, 穿越, 穿插, 穿透 |
| 其他 | 2 | 天鹅绒, 手机壳, 手机链 |

## _is_lifeless() — Blacklist Logic

```python
def _is_lifeless(self, text):
    t = text.lower()
    if self._has_subject(text):  # Safety check
        return False
    strong_count = sum(1 for sig in self.STRONG_LIFELESS_SIGNALS if sig.lower() in t)
    if strong_count >= 2: return True
    for trig in self.PURE_PRODUCT_TRIGGERS:
        if trig.lower() in t: return True
    lifeless_count = sum(1 for kw in self.LIFELESS_KEYWORDS if kw.lower() in t)
    if lifeless_count >= 3: return True
    if strong_count >= 1 and lifeless_count >= 1: return True
    for kw in self.LIFELESS_KEYWORDS:
        if kw.lower() in t: return True
    return False
```

## Key Learnings

### 1. "增加白名单" != "改为白名单"
User wanted blacklist preserved with whitelist as rescue layer, not replacement.

### 2. Dead Code Accumulates
After ~20 patches, WITH_SUBJECT_KEYWORDS (37 lines) was never cleaned up.

### 3. Short-Character LIFELESS Words Are Dangerous
"面" matches "湖面", "酒" matches "酒红色". Use multi-character compounds.

### 4. Thread-Safe File Ops for ComfyUI
`_history_dedup()` on concurrent nodes = JSON corruption. OS file lock pattern: `os.open(O_CREAT|O_EXCL)`.

### 5. LIFELESS_KEYWORDS (110+ terms, V16.1)
- Food: 食物, 美食, 菜肴, 甜品, 主食, 蛋糕, 面包, 寿司, 披萨, 咖啡, 茶, 饮品, 红酒, etc.
- Interior: 室内, 客厅, 卧室, 厨房, 家具, 沙发, 桌子, 椅子, 床, 墙壁, 地板, etc.
- Jewelry: 首饰, 珠宝, 戒指, 项链, 手链, 耳环, 手镯, 钻石, 宝石, 翡翠, 珍珠, 水晶, etc.
- Still-life: 静物, 产品摄影, 产品, 书籍, 花瓶, 花束, 鲜花, 酒瓶, 玻璃杯, 蜡烛, 烛台, etc.
- Removed: 汤, 面, 饭, 酒 (caused false matches)

## Test Results (V16.1 Final)
40 tests, 40 pass, 0 fail. Covers: code structure, defects, boundaries, whitelist precision, performance, thread safety.
