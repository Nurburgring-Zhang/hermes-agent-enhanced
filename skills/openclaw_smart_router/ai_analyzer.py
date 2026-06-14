"""
OpenClaw AI Smart Router - AI Analyzer
AI分析器 - 使用AI分析用户指令的意图和复杂度，支持规则回退
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .cache import SmartRouterCache
from .logger import get_logger
from .smart_router_types import InstructionAnalysis, RoutingContext, TaskComplexity, TaskIntent


@dataclass
class AnalyzerConfig:
    """分析器配置"""
    analysis_model: str = "claude-3-haiku"
    max_retries: int = 2
    timeout: int = 30000
    enable_cache: bool = True
    cache_ttl: int = 3600
    use_fallback: bool = True


class AIAnalyzer:
    """AI分析器"""

    def __init__(self, config: AnalyzerConfig | None = None, cache: SmartRouterCache | None = None):
        self.config = config or AnalyzerConfig()
        self.logger = get_logger("SmartRouter.AIAnalyzer")
        self.cache = cache or SmartRouterCache()
        self._ai_provider: Callable[[str], Any] | None = None

    def set_ai_provider(self, provider: Callable[[str], Any]):
        """设置AI提供者"""
        self._ai_provider = provider
        self.logger.info("AI provider set")

    async def analyze(
        self,
        instruction: str,
        context: RoutingContext | None = None
    ) -> InstructionAnalysis:
        """
        分析用户指令
        """
        # 检查缓存
        if self.config.enable_cache:
            cached = self.cache.get_analysis(instruction)
            if cached:
                self.logger.debug(f"Cache hit for instruction: {instruction[:50]}...")
                return cached

        self.logger.debug(f"Analyzing instruction: {instruction[:50]}...")

        try:
            # 尝试AI分析
            if self._ai_provider:
                analysis = await self._call_ai_for_analysis(instruction, context)
            else:
                # 如果没有AI提供者，使用规则回退
                self.logger.debug("No AI provider, using rule-based fallback")
                analysis = self._rule_based_analysis(instruction)

            # 缓存结果
            if self.config.enable_cache:
                self.cache.set_analysis(instruction, analysis, self.config.cache_ttl)

            return analysis

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            if self.config.use_fallback:
                return self._rule_based_analysis(instruction)
            raise

    async def _call_ai_for_analysis(
        self,
        instruction: str,
        context: RoutingContext | None
    ) -> InstructionAnalysis:
        """调用AI进行分析"""
        prompt = self._build_analysis_prompt(instruction, context)

        try:
            response = await self._ai_provider(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            self.logger.error(f"AI call failed: {e}")
            raise

    def _build_analysis_prompt(
        self,
        instruction: str,
        context: RoutingContext | None
    ) -> str:
        """构建分析提示词"""
        history_context = ""
        if context and context.conversation_history:
            recent_history = context.conversation_history[-5:]
            history_context = "\n".join(
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in recent_history
            )
            history_context = f"## 对话历史\n{history_context}\n\n"

        custom_prompt = self.config.analysis_prompt if hasattr(self.config, "analysis_prompt") else None

        if custom_prompt:
            return custom_prompt.format(
                instruction=instruction,
                history_context=history_context
            )

        return f"""你是一个专业的AI任务分析器。请分析以下用户指令，返回JSON格式的分析结果。

## 用户指令
"{instruction}"

{history_context}## 分析要求
请从以下维度分析：

1. **intent (意图)**: 从以下类别中选择最匹配的:
   - general_chat: 通用对话
   - code_generation: 代码生成
   - code_review: 代码审查
   - creative_writing: 创意写作
   - data_analysis: 数据分析
   - research: 研究/调研
   - image_understanding: 图像理解
   - summarization: 摘要总结
   - translation: 翻译
   - problem_solving: 问题解决
   - complex_reasoning: 复杂推理
   - math_calculation: 数学计算
   - multimodal: 多模态任务

2. **complexity (复杂度)**:
   - simple: 简单任务，几句话能解决
   - moderate: 中等复杂度，需要一些上下文
   - complex: 复杂任务，需要深入分析
   - expert: 专家级任务，需要高级推理能力

3. **required_capabilities (必需能力)**: 根据意图列出所需能力数组，选项包括:
   - reasoning: 推理能力
   - code_generation: 代码生成
   - creative: 创意写作
   - analysis: 分析能力
   - vision: 视觉理解
   - function_calling: 函数调用
   - long_context: 长上下文处理

4. **estimated_tokens**: 预估输入token数量（整数）

5. **language**: 指令语言（如 "中文", "English" 等）

6. **confidence**: 分析置信度（0-1之间的小数）

7. **reasoning**: 简要说明分析理由（1-2句话）

请只返回JSON，不要有其他内容:
{{
  "intent": "...",
  "complexity": "...",
  "required_capabilities": [...],
  "estimated_tokens": 1000,
  "language": "...",
  "confidence": 0.85,
  "reasoning": "..."
}}
"""

    def _parse_analysis_response(self, response: str) -> InstructionAnalysis:
        """解析AI响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)

                intent = TaskIntent(parsed["intent"])
                complexity = TaskComplexity(parsed["complexity"])

                return InstructionAnalysis(
                    intent=intent,
                    complexity=complexity,
                    required_capabilities=parsed.get("required_capabilities", []),
                    estimated_tokens=parsed.get("estimated_tokens", 500),
                    language=parsed.get("language", "Unknown"),
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", "基于AI分析")
                )
            self.logger.warning("No JSON found in AI response, using fallback")
            return self._rule_based_analysis(response)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse AI response: {e}, response: {response[:200]}")
            return self._rule_based_analysis(response)

    def _rule_based_analysis(self, instruction: str) -> InstructionAnalysis:
        """规则回退分析"""
        self.logger.debug("Performing rule-based analysis")

        text = instruction.lower()
        word_count = len(instruction.split())

        # 检测意图
        intent = TaskIntent.GENERAL_CHAT

        if re.search(r"代码|code|函数|function|程序|programming|python|javascript|typescript|java", text, re.IGNORECASE):
            intent = TaskIntent.CODE_GENERATION
        elif re.search(r"审查|review|检查|optimize|重构|refactor", text, re.IGNORECASE):
            intent = TaskIntent.CODE_REVIEW
        elif re.search(r"创意|写作|写一篇|故事|诗歌|article|blog|essay", text, re.IGNORECASE):
            intent = TaskIntent.CREATIVE_WRITING
        elif re.search(r"分析|analysis|数据|data|统计", text, re.IGNORECASE):
            intent = TaskIntent.DATA_ANALYSIS
        elif re.search(r"研究|research|调研|调查", text, re.IGNORECASE):
            intent = TaskIntent.RESEARCH
        elif re.search(r"图片|图像|vision|看图|image|photo", text, re.IGNORECASE):
            intent = TaskIntent.IMAGE_UNDERSTANDING
        elif re.search(r"摘要|总结|summarize|tl;dr", text, re.IGNORECASE):
            intent = TaskIntent.SUMMARIZATION
        elif re.search(r"翻译|translate", text, re.IGNORECASE):
            intent = TaskIntent.TRANSLATION
        elif re.search(r"解决|solve|问题|problem|help", text, re.IGNORECASE):
            intent = TaskIntent.PROBLEM_SOLVING
        elif re.search(r"推理|reason|思考|think|为什么|why|逻辑", text, re.IGNORECASE):
            intent = TaskIntent.COMPLEX_REASONING
        elif re.search(r"计算|数学|math|calculate|公式", text, re.IGNORECASE):
            intent = TaskIntent.MATH_CALCULATION

        # 检测复杂度
        complexity = TaskComplexity.SIMPLE

        if word_count > 500 or re.search(r"详细|复杂|高级|deep|complex|advanced", text, re.IGNORECASE):
            complexity = TaskComplexity.COMPLEX
        elif word_count > 100 or re.search(r"解释|说明|explain|describe|analyze", text, re.IGNORECASE):
            complexity = TaskComplexity.MODERATE

        if re.search(r"专家|专业级|enterprise|博士|论文|dissertation|phd", text, re.IGNORECASE):
            complexity = TaskComplexity.EXPERT

        # 推断所需能力
        required_capabilities = []

        if intent == TaskIntent.CODE_GENERATION or intent == TaskIntent.CODE_REVIEW:
            required_capabilities.append("code_generation")
            required_capabilities.append("reasoning")
        if intent == TaskIntent.DATA_ANALYSIS or intent == TaskIntent.RESEARCH:
            required_capabilities.append("analysis")
            required_capabilities.append("reasoning")
        if intent == TaskIntent.CREATIVE_WRITING:
            required_capabilities.append("creative")
        if intent == TaskIntent.IMAGE_UNDERSTANDING:
            required_capabilities.append("vision")
        if complexity in (TaskComplexity.COMPLEX, TaskComplexity.EXPERT):
            required_capabilities.append("reasoning")
            if word_count > 1000:
                required_capabilities.append("long_context")

        # 检测语言
        language = "English"
        if re.search(r"[\u4e00-\u9fa5]", instruction):
            language = "中文"

        # 预估token
        estimated_tokens = max(100, word_count * 2)

        # 置信度
        confidence = 0.7

        return InstructionAnalysis(
            intent=intent,
            complexity=complexity,
            required_capabilities=list(set(required_capabilities)),  # 去重
            estimated_tokens=estimated_tokens,
            language=language,
            confidence=confidence,
            reasoning=f"基于规则分析: 意图={intent.value}, 复杂度={complexity.value}, 字数={word_count}"
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        return self.cache.get_stats()

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.logger.info("Analysis cache cleared")
