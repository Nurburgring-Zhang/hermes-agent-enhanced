"""
OpenClaw SuperIntelligence Plugin - Hermes Plugin
Complete AI orchestration with multi-model collaboration, optimization, and monitoring.
"""

import asyncio
import hashlib
import json
import logging
import os
import statistics
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from hermes.plugins.plugin_system import Plugin, PluginConfig, PluginManifest

logger = logging.getLogger(__name__)


# ============ Data Structures ============

class Strategy(Enum):
    """Collaboration strategies."""
    VOTING = "voting"
    CONSENSUS = "consensus"
    CASCADE = "cascade"
    PARALLEL = "parallel"


@dataclass
class ModelConfig:
    """Model configuration."""
    id: str
    name: str
    provider: str
    model: str
    api_key: str
    endpoint: str
    temperature: float = 0.7
    max_tokens: int = 2048
    weight: float = 1.0
    capabilities: list[str] = field(default_factory=list)
    cost_per_token: float = 0.0
    priority: int = 1
    enabled: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelMetrics:
    """Performance metrics for a model."""
    requests: int = 0
    successes: int = 0
    failures: int = 0
    total_latency: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    quality_scores: list[float] = field(default_factory=list)
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    error_types: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.recent_latencies) if self.recent_latencies else 0.0

    @property
    def avg_quality(self) -> float:
        return statistics.mean(self.quality_scores) if self.quality_scores else 0.5

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.requests, 1)

    @property
    def cost_per_request(self) -> float:
        return self.total_cost / max(self.successes, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "success_rate": self.success_rate,
            "avg_latency": self.avg_latency,
            "avg_quality": self.avg_quality,
            "cost_per_request": self.cost_per_request,
            "total_cost": self.total_cost
        }


@dataclass
class Response:
    """Model response."""
    model_id: str
    content: str
    latency: float
    tokens: int
    cost: float
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatRequest:
    """Chat request context."""
    prompt: str
    context: list[dict[str, str]]
    strategy: str = "voting"
    max_iterations: int = 1
    required_models: list[str] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    enable_tools: bool = True
    tools: list[dict[str, Any]] = field(default_factory=list)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolCall:
    """Tool call from model."""
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None


# ============ Model Adapters ============

class ModelAdapter(ABC):
    """Abstract model adapter."""

    @abstractmethod
    async def generate(self, prompt: str, context: list[dict[str, str]], config: ModelConfig, tools: list[dict] = None) -> Response:
        """Generate response."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if model is healthy."""


class OpenRouterAdapter(ModelAdapter):
    """OpenRouter API adapter."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def generate(self, prompt: str, context: list[dict[str, str]], config: ModelConfig, tools: list[dict] = None) -> Response:
        """Call OpenRouter API."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp required")

        # Build messages
        messages = []
        for msg in context[-10:]:  # Last 10 messages
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {config.api_key or os.getenv('OPENROUTER_API_KEY', '')}",
            "Content-Type": "application/json"
        }

        start = time.time()
        try:
            async with self.session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"OpenRouter error: {resp.status} - {text}")

                data = await resp.json()
                latency = time.time() - start

                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                cost = tokens * config.cost_per_token / 1000

                return Response(
                    model_id=config.id,
                    content=content,
                    latency=latency,
                    tokens=tokens,
                    cost=cost,
                    confidence=0.8  # Placeholder
                )
        except Exception as e:
            logger.error(f"OpenRouter generate failed for {config.id}: {e}")
            raise

    async def health_check(self) -> bool:
        try:
            async with self.session.get("https://openrouter.ai/api/v1/models", timeout=5) as resp:
                return resp.status == 200
        except:
            return False


class DirectOpenAIAdapter(ModelAdapter):
    """Direct OpenAI API adapter."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def generate(self, prompt: str, context: list[dict[str, str]], config: ModelConfig, tools: list[dict] = None) -> Response:
        start = time.time()
        url = "https://api.openai.com/v1/chat/completions"

        messages = []
        for msg in context[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        async with self.session.post(url, json=payload, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError(f"OpenAI API error: {resp.status}")

            data = await resp.json()
            latency = time.time() - start

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            cost = tokens * config.cost_per_token / 1000

            return Response(
                model_id=config.id,
                content=content,
                latency=latency,
                tokens=tokens,
                cost=cost,
                confidence=0.8
            )

    async def health_check(self) -> bool:
        try:
            async with self.session.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {self.session._default_headers.get('Authorization', '')}"}, timeout=5) as resp:
                return resp.status == 200
        except:
            return False


class DirectAnthropicAdapter(ModelAdapter):
    """Direct Anthropic Claude API adapter."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def generate(self, prompt: str, context: list[dict[str, str]], config: ModelConfig, tools: list[dict] = None) -> Response:
        start = time.time()
        url = "https://api.anthropic.com/v1/messages"

        # Anthropic uses system prompt separately
        system_prompt = ""
        messages = []

        for msg in context[-10:]:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        async with self.session.post(url, json=payload, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Anthropic API error: {resp.status}")

            data = await resp.json()
            latency = time.time() - start

            content = data["content"][0]["text"]
            tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
            cost = tokens * config.cost_per_token / 1000

            return Response(
                model_id=config.id,
                content=content,
                latency=latency,
                tokens=tokens,
                cost=cost,
                confidence=0.8
            )

    async def health_check(self) -> bool:
        # Anthropic doesn't have a simple health endpoint
        return True  # Assume healthy if API key present


class LocalAdapter(ModelAdapter):
    """Local model adapter (Ollama, etc.)."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def generate(self, prompt: str, context: list[dict[str, str]], config: ModelConfig, tools: list[dict] = None) -> Response:
        start = time.time()
        endpoint = config.endpoint or "http://localhost:11434/api/generate"

        # Build prompt with context
        full_prompt = ""
        for msg in context[-5:]:
            role = "Human" if msg["role"] == "user" else "Assistant" if msg["role"] == "assistant" else "System"
            full_prompt += f"{role}: {msg['content']}\n"
        full_prompt += f"Human: {prompt}\nAssistant:"

        payload = {
            "model": config.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens
            }
        }

        async with self.session.post(endpoint, json=payload, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Local model error: {resp.status}")

            data = await resp.json()
            latency = time.time() - start

            content = data.get("response", "")
            tokens = len(content.split()) * 1.3  # Rough estimate
            cost = 0.0  # Local is free

            return Response(
                model_id=config.id,
                content=content,
                latency=latency,
                tokens=int(tokens),
                cost=cost,
                confidence=0.6  # Lower confidence for local models
            )

    async def health_check(self) -> bool:
        try:
            async with self.session.get("http://localhost:11434/api/tags", timeout=2) as resp:
                return resp.status == 200
        except:
            return False


class CustomAdapter(ModelAdapter):
    """Custom API adapter with configurable mapping."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def generate(self, prompt: str, context: list[dict[str, str]], config: ModelConfig, tools: list[dict] = None) -> Response:
        start = time.time()

        # Use custom endpoint and template
        endpoint = config.extra.get("custom_endpoint", config.endpoint)
        headers = config.extra.get("custom_headers", {})
        template = config.extra.get("custom_body_template")

        if template:
            import jinja2
            tmpl = jinja2.Template(template)
            payload = json.loads(tmpl.render(
                prompt=prompt,
                context=context,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            ))
        else:
            payload = {
                "prompt": prompt,
                "context": context,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens
            }

        async with self.session.post(endpoint, json=payload, headers=headers, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Custom API error: {resp.status}")

            data = await resp.json()

            # Extract content using path
            content_path = config.extra.get("custom_response_path", "content").split(".")
            content = data
            for key in content_path:
                content = content.get(key, "")
                if not isinstance(content, str):
                    break

            latency = time.time() - start
            tokens = len(prompt.split()) + len(content.split())
            cost = tokens * config.cost_per_token / 1000

            return Response(
                model_id=config.id,
                content=str(content),
                latency=latency,
                tokens=tokens,
                cost=cost
            )

    async def health_check(self) -> bool:
        try:
            endpoint = self.config.extra.get("health_endpoint", self.config.endpoint)
            async with self.session.get(endpoint, timeout=2) as resp:
                return resp.status == 200
        except:
            return False


# ============ Synthesis Engines ============

class SynthesisEngine:
    """Combine multiple responses into final answer."""

    @staticmethod
    async def voting(responses: list[Response]) -> Response:
        """Select best response via scoring."""
        if not responses:
            raise ValueError("No responses to vote on")

        # Score each response
        scores = []
        for resp in responses:
            # Length score (prefer reasonable length)
            word_count = len(resp.content.split())
            length_score = 1.0 if 20 < word_count < 500 else 0.5

            # Latency score (faster is better)
            latency_score = 1.0 / (1.0 + resp.latency)

            # Combined score (quality not yet available)
            score = length_score * 0.6 + latency_score * 0.4
            scores.append((score, resp))

        scores.sort(key=lambda x: x[0], reverse=True)
        best = scores[0][1]

        return Response(
            model_id="superintel",
            content=best.content,
            latency=sum(r.latency for r in responses),
            tokens=best.tokens,
            cost=sum(r.cost for r in responses),
            confidence=scores[0][0]
        )

    @staticmethod
    async def consensus(responses: list[Response], max_iterations: int = 3) -> Response:
        """Iterative refinement until agreement."""
        if len(responses) < 2:
            return responses[0] if responses else None

        # For simplicity: take highest confidence and have one model critique
        best = max(responses, key=lambda r: r.confidence)

        # Consensus would involve multiple rounds
        # Simplified: return best initial
        return best

    @staticmethod
    async def cascade(responses: list[Response], config: Any, threshold: float = 0.7) -> Response:
        """Cascade: use best acceptable or refine."""
        # Sort by priority/quality
        sorted_resps = sorted(responses, key=lambda r: r.confidence, reverse=True)

        for resp in sorted_resps:
            if resp.confidence >= threshold:
                return resp

        # If none meet threshold, return best anyway
        return sorted_resps[0] if sorted_resps else None

    @staticmethod
    async def parallel(responses: list[Response]) -> Response:
        """Combine insights from all responses."""
        # Take longest/most detailed response
        longest = max(responses, key=lambda r: len(r.content))
        return Response(
            model_id="superintel",
            content=f"[Combined from {len(responses)} models]\n\n{longest.content}",
            latency=max(r.latency for r in responses),
            tokens=sum(r.tokens for r in responses),
            cost=sum(r.cost for r in responses),
            confidence=statistics.mean([r.confidence for r in responses]) if responses else 0.5
        )


# ============ Self-Critique ============

class SelfCritiqueEngine:
    """Self-critique and refinement loop."""

    CRITIQUE_PROMPT = """
Evaluate the following response to the query. Identify:
1. Factual errors
2. Missing information
3. Logical inconsistencies
4. Areas needing clarification

Query: {prompt}

Response: {response}

Provide specific critique and suggestions for improvement.
"""

    REFINE_PROMPT = """
Original query: {prompt}

Previous response: {response}

Critique: {critique}

Provide an improved response addressing the critique.
"""

    def __init__(self, adapter: ModelAdapter, config: ModelConfig):
        self.adapter = adapter
        self.config = config

    async def refine(self, prompt: str, response: str, context: list[dict[str, str]], max_iterations: int = 3, min_confidence: float = 0.7) -> tuple[str, int]:
        """
        Iteratively refine response.
        Returns (final_response, iterations_performed)
        """
        current_response = response
        context = context.copy()

        for i in range(max_iterations):
            # Get critique
            critique_prompt = self.CRITIQUE_PROMPT.format(prompt=prompt, response=current_response)
            messages = context + [{"role": "user", "content": critique_prompt}]

            critique_resp = await self.adapter.generate(
                prompt=critique_prompt,
                context=context,
                config=self.config
            )

            critique = critique_resp.content

            # Check if critique indicates satisfaction (simple heuristic)
            if any(word in critique.lower() for word in ["excellent", "perfect", "no issues", "good", "satisfactory"]) and i > 0:
                logger.info(f"Self-critique satisfied after {i+1} iterations")
                return current_response, i + 1

            # Refine
            refine_prompt = self.REFINE_PROMPT.format(
                prompt=prompt,
                response=current_response,
                critique=critique
            )

            refine_resp = await self.adapter.generate(
                prompt=refine_prompt,
                context=context,
                config=self.config
            )

            # Estimate confidence improvement
            prev_len = len(current_response.split())
            new_len = len(refine_resp.content.split())
            # Simple heuristic: if response grew substantially, likely improved
            confidence = min(0.9, 0.5 + (new_len - prev_len) / 100) if new_len > prev_len else 0.5

            current_response = refine_resp.content
            context.append({"role": "assistant", "content": refine_resp.content})

            if confidence >= min_confidence:
                logger.info(f"Reached confidence {confidence:.2f} after {i+2} iterations")
                break

        return current_response, min(max_iterations, i + 2)


# ============ Main Plugin ============

class SuperIntelligencePlugin(Plugin):
    """Main SuperIntelligence plugin."""

    def __init__(self, manifest: PluginManifest, config: PluginConfig):
        super().__init__(manifest, config)
        self.models: dict[str, ModelConfig] = {}
        self.adapters: dict[str, ModelAdapter] = {}
        self.metrics: dict[str, ModelMetrics] = {}
        self.cache: dict[str, tuple[str, float, datetime]] = {}  # key: (response, confidence, timestamp)
        self._lock = asyncio.Lock()
        self._session: aiohttp.ClientSession | None = None
        self._strategy = Strategy.VOTING
        self._last_routing: dict[str, float] = {}  # model_id -> weight

    async def init(self) -> None:
        """Initialize plugin."""
        await super().init()
        await self._load_config()
        await self._initialise_adapters()
        self._load_metrics()
        self._build_adapter_map()
        logger.info(f"SuperIntelligence initialized with {len(self.models)} models")

    async def start(self) -> None:
        """Start plugin."""
        await super().start()
        logger.info("SuperIntelligence started")

    async def stop(self) -> None:
        """Stop plugin and save metrics."""
        await self._save_metrics()
        await super().stop()

    def _load_config(self):
        """Load configuration."""
        self._strategy = Strategy(self.config.config.get("strategy", "voting"))
        self.max_iterations = self.config.config.get("max_iterations", 3)
        self.auto_optimize = self.config.config.get("auto_optimize", True)
        self.cache_enabled = self.config.config.get("cache_responses", True)
        self.cache_ttl = self.config.config.get("cache_ttl", 3600)
        self.concurrency_limit = self.config.config.get("concurrency_limit", 4)
        self.timeout = self.config.config.get("timeout", 30)
        self.min_confidence = self.config.config.get("min_confidence_threshold", 0.7)
        self.enable_self_critique = self.config.config.get("enable_self_critique", True)
        self.log_requests = self.config.config.get("log_requests", False)

        # Load models
        for model_data in self.config.config.get("models", []):
            model = ModelConfig(
                id=model_data["id"],
                name=model_data["name"],
                provider=model_data["provider"],
                model=model_data["model"],
                api_key=model_data.get("api_key", ""),
                endpoint=model_data.get("endpoint", ""),
                temperature=model_data.get("temperature", 0.7),
                max_tokens=model_data.get("max_tokens", 2048),
                weight=model_data.get("weight", 1.0),
                capabilities=model_data.get("capabilities", []),
                cost_per_token=model_data.get("cost_per_token", 0.0),
                priority=model_data.get("priority", 1),
                enabled=model_data.get("enabled", True),
                extra=model_data.get("extra", {})
            )
            self.models[model.id] = model
            self.metrics[model.id] = ModelMetrics()

    async def _initialise_adapters(self):
        """Initialize HTTP session and adapters."""
        self._session = aiohttp.ClientSession()

    def _build_adapter_map(self):
        """Build adapter instances."""
        adapter_map = {
            "openrouter": OpenRouterAdapter,
            "openai": DirectOpenAIAdapter,
            "anthropic": DirectAnthropicAdapter,
            "local": LocalAdapter,
            "custom": CustomAdapter
        }

        for model in self.models.values():
            if not model.enabled:
                continue

            adapter_cls = adapter_map.get(model.provider)
            if adapter_cls:
                adapter = adapter_cls()
                adapter.session = self._session
                self.adapters[model.id] = adapter

    def _load_metrics(self):
        """Load metrics from file."""
        metrics_file = self.config.config.get("metrics_file", "./metrics.json")
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file) as f:
                    data = json.load(f)
                # Load into metrics
                for mid, mdata in data.items():
                    if mid in self.metrics:
                        self.metrics[mid] = ModelMetrics(**mdata)
                        # Convert recent_latencies
                        if "recent_latencies" in mdata:
                            self.metrics[mid].recent_latencies = deque(mdata["recent_latencies"], maxlen=100)
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")

    async def _save_metrics(self):
        """Save metrics to file."""
        metrics_file = self.config.config.get("metrics_file", "./metrics.json")
        data = {}
        for mid, metrics in self.metrics.items():
            mdict = metrics.to_dict()
            mdict["recent_latencies"] = list(metrics.recent_latencies)
            data[mid] = mdict

        try:
            with open(metrics_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def _select_models(self, required: list[str] = None, strategy: str = None) -> list[ModelConfig]:
        """Select models to use for a request."""
        if strategy:
            strat = Strategy(strategy)
        else:
            strat = self._strategy

        # Start with all enabled models
        candidates = [m for m in self.models.values() if m.enabled]

        # Filter required
        if required:
            candidates = [m for m in candidates if m.id in required] or candidates

        if not candidates:
            # Fallback
            fallback_id = self.config.config.get("fallback_model", "default")
            if fallback_id in self.models:
                return [self.models[fallback_id]]
            return []

        # Weight-based selection
        # For voting and consensus: use top N by weight
        if strat in [Strategy.VOTING, Strategy.CONSENSUS]:
            candidates.sort(key=lambda m: (m.weight, -m.priority), reverse=True)
            # Use at least 2 if available, max 4
            n = min(4, max(2, len(candidates)))
            return candidates[:n]

        # Cascade: start with top N by priority/speed
        if strat == Strategy.CASCADE:
            candidates.sort(key=lambda m: (m.priority, -m.weight))
            return candidates[:min(3, len(candidates))]

        # Parallel: use all
        return candidates[:self.concurrency_limit]

    def _get_cache_key(self, prompt: str, context: list[dict], models: list[str], strategy: str) -> str:
        key_str = f"{prompt}:{json.dumps(context[-5:])}:{','.join(sorted(models))}:{strategy}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def _process_tool_calls(self, tool_calls: list[ToolCall], context: list[dict]) -> list[dict]:
        """Process tool calls by delegating to other plugins."""
        results = []
        manager = self.manager  # Get plugin manager

        if not manager:
            return results

        for tc in tool_calls:
            try:
                # Map tool name to plugin action
                # Simple: tool name matches plugin capability
                plugins = manager.get_plugins_providing_capability(tc.tool_name)

                if plugins:
                    plugin = plugins[0]
                    result = await plugin.execute(tc.tool_name, **tc.arguments)
                    tc.result = result
                    results.append(tc)
                else:
                    logger.warning(f"No plugin provides capability: {tc.tool_name}")
            except Exception as e:
                logger.error(f"Tool call failed {tc.tool_name}: {e}")

        return results

    # ============ Main Entry Points ============

    async def chat(self, prompt: str, context: list[dict[str, str]] = None, strategy: str = None, max_iterations: int = None, required_models: list[str] = None, **kwargs) -> dict[str, Any]:
        """
        Generate response using multi-model collaboration.
        """
        if context is None:
            context = []

        # Build request
        request = ChatRequest(
            prompt=prompt,
            context=context,
            strategy=strategy or self._strategy.value,
            max_iterations=max_iterations or self.max_iterations,
            required_models=required_models or []
        )

        # Check cache
        if self.cache_enabled:
            cache_key = self._get_cache_key(
                request.prompt,
                request.context,
                [m.id for m in self._select_models(request.required_models, request.strategy)],
                request.strategy
            )
            if cache_key in self.cache:
                cached_resp, confidence, timestamp = self.cache[cache_key]
                age = (datetime.now() - timestamp).total_seconds()
                if age < self.cache_ttl:
                    logger.info(f"Cache hit for request {request.request_id[:8]}")
                    return {
                        "content": cached_resp,
                        "source": "cache",
                        "confidence": confidence,
                        "cached": True,
                        "latency": 0.0,
                        "cost": 0.0
                    }

        # Select models
        selected_models = self._select_models(request.required_models, request.strategy)
        if not selected_models:
            raise RuntimeError("No models available")

        logger.info(f"Request {request.request_id[:8]}: strategy={request.strategy}, models={[m.id for m in selected_models]}")

        # Execute according to strategy
        start_time = time.time()

        if request.strategy == Strategy.VOTING.value:
            raw_responses = await self._execute_parallel(request, selected_models)
            result = await SynthesisEngine.voting(raw_responses)

            # Self-critique if enabled
            if self.enable_self_critique and request.max_iterations > 1:
                best_model = selected_models[0]  # Use best model for critique
                critique_engine = SelfCritiqueEngine(self.adapters[best_model.id], best_model)
                refined, iterations = await critique_engine.refine(
                    request.prompt,
                    result.content,
                    request.context,
                    max_iterations=request.max_iterations,
                    min_confidence=self.min_confidence
                )
                result.content = refined
                result.confidence = min(0.95, result.confidence + 0.1 * iterations)

        elif request.strategy == Strategy.CONSENSUS.value:
            raw_responses = await self._execute_parallel(request, selected_models)
            result = await SynthesisEngine.consensus(raw_responses, request.max_iterations)

        elif request.strategy == Strategy.CASCADE.value:
            result = await self._execute_cascade(request, selected_models)

        elif request.strategy == Strategy.PARALLEL.value:
            raw_responses = await self._execute_parallel(request, selected_models)
            result = await SynthesisEngine.parallel(raw_responses)

        else:
            # Default: parallel + voting
            raw_responses = await self._execute_parallel(request, selected_models)
            result = await SynthesisEngine.voting(raw_responses)

        total_latency = time.time() - start_time

        # Update metrics
        for resp in raw_responses:
            metrics = self.metrics[resp.model_id]
            metrics.requests += 1
            metrics.successes += 1
            metrics.total_latency += resp.latency
            metrics.recent_latencies.append(resp.latency)
            metrics.total_tokens += resp.tokens
            metrics.total_cost += resp.cost

        # Cache result
        if self.cache_enabled and result.confidence >= self.min_confidence:
            cache_key = self._get_cache_key(request.prompt, request.context, [m.id for m in selected_models], request.strategy)
            self.cache[cache_key] = (result.content, result.confidence, datetime.now())

        # Auto-optimize
        if self.auto_optimize:
            await self._optimize_weights()

        # Save metrics periodically
        await self._save_metrics()

        return {
            "content": result.content,
            "source": result.model_id,
            "confidence": result.confidence,
            "cached": False,
            "latency": total_latency,
            "cost": result.cost,
            "models_used": [r.model_id for r in raw_responses],
            "iterations": 1,
            "request_id": request.request_id
        }

    async def _execute_parallel(self, request: ChatRequest, models: list[ModelConfig]) -> list[Response]:
        """Execute all models in parallel."""
        tasks = []
        for model in models:
            adapter = self.adapters.get(model.id)
            if adapter:
                task = asyncio.create_task(self._call_model(adapter, model, request))
                tasks.append(task)

        responses = []
        for coro in asyncio.as_completed(tasks):
            try:
                resp = await coro
                if resp:
                    responses.append(resp)
            except Exception as e:
                logger.error(f"Model call failed: {e}")

        return responses

    async def _call_model(self, adapter: ModelAdapter, model: ModelConfig, request: ChatRequest) -> Response | None:
        """Call a single model."""
        try:
            resp = await adapter.generate(
                prompt=request.prompt,
                context=request.context,
                config=model
            )
            if self.log_requests:
                logger.debug(f"Model {model.id} responded ({resp.latency:.2f}s, {resp.tokens} tokens)")
            return resp
        except Exception as e:
            logger.error(f"Model {model.id} error: {e}")
            metrics = self.metrics[model.id]
            metrics.failures += 1
            metrics.requests += 1
            metrics.error_types[type(e).__name__] += 1
            return None

    async def _execute_cascade(self, request: ChatRequest, models: list[ModelConfig]) -> Response:
        """Execute cascade strategy."""
        for model in models:
            adapter = self.adapters.get(model.id)
            if not adapter:
                continue

            resp = await self._call_model(adapter, model, request)
            if resp and resp.confidence >= self.min_confidence:
                return resp

        # If none meet threshold, return best we got (from last iteration)
        # But we only executed last one, so run all and pick best
        responses = await self._execute_parallel(request, models)
        if responses:
            return await SynthesisEngine.voting(responses)
        raise RuntimeError("All models failed in cascade")

    async def _optimize_weights(self):
        """Dynamically optimize model weights based on performance."""
        for model_id, metrics in self.metrics.items():
            if metrics.requests < 10:
                continue  # Not enough data

            # Quality score
            quality = metrics.avg_quality if metrics.quality_scores else 0.5
            # Latency penalty (prefer under 2s)
            latency_penalty = 1.0 if metrics.avg_latency < 2.0 else 2.0 / metrics.avg_latency
            # Cost penalty
            cost_score = 1.0 / (1.0 + metrics.cost_per_request * 10)

            # Combined score
            score = quality * 0.5 + latency_penalty * 0.3 + cost_score * 0.2

            # Adjust weight
            model = self.models.get(model_id)
            if model:
                # Blend current weight with new score
                new_weight = model.weight * 0.8 + score * 0.2
                model.weight = max(0.1, min(2.0, new_weight))
                logger.debug(f"Optimized weight for {model_id}: {model.weight:.3f}")

    # ============ Actions & Tools ============

    async def optimize(self, task: str, prompt: str, **kwargs) -> dict[str, Any]:
        """Optimize query for specific task."""
        context = [{"role": "system", "content": f"You are optimizing for task: {task}.\nProvide the best possible response."}]
        return await self.chat(prompt=prompt, context=context, **kwargs)

    async def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        total_requests = sum(m.requests for m in self.metrics.values())
        total_cost = sum(m.total_cost for m in self.metrics.values())
        total_success = sum(m.successes for m in self.metrics.values())

        avg_latency = statistics.mean([m.avg_latency for m in self.metrics.values() if m.avg_latency > 0]) if any(m.avg_latency > 0 for m in self.metrics.values()) else 0

        model_perf = {}
        for mid, m in self.metrics.items():
            model_perf[mid] = m.to_dict()
            model_perf[mid]["current_weight"] = self.models.get(mid).weight if mid in self.models else 1.0

        cache_size = len(self.cache)

        return {
            "total_requests": total_requests,
            "total_cost": total_cost,
            "success_rate": total_success / max(total_requests, 1),
            "avg_latency": avg_latency,
            "cache_size": cache_size,
            "strategy": self._strategy.value,
            "model_performance": model_perf,
            "timestamp": datetime.now().isoformat()
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """List configured models."""
        result = []
        for model in self.models.values():
            metrics = self.metrics.get(model.id)
            result.append({
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "model": model.model,
                "enabled": model.enabled,
                "weight": model.weight,
                "priority": model.priority,
                "performance": metrics.to_dict() if metrics else None,
                "cost_per_token": model.cost_per_token
            })
        return sorted(result, key=lambda x: x["weight"], reverse=True)

    async def enable_model(self, model_id: str, enable: bool = True) -> bool:
        """Enable or disable a model."""
        if model_id in self.models:
            self.models[model_id].enabled = enable
            logger.info(f"Model {model_id} {'enabled' if enable else 'disabled'}")
            return True
        return False

    async def benchmark(self, queries: list[str], models: list[str] = None) -> dict[str, Any]:
        """Benchmark models with test queries."""
        test_models = [m for m in self.models.values() if m.enabled]
        if models:
            test_models = [m for m in test_models if m.id in models]

        results = {}
        for model in test_models[:3]:  # Limit to 3 models for benchmark
            model_times = []
            for query in queries[:5]:  # Limit to 5 queries
                start = time.time()
                try:
                    resp = await self._call_model(self.adapters[model.id], model, ChatRequest(prompt=query, context=[]))
                    if resp:
                        elapsed = time.time() - start
                        model_times.append(elapsed)
                except:
                    pass

            results[model.id] = {
                "avg_latency": statistics.mean(model_times) if model_times else None,
                "samples": len(model_times)
            }

        return results

    async def provide_feedback(self, response_id: str, rating: int, comments: str = "") -> bool:
        """
        Provide feedback to improve routing.
        rating: 1-5 scale
        """
        # In a full implementation, would connect to actual response
        # For now, adjust weights based on rating
        confidence_boost = (rating - 3) * 0.1  # +/- 0.2

        # Find model from response (would need response storage)
        # Simplified: apply to all models as negative example if rating low
        if rating < 3:
            for model in self.models.values():
                model.weight = max(0.1, model.weight - 0.1)
        elif rating > 3:
            for model in self.models.values():
                model.weight = min(2.0, model.weight + 0.05)

        logger.info(f"Feedback recorded: rating={rating}, confidence_boost={confidence_boost}")
        return True

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute actions."""
        actions = {
            "chat": self.chat,
            "optimize": self.optimize,
            "get_metrics": self.get_metrics,
            "list_models": self.list_models,
            "enable_model": self.enable_model,
            "benchmark": self.benchmark,
            "provide_feedback": self.provide_feedback
        }

        if action not in actions:
            raise ValueError(f"Unknown action: {action}")

        method = actions[action]
        return await method(**kwargs)

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions."""
        # Get tool-exposing plugins
        available_tools = []
        if self.manager:
            tools = self.manager.get_plugin_tools()
            available_tools.extend([t for t in tools if t["name"] != "superintel_chat"])

        return [{
            "name": "superintel_chat",
            "description": "Generate responses using multi-model collaboration with self-optimization",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "User prompt/query"},
                    "context": {"type": "array", "description": "Prior conversation messages", "items": {"type": "object"}},
                    "strategy": {"type": "string", "enum": ["voting", "consensus", "cascade", "parallel"], "default": "voting"},
                    "max_iterations": {"type": "integer", "description": "Max self-critique iterations", "default": 3},
                    "required_models": {"type": "array", "description": "Model IDs to use", "items": {"type": "string"}}
                },
                "required": ["prompt"]
            }
        }] + available_tools

    async def health_check(self) -> dict[str, Any]:
        """Return plugin health status."""
        status = await super().health_check()
        status["models_configured"] = len(self.models)
        status["models_enabled"] = sum(1 for m in self.models.values() if m.enabled)
        status["adapters_loaded"] = len(self.adapters)
        status["strategy"] = self._strategy.value
        status["cache_size"] = len(self.cache)
        status["total_requests"] = sum(m.requests for m in self.metrics.values())
        status["avg_latency"] = statistics.mean([m.avg_latency for m in self.metrics.values() if m.avg_latency > 0]) if any(m.avg_latency > 0 for m in self.metrics.values()) else 0
        return status
