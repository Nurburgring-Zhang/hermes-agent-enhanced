# E2E运行时验证协议

> 来源: 2026-06-15 Hermes Agent Enhanced 部署验证
> 核心发现: import通过≠系统能运行，API表面差异是#1误报源

## 8层验证矩阵

```
L1: 规则引擎    R1 AntiHallucination / R3 BackupGuard / R14 SdlcEnforcer / PreCheck
L2: 弹性模式    CircuitBreaker(CLOSED→OPEN) / SlidingWindowRateLimiter
L3: 安全链      拦截危险路径 / 放行正常路径 / Canary加载 / 密钥脱敏
L4: Agent编排   ModelRouter / MonitorEngine / ReflectorEngine
L5: 自主引擎    MasterIntegrationHub / SelfEvolutionEngine
L6: Loop工程    LoopEngine / CheckpointStore
L7: 可观测性    ObservabilityCollector / 指标收集 / 健康检查
L8: 故障恢复    熔断断开→恢复 / 状态持久化 / 新实例替代reset
```

## API发现循环

当E2E验证中方法调用失败时：

```python
# 1. 尝试调用
cb = CircuitBreaker(name="e2e")
cb.record_failure()  # AttributeError!

# 2. 查找实际API
import inspect
print(inspect.signature(cb.__init__))  # 看参数
print([m for m in dir(cb) if 'fail' in m.lower()])  # 找相关方法

# 3. 发现实际方法名不同
# CircuitBreaker用 call(func) 包装调用, 不是 record_failure()

# 4. 修正测试
for _ in range(5):
    try: cb.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
    except: pass
assert cb.state.name == "OPEN"  # ✅
```

## 本会话验证结果

```
27/27 import验证 ✅ (100%)
20/24 运行时验证 ✅ (83%)
  - 4个失败: API表面差异(方法名/参数签名/返回类型)
  - 0个功能缺陷
结论: 系统功能完整, API文档需要补充
```

## 已知API限制

| 模块 | 限制 | 替代方案 |
|------|------|---------|
| CircuitBreaker | 无reset()方法 | 创建新实例达到等效效果 |
| SlidingWindowRateLimiter | allow()无参 | config通过构造函数传入 |
| PromptGuard | canary属性名`_canary_token` | 非`_canary` |
| CircuitBreakerConfig | fail_max(非failure_threshold) | 正确属性名 |
