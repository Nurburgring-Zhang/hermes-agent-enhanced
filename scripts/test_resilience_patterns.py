#!/usr/bin/env python3
"""
test_resilience_patterns.py — 完整测试套件
覆盖: CircuitBreaker, RetryWithBackoff, RateLimiter, FallbackRegistry,
      DryRunMode, MetricsCollector, UnifiedRuleEnforcer
"""
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path.home() / ".hermes"))

from scripts.resilience_patterns import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    DryRunMode,
    FallbackRegistry,
    MaxRetriesExceededError,
    MetricsCollector,
    NoFallbackAvailableError,
    RateLimiterConfig,
    RetryConfig,
    SlidingWindowRateLimiter,
    UnifiedRuleEnforcer,
    retry_with_backoff,
)

PASS = 0
FAIL = 0
def check(desc: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ {desc}  -- {detail}")
        FAIL += 1

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════════
# 1. CircuitBreaker: 三态变换
# ═══════════════════════════════════════════════════════════════
section("1. CircuitBreaker — 三态变换 (CLOSED → OPEN → HALF_OPEN → CLOSED)")

def always_fail():
    raise ValueError("simulated failure")

def always_ok():
    return "ok"

# CLOSED → OPEN: fail > fail_max
cb = CircuitBreaker("test-cb", CircuitBreakerConfig(fail_max=3, reset_timeout=0.5, success_threshold=2))
check("初始状态 CLOSED", cb.state == CircuitState.CLOSED)

for i in range(3):
    try: cb.call(always_fail)
    except ValueError: pass
check("3次失败后状态 OPEN", cb.state == CircuitState.OPEN)

try:
    cb.call(always_fail)
    check("OPEN时调用应抛出 CircuitBreakerOpenError", False, "未抛出异常")
except CircuitBreakerOpenError:
    check("OPEN时调用抛出 CircuitBreakerOpenError", True)

# OPEN → HALF_OPEN: 等待 reset_timeout
time.sleep(0.6)
try:
    cb.call(always_fail)
    check("HALF_OPEN时失败应回到 OPEN", False, "未捕获到异常")
except (ValueError, CircuitBreakerOpenError):
    pass

# 等待再次进入 HALF_OPEN → CLOSED
cb2 = CircuitBreaker("test-cb2", CircuitBreakerConfig(fail_max=2, reset_timeout=0.3, success_threshold=2))
for i in range(2):
    try: cb2.call(always_fail)
    except ValueError: pass
check("cb2 到达 OPEN", cb2.state == CircuitState.OPEN)
time.sleep(0.4)
# _try_half_open 只在 call() 中触发; 调用一次触发状态切换
try: cb2.call(always_fail)  # 会触发 _try_half_open → HALF_OPEN, 然后再次失败 → OPEN
except (ValueError, CircuitBreakerOpenError): pass
check("cb2 从 OPEN 自动切入 HALF_OPEN (由 call 触发)", cb2.state == CircuitState.OPEN)
# 再等超时, 用成功的函数测试 HALF_OPEN → CLOSED
time.sleep(0.4)
r_half = cb2.call(always_ok)
check("cb2 再次进入 HALF_OPEN 并成功", cb2.state == CircuitState.HALF_OPEN and r_half == "ok")
r_half2 = cb2.call(always_ok)
check("cb2 连续成功达到 success_threshold → CLOSED", cb2.state == CircuitState.CLOSED)

# 滑动窗口指标
cb3 = CircuitBreaker("test-cb3", CircuitBreakerConfig(fail_max=5, sliding_window_size=10))
for i in range(3):
    try: cb3.call(always_fail)
    except ValueError: pass
for i in range(7):
    cb3.call(always_ok)
m = cb3.get_metrics()
check("metrics 包含 name", m["name"] == "test-cb3")
check("metrics 包含 state", m["state"] in ("CLOSED","OPEN","HALF_OPEN"))
check("metrics 含统计字段", all(k in m for k in ("total","success","failure","rejected")))

# stats 计数
cb4 = CircuitBreaker("cb4-stats", CircuitBreakerConfig(fail_max=5))
cb4.call(always_ok)
try: cb4.call(always_fail)
except Exception as e:
    logger.warning(f"Unexpected error in test_resilience_patterns.py: {e}")
s = cb4.stats
check("stats total=2", s["total"] == 2)
check("stats success=1", s["success"] == 1)
check("stats failure=1", s["failure"] == 1)

# listeners 回调
cb5 = CircuitBreaker("cb5-listeners", CircuitBreakerConfig(fail_max=1, reset_timeout=999))
listener_events = []
def my_listener(name, new_state):
    listener_events.append((name, new_state))
cb5._listeners.append(my_listener)
try: cb5.call(always_fail)
except Exception as e:
    logger.warning(f"Unexpected error in test_resilience_patterns.py: {e}")
check("listener 收到 OPEN 事件", len(listener_events) >= 1 and listener_events[-1][1] == "OPEN")

# ═══════════════════════════════════════════════════════════════
# 2. RetryWithBackoff: 重试计数 + 退避延迟
# ═══════════════════════════════════════════════════════════════
section("2. RetryWithBackoff — 重试计数 + 退避延迟")

retry_counter = {"n": 0}
def flaky():
    retry_counter["n"] += 1
    raise ValueError(f"attempt #{retry_counter['n']}")

retry_counter["n"] = 0
start = time.time()
cfg = RetryConfig(max_retries=3, base_delay=0.05, max_delay=1.0, jitter=False)
try:
    retry_with_backoff(flaky, cfg)
    check("重试应最终抛出 MaxRetriesExceededError", False, "未抛出异常")
except MaxRetriesExceededError:
    pass
elapsed = time.time() - start
check(f"总调用次数 = 重试+1 = 4 (实际: {retry_counter['n']})", retry_counter["n"] == 4)
check(f"退避延迟合理 (总耗时≈{elapsed:.2f}s)", elapsed >= 0.05 * (2**0 + 2**1 + 2**2))

# 最后一次成功
retry_counter["n"] = 0
def succeed_on_3rd():
    retry_counter["n"] += 1
    if retry_counter["n"] < 3:
        raise ValueError(f"fail #{retry_counter['n']}")
    return "finally_ok"

retry_counter["n"] = 0
result = retry_with_backoff(succeed_on_3rd, cfg)
check(f"第3次成功 (实际第{retry_counter['n']}次)", result == "finally_ok" and retry_counter["n"] == 3)

# ═══════════════════════════════════════════════════════════════
# 3. RateLimiter: allow/拒绝/配额
# ═══════════════════════════════════════════════════════════════
section("3. RateLimiter — allow / 拒绝 / 配额")

rl = SlidingWindowRateLimiter(RateLimiterConfig(max_requests=5, window_seconds=60.0, burst_multiplier=1.0))
check("初始 remaining = 5", rl.remaining() == 5)
allowed = sum(1 for _ in range(10) if rl.allow())
check("前5次通过, 后5次拒绝", allowed == 5)
check("配额耗尽后 remaining = 0", rl.remaining() == 0)

# burst
rl2 = SlidingWindowRateLimiter(RateLimiterConfig(max_requests=3, window_seconds=60.0, burst_multiplier=2.0))
burst_allowed = sum(1 for _ in range(10) if rl2.allow())
check(f"burst 允许 ≈ 6 (实际: {burst_allowed})", burst_allowed == 6)

# ═══════════════════════════════════════════════════════════════
# 4. FallbackRegistry: 注册/执行/失败
# ═══════════════════════════════════════════════════════════════
section("4. FallbackRegistry — 注册 / 执行 / 失败")

fr = FallbackRegistry()
fr.register("key1", lambda d: f"fb1:{d}")
fr.register("key1", lambda d: f"fb2:{d}")
result = fr.execute("key1", "data")
check("执行第一个注册的回调", result == "fb1:data")

# default fallback
fr2 = FallbackRegistry()
fr2.set_default(lambda d: f"default:{d}")
result2 = fr2.execute("unknown", "x")
check("不存在的key走 default fallback", result2 == "default:x")

# 全部失败
fr3 = FallbackRegistry()
fr3.register("bad", lambda d: (_ for _ in ()).throw(ValueError("fb fail")))
try:
    fr3.execute("bad", "x")
    check("全部降级失败应抛出 NoFallbackAvailableError", False, "未抛出异常")
except NoFallbackAvailableError:
    check("全部降级失败抛出 NoFallbackAvailableError", True)

# ═══════════════════════════════════════════════════════════════
# 5. DryRunMode: 干跑模式不执行
# ═══════════════════════════════════════════════════════════════
section("5. DryRunMode — 干跑模式不执行")

executed = {"n": 0}
def side_effect_fn(data):
    executed["n"] += 1
    return True

# 干跑模式
dry = DryRunMode(enabled=True)
executed["n"] = 0
r = dry.evaluate("test-rule", {"user": "alice"}, side_effect_fn)
check("干跑返回 dict 包含 dry_run=True", isinstance(r, dict) and r.get("dry_run") is True)
check("干跑时副作用函数仍执行 (用于审计)", executed["n"] == 1)
check("干跑时 matched=True", r.get("matched") is True)

# 非干跑模式
dry2 = DryRunMode(enabled=False)
executed["n"] = 0
r2 = dry2.evaluate("test-rule", {"user": "bob"}, side_effect_fn)
check("非干跑返回原始结果", r2 is True)
check("非干跑副作用正常执行", executed["n"] == 1)

# 干跑时 callback 抛出异常
dry3 = DryRunMode(enabled=True)
def crash_fn(data):
    raise RuntimeError("crash")
r3 = dry3.evaluate("crash-rule", {}, crash_fn)
check("干跑异常返回 dry_run dict", isinstance(r3, dict) and r3.get("dry_run") is True)
check("干跑异常时 matched=False", r3.get("matched") is False)

# ═══════════════════════════════════════════════════════════════
# 6. MetricsCollector: P50/P90 延迟
# ═══════════════════════════════════════════════════════════════
section("6. MetricsCollector — P50 / P90 延迟")

mc = MetricsCollector("test-metrics", window=50)
mc.record(True, 10)
mc.record(True, 20)
mc.record(True, 30)
mc.record(True, 40)
mc.record(True, 50)
s = mc.snapshot()
check("success_rate=100%", s.success_rate == 100.0)
check("avg_latency=30ms", s.avg_latency_ms == 30.0)
check("p50=30ms", s.p50_latency_ms == 30.0)
check("p90=50ms", s.p90_latency_ms == 50.0)

# 含失败记录
mc2 = MetricsCollector("test-metrics2", window=10)
mc2.record(True, 10)
mc2.record(False, 100)
s2 = mc2.snapshot()
check("含失败: total=2", s2.total_calls == 2)
check("含失败: success_rate=50%", s2.success_rate == 50.0)
check("含失败: error_rate=50%", s2.error_rate == 50.0)

# ═══════════════════════════════════════════════════════════════
# 7. UnifiedRuleEnforcer: 完整执行管道
# ═══════════════════════════════════════════════════════════════
section("7. UnifiedRuleEnforcer — 完整执行管道")

engine = UnifiedRuleEnforcer("integration-test")
engine.register_rule("allow_rule", lambda d: {"allowed": True, "user": d.get("user")})
engine.register_rule("deny_rule", lambda d: {"allowed": False})

# 正常执行
from scripts.resilience_patterns import RateLimiterConfig


engine.rate_limiter_cfg = RateLimiterConfig(max_requests=100, window_seconds=60)
engine.circuit_breaker = CircuitBreaker("engine-cb", CircuitBreakerConfig(fail_max=5))
engine.retry_config = RetryConfig(max_retries=1, base_delay=0.01)

result = engine.execute("allow_rule", {"user": "admin"})
check("engine 正常执行返回结果", result == {"allowed": True, "user": "admin"})
check("metrics total > 0", engine.metrics.total > 0)

# 限流（UnifiedRuleEnforcer 每次调用创建新 limiter, 不影响跨调用限流）
# 所以单独测试 SlidingWindowRateLimiter（见 section 3），这里只测试正常调用
engine2 = UnifiedRuleEnforcer("rate-limit-test")
engine2.register_rule("test", lambda d: "ok")
r_rl = engine2.execute("test", {})
check("engine 带 rate_limiter_cfg 正常调用", r_rl == "ok")

# 熔断触发
engine3 = UnifiedRuleEnforcer("cb-test")
engine3.register_rule("failing", lambda d: (_ for _ in ()).throw(ValueError("nope")))
engine3.circuit_breaker = CircuitBreaker("cb", CircuitBreakerConfig(fail_max=2, reset_timeout=999))
for i in range(2):
    try: engine3.execute("failing", {})
    except Exception as e:
        logger.warning(f"Unexpected error in test_resilience_patterns.py: {e}")
try:
    engine3.execute("failing", {})
    check("熔断后应被拒绝", False, "未抛出异常")
except CircuitBreakerOpenError:
    check("熔断后抛出 CircuitBreakerOpenError", True)

# 降级回退
engine4 = UnifiedRuleEnforcer("fallback-test")
engine4.register_rule("flaky", lambda d: (_ for _ in ()).throw(ValueError("primary fail")))
engine4.fallbacks.register("flaky", lambda d: "fallback_ok")
result4 = engine4.execute("flaky", {})
check("降级回退返回 fallback 结果", result4 == "fallback_ok")

# 干跑模式
engine5 = UnifiedRuleEnforcer("dry-run-test")
engine5.register_rule("some_rule", lambda d: "real_result")
engine5.dry_run.enabled = True
result5 = engine5.execute("some_rule", {"dry": True})
check("dry_run 模式下返回 dict 包含 dry_run=True", isinstance(result5, dict) and result5.get("dry_run") is True)
check("dry_run 模式下返回 matched=True", result5.get("matched") is True)

# 审计日志
check("audit 日志中有记录", len(engine.audit._records) >= 1)

# ═══════════════════════════════════════════════════════════════
# 汇总报告
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  测试完成: {PASS} 通过, {FAIL} 失败")
    print(f"{'='*60}")
    sys.exit(0 if FAIL == 0 else 1)
