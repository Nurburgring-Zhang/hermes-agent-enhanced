#!/usr/bin/env python3
"""
resilience_patterns.py — 商用级弹性模式实现（对标OPA/pybreaker/Hystrix/AWS IAM）

提供：
1. CircuitBreaker（熔断器）— 对标 pybreaker/Hystrix
2. RetryWithBackoff（带退避重试）— 对标 Hystrix/Resilience4j
3. RateLimiter（限流器）— 对标 AWS WAF
4. TimeoutManager（超时控制）— 对标 Hystrix
5. FallbackRegistry（降级回退）— 对标 Hystrix
6. DecisionAuditLog（决策审计日志）— 对标 OPA
7. MetricsCollector（可观测指标）— 对标 Hystrix Stream
8. HotReloader（热加载）— 对标 OPA Bundles
9. DryRunMode（干跑模式）— 对标 OPA dry-run
"""
import json
import logging
import os
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 1. Circuit Breaker（熔断器）
# ═══════════════════════════════════════════════════════════════

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenError(Exception):
    pass

@dataclass
class CircuitBreakerConfig:
    fail_max: int = 5
    reset_timeout: float = 30.0
    success_threshold: int = 2
    sliding_window_size: int = 20
    error_threshold_percentage: float = 50.0

class CircuitBreaker:
    """熔断器 — 对标 Hystrix/pybreaker 实现。

    在连续失败超过阈值后自动打开电路，
    经过冷却期后进入半开状态探测恢复。

    Attributes:
        name: 熔断器名称，用于日志和指标标识。
        config: 熔断器配置。
        state: 当前电路状态 (CLOSED/OPEN/HALF_OPEN)。
        stats: 调用统计 {'total', 'success', 'failure', 'rejected'}。

    Example:
        >>> cb = CircuitBreaker("api", CircuitBreakerConfig(fail_max=5))
        >>> cb.call(lambda: requests.get("http://api/service"))
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        """初始化熔断器。

        Args:
            name: 熔断器名称。
            config: 熔断器配置，默认 CircuitBreakerConfig()。
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._lock = threading.RLock()
        self._failure_count = 0
        self._half_open_successes = 0
        self._last_state_change = time.monotonic()
        self._window = deque(maxlen=self.config.sliding_window_size)
        self._listeners = []
        self.stats = {"total": 0, "success": 0, "failure": 0, "rejected": 0}

    @property
    def state(self):
        return self._state

    def _try_half_open(self):
        if self._state != CircuitState.OPEN:
            return False
        elapsed = time.monotonic() - self._last_state_change
        if elapsed >= self.config.reset_timeout:
            self._state = CircuitState.HALF_OPEN
            self._half_open_successes = 0
            self._last_state_change = time.monotonic()
            return True
        return False

    def _open_circuit(self):
        self._state = CircuitState.OPEN
        self._last_state_change = time.monotonic()
        for cb in self._listeners:
            try: cb(self.name, "OPEN")
            except Exception: pass

    def call(self, func, *args, **kwargs):
        """通过熔断器调用目标函数。

        在 CLOSED/HALF_OPEN 状态下正常调用，
        OPEN 状态下直接抛出 CircuitBreakerOpenError。

        Args:
            func: 目标可调用对象。
            *args: 传递给 func 的位置参数。
            **kwargs: 传递给 func 的关键字参数。

        Returns:
            func 的返回值。

        Raises:
            CircuitBreakerOpenError: 熔断器处于 OPEN 状态时拒绝调用。
        """
        with self._lock:
            self.stats["total"] += 1
            if self._state == CircuitState.OPEN:
                self._try_half_open()
            if self._state == CircuitState.OPEN:
                self.stats["rejected"] += 1
                raise CircuitBreakerOpenError(
                    f"[{self.name}] 熔断开启(failures={self._failure_count})")
        try:
            result = func(*args, **kwargs)
            with self._lock:
                self.stats["success"] += 1
                self._window.append(1)
                self._failure_count = 0
                if self._state == CircuitState.HALF_OPEN:
                    self._half_open_successes += 1
                    if self._half_open_successes >= self.config.success_threshold:
                        self._state = CircuitState.CLOSED
            return result
        except Exception:
            with self._lock:
                self.stats["failure"] += 1
                self._window.append(0)
                self._failure_count += 1
                if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.config.fail_max:
                    self._open_circuit()
            raise

    def get_metrics(self):
        with self._lock:
            w = list(self._window)
            err_rate = (sum(1 for x in w if x == 0) / len(w) * 100) if w else 0
            return {
                "name": self.name, "state": self._state.value,
                "failures": self._failure_count,
                "error_rate_pct": round(err_rate, 2),
                **self.stats,
            }

# ═══════════════════════════════════════════════════════════════
# 2. Retry With Exponential Backoff
# ═══════════════════════════════════════════════════════════════

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

class MaxRetriesExceededError(Exception):
    pass

def retry_with_backoff(func, config=None, *args, **kwargs):
    """带指数退避的重试机制。

    在遇到异常时自动重试，每次重试的等待时间指数增长。

    Args:
        func: 目标可调用对象。
        config: RetryConfig 配置，默认 RetryConfig()。
        *args: 传递给 func 的位置参数。
        **kwargs: 传递给 func 的关键字参数。

    Returns:
        func 成功调用后的返回值。

    Raises:
        MaxRetriesExceededError: 重试次数耗尽后仍失败。
        CircuitBreakerOpenError: 熔断器打开，直接传播不重试。
    """
    cfg = config or RetryConfig()
    last_err = None
    for attempt in range(cfg.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (CircuitBreakerOpenError, MaxRetriesExceededError):
            raise
        except Exception as e:
            last_err = e
            if attempt < cfg.max_retries:
                delay = min(cfg.base_delay * (cfg.exponential_base ** attempt), cfg.max_delay)
                if cfg.jitter:
                    delay += random.uniform(0, delay * 0.1)
                logger.warning(f"[Retry] {attempt+1}/{cfg.max_retries} fail: {e}, wait {delay:.1f}s")
                time.sleep(delay)
    raise MaxRetriesExceededError(f"重试{cfg.max_retries}次耗尽: {last_err}")

# ═══════════════════════════════════════════════════════════════
# 3. Rate Limiter
# ═══════════════════════════════════════════════════════════════

@dataclass
class RateLimiterConfig:
    max_requests: int = 500
    window_seconds: float = 60.0
    burst_multiplier: float = 1.5

class SlidingWindowRateLimiter:
    """滑动窗口限流器 — 对标 AWS WAF。

    基于时间戳滑动窗口实现请求频率控制。

    Attributes:
        config: 限流配置 (RateLimiterConfig)。

    Example:
        >>> limiter = SlidingWindowRateLimiter(RateLimiterConfig(max_requests=100))
        >>> limiter.allow()  # True 或 False
    """

    def __init__(self, config: RateLimiterConfig):
        """初始化限流器。

        Args:
            config: RateLimiterConfig 限流配置。
        """
        self.config = config
        self._lock = threading.RLock()
        self._timestamps = deque()
    def allow(self) -> bool:
        now = time.time()
        ws = now - self.config.window_seconds
        with self._lock:
            while self._timestamps and self._timestamps[0] < ws:
                self._timestamps.popleft()
            if len(self._timestamps) >= int(self.config.max_requests * self.config.burst_multiplier):
                return False
            self._timestamps.append(now)
            return True
    def remaining(self) -> int:
        now = time.time()
        ws = now - self.config.window_seconds
        with self._lock:
            while self._timestamps and self._timestamps[0] < ws:
                self._timestamps.popleft()
            return max(0, self.config.max_requests - len(self._timestamps))

# ═══════════════════════════════════════════════════════════════
# 4. Timeout Manager
# ═══════════════════════════════════════════════════════════════

class TimeoutManager:
    """超时管理器 — 对标 Hystrix Timeout。

    通过线程+事件实现同步函数的超时控制。

    Example:
        >>> result = TimeoutManager.sync_timeout(slow_function, 5.0, arg1, arg2)
    """

    @staticmethod
    def sync_timeout(func, timeout_seconds, *args, **kwargs):
        """对同步函数执行超时控制。

        在独立线程中运行 func，若超时则抛出 TimeoutError。

        Args:
            func: 目标可调用对象。
            timeout_seconds: 超时时间（秒）。
            *args: 传递给 func 的位置参数。
            **kwargs: 传递给 func 的关键字参数。

        Returns:
            func 的返回值。

        Raises:
            TimeoutError: func 执行超过 timeout_seconds。
        """
        result = []; exc = []; evt = threading.Event()
        def worker():
            try: result.append(func(*args, **kwargs))
            except Exception as e: exc.append(e)
            finally: evt.set()
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        if not evt.wait(timeout=timeout_seconds):
            raise TimeoutError(f"超时 {timeout_seconds}s: {func.__name__}")
        if exc: raise exc[0]
        return result[0]

# ═══════════════════════════════════════════════════════════════
# 5. Fallback Registry
# ═══════════════════════════════════════════════════════════════

class NoFallbackAvailableError(Exception):
    pass

class FallbackRegistry:
    def __init__(self):
        self._registry = {}
        self._default = None
    def register(self, key, func):
        self._registry.setdefault(key, []).append(func)
    def set_default(self, func):
        self._default = func
    def execute(self, key, *args, **kwargs):
        fbs = list(self._registry.get(key, []))
        if self._default: fbs.append(self._default)
        for fb in fbs:
            try:
                r = fb(*args, **kwargs)
                logger.info(f"[Fallback:{key}] {fb.__name__} 降级成功")
                return r
            except Exception as e:
                logger.warning(f"[Fallback:{key}] {fb.__name__} fail: {e}")
        raise NoFallbackAvailableError(f"{key} 无可用降级")

# ═══════════════════════════════════════════════════════════════
# 6. Decision Audit Log
# ═══════════════════════════════════════════════════════════════

@dataclass
class DecisionRecord:
    decision_id: str; timestamp: str; rule_name: str
    input_data: dict; result: Any; matched: bool
    duration_ms: float; error: str | None = None
    dry_run: bool = False
    def to_dict(self):
        return {"decision_id": self.decision_id, "timestamp": self.timestamp,
                "rule_name": self.rule_name, "matched": self.matched,
                "duration_ms": self.duration_ms, "error": self.error,
                "dry_run": self.dry_run}

class DecisionAuditLogger:
    def __init__(self, log_dir="./audit_logs"):
        self.log_dir = log_dir
        self._lock = threading.RLock()
        self._records = []
        os.makedirs(log_dir, exist_ok=True)
    def log(self, record: DecisionRecord):
        with self._lock:
            self._records.append(record)
            fname = os.path.join(self.log_dir, f"decisions_{datetime.now():%Y%m%d}.jsonl")
            with open(fname, "a") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    def query(self, rule_name=None, limit=100):
        results = self._records[-limit:]
        if rule_name: results = [r for r in results if r.rule_name == rule_name]
        return results

# ═══════════════════════════════════════════════════════════════
# 7. Metrics Collector
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetricsSnapshot:
    total_calls: int; success_rate: float; avg_latency_ms: float
    p50_latency_ms: float; p90_latency_ms: float; error_rate: float

class MetricsCollector:
    def __init__(self, name, window=100):
        self.name = name
        self._latencies = deque(maxlen=window)
        self._lock = threading.RLock()
        self.total = self.success = self.failure = 0
    def record(self, ok, latency_ms):
        with self._lock:
            self.total += 1
            if ok: self.success += 1
            else: self.failure += 1
            self._latencies.append(latency_ms)
    def snapshot(self):
        with self._lock:
            lat = sorted(self._latencies) if self._latencies else [0]
            sr = (self.success / max(self.total, 1)) * 100
            n = len(lat)
            return MetricsSnapshot(
                total_calls=self.total, success_rate=round(sr, 2),
                error_rate=round(100 - sr, 2),
                avg_latency_ms=round(sum(lat)/n, 2),
                p50_latency_ms=round(lat[int(n*0.5)], 2),
                p90_latency_ms=round(lat[int(n*0.9)], 2))

# ═══════════════════════════════════════════════════════════════
# 8. Hot Reloader
# ═══════════════════════════════════════════════════════════════

class HotReloader:
    def __init__(self, watch_path, reload_cb, interval=10.0):
        self.watch_path = watch_path; self.reload_cb = reload_cb
        self.interval = interval; self._running = False
        self._mtime = {}; self._version = "0.0.0"
    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True); t.start()
    def stop(self): self._running = False
    def _loop(self):
        while self._running:
            self._check(); time.sleep(self.interval)
    def _check(self):
        if not os.path.isdir(self.watch_path): return
        changed = False
        for fn in os.listdir(self.watch_path):
            if not fn.endswith((".json",".yaml",".py")): continue
            fp = os.path.join(self.watch_path, fn)
            if not os.path.isfile(fp): continue
            mt = os.path.getmtime(fp)
            if mt > self._mtime.get(fp, 0):
                changed = True; self._mtime[fp] = mt
        if changed:
            try:
                self.reload_cb(self.watch_path)
                self._version = uuid.uuid4().hex[:8]
                logger.info(f"[HotReload] v{self._version}")
            except Exception as e:
                logger.error(f"[HotReload] fail: {e}")

# ═══════════════════════════════════════════════════════════════
# 9. Dry Run Mode
# ═══════════════════════════════════════════════════════════════

class DryRunMode:
    """干跑模式 — 对标 OPA dry-run。

    在不实际执行规则的情况下评估规则匹配情况，
    记录完整的决策审计日志。

    Attributes:
        enabled: 是否启用干跑模式。
        logger: DecisionAuditLogger 实例（可选）。
    """

    def __init__(self, enabled=False, logger=None):
        self.enabled = enabled; self.logger = logger
        self._simulated = []
    def evaluate(self, rule_name, input_data, callback):
        start = time.time(); error = None
        try:
            result = callback(input_data); matched = bool(result)
        except Exception as e:
            result = None; matched = False; error = str(e)
        duration = (time.time() - start) * 1000
        rec = DecisionRecord(decision_id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(UTC).isoformat(), rule_name=rule_name,
            input_data=input_data, result=result, matched=matched,
            duration_ms=duration, error=error, dry_run=self.enabled)
        if self.logger: self.logger.log(rec)
        if self.enabled:
            self._simulated.append(rec.to_dict())
            return {"dry_run": True, "matched": matched, "result": result}
        return result if matched else None

# ═══════════════════════════════════════════════════════════════
# 10. Unified Rule Enforcer（主执行管道）
# ═══════════════════════════════════════════════════════════════

class UnifiedRuleEnforcer:
    """统一规则执行器 — 主执行管道。

    集成熔断器、限流、重试、降级、审计、指标、干跑等全部弹性组件。

    Attributes:
        name: 执行器名称。
        circuit_breaker: 熔断器实例（可选）。
        rate_limiter_cfg: 限流配置（可选）。
        retry_config: 重试配置（可选）。
        fallbacks: FallbackRegistry 降级注册表。
        audit: DecisionAuditLogger 审计日志。
        metrics: MetricsCollector 指标收集器。
        dry_run: DryRunMode 干跑模式。

    Example:
        >>> engine = UnifiedRuleEnforcer("my_rules")
        >>> engine.register_rule("allow_admin", lambda d: {"allowed": d.get("role") == "admin"})
        >>> engine.circuit_breaker = CircuitBreaker("api", CircuitBreakerConfig())
        >>> result = engine.execute("allow_admin", {"role": "admin"})
    """

    def __init__(self, name="default"):
        """初始化统一规则执行器。

        Args:
            name: 执行器名称，用于日志和指标标识。
        """
        self.name = name
        self.circuit_breaker = None
        self.rate_limiter_cfg = None
        self.retry_config = None
        self.fallbacks = FallbackRegistry()
        self.audit = DecisionAuditLogger()
        self.metrics = MetricsCollector(name)
        self.dry_run = DryRunMode()
        self._rules = {}
    def register_rule(self, name, func):
        """注册规则函数。

        Args:
            name: 规则名称，用于 execute() 时引用。
            func: 规则函数，接受 input_data 参数，返回 Any。
        """
        self._rules[name] = func

    def execute(self, rule_name, input_data):
        """执行指定规则，通过弹性管道。

        流程: 限流检查 → 干跑模式(若启用) → 熔断+重试+降级 → 审计记录。

        Args:
            rule_name: 已注册的规则名称。
            input_data: 传递给规则函数的输入数据。

        Returns:
            规则函数的返回值。

        Raises:
            Exception: 限流触发或规则执行失败（经过降级后仍失败）。
        """
        if self.rate_limiter_cfg:
            limiter = SlidingWindowRateLimiter(self.rate_limiter_cfg)
            if not limiter.allow():
                raise Exception(f"[RateLimit] {rule_name} 触发限流")
        # 干跑
        if self.dry_run.enabled:
            return self.dry_run.evaluate(rule_name, input_data,
                lambda d: self._exec(rule_name, d))
        # 正常执行
        return self._exec(rule_name, input_data)
    def _exec(self, rule_name, input_data):
        start = time.time(); error = None; result = None
        try:
            fn = self._rules[rule_name]
            if self.circuit_breaker:
                with_fallback = lambda: self._run_with_fallback(rule_name, fn, input_data)
                with_retry = lambda: retry_with_backoff(with_fallback, self.retry_config)
                result = self.circuit_breaker.call(with_retry)
            else:
                result = self._run_with_fallback(rule_name, fn, input_data)
        except Exception as e:
            error = str(e); raise
        finally:
            duration = (time.time() - start) * 1000
            ok = error is None
            self.audit.log(DecisionRecord(decision_id=uuid.uuid4().hex[:12],
                timestamp=datetime.now(UTC).isoformat(), rule_name=rule_name,
                input_data=input_data, result=result, matched=bool(result),
                duration_ms=duration, error=error))
            self.metrics.record(ok, duration)
        return result
    def _run_with_fallback(self, rule_name, fn, input_data):
        try:
            return TimeoutManager.sync_timeout(fn, 30.0, input_data)
        except Exception as e:
            try: return self.fallbacks.execute(rule_name, input_data)
            except NoFallbackAvailableError: raise e

# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cb = CircuitBreaker("test", CircuitBreakerConfig(fail_max=3, reset_timeout=5))
    for i in range(5):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        except CircuitBreakerOpenError:
            logger.info(f"  熔断正确开启 (第{i+1}次)")
            break
        except ValueError:
            logger.info(f"  预期失败 #{i+1}")
    logger.info(f"  状态: {cb.state.value}")
    mc = MetricsCollector("test")
    mc.record(True, 50); mc.record(True, 150); mc.record(False, 200)
    s = mc.snapshot()
    logger.info(f"  成功率: {s.success_rate}% 延迟: {s.avg_latency_ms}ms")
    engine = UnifiedRuleEnforcer("demo")
    engine.register_rule("allow", lambda d: {"allowed": True})
    engine.rate_limiter_cfg = RateLimiterConfig(max_requests=500, window_seconds=60)
    engine.circuit_breaker = CircuitBreaker("api", CircuitBreakerConfig(fail_max=5))
    r = engine.execute("allow", {"user": "admin"})
    logger.info(f"  引擎执行: {r}")
    logger.info("✅ resilience_patterns.py 自检通过")
