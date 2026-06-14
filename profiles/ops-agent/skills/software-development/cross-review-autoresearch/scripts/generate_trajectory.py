#!/usr/bin/env python3
"""
generate_trajectory.py — 从审核报告生成评分变化轨迹CSV
交叉审核工具链的一部分

用法:
  python3 generate_trajectory.py [outputs/cross-review]
  python3 generate_trajectory.py outputs/cross-review
"""

import csv
import glob
import os
import re
import sys

DIMENSIONS = ["correctness", "test_quality", "code_quality", "security", "performance"]
DIMENSION_NAMES_CN = {
    "correctness": "正确性",
    "test_quality": "测试质量",
    "code_quality": "代码质量",
    "security": "安全性",
    "performance": "性能",
}


def extract_scores(report_path: str) -> dict:
    """从审核报告md提取评分"""
    with open(report_path, encoding="utf-8") as f:
        content = f.read()

    scores = {}
    patterns = {
        "correctness": r"正确性[：:\s-]+([0-9.]+)",
        "test_quality": r"测试质量[：:\s-]+([0-9.]+)",
        "code_quality": r"代码质量[：:\s-]+([0-9.]+)",
        "security": r"安全性[：:\s-]+([0-9.]+)",
        "performance": r"性能[：:\s-]+([0-9.]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            scores[key] = float(match.group(1))

    return scores


def round_num(path: str) -> int:
    """从路径提取轮次号"""
    m = re.search(r"round-(\d+)", path)
    return int(m.group(1)) if m else 0


def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/cross-review"

    if not os.path.isdir(root_dir):
        print(f"错误: 目录不存在: {root_dir}")
        print(f"用法: {sys.argv[0]} [输出目录]")
        sys.exit(1)

    # 找到所有审核报告
    reports = glob.glob(f"{root_dir}/round-*/review-report.md")
    reports.sort(key=round_num)

    if not reports:
        print(f"在 {root_dir}/round-*/review-report.md 中未找到审核报告")
        sys.exit(1)

    # 确保summary目录存在
    summary_dir = os.path.join(root_dir, "summary")
    os.makedirs(summary_dir, exist_ok=True)

    # 写入CSV
    headers = ["round"] + DIMENSIONS + ["composite"]
    csv_path = os.path.join(summary_dir, "score-trajectory.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)

        for report_path in reports:
            rn = round_num(report_path)
            scores = extract_scores(report_path)

            if len(scores) == 5:
                # 计算综合评分
                WEIGHTS = {"correctness": 0.35, "test_quality": 0.25,
                           "code_quality": 0.20, "security": 0.10, "performance": 0.10}
                composite = sum(scores[d] * WEIGHTS[d] for d in DIMENSIONS)
                composite = round(composite, 2)
            else:
                composite = ""

            writer.writerow([
                rn,
                scores.get("correctness", ""),
                scores.get("test_quality", ""),
                scores.get("code_quality", ""),
                scores.get("security", ""),
                scores.get("performance", ""),
                composite,
            ])

    # 打印摘要
    print(f"评分轨迹已保存: {csv_path}")
    print()

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    if rows:
        print(f"{'轮次':<8} {'正确性':<8} {'测试':<8} {'质量':<8} {'安全':<8} {'性能':<8} {'综合':<8}")
        print("-" * 56)
        for row in rows:
            print(f"{row['round']:<8} {row['correctness']:<8} {row['test_quality']:<8} "
                  f"{row['code_quality']:<8} {row['security']:<8} {row['performance']:<8} "
                  f"{row['composite']:<8}")

        # 如果有至少两轮，显示变化
        if len(rows) >= 2:
            print()
            print("评分变化趋势:")
            first = rows[0]
            last = rows[-1]
            for dim in DIMENSIONS + ["composite"]:
                try:
                    delta = float(last[dim]) - float(first[dim])
                    arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                    cn_name = DIMENSION_NAMES_CN.get(dim, dim) if dim in DIMENSIONS else "综合"
                    print(f"  {cn_name}: {first[dim]} → {last[dim]} {arrow} {delta:+.2f}")
                except (ValueError, KeyError):
                    pass

    print(f"\n共 {len(reports)} 轮审核评分已归档")


if __name__ == "__main__":
    main()
