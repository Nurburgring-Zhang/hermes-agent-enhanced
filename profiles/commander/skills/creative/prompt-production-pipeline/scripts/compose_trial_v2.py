#!/usr/bin/env python3
"""
Trial Production V2 — Composition engine that samples 17 dimension libraries
and calls DeepSeek API to assemble 500-800 char prompts.

Key differences from V1:
1. Pre-composition consistency checks (scene type, nude detection, three-hand filter)
2. System prompt with 5x simile-word warning + forced style opening
3. post_clean pipeline removes 比喻词/标题目科技词
4. Progress tracking via output file (append per prompt)
"""
import os
import random
import re
import sys

import requests

DK = "sk-REPLACED-PLACEHOLDER"
DU = "https://api.deepseek.com/chat/completions"
V7_DIR = "/mnt/d/Hermes/1000000提示词/高质量模板/维度库_api_v7/"
OUTPUT_DIR = "/mnt/d/Hermes/1000000提示词/试生产/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DIMS = ["A01_年龄性别","A02_发型","A03_肤色","A04_表情眼神","A05_姿势",
        "B01_场景环境","B02_活动行为","C01_美学风格","C02_光照条件",
        "C03_色彩调性","C04_构图镜头","D01_服装款式","D02_配饰鞋帽",
        "D03_材质质感","D04_动态效果","D05_天气时间","D06_氛围情感"]

dim_data = {}
for d in DIMS:
    fp = os.path.join(V7_DIR, d+".txt")
    with open(fp, encoding="utf-8") as f:
        dim_data[d] = [l.strip() for l in f if l.strip()]
    print(f"  {d}: {len(dim_data[d]):,}条")

# Scene type keywords
INDOOR_KW = ["室内","房间","卧室","客厅","厨房","浴室","办公室","走廊","楼梯间","地下室","仓库"]
OUTDOOR_KW = ["户外","花园","公园","街道","海滩","海边","森林","草地","山坡","阳台","天台","马路"]
NUDE_KW = ["裸体","赤裸","裸","裸露","一丝不挂"]
THREE_HAND = re.compile(r"(左手.{0,15}右手.{0,15}左手|右手.{0,15}左手.{0,15}右手)")
BIYU = ["仿佛","犹如","就像","好似","宛如","如同"]
KEJI = ["量子","夸克","粒子","齿轮","青铜","全息","数据","光纤","纳米","芯片","电路","像素","矩阵"]

def scene_type(text):
    i = any(k in text for k in INDOOR_KW)
    o = any(k in text for k in OUTDOOR_KW)
    return "both" if (i and o) else ("indoor" if i else ("outdoor" if o else "none"))

def is_nude(t): return any(k in t for k in NUDE_KW)
def has_three_hand(t): return bool(THREE_HAND.search(t))

def pick(dim, count=1, fn=None):
    pool = dim_data.get(dim, [])
    if fn: pool = [p for p in pool if fn(p)]
    if not pool: pool = dim_data.get(dim, [])
    return random.sample(pool, min(count, len(pool)))

def post_clean(text):
    for kw in BIYU: text = text.replace(kw, "")
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        while line.startswith("【") and "】" in line: line = line[line.find("】")+1:].strip()
        while line.startswith("["): line = line[1:].strip()
        while line.startswith("#"): line = line[1:].strip()
        line = re.sub(r"^第\s*\d+\s*条[：:]\s*", "", line)
        line = re.sub(r"^\d+[\.\、\s]\s*", "", line)
        cleaned.append(line)
    text = "\n".join(cleaned)
    for kw in KEJI: text = text.replace(kw, "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def compose():
    frags = []
    scene_chosen = random.choice(["indoor","outdoor"])

    # A01 (nude check)
    nude_chance = random.random() < 0.05
    fn = (lambda p: any(k in p for k in NUDE_KW)) if nude_chance else (lambda p: not any(k in p for k in NUDE_KW))
    a01 = pick("A01_年龄性别", 1, fn)
    if not a01: a01 = pick("A01_年龄性别", 1)
    frags.extend([("A01_年龄性别", p) for p in a01])
    is_nude_p = is_nude(" ".join(a01))

    # A02
    frags.extend([("A02_发型", p) for p in pick("A02_发型", 1)])
    # A05 (no three-hand)
    frags.extend([("A05_姿势", p) for p in pick("A05_姿势", 2, lambda p: not has_three_hand(p))])
    # B01
    b1_fn = (lambda p: any(k in p for k in INDOOR_KW)) if scene_chosen == "indoor" else (lambda p: any(k in p for k in OUTDOOR_KW))
    b1 = pick("B01_场景环境", 2, b1_fn)
    if not b1: b1 = pick("B01_场景环境", 2)
    frags.extend([("B01_场景环境", p) for p in b1])
    # D01 (skip if nude)
    if not is_nude_p:
        frags.extend([("D01_服装款式", p) for p in pick("D01_服装款式", 2, lambda p: len(p) >= 12)])
    # Optional
    if random.random() < 0.6: frags.extend([("D02_配饰鞋帽", p) for p in pick("D02_配饰鞋帽", 1)])
    if random.random() < 0.55: frags.extend([("D03_材质质感", p) for p in pick("D03_材质质感", 1)])
    # B02
    frags.extend([("B02_活动行为", p) for p in pick("B02_活动行为", 2)])
    for d,p in frags:
        if d == "A05_姿势" and len(p) < 20 and ("B02_活动行为",p) not in frags:
            frags.append(("B02_活动行为", p))
    # A04
    frags.extend([("A04_表情眼神", p) for p in pick("A04_表情眼神", 1)])
    # D05 (outdoor only)
    if scene_chosen == "outdoor":
        frags.extend([("D05_天气时间", p) for p in pick("D05_天气时间", 1)])
    # C02
    c2_fn = (lambda p: any(k in p for k in ["室内","灯","窗","柔"])) if scene_chosen == "indoor" else (lambda p: any(k in p for k in ["自然光","阳光","日","夕","晨"]))
    c2 = pick("C02_光照条件", 1, c2_fn)
    if not c2: c2 = pick("C02_光照条件", 1)
    frags.extend([("C02_光照条件", p) for p in c2])
    # C03, C04, C01, D06
    frags.extend([("C03_色彩调性", p) for p in pick("C03_色彩调性", 1)])
    frags.extend([("C04_构图镜头", p) for p in pick("C04_构图镜头", 1)])
    frags.extend([("C01_美学风格", p) for p in pick("C01_美学风格", 1)])
    frags.extend([("D06_氛围情感", p) for p in pick("D06_氛围情感", 1)])
    return frags

def assemble(frags):
    style = [p for d,p in frags if d == "C01_美学风格"]
    sname = random.choice(style) if style else "写实风格"
    seg_text = "\n".join([f"[{d}] {p}" for d,p in frags])

    system = """你是顶级的AIGC文生图提示词工程师。用提供的片段组合成一条高质量的500-800字提示词。

【绝对禁忌——违反则不合格】
- 绝对禁止使用比喻词：仿佛、犹如、就像、好似、宛如、如同。出现任何一个即不合格。
- 绝对禁止使用科技词汇：量子、夸克、粒子、齿轮、全息、数据、芯片、像素、矩阵。
- 绝对禁止标题/序号/分段。只输出一个完整段落。
- 绝对禁止描述三只手或更多（一个人只能有两只手）。
- 绝对禁止数字化描述（距离、厚度、角度、厘米等具体数字）。

【必须遵守】
1. 开篇第一句必须是：**[风格名]风** + 风格特征描述（1-2句）。
   示例："吉卜力治愈风，画面如宫崎骏动画般梦幻治愈，水彩质感的天空与柔和空气感贯穿始终。"
2. 将提供的所有片段自然融入，保持人物→场景→服装→动作→光影→构图→风格的叙述顺序。
3. 500-800字中文，完整段落，只输出一段提示词，可以有逗号和句号。"""

    user = f"""用以下片段组合成一条500-800字的提示词，开篇必须是「{sname}风，」：

{seg_text}"""

    payload = {"model":"deepseek-chat","messages":[
        {"role":"system","content":system},{"role":"user","content":user}
    ],"temperature":0.9,"max_tokens":2000}
    headers = {"Authorization":f"Bearer {DK}","Content-Type":"application/json"}
    r = requests.post(DU, json=payload, headers=headers, timeout=120)
    j = r.json()
    return j["choices"][0]["message"]["content"], j.get("usage",{})

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    out_fp = os.path.join(OUTPUT_DIR, f"trial_v2_{count}.txt")
    if os.path.exists(out_fp): os.remove(out_fp)

    print(f"Trial producing {count} prompts...")
    for i in range(count):
        frags = compose()
        raw, usage = assemble(frags)
        clean = post_clean(raw)
        cn = sum(1 for c in clean if "\u4e00" <= c <= "\u9fff")
        with open(out_fp, "a", encoding="utf-8") as f:
            f.write(clean + "\n\n")
        status = "OK" if 500 <= cn <= 800 else "SHORT"
        print(f"  [{i+1}/{count}] {status} {cn}字")
    print(f"Done: {out_fp}")
