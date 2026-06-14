#!/usr/bin/env python3
"""quality_filter.py — 提示词质量过滤器
格林主人标准：10条规则，返回PASS/FAIL/WARN + 分数

用法:
  python3 quality_filter.py <prompt_text>
  python3 quality_filter.py --file <path>
  from quality_filter import check_prompt

10条规则:
1. 比喻词禁止: 仿佛/犹如/就像/好似/宛如/如同/宛若等 (FAIL)
2. 科技词禁止: 量子/粒子/全息/像素/赛博/AI/数字/芯片等 (FAIL)
3. 三手检测: 3个以上矛盾手部动作描述 (FAIL)
4. 服装堆叠: 3件以上上装或季节矛盾 (WARN)
5. 场景矛盾: 室内+户外场景词同时出现 (FAIL)
6. 种族矛盾: 亚裔+金发/蓝眼/棕眼 (FAIL)
7. 站+床: 站姿+床/沙发 (WARN)
8. 字数检查: <400或>1200字 (WARN)
9. 重复检测: 相同维度关键词重复 (WARN)
10. 性别矛盾: 男+女装描述冲突 (WARN)
"""

import json
import sys

# ============ 禁止词 ============
BANNED_METAPHORS = [
    "仿佛", "犹如", "就像", "好似", "宛如", "如同",
    "似乎是", "好像", "好比", "恰似", "宛若", "恰如", "若"
]
BANNED_TECH = [
    "量子", "粒子", "全息", "像素", "赛博", "数码",
    "电子", "AI", "人工智能", "虚拟", "数字", "芯片",
    "代码", "数据"
]
BANNED_ALL = set(BANNED_METAPHORS + BANNED_TECH + ["数字插画", "数字艺术", "数字化"])

# ============ 场景词 ============
INDOOR_KW = {
    "室内", "卧室", "客厅", "浴室", "厨房", "走廊", "教室",
    "咖啡馆", "餐厅", "办公室", "图书馆", "博物馆", "沙发",
    "床上", "书桌", "健身房", "剧院", "楼梯", "仓库",
    "旅馆", "酒店", "酒吧", "书房"
}
OUTDOOR_KW = {
    "户外", "公园", "花园", "草地", "海滩", "海边", "森林",
    "山脉", "街道", "阳台", "庭院", "广场", "雪地", "海岸",
    "沙滩", "田野", "山坡", "树林", "天台", "屋顶", "湖边",
    "沙漠", "泳池", "运动场", "登山", "小路", "草原"
}

# ============ 手部动作词 ============
HAND_ACTIONS = [
    "手握", "手拿", "手捧", "手扶", "手托", "手撑",
    "右手", "左手", "双手", "手指", "手掌", "手腕",
    "握手", "握笔", "握杯", "握拳", "手搭", "手放", "手按"
]

# ============ 种族矛盾 ============
ASIAN_KW = ["亚裔", "亚洲", "东亚"]
RACE_CONFLICT_KW = ["金发", "蓝眼", "棕眼"]

# ============ 服装堆叠 ============
UPPER_GARMENTS = ["上衣", "外套", "夹克", "衬衫", "卫衣", "毛衣",
                  "T恤", "背心", "马甲", "风衣", "大衣", "西装",
                  "开衫", "针织衫", "帽衫"]

# ============ 站+床 ============
STAND_KW = ["站立", "站着", "站姿", "直立", "站立着"]
BED_KW = ["床上", "床", "沙发", "沙发", "床垫"]

# ============ 重复检测 ============
DIM_KEYWORDS = {
    "A01": ["女子", "女性", "男子", "男性", "年轻", "少女"],
    "A02": ["长发", "短发", "卷发", "直发", "马尾", "刘海"],
    "B01": ["室内", "户外", "卧室", "公园", "房间", "背景"],
    "C02": ["光线", "光照", "阳光", "光", "灯", "阴影"],
    "C03": ["色调", "色彩", "颜色", "色", "饱和度"],
    "D01": ["穿着", "身着", "身穿", "上衣", "裙子", "裤子"]
}


def check_prompt(text):
    """主入口：返回检测结果字典"""
    checks = []
    fail_count = 0
    warn_count = 0

    # 1. 比喻词
    found_metaphors = [w for w in BANNED_METAPHORS if w in text]
    passed_1 = len(found_metaphors) == 0
    detail_1 = f"发现比喻词{'、'.join(found_metaphors[:3])}" if found_metaphors else ""
    checks.append({"rule": "比喻词", "passed": passed_1, "detail": detail_1})
    if not passed_1: fail_count += 1

    # 2. 科技词
    found_tech = [w for w in BANNED_TECH if w in text]
    passed_2 = len(found_tech) == 0
    detail_2 = f"发现科技词{'、'.join(found_tech[:3])}" if found_tech else ""
    checks.append({"rule": "科技词", "passed": passed_2, "detail": detail_2})
    if not passed_2: fail_count += 1

    # 3. 三手检测
    hand_descriptions = [a for a in HAND_ACTIONS if a in text]
    hand_count = sum(text.count(a) for a in HAND_ACTIONS)
    passed_3 = hand_count <= 3
    detail_3 = f"发现{hand_count}处手部动作描述" if hand_count > 3 else ""
    checks.append({"rule": "三手检测", "passed": passed_3, "detail": detail_3})
    if not passed_3: fail_count += 1

    # 4. 服装堆叠
    upper_count = sum(1 for g in UPPER_GARMENTS if g in text)
    passed_4 = upper_count < 3
    detail_4 = f"检测到{upper_count}件上装" if upper_count >= 3 else ""
    checks.append({"rule": "服装堆叠", "passed": passed_4, "detail": detail_4})
    if not passed_4: warn_count += 1

    # 5. 场景矛盾
    in_found = [k for k in INDOOR_KW if k in text]
    out_found = [k for k in OUTDOOR_KW if k in text]
    passed_5 = len(in_found) == 0 or len(out_found) == 0
    detail_5 = ""
    if not passed_5:
        detail_5 = f"场景矛盾：同时出现室内词({'、'.join(list(in_found)[:3])})和户外词({'、'.join(list(out_found)[:3])})"
    checks.append({"rule": "场景矛盾", "passed": passed_5, "detail": detail_5})
    if not passed_5: fail_count += 1

    # 6. 种族矛盾
    has_asian = any(k in text for k in ASIAN_KW)
    has_race_conflict = any(k in text for k in RACE_CONFLICT_KW)
    passed_6 = not (has_asian and has_race_conflict)
    detail_6 = ""
    if not passed_6:
        conflict_words = [k for k in RACE_CONFLICT_KW if k in text]
        detail_6 = f"亚裔+{'、'.join(conflict_words[:2])}存在天然矛盾"
    checks.append({"rule": "种族矛盾", "passed": passed_6, "detail": detail_6})
    if not passed_6: fail_count += 1

    # 7. 站+床
    has_stand = any(k in text for k in STAND_KW)
    has_bed = any(k in text for k in BED_KW)
    passed_7 = not (has_stand and has_bed)
    detail_7 = "同时出现站姿和床/沙发" if not passed_7 else ""
    checks.append({"rule": "站+床", "passed": passed_7, "detail": detail_7})
    if not passed_7: warn_count += 1

    # 8. 字数
    char_count = len(text)
    passed_8 = 400 <= char_count <= 1200
    detail_8 = f"{char_count}字" if not passed_8 else ""
    checks.append({"rule": "字数检查", "passed": passed_8, "detail": detail_8})
    if not passed_8: warn_count += 1

    # 9. 重复检测
    repeats = []
    for dim, keywords in DIM_KEYWORDS.items():
        found = [k for k in keywords if text.count(k) >= 2]
        if found:
            repeats.extend(found[:2])
    passed_9 = len(repeats) == 0
    detail_9 = f"重复词: {'、'.join(repeats[:3])}" if repeats else ""
    checks.append({"rule": "重复检测", "passed": passed_9, "detail": detail_9})
    if not passed_9: warn_count += 1

    # 10. 性别矛盾
    male_clothing = ["西装", "领带", "皮鞋", "马甲"]
    female_clothing = ["裙子", "丝袜", "文胸", "比基尼", "蕾丝"]
    has_male = any(k in text for k in male_clothing)
    has_female = any(k in text for k in female_clothing)
    passed_10 = not (has_male and has_female)
    detail_10 = "同时出现男女装描述" if not passed_10 else ""
    checks.append({"rule": "性别矛盾", "passed": passed_10, "detail": detail_10})
    if not passed_10: warn_count += 1

    # 综合评分
    base = 100
    base -= fail_count * 12
    base -= warn_count * 4
    score = max(0, min(100, base))

    # 综合判定
    if fail_count > 0:
        overall = "FAIL"
    elif warn_count > 0:
        overall = "WARN"
    else:
        overall = "PASS"

    fail_reasons = [c["detail"] for c in checks if not c["passed"] and c["detail"]]

    return {
        "overall": overall,
        "score": score,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "checks": checks,
        "fail_reasons": fail_reasons
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 quality_filter.py <文本> 或 --file <path>")
        sys.exit(1)

    if sys.argv[1] == "--file":
        with open(sys.argv[2], encoding="utf-8") as f:
            texts = [l.strip() for l in f if l.strip()]
        results = [check_prompt(t) for t in texts]
        passed = sum(1 for r in results if r["overall"] == "PASS")
        failed = sum(1 for r in results if r["overall"] == "FAIL")
        warned = sum(1 for r in results if r["overall"] == "WARN")
        avg_score = sum(r["score"] for r in results) / len(results)
        print(json.dumps({
            "total": len(results),
            "PASS": passed,
            "FAIL": failed,
            "WARN": warned,
            "avg_score": round(avg_score, 1),
            "details": [{"index": i+1, "overall": r["overall"], "score": r["score"],
                         "fail_reasons": r["fail_reasons"]} for i, r in enumerate(results)]
        }, ensure_ascii=False, indent=2))
    else:
        text = sys.argv[1]
        result = check_prompt(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
