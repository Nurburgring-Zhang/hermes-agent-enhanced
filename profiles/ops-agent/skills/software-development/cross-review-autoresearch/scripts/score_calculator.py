#!/usr/bin/env python3
"""
score_calculator.py — 五维度加权综合评分计算器
交叉审核工具链的一部分: https://github.com/NousResearch/Hermes

用法:
  python3 score_calculator.py 0.90 0.85 0.80 1.00 0.95
  python3 score_calculator.py --interactive
"""

import re
import sys

WEIGHTS = {
    "correctness": 0.35,
    "test_quality": 0.25,
    "code_quality": 0.20,
    "security": 0.10,
    "performance": 0.10,
}

DIMENSION_NAMES_CN = {
    "correctness": "正确性",
    "test_quality": "测试质量",
    "code_quality": "代码质量",
    "security": "安全性",
    "performance": "性能",
}

DIMENSIONS_ORDER = ["correctness", "test_quality", "code_quality", "security", "performance"]


def calculate(scores: dict) -> float:
    """计算五维度加权综合评分"""
    if set(scores.keys()) != set(WEIGHTS.keys()):
        missing = set(WEIGHTS.keys()) - set(scores.keys())
        extra = set(scores.keys()) - set(WEIGHTS.keys())
        raise ValueError(f"维度不匹配: 缺少 {missing}, 多余 {extra}")

    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total, 2)


def rating(score: float) -> str:
    """根据评分返回评级"""
    if score >= 0.90:
        return "✅ 优秀"
    if score >= 0.80:
        return "✅ 良好"
    if score >= 0.65:
        return "⚠️ 合格"
    return "❌ 不合格"


def extract_scores_from_report(report_path: str) -> dict:
    """从审核报告md文件中提取评分"""
    with open(report_path, encoding="utf-8") as f:
        content = f.read()

    scores = {}
    # 尝试中文和英文维度名
    patterns = {
        "correctness": [
            r"正确性[：:\s-]+([0-9.]+)",
            r"\[正确性\]\s*[:：]\s*([0-9.]+)",
            r"[Cc]orrectness[：:\s-]+([0-9.]+)",
        ],
        "test_quality": [
            r"测试质量[：:\s-]+([0-9.]+)",
            r"[Tt]est[_\s][Qq]uality[：:\s-]+([0-9.]+)",
        ],
        "code_quality": [
            r"代码质量[：:\s-]+([0-9.]+)",
            r"[Cc]ode[_\s][Qq]uality[：:\s-]+([0-9.]+)",
        ],
        "security": [
            r"安全性[：:\s-]+([0-9.]+)",
            r"[Ss]ecurity[：:\s-]+([0-9.]+)",
        ],
        "performance": [
            r"性能[：:\s-]+([0-9.]+)",
            r"[Pp]erformance[：:\s-]+([0-9.]+)",
        ],
    }

    for dim, pat_list in patterns.items():
        for pattern in pat_list:
            match = re.search(pattern, content)
            if match:
                scores[dim] = float(match.group(1))
                break

    return scores


def print_score_breakdown(scores: dict, score: float):
    """打印评分明细"""
    print(f"\n{'='*50}")
    print(f"{'评分明细':^50}")
    print(f"{'='*50}")
    print(f"{'维度':<12} {'得分':<8} {'权重':<8} {'贡献':<8}")
    print(f"{'-'*36}")
    for dim in DIMENSIONS_ORDER:
        contribution = scores[dim] * WEIGHTS[dim]
        name = DIMENSION_NAMES_CN.get(dim, dim)
        print(f"{name:<12} {scores[dim]:<8.2f} {WEIGHTS[dim]:<8.2f} {contribution:<8.3f}")
    print(f"{'-'*36}")
    print(f"{'综合评分':<12} {score:<8.2f}  1.00")
    print()


def interactive_mode():
    """交互式输入评分"""
    scores = {}
    print("\n五维度评分输入 (0.0 - 1.0)")
    print("=" * 40)
    for dim in DIMENSIONS_ORDER:
        name = DIMENSION_NAMES_CN.get(dim, dim)
        while True:
            try:
                raw = input(f"  {name} ({dim}): ").strip()
                val = float(raw)
                if 0.0 <= val <= 1.0:
                    scores[dim] = val
                    break
                print(f"    范围 0.0-1.0, 你输入了 {val}")
            except ValueError:
                if raw.lower() in ("q", "quit", "exit"):
                    print("退出")
                    return
                print("    请输入数字 (0.0-1.0)")

    score = calculate(scores)
    print_score_breakdown(scores, score)
    print(f"评级: {rating(score)}")


def batch_extract(glob_pattern: str = "outputs/cross-review/round-*/review-report.md"):
    """从多个审核报告批量提取评分"""
    import glob
    import re as regex

    reports = sorted(glob.glob(glob_pattern))

    if not reports:
        print(f"没有找到匹配 {glob_pattern} 的审核报告")
        return

    print(f"\n{'='*60}")
    print(f"{'批量评分提取':^60}")
    print(f"{'='*60}")
    print(f"{'轮次':<8} {'正确性':<8} {'测试':<8} {'质量':<8} {'安全':<8} {'性能':<8} {'综合':<8} {'评级':<10}")
    print(f"{'-'*60}")

    for report_path in reports:
        scores = extract_scores_from_report(report_path)

        # 提取轮次号
        m = regex.search(r"round-(\d+)", report_path)
        rn = m.group(1) if m else "?"

        if len(scores) == 5:
            total = calculate(scores)
            print(f"{rn:<8} {scores['correctness']:<8.2f} {scores['test_quality']:<8.2f} "
                  f"{scores['code_quality']:<8.2f} {scores['security']:<8.2f} "
                  f"{scores['performance']:<8.2f} {total:<8.2f} {rating(total):<10}")
        else:
            print(f"{rn:<8} {'—':<8} {'—':<8} {'—':<8} {'—':<8} {'—':<8} {'—':<8} {'数据不完整':<10}")

    print()


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--help", "-h"):
            print("用法:")
            print("  score_calculator.py <correctness> <test_quality> <code_quality> <security> <performance>")
            print("  score_calculator.py --interactive")
            print("  score_calculator.py --batch [glob_pattern]")
            return

        if sys.argv[1] == "--interactive":
            interactive_mode()
            return

        if sys.argv[1] == "--batch":
            pattern = sys.argv[2] if len(sys.argv) > 2 else "outputs/cross-review/round-*/review-report.md"
            batch_extract(pattern)
            return

        # CLI: 5 个数字参数
        if len(sys.argv) == 6:
            try:
                values = [float(v) for v in sys.argv[1:6]]
                scores = dict(zip(DIMENSIONS_ORDER, values))
                score = calculate(scores)
                print_score_breakdown(scores, score)
                print(f"评级: {rating(score)}")
                return
            except ValueError:
                pass

        # 处理中文顺序: 正确性 测试质量 代码质量 安全性 性能
        try:
            values = [float(v) for v in sys.argv[1:6]]
            cn_order = ["正确性", "测试质量", "代码质量", "安全性", "性能"]
            scores = dict(zip(DIMENSIONS_ORDER, values))
            score = calculate(scores)
            print_score_breakdown(scores, score)
            print(f"评级: {rating(score)}")
            return
        except ValueError:
            pass

        print(f"无法解析参数: {sys.argv[1:]}")
        print("使用 --help 查看用法")
        sys.exit(1)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
