#!/usr/bin/env python3
"""
Surgical clean: remove person-description parts from sentences while keeping item/accessory/material descriptions.
Usage: python3 surgical_clean.py <input_file> [output_file]
"""
import re
import sys


def surgical_clean(text):
    """Remove person-description parts from a sentence, keep item descriptions."""
    patterns = [
        # Leading person pronouns + actions
        (r"^[她他]双手[^。，]{2,30}[，,]", ""),
        (r"^[她他]左手[^。，]{2,30}[，,]", ""),
        (r"^[她他]右手[^。，]{2,30}[，,]", ""),
        (r"^[她他]双臂[^。，]{2,30}[，,]", ""),
        (r"^[她他]抬起[^。，]{2,30}[，,]", ""),
        (r"^[她他]举起[^。，]{2,30}[，,]", ""),
        (r"^[她他]伸出[^。，]{2,30}[，,]", ""),
        (r"^[她他]放下[^。，]{2,30}[，,]", ""),
        (r"^[她他]面向[^。，]{2,30}[，,]", ""),
        (r"^[她他]站在[^。，]{2,30}[，,]", ""),
        (r"^[她他]坐[在着][^。，]{2,30}[，,]", ""),
        (r"^[她他]跪[在着][^。，]{2,30}[，,]", ""),
        (r"^[她他]躺[在着][^。，]{2,30}[，,]", ""),
        (r"^[她他]蹲[在着][^。，]{2,30}[，,]", ""),
        (r"^[她他]趴[在着][^。，]{2,30}[，,]", ""),
        (r"^[她他]看向[^。，]{2,30}[，,]", ""),
        (r"^[她他]直视[^。，]{2,30}[，,]", ""),
        (r"^[她他]转头[^。，]{2,30}[，,]", ""),
        (r"^[她他]回头[^。，]{2,30}[，,]", ""),
        (r"^[她他]低头[^。，]{2,30}[，,]", ""),
        (r"^[她他]抬头[^。，]{2,30}[，,]", ""),
        (r"^[她他]微笑[着]?[^。，]{2,30}[，,]", ""),
        (r"^[她他]露出[^。，]{2,30}[，,]", ""),
        (r"^[她他]面带[^。，]{2,30}[，,]", ""),

        # Leading identity descriptors
        (r"^一位[^。，]{1,15}[，,]", ""),
        (r"^一名[^。，]{1,15}[，,]", ""),
        (r"^[男女]子[^。，]{1,15}[，,]", ""),
        (r"^[男女]性[^。，]{1,15}[，,]", ""),
        (r"^年轻[男女][^。，]{1,15}[，,]", ""),

        # Leading appearance + action
        (r"^留着[^。，]{3,25}[，,]", ""),
        (r"^梳着[^。，]{3,25}[，,]", ""),
        (r"^扎着[^。，]{3,25}[，,]", ""),
        (r"^身穿[^。，]{3,25}[，,]", ""),
        (r"^身着[^。，]{3,25}[，,]", ""),
        (r"^穿着[^。，]{3,25}[，,]", ""),
        (r"^头戴[^。，]{3,25}[，,]", ""),
        (r"^脚穿[^。，]{3,25}[，,]", ""),
        (r"^佩戴[着]?[^。，]{3,25}[，,]", ""),
        (r"^戴着[^。，]{3,25}[，,]", ""),

        # Leading position
        (r"^位于[^。，]{3,20}[，,]", ""),
        (r"^站在[^。，]{3,20}[，,]", ""),
        (r"^坐[在着][^。，]{3,20}[，,]", ""),
        (r"^跪[在着][^。，]{3,20}[，,]", ""),
        (r"^面向[^。，]{3,20}[，,]", ""),
        (r"^背对[^。，]{3,20}[，,]", ""),
        (r"^正对[^。，]{3,20}[，,]", ""),

        # Leading body parts
        (r"^[左右]手[^。，]{3,25}[，,]", ""),
        (r"^[左右]臂[^。，]{3,25}[，,]", ""),
        (r"^[左右]腿[^。，]{3,25}[，,]", ""),
        (r"^双手[^。，]{3,25}[，,]", ""),
        (r"^双脚[^。，]{3,25}[，,]", ""),
        (r"^双臂[^。，]{3,25}[，,]", ""),
        (r"^面部[^。，]{3,25}[，,]", ""),
        (r"^肤色[^。，]{3,25}[，,]", ""),

        # Inline person actions (inserted in middle of sentence)
        (r"，[她他]双手[^。，]{2,25}", "，"),
        (r"，[她他]左手[^。，]{2,25}", "，"),
        (r"，[她他]右手[^。，]{2,25}", "，"),
        (r"，[她他]抬起[^。，]{2,25}", "，"),
        (r"，[她他]举起[^。，]{2,25}", "，"),
        (r"，[她他]伸出[^。，]{2,25}", "，"),
        (r"，[她他]看向[^。，]{2,25}", "，"),
        (r"，[她他]露出[^。，]{2,25}", "，"),
        (r"，[她他]站在[^。，]{2,25}", "，"),
        (r"，[她他]坐[在着][^。，]{2,25}", "，"),
        (r"，[她他]跪[在着][^。，]{2,25}", "，"),
        (r"，[她他]穿着[^。，]{2,25}", "，"),
        (r"，[她他]身[着穿][^。，]{2,25}", "，"),
        (r"，[她他]的[^。，]{2,25}", "，"),
        (r"，[她他]身体[^。，]{2,25}", "，"),
        (r"，[她他]头部[^。，]{2,25}", "，"),
        (r"，[她他]面部[^。，]{2,25}", "，"),
        (r"，[她他]脸上[^。，]{2,25}", "，"),
        (r"，[她他]双眼[^。，]{2,25}", "，"),
        (r"，[她他]嘴角[^。，]{2,25}", "，"),
    ]

    original = text
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    # Clean up residue
    text = re.sub(r"^[，,、\s]+", "", text)
    text = re.sub(r"[，,、]{2,}", "，", text)
    text = text.strip()

    # If cleaning removed too much, keep original
    if len(text) < 15:
        return original
    return text


def main():
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file + ".clean"

    with open(input_file, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    changed = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            cleaned = surgical_clean(line)
            if cleaned != line:
                changed += 1
            f.write(cleaned + "\n")

    print(f"Processed {len(lines)} lines, changed {changed} ({changed/len(lines)*100:.1f}%)")

if __name__ == "__main__":
    main()
