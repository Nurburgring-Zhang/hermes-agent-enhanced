#!/usr/bin/env python3
"""
Massive Prompt Generator — Template-combination engine
100x faster than cronjob-based AI generation.

Usage:
    python3 massive_generator.py              # Generate for all files
    python3 massive_generator.py 02.txt 5000  # Single file, 5000 items

Design:
    Loads template libraries (style/outfit/pose/photography/scene) and
    randomly combines them using 9-layer template structure.
    Each item is 550-750 chars, single paragraph, no titles.

    Key performance edge vs cronjob approach:
    - Cronjob (AI): ~9 items/min → 540/hr
    - This script: ~500 items/sec → 1,800,000/hr

Prerequisites:
    Template files in /mnt/d/Hermes/1000000提示词/高质量模板/:
    - 15_女性风格库.txt (2000+ entries)
    - 16_女性穿搭库.txt (2000+ entries)
    - 17_女性姿势库.txt (2000+ entries)
    - 18_摄影风格库.txt (148+ entries)
    - 13_场景库.txt (127+ entries)
"""
import os
import random
import re
import sys

BASE = "/mnt/d/Hermes/1000000提示词/高质量模板"
OUT_DIR = "/mnt/d/Hermes/1000000提示词/10万提示词"

def load_lines(filepath):
    full_path = os.path.join(BASE, filepath)
    if not os.path.exists(full_path):
        return []
    with open(full_path, encoding="utf-8") as f:
        lines = f.readlines()
    result = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("===") or line.startswith("---") or line.startswith("##"):
            continue
        line = re.sub(r"^\d+[\.\、\s\u3000]+", "", line)
        if len(line) >= 15:
            result.append(line)
    return result

print("Loading template libraries...", flush=True)
styles = load_lines("15_女性风格库.txt")
outfits = load_lines("16_女性穿搭库.txt")
poses_all = load_lines("17_女性姿势库.txt") + load_lines("14_姿势库.txt")
photo_styles = load_lines("18_摄影风格库.txt")
scenes = load_lines("13_场景库.txt")

COLORS = ["月白","竹青","黛蓝","藕荷","赭石","鸦青","象牙白","胭脂","群青","琥珀","秋香",
"松花绿","丁香紫","玫瑰红","天青","荼白","艾绿","雪青","朱砂","苍色","靛蓝",
"檀棕","驼色","米白","烟灰","雾蓝","奶咖","豆沙","茶褐","藏蓝","墨绿","酒红",
"姜黄","藕粉","水蓝","草绿","樱粉","杏色","珍珠白","珊瑚粉","松石绿",
"绛紫","藤黄","石绿","青碧","桃红","缃叶","退红","天水碧","湖蓝","雾紫"]

def rc(lst): return random.choice(lst) if lst else ""

def gen():
    style = rc(styles); scene = rc(scenes); outfit = rc(outfits)
    pose = rc(poses_all); photo = rc(photo_styles)
    c1, c2 = random.sample(COLORS, 2); c3, c4 = random.sample(COLORS, 2)
    r = random.random()
    if r < 0.2: op = f"在{style[:40]}的美学框架下，{scene[:60]}"
    elif r < 0.4 and photo: op = f"{photo[:80]}。这张向{style[:30]}致敬的画面中，{scene[:50]}"
    elif r < 0.6: op = f"{scene[:60]}整幅画面被{style[:40]}的质感包裹"
    elif r < 0.8: op = f"镜头在{style[:40]}的视觉语言中定格{scene[:60]}"
    else: op = f"以{style[:35]}的表现手法呈现{scene[:55]}"
    shot = rc(["中近景平视","中景平视","近景特写","仰拍","俯拍","侧拍45度","低角度仰拍","长焦压缩","广角变形","全景"])
    comp = rc(["三分构图","居中对称","黄金螺旋","对角线构图","框架式构图","引导线构图","极简留白","S形曲线","三角构图","框中框"])
    light = rc([f"柔和的{rc(['正面漫射光','侧光','逆光','窗光','晨光','黄昏光'])}在{rc(['皮肤','发丝','面料','轮廓'])}上形成{rc(['细腻的光影过渡','温柔的光晕','清晰的明暗层次','自然的立体感'])}",
                f"{rc(['午后硬朗阳光','聚光灯','顶光','霓虹光','烛光','钨丝灯光'])}在{rc(['墙面','地面','面部','空间'])}营造出{rc(['锐利几何阴影','戏剧性效果','温暖暧昧氛围','深邃的结构感'])}"])
    color_atm = rc([f"整体色调偏{rc(['冷','暖'])}，{rc(['低饱和度呈现高级灰度','色彩的过渡柔和如水彩晕开','鲜明的对比形成视觉张力'])}",
                    f"色彩以{rc(['莫兰迪色系','大地色系','日系低饱和','高对比撞色'])}为基调，{rc(['在灰调中藏着微妙色彩倾向','冷暖交织出丰富层次','如水彩自然晕开'])}"])
    mood = rc([f"温柔{rc(['快乐','治愈','慵懒','宁静'])}如同{rc(['春日阳光','冬日热茶','午后微风','清澈溪水'])}",
               f"{rc(['忧郁','荒诞','神秘','温暖','性感','孤独','沉静'])}而{rc(['诗意','迷人','深邃','怀旧','克制'])}"])
    breakout = rc(["在极致中保留不完美的生活痕迹，让真实感超越技术呈现","将日常碎片提升到艺术品高度，让平凡值得凝视",
        "通过光影叙事将平凡场景升华为充满诗意的瞬间","用最克制的视觉语言表达最浓烈的情感",
        "唤醒深藏在集体审美记忆中的情感共鸣","将不同时空的美学元素解构重组，创造全新视觉叙事"])
    prompt = f"{op}，镜头采用{shot}的{comp}方式捕捉，浅景深让背景化作朦胧色块，主体立体浮现。人物穿搭以{c1}与{c2}为主调，{c3}和{c4}点缀，{outfit}。姿态自然富有表现力，{pose}。前景虚化制造空间深度，中景人物占据视觉重心，背景通过光影变化营造纵深感。光线处理上，{light}。色彩方面，{color_atm}。整幅画面浸润在{mood}的氛围中。{breakout}。"
    prompt = re.sub(r"[，,]{2,}", "，", prompt)
    prompt = re.sub(r"[。.]{2,}", "。", prompt)
    return prompt.strip()

if __name__ == "__main__":
    import sys
    target_file = sys.argv[1] if len(sys.argv) > 1 else None
    target_count = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    files = ["modern_art_prompts_02.txt","modern_art_prompts_03.txt","modern_art_prompts_04.txt",
             "modern_art_prompts_05.txt","modern_art_prompts_06.txt","modern_art_prompts_07.txt",
             "modern_art_prompts_08.txt","modern_art_prompts_09.txt","modern_art_prompts_10.txt"]

    if target_file:
        files = [f for f in files if target_file in f]

    total = 0
    for fname in files:
        fpath = os.path.join(OUT_DIR, fname)
        existing = set()
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line: existing.add(line[:20])
        need = target_count - len(existing) if target_count > 0 else 5000
        if need <= 0: continue
        print(f"\n{fname}: need {need} (have {len(existing)})", flush=True)
        batch, attempts = [], 0
        while len(batch) < need and attempts < need * 30:
            p = gen()
            if p[:20] not in existing:
                existing.add(p[:20]); batch.append(p)
            attempts += 1
            if len(batch) >= 200:
                with open(fpath, "a", encoding="utf-8") as f:
                    f.write("\n".join(batch) + "\n")
                batch = []
                print(f"  +200 (now {len(existing)})", flush=True)
        if batch:
            with open(fpath, "a", encoding="utf-8") as f:
                f.write("\n".join(batch) + "\n")
        print(f"{fname}: final={len(existing)}", flush=True)
        total += len(batch)
    print(f"\n=== DONE: {total} items ===", flush=True)
