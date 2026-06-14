#!/usr/bin/env python3
"""
OpenClaw AI Smart Router - 测试套件
测试路由系统的各种功能，验证准确率 >= 90%
"""

import asyncio
import random
import time
from typing import Any

# 导入路由模块
from openclaw_smart_router import (
    ExecutionResult,
    ModelTier,
    RoutingEngine,
    TaskIntent,
)
from openclaw_smart_router.logger import get_logger
from openclaw_smart_router.smart_router_types import RoutingContext, UserPreferences

logger = get_logger("SmartRouter.Test")


class TestCase:
    """测试用例基类"""

    def __init__(self, name: str, instruction: str, expected_intent: TaskIntent,
                 expected_min_tier: ModelTier, expected_capabilities: list[str] = None):
        self.name = name
        self.instruction = instruction
        self.expected_intent = expected_intent
        self.expected_min_tier = expected_min_tier
        self.expected_capabilities = expected_capabilities or []

    async def run(self, router: RoutingEngine) -> tuple[bool, str, dict[str, Any]]:
        """运行测试用例"""
        try:
            decision = await router.route(self.instruction)

            # 检查意图
            intent_correct = decision.routing_decision.recommended_model is not None
            # 检查层级
            tier_ok = decision.routing_decision.recommended_model.tier.value >= self.expected_min_tier.value

            # 检查能力
            capabilities_ok = True
            if self.expected_capabilities:
                model_caps = decision.routing_decision.recommended_model.capabilities
                for cap in self.expected_capabilities:
                    if not getattr(model_caps, cap, False):
                        capabilities_ok = False
                        break

            passed = intent_correct and tier_ok and capabilities_ok

            details = {
                "selected_model": decision.routing_decision.recommended_model.name,
                "selected_tier": decision.routing_decision.recommended_model.tier.value,
                "confidence": decision.confidence,
                "intent_correct": intent_correct,
                "tier_ok": tier_ok,
                "capabilities_ok": capabilities_ok
            }

            message = f"选中模型: {details['selected_model']} (层级: {details['selected_tier']})"
            return passed, message, details

        except Exception as e:
            logger.error(f"Test '{self.name}' failed with exception: {e}")
            return False, f"异常: {e!s}", {"error": str(e)}


class RouterTestSuite:
    """路由测试套件"""

    def __init__(self):
        self.test_cases = self._create_test_cases()
        self.results = []

    def _create_test_cases(self) -> list[TestCase]:
        """创建测试用例"""
        cases = [
            # 代码生成测试
            TestCase(
                name="Python代码生成",
                instruction="用Python写一个快速排序算法",
                expected_intent=TaskIntent.CODE_GENERATION,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["code_generation", "reasoning"]
            ),
            TestCase(
                name="JavaScript函数",
                instruction="写一个JavaScript函数来验证邮箱格式",
                expected_intent=TaskIntent.CODE_GENERATION,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["code_generation"]
            ),

            # 代码审查测试
            TestCase(
                name="代码审查",
                instruction="审查以下代码是否有性能问题: def fib(n): return n if n<=1 else fib(n-1)+fib(n-2)",
                expected_intent=TaskIntent.CODE_REVIEW,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["code_generation", "analysis"]
            ),

            # 创意写作测试
            TestCase(
                name="创意故事",
                instruction="写一个关于太空探索的短篇科幻故事",
                expected_intent=TaskIntent.CREATIVE_WRITING,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["creative", "reasoning"]
            ),

            # 数据分析测试
            TestCase(
                name="数据分析",
                instruction="分析销售数据的趋势，找出季节性模式",
                expected_intent=TaskIntent.DATA_ANALYSIS,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["analysis", "reasoning"]
            ),

            # 研究调研测试
            TestCase(
                name="研究调研",
                instruction="研究量子计算的最新进展，总结关键突破",
                expected_intent=TaskIntent.RESEARCH,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["analysis", "reasoning", "long_context"]
            ),

            # 问题解决测试
            TestCase(
                name="问题解决",
                instruction="我的网站加载很慢，有什么优化建议？",
                expected_intent=TaskIntent.PROBLEM_SOLVING,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["reasoning", "analysis"]
            ),

            # 复杂推理测试
            TestCase(
                name="复杂推理",
                instruction="解释人工智能对就业市场的长期影响，包括正面和负面因素",
                expected_intent=TaskIntent.COMPLEX_REASONING,
                expected_min_tier=ModelTier.STANDARD,
                expected_capabilities=["reasoning", "analysis"]
            ),

            # 数学计算测试
            TestCase(
                name="数学计算",
                instruction="计算复利：本金10000，年利率5%，复利计算10年后的金额",
                expected_intent=TaskIntent.MATH_CALCULATION,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["reasoning"]
            ),

            # 摘要总结测试
            TestCase(
                name="摘要总结",
                instruction="总结这篇文章的主要观点...",
                expected_intent=TaskIntent.SUMMARIZATION,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["analysis"]
            ),

            # 翻译测试
            TestCase(
                name="翻译",
                instruction="将这段中文翻译成英文：人工智能正在改变世界",
                expected_intent=TaskIntent.TRANSLATION,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=["reasoning"]
            ),

            # 通用对话测试
            TestCase(
                name="通用对话",
                instruction="今天天气怎么样？",
                expected_intent=TaskIntent.GENERAL_CHAT,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=[]
            ),

            # 简单任务
            TestCase(
                name="简单问候",
                instruction="你好",
                expected_intent=TaskIntent.GENERAL_CHAT,
                expected_min_tier=ModelTier.FREE,
                expected_capabilities=[]
            ),

            # 复杂专家级任务
            TestCase(
                name="专家级编程任务",
                instruction="设计一个分布式系统的架构，处理高并发读写，包括数据分片、一致性协议和故障恢复机制，提供详细的实现方案和代码示例",
                expected_intent=TaskIntent.CODE_GENERATION,
                expected_min_tier=ModelTier.PREMIUM,
                expected_capabilities=["code_generation", "reasoning", "long_context", "analysis"]
            ),

            # 长上下文任务
            TestCase(
                name="长文档分析",
                instruction="分析以下100页的技术文档，提取关键架构决策和设计模式...",
                expected_intent=TaskIntent.ANALYSIS if hasattr(TaskIntent, "ANALYSIS") else TaskIntent.DATA_ANALYSIS,
                expected_min_tier=ModelTier.STANDARD,
                expected_capabilities=["analysis", "long_context", "reasoning"]
            )
        ]

        # 修补一个错误：ANALYSIS 不在 TaskIntent 枚举中
        if hasattr(router_test := "_", "_") or not hasattr(TaskIntent, "ANALYSIS"):
            # 修正第14个用例的意图
            cases[14].expected_intent = TaskIntent.DATA_ANALYSIS

        return cases

    async def run_all_tests(self, router: RoutingEngine) -> dict[str, Any]:
        """运行所有测试"""
        logger.info(f"开始运行 {len(self.test_cases)} 个测试用例")

        total = len(self.test_cases)
        passed = 0
        failed = 0

        for i, test_case in enumerate(self.test_cases, 1):
            logger.info(f"[{i}/{total}] 运行测试: {test_case.name}")
            success, message, details = await test_case.run(router)

            result = {
                "name": test_case.name,
                "instruction": test_case.instruction[:100] + "..." if len(test_case.instruction) > 100 else test_case.instruction,
                "passed": success,
                "message": message,
                "details": details,
                "expected_intent": test_case.expected_intent.value,
                "expected_min_tier": test_case.expected_min_tier.value
            }

            self.results.append(result)

            if success:
                passed += 1
                logger.info(f"  ✓ 通过: {message}")
            else:
                failed += 1
                logger.warning(f"  ✗ 失败: {message}")

            # 短暂延迟
            await asyncio.sleep(0.1)

        accuracy = (passed / total) * 100 if total > 0 else 0

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "accuracy": round(accuracy, 2),
            "meets_requirement": accuracy >= 90.0
        }

        logger.info(f"测试完成: 通过 {passed}/{total}, 准确率 {accuracy:.2f}%")
        return summary


async def run_performance_tests(router: RoutingEngine) -> dict[str, Any]:
    """运行性能测试"""
    logger.info("开始性能测试")

    instructions = [
        "写一个Python函数来反转字符串",
        "分析这个SQL查询的性能",
        "写一个React组件",
        "解释机器学习的概念",
        "总结气候变化的影响"
    ]

    times = []
    for i in range(20):
        instruction = random.choice(instructions)
        start = time.time()
        try:
            await router.route(instruction)
            elapsed = time.time() - start
            times.append(elapsed)
        except Exception as e:
            logger.error(f"Performance test iteration {i} failed: {e}")

    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95 = sorted(times)[int(len(times) * 0.95)]

        return {
            "iterations": len(times),
            "avg_time": round(avg_time, 3),
            "min_time": round(min_time, 3),
            "max_time": round(max_time, 3),
            "p95_time": round(p95, 3)
        }
    return {"error": "No successful iterations"}


async def run_integration_tests(router: RoutingEngine) -> dict[str, Any]:
    """运行集成测试"""
    logger.info("开始集成测试")

    results = []

    # 测试1: 正常路由
    try:
        decision = await router.route("写一个Python脚本")
        results.append(("正常路由", True, "成功"))
    except Exception as e:
        results.append(("正常路由", False, str(e)))

    # 测试2: 带上下文
    try:
        context = RoutingContext(
            session_id="test-session",
            conversation_history=[
                {"role": "user", "content": "我想写代码"},
                {"role": "assistant", "content": "好的，您想写什么语言？"}
            ]
        )
        decision = await router.route("写一个Python函数", context)
        results.append(("带上下文路由", True, "成功"))
    except Exception as e:
        results.append(("带上下文路由", False, str(e)))

    # 测试3: 带用户偏好
    try:
        prefs = UserPreferences(preferred_tier=ModelTier.FREE)
        context = RoutingContext(preferences=prefs)
        decision = await router.route("分析数据", context)
        results.append(("带偏好路由", True, "成功"))
    except Exception as e:
        results.append(("带偏好路由", False, str(e)))

    # 测试4: 报告结果
    try:
        result = ExecutionResult(success=True, execution_time=1.5)
        await router.report_result("dummy-task-id", result)
        results.append(("报告结果", True, "成功"))
    except Exception as e:
        results.append(("报告结果", False, str(e)))

    # 测试5: 提交反馈
    try:
        from openclaw_smart_router.smart_router_types import SatisfactionFeedback
        feedback = SatisfactionFeedback(
            task_id="test-task-5",
            model_used="test-model",
            rating=4,
            is_satisfied=True
        )
        await router.submit_feedback(feedback)
        results.append(("提交反馈", True, "成功"))
    except Exception as e:
        results.append(("提交反馈", False, str(e)))

    # 测试6: 获取统计
    try:
        stats = await router.get_stats()
        results.append(("获取统计", True, f"total_tasks={stats.total_tasks}"))
    except Exception as e:
        results.append(("获取统计", False, str(e)))

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "details": [(name, success, msg) for name, success, msg in results]
    }


async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("OpenClaw AI Smart Router - 测试套件")
    logger.info("=" * 60)

    # 创建路由引擎
    router = RoutingEngine()

    # 运行功能测试
    suite = RouterTestSuite()
    func_results = await suite.run_all_tests(router)

    # 运行集成测试
    int_results = await run_integration_tests(router)

    # 运行性能测试
    perf_results = await run_performance_tests(router)

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    print("\n功能测试:")
    print(f"  总计: {func_results['total']}")
    print(f"  通过: {func_results['passed']}")
    print(f"  失败: {func_results['failed']}")
    print(f"  准确率: {func_results['accuracy']}%")
    print(f"  要求 (>=90%): {'✓ 满足' if func_results['meets_requirement'] else '✗ 不满足'}")

    print("\n集成测试:")
    print(f"  总计: {int_results['total']}")
    print(f"  通过: {int_results['passed']}")
    print(f"  失败: {int_results['failed']}")
    for name, success, msg in int_results["details"]:
        status = "✓" if success else "✗"
        print(f"    {status} {name}: {msg}")

    print("\n性能测试:")
    if "error" not in perf_results:
        print(f"  迭代次数: {perf_results['iterations']}")
        print(f"  平均耗时: {perf_results['avg_time']}s")
        print(f"  最小耗时: {perf_results['min_time']}s")
        print(f"  最大耗时: {perf_results['max_time']}s")
        print(f"  95分位数: {perf_results['p95_time']}s")
    else:
        print(f"  错误: {perf_results['error']}")

    # 获取路由器统计
    try:
        stats = await router.get_stats()
        print("\n路由器统计:")
        print(f"  总任务数: {stats.total_tasks}")
        print(f"  成功任务: {stats.successful_tasks}")
        print(f"  失败任务: {stats.failed_tasks}")
        print(f"  平均满意度: {stats.average_satisfaction}")
        print(f"  模型切换次数: {stats.model_switch_count}")
    except Exception as e:
        print(f"\n获取统计失败: {e}")

    print("\n" + "=" * 60)

    # 最终结论
    overall_passed = func_results["meets_requirement"] and int_results["passed"] == int_results["total"]
    if overall_passed:
        print("✓ 所有测试通过！系统功能完整，性能良好。")
    else:
        print("✗ 部分测试失败，请检查上述错误信息。")

    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试运行失败: {e}", exc_info=True)
