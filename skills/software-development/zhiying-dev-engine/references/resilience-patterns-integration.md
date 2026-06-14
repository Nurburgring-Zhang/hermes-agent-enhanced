# Resilience Patterns Integration Guide

## What was built (2026-06-13, Phase2-Round1)

`/home/administrator/.hermes/scripts/resilience_patterns.py` — 20255 bytes, 10 components.

### Component Map

| Component | Lines | CLI Test | Integration Point |
|-----------|-------|----------|-------------------|
| CircuitBreaker (3-state, sliding window, listeners) | ~80 | `call(failing_func)` → OPEN in 3 failures | rule_enforcer.py import |
| RetryWithBackoff (exponential + jitter) | ~30 | 1 retry with 0.1s delay → MaxRetriesExceededError | rule_enforcer._resilience.retry_config |
| SlidingWindowRateLimiter (burst multiplier) | ~25 | `allow()` returns False after burst | rule_enforcer._resilience.rate_limiter_cfg |
| TimeoutManager (threading.Timer + daemon worker) | ~20 | `sync_timeout(lambda: 42, 5)` → 42 | UnifiedRuleEnforcer._run_with_fallback |
| FallbackRegistry (priority-ordered) | ~25 | register → execute → fallback_ok | UnifiedRuleEnforcer._run_with_fallback |
| DecisionAuditLogger (JSONL, queryable, daily files) | ~40 | log → query(limit=5) → 1 record | rule_enforcer _resilience.audit |
| MetricsCollector (P50/P90/success rate) | ~35 | record(True,50) → snapshot.success_rate | rule_enforcer._resilience.metrics |
| HotReloader (file polling, versioned) | ~40 | start/stop lifecycle check | standalone |
| DryRunMode (evaluate without executing) | ~40 | `evaluate()` → `dry_run=True` | rule_enforcer._resilience.dry_run |
| UnifiedRuleEnforcer (orchestrated pipeline) | ~60 | `execute("ok", {})` → `{'allowed': True}` | **imported in rule_enforcer.py** |

### Integration into rule_enforcer.py

At the top of the file, after `logger = logging.getLogger(__name__)`:

```python
try:
    from resilience_patterns import (
        UnifiedRuleEnforcer, CircuitBreaker, CircuitBreakerConfig,
        RetryConfig, retry_with_backoff, TimeoutManager,
        FallbackRegistry, DecisionAuditLogger, DecisionRecord,
        MetricsCollector, HotReloader, DryRunMode,
        RateLimiterConfig, SlidingWindowRateLimiter,
        CircuitBreakerOpenError, MaxRetriesExceededError,
        NoFallbackAvailableError,
    )
    _resilience = UnifiedRuleEnforcer("rule_enforcer")
    _resilience.circuit_breaker = CircuitBreaker(
        "rule_eval", CircuitBreakerConfig(fail_max=10, reset_timeout=60.0)
    )
    _resilience.retry_config = RetryConfig(max_retries=2, base_delay=0.5, jitter=True)
    _resilience.rate_limiter_cfg = RateLimiterConfig(max_requests=500, window_seconds=60)
    _resilience_available = True
except Exception as e:
    _resilience_available = False
```

### Verification script

```python
from resilience_patterns import *

# 1. CircuitBreaker
cb = CircuitBreaker("test", CircuitBreakerConfig(fail_max=3, reset_timeout=5))
for i in range(5):
    try: cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
    except CircuitBreakerOpenError: break
    except ValueError: pass
assert cb.state == CircuitState.OPEN

# 2. Metrics
mc = MetricsCollector("test")
mc.record(True, 50); mc.record(False, 200)
s = mc.snapshot()
assert s.success_rate == 50.0

# 3. RateLimiter
rl = SlidingWindowRateLimiter(RateLimiterConfig(max_requests=1000))
assert rl.allow()

# 4. Fallback
fb = FallbackRegistry()
fb.register("test", lambda d: "fallback_ok")
assert fb.execute("test", {}) == "fallback_ok"

# 5. DryRun
dry = DryRunMode(enabled=True)
r = dry.evaluate("test", {"x": 1}, lambda d: "result")
assert r["dry_run"]

# 6. AuditLog
audit = DecisionAuditLogger()
audit.log(DecisionRecord("id1", "ts", "rule", {}, {}, True, 10))
assert len(audit.query(limit=5)) == 1

# 7. Timeout
tm = TimeoutManager()
assert tm.sync_timeout(lambda: 42, 5) == 42

# 8. Retry
try:
    retry_with_backoff(lambda: (_ for _ in ()).throw(ValueError("x")),
                       RetryConfig(max_retries=1, base_delay=0.1))
    assert False
except MaxRetriesExceededError:
    pass

# 9. UnifiedEngine
engine = UnifiedRuleEnforcer("test")
engine.register_rule("ok", lambda d: {"allowed": True})
assert engine.execute("ok", {}) == {"allowed": True}
```
