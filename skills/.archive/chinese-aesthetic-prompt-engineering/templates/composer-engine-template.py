#!/usr/bin/env python3
"""
组合引擎模板 v15-style — 从15个维度库组合生成高质量prompt

用法：
  1. 将15个库放在 lib_dir 指定目录
  2. 调整固定池(STARTS/SCENES/COLORS/LIGHTS/BREAKOUTS)
  3. 运行 python3 this_script.py [start_batch] [num_batches]

关键规则：
  - 每条只从01库抽一次角色（避免多角色拼接）
  - 从活动库只取活动动作（丢弃人物头）
  - 裸体时跳过材质/配饰
  - 禁止"一只手自然垂落""另一只手轻触"句式
"""
import os
import random
import re
import sys

lib_dir = "/mnt/d/Hermes/1000000提示词/高质量模板/新建库/"
output_dir = "/mnt/d/Hermes/1000000提示词/10万提示词/"

# ====== 固定池（不是从库抽，是硬编码的高质量描述）======
STARTS = [
    "极简主义的留白与减法美学,大面积留空以最少的视觉元素承载最丰富的情感。",
    "巴洛克暗调主义风格,画面沉入近乎绝对的黑色调中,一束锐利的光斜射照亮主体。",
    "印象派追逐光线的短促笔触,捕捉光线在物体表面的瞬间变化。",
    "水彩湿画法让颜料在湿润的粗纹纸上自由扩散,色彩从中心向边缘递减。",
    "厚涂油画的颜料层在画布上层层堆叠,底层色彩从刀痕缝隙中透出。",
    "超写实主义的极致细节,每一根纤维和每一粒灰尘都精确呈现。",
    "维也纳分离派的金箔装饰风格,人物从金色包裹中浮现。",
    "洛可可风格的轻快优雅,饱满流畅的曲线与柔和色彩贯穿画面。",
    "日本琳派风格以金箔铺底,用装饰性手法描绘流水花卉。",
    "包豪斯风格以几何线条与纯粹色块构建画面骨架。",
    "新艺术派穆夏风格,女性轮廓被流动的曲线包裹。",
    "波普艺术的高饱和色彩与硬边轮廓让画面充满现代感。",
    "抽象表现主义的滴画技法,颜料在画布上自由流淌。",
    "野兽派的色彩解放,高纯度色彩直铺画面。",
    "浮世绘版画的黑色轮廓线勾勒形体和衣纹。",
]

SCENES = [
    "清晨的阳光透过结满霜花的玻璃窗漫射进来。",
    "黄昏的残阳将金色涂抹在旧公寓的白色墙壁上。",
    "雨滴敲打着窗户玻璃,窗外的城市在雨幕中化成一幅模糊的水彩画。",
    "午后的阳光穿过梧桐树叶在桌面上投下不断晃动的光斑。",
    "深夜一盏台灯散发暖黄色的光,在墙面上形成一个明亮的扇形区域。",
    "冬天的第一场雪覆盖了城市,窗台上积起松软的白雪。",
    "海风带着咸湿的气息扑面而来,海浪拍打着岸边的礁石。",
    "清晨的雾气还未散去,草地上挂着晶莹的露珠。",
]

COLORS = [
    "主色为暖赭与象牙白交织,群青点缀在暗部形成冷暖对抗。",
    "月白与铅灰构成冷调基底,唇间一抹胭脂红成为视觉锚点。",
    "琥珀色铺陈画面,墨黑阴影衬得金色饱满浓郁。",
    "雪青与丁香紫的邻近色渐变笼罩全场。",
    "檀褐与茶绿的低饱和色调像是被岁月滤过的颜色。",
    "骨白和烟灰构成画面主体,墨黑作为重色压住重心。",
    "群青与月白的冷色组合贯穿画面。",
    "驼色卡其和米色的大地色系铺陈全场。",
]

LIGHTS = [
    "光源从侧上方照射,在颧骨和鼻梁上形成柔和的高光带。",
    "柔和的漫射光均匀包裹整个场景,没有强烈明暗对比。",
    "一束集中的侧光将主体一半照亮一半隐入暗影。",
    "逆光勾勒出主体的轮廓光,发丝边缘半透明发光。",
    "窗光从左侧落地窗射入经过纱帘过滤转化为柔和漫射光。",
]

BREAKOUTS = [
    "不起眼的角落藏着违背物理常理的细节——水洼中映出的不是当前天空而是星空的倒影。",
    "古典美学与当代生活场景在同一画面中相遇。",
    "镜中反射的世界与镜前的现实微妙地错位。",
    "不同时代的物件共处一室,历史的断层在同一视口中缝合。",
    "极度的写实中留下偶然性的失控痕迹。",
]

def load_libraries():
    """加载15个库并清洗"""
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
            content = re.sub(r"无可见文字[。，]?|无可见文字或书写内容[。，]?", "", content)
            content = re.sub(r"[特写照片摄影][，,。]?(?:展示|聚焦|的)?", "", content)
            # 关键：去掉开头"一位/一名"避免多角色拼接
            content = re.sub(r"^一位|^一名|^一张|^一幅", "", content)
            content = content.strip()
            if content and len(content) > 10:
                items.append(content)
        libs[fname] = items
    return libs

def extract_doing(text):
    """从活动库条目中提取'正在'动作，去掉人物头"""
    doing = re.search(r"正在[^。]{5,40}", text)
    return doing.group(0) if doing else ""

def compose_one(libs):
    """生成一条prompt——每条只抽一次角色"""
    start = random.choice(STARTS)
    scene = random.choice(SCENES)
    color = random.choice(COLORS)
    light = random.choice(LIGHTS)
    breakout = random.choice(BREAKOUTS)

    role_text = random.choice(libs.get("01_角色特征库.txt", ["一位年轻女性"]))
    is_nude = any(w in role_text for w in ["裸体","赤裸","裸露","一丝不挂","未着寸缕"])

    activity = ""
    if "08_活动行为库.txt" in libs:
        a = random.choice(libs["08_活动行为库.txt"])
        activity = extract_doing(a)

    material = ""
    if not is_nude and "11_材质质感库.txt" in libs:
        material = random.choice(libs["11_材质质感库.txt"])[:60]
    accessory = ""
    if not is_nude and "12_配饰鞋帽库.txt" in libs:
        accessory = random.choice(libs["12_配饰鞋帽库.txt"])[:60]

    prop = random.choice(libs.get("13_环境道具库.txt", [""]))[:60] if "13_环境道具库.txt" in libs else ""
    dynamic = random.choice(libs.get("10_动态效果库.txt", [""]))[:40] if "10_动态效果库.txt" in libs else ""
    mood = random.choice(libs.get("06_情感氛围库.txt", [""])).split("。")[0][:50] if "06_情感氛围库.txt" in libs else ""

    parts = [start, scene, role_text]
    if activity: parts.append(activity)
    if material: parts.append(material)
    if accessory: parts.append(accessory)
    if prop: parts.append(prop)
    if dynamic: parts.append(dynamic)
    parts += [color, light]
    if mood: parts.append(mood)
    parts.append(breakout)

    prompt = "。".join(parts)
    prompt = prompt.replace("。。", "。")
    prompt = re.sub(r"[。]{2,}", "。", prompt)
    prompt = prompt.strip()

    cn = len(re.findall(r"[\u4e00-\u9fff]", prompt))
    if cn < 500:
        extras = ["皮肤的质感在光线下呈现出细腻的光泽。", "前景的物件细节丰富,中景与背景形成自然的空间层次。"]
        prompt += "。" + random.choice(extras)
    if cn > 800:
        sents = prompt.split("。")
        prompt = "。".join(sents[:8]) + "。"

    return prompt

if __name__ == "__main__":
    os.makedirs(output_dir, exist_ok=True)
    libs = load_libraries()
    start_batch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    num = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    for b in range(start_batch, start_batch + num):
        out = os.path.join(output_dir, f"modern_art_prompts_{b:02d}.txt")
        results = [compose_one(libs) for _ in range(1000)]
        with open(out, "w", encoding="utf-8") as f:
            f.writelines(p + "\n" for p in results)
        print(f"Batch {b}: 1000条 -> {out}")
