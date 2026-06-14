"""
OpenClaw AI Smart Router - Satisfaction Evaluator
满意度评估器 - 收集和分析用户反馈，决定是否需要模型升级
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .logger import get_logger
from .smart_router_types import (
    InstructionAnalysis,
    ModelInfo,
    ModelTier,
    RoutingHistory,
    SatisfactionFeedback,
)


@dataclass
class SatisfactionConfig:
    """满意度评估配置"""
    auto_upgrade_enabled: bool = True
    upgrade_threshold: int = 3  # 评分低于此值自动升级 (1-5)
    consecutive_dissatisfaction: int = 2  # 连续不满意次数触发升级
    enable_negative_feedback: bool = True
    feedback_retention_days: int = 30


@dataclass
class UpgradeSuggestion:
    """升级建议"""
    should_upgrade: bool
    reason: str
    suggested_tier: ModelTier
    alternative_models: list[str]
    confidence: float


class SatisfactionEvaluator:
    """满意度评估器"""

    def __init__(self, config: SatisfactionConfig | None = None):
        self.config = config or SatisfactionConfig()
        self.logger = get_logger("SmartRouter.SatisfactionEvaluator")
        self._feedback_history: dict[str, list[SatisfactionFeedback]] = {}
        self._consecutive_dissatisfaction: dict[str, int] = {}
        self._recent_feedbacks: list[SatisfactionFeedback] = []

    def evaluate_upgrade(
        self,
        task_id: str,
        analysis: InstructionAnalysis,
        current_model: ModelInfo,
        recent_history: list[RoutingHistory] | None = None
    ) -> UpgradeSuggestion:
        """
        评估是否应该升级模型
        """
        user_feedbacks = self._feedback_history.get(task_id, [])

        # 1. 检查最近的反馈
        feedback_upgrade = self._check_recent_feedback(task_id, user_feedbacks)

        # 2. 检查连续不满意
        consecutive_count = self._consecutive_dissatisfaction.get(task_id, 0)

        # 3. 检查复杂度不匹配
        complexity_upgrade = self._check_complexity_mismatch(analysis, current_model)

        # 4. 检查历史执行问题
        historical_upgrade = self._analyze_historical_issues(recent_history)

        should_upgrade = (
            feedback_upgrade or
            consecutive_count >= self.config.consecutive_dissatisfaction or
            complexity_upgrade["should_upgrade"] or
            historical_upgrade["many_failures"]
        )

        reason = ""
        suggested_tier = current_model.tier

        if feedback_upgrade:
            reason = "用户反馈不满意"
            suggested_tier = self._get_next_tier(current_model.tier)
        elif consecutive_count >= self.config.consecutive_dissatisfaction:
            reason = f"连续{consecutive_count}次不满意反馈"
            suggested_tier = self._get_next_tier(current_model.tier)
        elif complexity_upgrade["should_upgrade"]:
            reason = complexity_upgrade["reason"]
            suggested_tier = self._get_next_tier(current_model.tier)
        elif historical_upgrade["many_failures"]:
            reason = f"历史执行失败率较高 ({historical_upgrade['failure_rate']}%)"
            suggested_tier = self._get_next_tier(current_model.tier)

        confidence = self._calculate_confidence(
            feedback_upgrade,
            consecutive_count,
            complexity_upgrade,
            historical_upgrade
        )

        suggestion = UpgradeSuggestion(
            should_upgrade=should_upgrade,
            reason=reason,
            suggested_tier=suggested_tier,
            alternative_models=self._suggest_alternative_models(current_model),
            confidence=confidence
        )

        self.logger.debug(
            f"Upgrade evaluation: task={task_id}, should_upgrade={should_upgrade}, "
            f"reason={reason}, confidence={confidence:.2f}"
        )

        return suggestion

    def _check_recent_feedback(
        self,
        task_id: str,
        feedbacks: list[SatisfactionFeedback]
    ) -> bool:
        """检查最近的反馈"""
        if not feedbacks:
            return False

        recent_count = min(3, len(feedbacks))
        recent = feedbacks[-recent_count:]

        has_dissatisfaction = any(not f.is_satisfied for f in recent)

        if has_dissatisfaction:
            avg_rating = sum(f.rating for f in recent) / len(recent)
            return avg_rating < self.config.upgrade_threshold

        return False

    def _check_complexity_mismatch(
        self,
        analysis: InstructionAnalysis,
        model: ModelInfo
    ) -> dict[str, Any]:
        """检查复杂度不匹配"""
        should_upgrade = False
        reasons = []

        # 专家级任务需要高级模型
        if analysis.complexity.value == "expert":
            if not model.capabilities.reasoning:
                should_upgrade = True
                reasons.append("专家级任务需要推理能力")

        # 能力检查
        missing_capabilities = [
            cap for cap in analysis.required_capabilities
            if not getattr(model.capabilities, cap, False)
        ]

        if missing_capabilities:
            should_upgrade = True
            reasons.append(f"缺少能力: {', '.join(missing_capabilities)}")

        return {
            "should_upgrade": should_upgrade,
            "reason": "; ".join(reasons) if reasons else ""
        }

    def _analyze_historical_issues(
        self,
        history: list[RoutingHistory] | None
    ) -> dict[str, Any]:
        """分析历史执行问题"""
        if not history:
            return {"many_failures": False, "failure_rate": 0}

        recent = history[-10:]
        failure_count = sum(1 for h in recent if h.execution_result and not h.execution_result.success)
        failure_rate = (failure_count / len(recent)) * 100 if recent else 0

        return {
            "many_failures": failure_rate > 30,
            "failure_rate": round(failure_rate, 1)
        }

    def _get_next_tier(self, current_tier: ModelTier) -> ModelTier:
        """获取下一层级"""
        tier_order = [ModelTier.FREE, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]
        current_index = tier_order.index(current_tier)
        if current_index + 1 < len(tier_order):
            return tier_order[current_index + 1]
        return current_tier

    def _suggest_alternative_models(self, current_model: ModelInfo) -> list[str]:
        """建议替代模型"""
        alternatives = []
        tier_order = [ModelTier.FREE, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.ENTERPRISE]
        current_index = tier_order.index(current_model.tier)

        # 添加同一层级或更高层级的其他模型
        for i in range(current_index, len(tier_order)):
            tier_name = tier_order[i].value
            alternatives.append(f"{tier_name} 层级推荐模型")

        return alternatives[:3]

    def _calculate_confidence(
        self,
        feedback_upgrade: bool,
        consecutive_count: int,
        complexity_mismatch: dict[str, Any],
        historical_issues: dict[str, Any]
    ) -> float:
        """计算升级置信度"""
        confidence = 0.0

        if feedback_upgrade:
            confidence += 0.3
        if consecutive_count >= 2:
            confidence += 0.25
        if complexity_mismatch["should_upgrade"]:
            confidence += 0.25
        if historical_issues["many_failures"]:
            confidence += 0.2

        return min(1.0, confidence)

    def submit_feedback(self, feedback: SatisfactionFeedback):
        """提交用户反馈"""
        task_id = feedback.task_id

        # 存储反馈
        if task_id not in self._feedback_history:
            self._feedback_history[task_id] = []
        self._feedback_history[task_id].append(feedback)

        # 追踪连续不满意
        if not feedback.is_satisfied:
            count = self._consecutive_dissatisfaction.get(task_id, 0) + 1
            self._consecutive_dissatisfaction[task_id] = count
        else:
            self._consecutive_dissatisfaction.pop(task_id, None)

        # 记录最近反馈
        self._recent_feedbacks.append(feedback)

        # 维持最近100条反馈
        if len(self._recent_feedbacks) > 100:
            self._recent_feedbacks = self._recent_feedbacks[-100:]

        self.logger.info(
            f"Feedback received: task={task_id}, rating={feedback.rating}, "
            f"satisfied={feedback.is_satisfied}"
        )

        # 清理过期数据
        self._cleanup_old_data()

    def get_task_feedbacks(self, task_id: str) -> list[SatisfactionFeedback]:
        """获取任务的反馈历史"""
        return self._feedback_history.get(task_id, [])

    def get_satisfaction_stats(self) -> dict[str, Any]:
        """获取整体满意度统计"""
        feedbacks = self._recent_feedbacks

        if not feedbacks:
            return {
                "total_feedbacks": 0,
                "average_rating": 0.0,
                "satisfaction_rate": 0,
                "common_issues": [],
                "most_needed_capability": "unknown"
            }

        total = len(feedbacks)
        avg_rating = sum(f.rating for f in feedbacks) / total
        satisfied_count = sum(1 for f in feedbacks if f.is_satisfied)
        satisfaction_rate = round((satisfied_count / total) * 100)

        # 统计常见问题
        issue_counts: dict[str, int] = {}
        for f in feedbacks:
            if f.issues:
                for issue in f.issues:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

        common_issues = sorted(
            issue_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        common_issues = [issue for issue, _ in common_issues]

        return {
            "total_feedbacks": total,
            "average_rating": round(avg_rating, 2),
            "satisfaction_rate": satisfaction_rate,
            "common_issues": common_issues,
            "most_needed_capability": self._infer_most_needed_capability(feedbacks)
        }

    def _infer_most_needed_capability(self, feedbacks: list[SatisfactionFeedback]) -> str:
        """推断最需要的能力"""
        capability_counts = {
            "reasoning": 0,
            "code_generation": 0,
            "creative": 0,
            "analysis": 0,
            "vision": 0
        }

        for f in feedbacks:
            if f.improvement_areas:
                for area in f.improvement_areas:
                    area_lower = area.lower()
                    if "code" in area_lower or "代码" in area_lower:
                        capability_counts["code_generation"] += 1
                    if "reason" in area_lower or "推理" in area_lower:
                        capability_counts["reasoning"] += 1
                    if "creative" in area_lower or "创意" in area_lower:
                        capability_counts["creative"] += 1
                    if "analyze" in area_lower or "分析" in area_lower:
                        capability_counts["analysis"] += 1
                    if "vision" in area_lower or "视觉" in area_lower or "image" in area_lower:
                        capability_counts["vision"] += 1

        if any(capability_counts.values()):
            return max(capability_counts.items(), key=lambda x: x[1])[0]

        return "unknown"

    def _cleanup_old_data(self):
        """清理过期数据"""
        now = datetime.now()
        cutoff = now - timedelta(days=self.config.feedback_retention_days)
        cutoff_timestamp = cutoff.timestamp()

        # 清理旧反馈
        for task_id in list(self._feedback_history.keys()):
            original_len = len(self._feedback_history[task_id])
            self._feedback_history[task_id] = [
                f for f in self._feedback_history[task_id]
                if f.timestamp >= cutoff_timestamp
            ]
            if not self._feedback_history[task_id]:
                self._feedback_history.pop(task_id, None)

        # 清理连续不满意计数（超过7天的重置）
        week_ago = (now - timedelta(days=7)).timestamp()
        recent_task_ids = {
            f.task_id for f in self._recent_feedbacks
            if f.timestamp >= week_ago
        }

        for task_id in list(self._consecutive_dissatisfaction.keys()):
            if task_id not in recent_task_ids:
                self._consecutive_dissatisfaction.pop(task_id, None)

    def get_feedback_trend(self, days: int = 7) -> dict[str, Any]:
        """获取反馈趋势"""
        cutoff = datetime.now().timestamp() - days * 24 * 60 * 60
        recent = [f for f in self._recent_feedbacks if f.timestamp >= cutoff]

        if not recent:
            return {
                "daily_satisfaction": [],
                "trend": "stable"
            }

        # 按天分组
        daily_data: dict[str, list[float]] = {}
        for f in recent:
            date = datetime.fromtimestamp(f.timestamp).strftime("%Y-%m-%d")
            if date not in daily_data:
                daily_data[date] = []
            daily_data[date].append(f.rating)

        daily_satisfaction = [
            {
                "date": date,
                "rating": round(sum(ratings) / len(ratings), 2),
                "count": len(ratings)
            }
            for date, ratings in sorted(daily_data.items())
        ]

        # 判断趋势
        trend = "stable"
        if len(daily_satisfaction) >= 2:
            half = len(daily_satisfaction) // 2
            first_half = daily_satisfaction[:half]
            second_half = daily_satisfaction[half:]

            first_avg = sum(d["rating"] for d in first_half) / len(first_half)
            second_avg = sum(d["rating"] for d in second_half) / len(second_half)

            if second_avg - first_avg > 0.2:
                trend = "improving"
            elif first_avg - second_avg > 0.2:
                trend = "declining"

        return {
            "daily_satisfaction": daily_satisfaction,
            "trend": trend
        }

    def update_config(self, config: SatisfactionConfig):
        """更新配置"""
        self.config = config

    def reset(self):
        """重置评估器状态"""
        self._feedback_history.clear()
        self._consecutive_dissatisfaction.clear()
        self._recent_feedbacks.clear()
        self.logger.info("Satisfaction evaluator reset")

    def get_stats(self) -> dict[str, Any]:
        """获取评估器统计"""
        satisfaction = self.get_satisfaction_stats()
        trend = self.get_feedback_trend(7)

        return {
            **satisfaction,
            "total_tasks_with_feedback": len(self._feedback_history),
            "consecutive_dissatisfaction_counts": self._consecutive_dissatisfaction.copy(),
            "trend_7days": trend["trend"]
        }
