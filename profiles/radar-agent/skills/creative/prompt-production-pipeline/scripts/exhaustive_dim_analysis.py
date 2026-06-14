#!/usr/bin/env python3
"""
Exhaustive dimension analysis from to_chi data.
Usage: python3 exhaustive_dim_analysis.py
Output: analysis report with all dimensions, coverage, and combinatorial patterns
"""
import collections
import os
import random

chi_dir = "/mnt/d/ComfyUI/提示词/to_chi/"

def sample_data(target=10000):
    """Sample N random lines from to_chi files"""
    files = []
    for root, dirs, fnames in os.walk(chi_dir):
        for f in fnames:
            fpath = os.path.join(root, f)
            if os.path.getsize(fpath) < 1000: continue
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as test:
                    test.read(100)
                files.append(fpath)
            except: pass

    random.shuffle(files)
    sample = []
    for fpath in files:
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and len(line) > 50:
                        sample.append(line)
                    if len(sample) >= target: break
        except: pass
        if len(sample) >= target: break
    return sample

def build_analysis(sample, concepts):
    """Analyze dimension coverage in sample"""
    dim_counts = dict.fromkeys(concepts, 0)
    dim_detail = {k: collections.Counter() for k in concepts}
    per_line = []

    for text in sample:
        detected = set()
        for dim_name, kws in concepts.items():
            found = [kw for kw in kws if kw in text]
            if found:
                dim_counts[dim_name] += 1
                dim_detail[dim_name].update(found)
                detected.add(dim_name)
        per_line.append(len(detected))

    return dim_counts, dim_detail, per_line

# Key concepts — expanded from 15K-line analysis
CONCEPTS = {
    "空间位置": ["背景","前景","中央","左侧","右侧","上方","下方","前方","后方","角落"],
    "基本色": ["红色","橙色","黄色","绿色","蓝色","紫色","粉色","白色","黑色","灰色","棕色","褐色"],
    "色彩调性": ["暖色调","冷色调","中性色调","高对比","低对比","明亮","昏暗","通透"],
    "日常活动": ["画","写","拍照","自拍","读书","阅读"],
    "材质表面": ["纹理","肌质","光泽","编织","经纬线","纹路","颗粒","凹凸","抛光","拉丝"],
    "光照软硬": ["柔光","硬光","漫射光","柔和","强烈","均匀"],
    "手部动作": ["握","拿","捧","举","端","提","扶","抱","托","捏","搭","叉腰"],
    # ... (full list from dimension_analysis_results.md)
}

# Note: The full concept list is maintained in the analysis report.
# This script is a skeleton — run the full exhaustive analysis separately.
