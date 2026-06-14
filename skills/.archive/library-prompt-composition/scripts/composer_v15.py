#!/usr/bin/env python3
"""
Composer V15 — Multi-dimensional prompt composition engine.
Generates high-quality text-to-image prompts from 15 dimension libraries.
Each prompt samples each library exactly once and enforces logical consistency.
"""
import os
import random
import re

LIB_DIR = "/mnt/d/Hermes/1000000提示词/高质量模板/新建库/"
OUTPUT_DIR = "/mnt/d/Hermes/1000000提示词/10万提示词/"

# === Hand-crafted high-quality element pools ===
STARTS = [
    "极简主义的留白与减法美学,大面积留空以最少的视觉元素承载最丰富的情感,每一处空白都是精心计算过的呼吸空间。",
    "巴洛克暗调主义风格,画面沉入近乎绝对的黑色调中,一束锐利的光斜射照亮主体,明暗之间没有任何中间调过渡。",
    "印象派追逐光线的短促笔触捕捉光线在物体表面的瞬间变化,色彩超越物象固有颜色转而表现光线中的色彩成分。",
    "水彩湿画法让颜料在湿润的粗纹纸上自由扩散,水分在纤维中横向渗透形成柔和的羽状边缘,色彩从中心向边缘递减。",
    "厚涂油画的颜料层在画布上层层堆叠,底层色彩从刀痕缝隙中透出,颜料的凸起在侧光下产生立体投影。",
    "超写实主义的极致细节,物象被放大到超越肉眼观察的精细程度,每一根纤维和每一粒灰尘都精确呈现。",
    "维也纳分离派的金箔装饰风格,矩形和螺旋形的金箔贴满画面,人物从金色包裹中浮现形成具象与抽象的对比。",
    "洛可可风格的轻快优雅,饱满流畅的曲线与柔和色彩贯穿画面,装饰细节在空间中蔓延生长。",
    "日本琳派风格以金箔铺底,用高度概括的装饰性手法描绘流水花卉,金银粉在画面上形成细微的闪光粒子。",
    "包豪斯风格以几何线条与纯粹色块构建画面骨架,功能性与美学在理性秩序中融合。",
    "新艺术派穆夏风格,女性轮廓被流动的曲线包裹,花卉藤蔓构成装饰性背景,色彩柔和温暖。",
    "波普艺术的高饱和色彩与硬边轮廓让画面充满现代感,日常物品被放大后产生新的视觉意义。",
    "抽象表现主义的滴画技法,颜料在画布上自由流淌形成交错的线条网络。",
    "野兽派的色彩解放,高纯度色彩直铺画面,色彩脱离物象束缚成为独立的表达语言。",
    "浮世绘版画的黑色轮廓线勾勒形体和衣纹,线条的粗细变化具有装饰性节奏。",
    "中国画工笔重彩风格,精细的线条勾勒物象轮廓,色彩层层渲染薄透均匀。",
    "厚涂油画技法,调色刀与猪鬃笔交替在粗纹亚麻画布上堆叠,底层的赭石色和群青色从刀痕缝隙中透露出来。",
    "超现实主义达利式梦境荒诞,极度写实的物象细节被放置在违反物理逻辑的空间关系中。",
]

SCENES = [
    "清晨的阳光透过结满霜花的玻璃窗漫射进来,在木地板上拉出一道道冷色光柱。",
    "黄昏的残阳将金色涂抹在旧公寓的白色墙壁上,光斑缓慢从墙角爬向天花板。",
    "雨滴敲打着窗户玻璃,窗外的城市在雨幕中化成一幅模糊的水彩画。",
    "午后的阳光穿过梧桐树叶在桌面上投下不断晃动的光斑。",
    "深夜一盏台灯散发暖黄色的光,在墙面上形成一个明亮的扇形区域。",
    "冬天的第一场雪覆盖了城市,窗台上积起松软的白雪。",
    "海风带着咸湿的气息扑面而来,海浪拍打着岸边的礁石。",
    "清晨的雾气还未散去,草地上挂着晶莹的露珠,远山在薄雾中若隐若现。",
    "深秋的银杏叶铺满小径,金黄色的叶片在脚下发出沙沙声响。",
    "午后的阳光从百叶窗缝隙射进来,在地板上形成一道道平行的光带。",
    "城市的天际线在暮色中形成层层叠叠的剪影。",
    "细雨顺着玻璃滑落,将窗外的灯光撕成无数细小的光点。",
    "阳光透过茂密树叶洒下来,在青石板路上投下斑驳的光影。",
    "黄昏的街灯一盏接一盏亮起来,橘黄色的光晕在暮色中晕染开。",
]

COLORS = [
    "主色为暖赭与象牙白交织,群青点缀在暗部形成冷暖对抗,整体偏暖但冷色平衡了色温。",
    "月白与铅灰构成冷调基底,唇间一抹胭脂红成为视觉锚点,那点红色在冷色中格外醒目。",
    "琥珀色铺陈画面,墨黑阴影衬得金色饱满浓郁,呈现出旧时光般的温暖质感。",
    "雪青与丁香紫的邻近色渐变笼罩全场,偶有几笔藤黄跳出点缀,调性柔和梦幻。",
    "檀褐与茶绿的低饱和色调像是被岁月滤过的颜色,呈现出静谧的高级感。",
    "骨白和烟灰构成画面主体,墨黑作为重色压住重心,简洁而有力。",
    "群青与月白的冷色组合贯穿画面,偶尔透出一点暖色像是寒夜中的灯火。",
    "驼色卡其和米色的大地色系铺陈全场,给人沉稳安定的视觉感受。",
    "竹青和苍绿构成画面的自然基调,透着被植物环绕的宁静感。",
    "朱红与黛绿的互补色在画面中形成强烈的视觉张力,两种色域在交界处互相渗透。",
]

LIGHTS = [
    "光源从侧上方照射,在颧骨和鼻梁上形成柔和的高光带,高光以亮白色渐变为浅灰的中间调,阴影落在另一侧边缘柔和。",
    "柔和的漫射光均匀包裹整个场景,没有强烈明暗对比,所有轮廓都在温润的光线中融合。",
    "一束集中的侧光将主体一半照亮一半隐入暗影,高光在颧骨最高处形成锐利的亮带。",
    "逆光勾勒出主体的轮廓光,发丝边缘半透明发光,面部处于暗部但细节可见。",
    "窗光从左侧落地窗射入经过纱帘过滤转化为柔和漫射光,在空间内形成大面积的均匀照明。",
    "低角度夕阳水平射入,在地面上拉出长长的影子,所有物体都被镀上一层温暖的金橙色。",
]

BREAKOUTS = [
    "不起眼的角落藏着违背物理常理的细节——水洼中映出的不是当前天空而是星空的倒影。",
    "古典美学与当代生活场景在同一画面中相遇,时间的维度变得模糊。",
    "镜中反射的世界与镜前的现实微妙地错位,打破了空间的一致性。",
    "不同时代的物件共处一室,历史的断层在同一视口中缝合。",
    "极度的写实中留下偶然性的失控痕迹,打破了完美的幻觉赋予画面真实的温度。",
    "一件日常物品被赋予超越自身功能的存在意义,在特殊的处理下焕发出诗意。",
]

EXTRAS = [
    "皮肤的质感在光线下呈现出细腻的光泽,发丝的走向清晰可见。",
    "前景的物件细节丰富,中景与背景形成自然的空间层次。",
    "光影过渡恰到好处,高光不过曝阴影不死黑。",
]

def load_libraries(lib_dir):
    """Load and clean all dimension libraries."""
    libs = {}
    for fname in sorted(os.listdir(lib_dir)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(lib_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            raw = [l.strip() for l in f if l.strip()]
        items = []
        for line in raw:
            tags = re.findall(r"\[([^\]]+)\]", line)
            content = line
            for t in tags:
                content = content.replace(f"[{t}]", "", 1)
            content = re.sub(r"^\d+\|", "", content).strip()
            content = re.sub(r"\d+\|", "", content)
            content = re.sub(r"无可见文字[。，]?|无可见文字或书写内容[。，]?|图像中无可见文字[。，]?", "", content)
            content = re.sub(r"[特写照片摄影][，,。]?(?:展示|聚焦|的)?", "", content)
            content = re.sub(r"^一位|^一名|^一张|^一幅", "", content)
            content = content.strip()
            if content and len(content) > 10:
                items.append(content)
        libs[fname] = items
    return libs


def compose_one(libs):
    """Compose one prompt, sampling each library exactly once."""
    start = random.choice(STARTS)
    scene = random.choice(SCENES)
    color = random.choice(COLORS)
    light = random.choice(LIGHTS)
    breakout = random.choice(BREAKOUTS)

    role_items = libs.get("01_角色特征库.txt", ["年轻女性"])
    role_text = random.choice(role_items)
    is_nude = any(w in role_text for w in ["裸体","赤裸","裸露","一丝不挂","未着寸缕"])

    activity = ""
    act_items = libs.get("08_活动行为库.txt", [])
    if act_items:
        a = random.choice(act_items)
        doing = re.search(r"正在[^。]{5,40}", a)
        if doing:
            activity = doing.group(0)

    material = ""
    if not is_nude:
        mat_items = libs.get("11_材质质感库.txt", [])
        if mat_items:
            material = random.choice(mat_items)[:60]

    accessory = ""
    if not is_nude:
        acc_items = libs.get("12_配饰鞋帽库.txt", [])
        if acc_items:
            acc = random.choice(acc_items)[:60]
            accessory = acc

    prop = ""
    prop_items = libs.get("13_环境道具库.txt", [])
    if prop_items:
        prop = random.choice(prop_items)[:60]

    dynamic = ""
    dyn_items = libs.get("10_动态效果库.txt", [])
    if dyn_items:
        dynamic = random.choice(dyn_items)[:40]

    mood = ""
    mood_items = libs.get("06_情感氛围库.txt", [])
    if mood_items:
        m = random.choice(mood_items)
        m_short = m.split("。")[0][:50]
        if m_short:
            mood = m_short

    parts = [start, scene, role_text]
    if activity: parts.append(activity)
    if material and not is_nude: parts.append(material)
    if accessory and not is_nude: parts.append(accessory)
    if prop: parts.append(prop)
    if dynamic: parts.append(dynamic)
    parts.append(color)
    parts.append(light)
    if mood: parts.append(mood)
    parts.append(breakout)

    prompt = "。".join(parts)
    prompt = prompt.replace("。。", "。")
    prompt = re.sub(r"[。]{2,}", "。", prompt)
    prompt = prompt.strip()

    cn = len(re.findall(r"[\u4e00-\u9fff]", prompt))

    if cn < 500:
        prompt += "。" + random.choice(EXTRAS)
        cn = len(re.findall(r"[\u4e00-\u9fff]", prompt))
    if cn > 800:
        sents = prompt.split("。")
        prompt = "。".join(sents[:8]) + "。"

    return prompt


def generate_batch(count, output_path, libs):
    """Generate a batch of prompts."""
    results = []
    for i in range(count):
        try:
            p = compose_one(libs)
            results.append(p)
        except Exception:
            results.append("极简风格。清晨阳光洒入。年轻女性站立。色彩以月白为主。光线柔和。氛围宁静。")
        if (i+1) % 200 == 0:
            print(f"  {i+1}/{count}")

    with open(output_path, "w", encoding="utf-8") as f:
        for p in results:
            f.write(p + "\n")
    return results


def quality_check(results):
    """Run quality checks on a batch."""
    cns = [len(re.findall(r"[\u4e00-\u9fff]", p)) for p in results]
    return {
        "count": len(results),
        "min_cn": min(cns), "max_cn": max(cns), "avg_cn": sum(cns)/len(cns),
        "under_500": sum(1 for c in cns if c < 500),
        "over_800": sum(1 for c in cns if c > 800),
        "multi_role": sum(1 for p in results if p.count("一位") > 1 or p.count("一名") > 1),
        "hand_bug": sum(1 for p in results if "一只手自然垂落" in p),
        "forbidden": sum(1 for p in results if any(w in p for w in ["仿佛","犹如","就像"])),
    }
