#!/usr/bin/env python3
"""
OpenClaw Smart Router - 演示脚本
展示基本功能
"""

import asyncio
import importlib.util
import os
import sys

# 直接加载模块
spec = importlib.util.spec_from_file_location(
    "openclaw_smart_router",
    os.path.join(os.path.dirname(__file__), "__init__.py")
)
router_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router_module)

# 导入需要的类
SmartRouter = router_module.SmartRouter
RoutingEngine = router_module.RoutingEngine
TaskIntent = router_module.TaskIntent
ModelTier = router_module.ModelTier
UserPreferences = router_module.UserPreferences
ExecutionResult = router_module.ExecutionResult
get_all_models = router_module.get_all_models
RoutingContext = router_module.RoutingContext
SatisfactionFeedback = router_module.SatisfactionFeedback


async def main():
    print("=" * 60)
    print("OpenClaw Smart Router - 演示")
    print("=" * 60)

    # 列可用的模型
    print("\n可用模型:")
    all_models = get_all_models()
    for model in all_models[:8]:  # 只显示前8个
        print(f"  - {model.name} ({model.provider}, {model.tier.value})")
    print(f"  共 {len(all_models)} 个模型")

    # 创建路由器（不使用AI提供者，会使用规则回退）
    print("\n1. 创建路由器...")
    router = RoutingEngine()
    print("   ✓ 路由器创建成功")

    # 测试各种指令
    test_instructions = [
        "用Python写一个快速排序算法",
        "解释量子力学的基本原理",
        "写一个React组件来处理表单提交",
        "分析当前的全球经济趋势",
        "创建一个数据库设计：用户管理系统",
        "写一首关于春天的诗",
        "我的网站加载慢，如何优化？",
        "将'Hello World'翻译成中文"
    ]

    print("\n2. 路由测试:")
    for i, instruction in enumerate(test_instructions, 1):
        print(f"\n  [{i}] 指令: {instruction}")
        try:
            decision = await router.route(instruction)

            model = decision.recommended_model
            print(f"      ✓ 选择: {model.name} ({model.tier.value})")
            print(f"        理由: {decision.reasoning[:100]}...")
            print(f"        置信度: {decision.confidence:.2%}")
        except Exception as e:
            print(f"      ✗ 错误: {e}")

    # 测试带上下文的场景
    print("\n3. 带上下文的路由:")
    from openclaw_smart_router.smart_router_types import RoutingContext

    context = RoutingContext(
        session_id="demo-session",
        conversation_history=[
            {"role": "user", "content": "我想写代码"},
            {"role": "assistant", "content": "好的，您想写什么语言？"}
        ]
    )

    decision = await router.route("用Python写一个hello world", context)
    model = decision.recommended_model
    print(f"  选择: {model.name} ({model.tier.value})")

    # 测试用户偏好
    print("\n4. 带用户偏好的路由:")
    from openclaw_smart_router.smart_router_types import UserPreferences

    prefs = UserPreferences(
        preferred_tier=ModelTier.FREE,
        exclude_models=["gpt-4-turbo"]
    )

    context = RoutingContext(preferences=prefs)
    decision = await router.route("分析数据", context)
    model = decision.recommended_model
    print(f"  选择: {model.name} ({model.tier.value})")

    # 测试反馈提交
    print("\n5. 提交反馈:")
    from openclaw_smart_router.smart_router_types import SatisfactionFeedback

    feedback = SatisfactionFeedback(
        task_id=decision.routing_decision.recommended_model.id,
        model_used=decision.recommended_model.id,
        rating=5,
        is_satisfied=True,
        comments="回答质量很好"
    )

    await router.submit_feedback(feedback)
    print("   ✓ 反馈已提交")

    # 获取统计
    print("\n6. 系统统计:")
    stats = await router.get_stats()
    print(f"  总任务数: {stats.total_tasks}")
    print(f"  成功任务: {stats.successful_tasks}")
    print(f"  平均满意度: {stats.average_satisfaction}")
    print(f"  模型切换次数: {stats.model_switch_count}")

    # 层级分布
    print("\n  层级分布:")
    for tier, count in stats.tier_distribution.items():
        print(f"    {tier.value}: {count}")

    # 意图分布
    print("\n  意图分布 (前5):")
    sorted_intents = sorted(
        stats.intent_distribution.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    for intent, count in sorted_intents:
        print(f"    {intent.value}: {count}")

    # 健康检查
    print("\n7. 健康检查:")
    try:
        health = await router.health_check() if hasattr(router, "health_check") else None
        if health:
            print(f"  健康状态: {'✓ 正常' if health.get('healthy') else '✗ 异常'}")
            if not health.get("healthy"):
                print(f"  问题: {health.get('issues', [])}")
        else:
            print("  健康检查方法未实现")
    except Exception as e:
        print(f"  健康检查失败: {e}")

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    # 重置
    router.reset()
    print("\n路由器已重置")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n演示被中断")
    except Exception as e:
        print(f"演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
