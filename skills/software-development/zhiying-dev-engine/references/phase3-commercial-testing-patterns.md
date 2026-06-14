# 第三阶段全功能审核测试模式（2026-06-13实战）

## 测试范围（四个模块，205个测试）

| 模块 | 文件 | 测试数 | 覆盖内容 |
|------|------|--------|---------|
| 核心规则引擎 | test_rule_enforcer.py | 43 | R1反幻觉/R3改前备份/R14三阶段(状态/步进/阻断/证据) |
| 审计系统 | test_audit_system.py | 35 | 事件写入/查询过滤/JSONL后端/便捷方法/导出/多线程/单例 |
| 弹性模式 | test_resilience_patterns.py | 46 | CircuitBreaker(三态)/Retry/RateLimiter/Fallback/DryRun/Metrics/UnifiedEngine |
| 六部模块 | test_ministry.py | 81 | 9异常类/CircuitBreaker/MinistryBase/角色编排/状态机(串行/并行/条件) |

## 审计系统测试关键点

**test_audit_system.py** 的 import 必须使用完整路径:
```python
from scripts.audit_system import AuditLogger, JsonlBackend, AuditEvent
```

**JsonlBackend** 构造参数是 `base_path` 不是 `log_dir`:
```python
JsonlBackend(base_path=tmpdir + '/test.jsonl')  # 正确
# JsonlBackend(log_dir=tmpdir)  # 错误
```

**多线程测试**需要 `get_audit_logger()` 返回同一实例，用模块级单例模式。

## 弹性模式测试关键点

**熔断器三态验证序列:**
```
CLOSED → 连续fail_max次失败 → OPEN
OPEN → reset_timeout后调用call() → HALF_OPEN
HALF_OPEN → continue成功态次 → CLOSED
```

**滑动窗口测试:** 需要连续 `sliding_window_size` 次调用才能触发窗口错误率检查。

**限流器:** `SlidingWindowRateLimiter` 是"每次新建"的——在 `UnifiedRuleEnforcer.execute()` 中每次调用新建实例，跨调用限流不生效。这不是bug，是设计约束。

## 六部模块测试关键点

**MinistryBase** 执行管道:
1. `register_pipeline_step()` 注册处理函数
2. `execute()` 按注册顺序执行
3. 熔断器开放时返回 `CIRCUIT_OPEN`

**RoleOrchestrator** 路由优先级:
1. 显式指定角色 (`route_to("工部")`) → 最高
2. 自动匹配 (`route(action="编辑")`) → 按部门职责匹配
3. 无匹配 → `None`

**WorkflowStateMachine** 状态转移:
- 条件引擎支持 `result.status == 'success'` (单引号) 但不支持 `"success"` (双引号)
- 终态状态(COMPLETE/ERROR/CANCELLED)不记录在history中
- `run()` 返回的 `success` 字段只有终态为 COMPLETE 时才为True

## pytest-asyncio兼容性故障

**症状:** `INTERNALERROR> AttributeError: 'Package' object has no attribute 'obj'`
**根因:** pytest-asyncio 0.23.2 的 `pytest_collectstart` hook 与 pytest 9.0.3 不兼容
**修复:** 直接删除 pytest-asyncio:
```bash
rm -rf /home/administrator/.local/lib/python3.12/site-packages/pytest_asyncio*
```
测试文件不需要asyncio支持。

## 测试驱动开发模式

第一阶段和第三阶段都采用以下测试模式：

### Phase1测试（功能验证）
- 子Agent完成后立即验证: `python3 -c "from scripts.X import Y; print(Y())"`
- 回归检查: `grep -rn "旧模式"` 确保无残留
- R14标记步骤完成

### Phase2测试（对标验证）
- 43个已有测试必须无损通过
- 新增组件级测试至少5个断言
- 集成验证到现有系统后再回归43个测试

### Phase3测试（全量验证）
- 所有模块独立运行: `python3 -m pytest test_X.py -v`
- 全量运行: 所有测试在一个会话中运行，0失败
- 修复测试文件中的模块级代码（如 `sys.exit()` 放在 `if __name__ == "__main__"` 块内，防止pytest收集中断）

## 测试文件模块级代码保护

弹性模式测试原始代码在模块级别调用了 `sys.exit()`:
```python
# ❌ 错误: 模块级别代码，pytest收集时中断
sys.exit(0 if FAIL == 0 else 1)

# ✅ 正确: 放在 __main__ 保护下
if __name__ == "__main__":
    sys.exit(0 if FAIL == 0 else 1)
```

这是unittest手动测试转化为pytest兼容文件时的常见陷阱。检查所有测试文件的模块级别代码，确保没有裸 `sys.exit()` / `print()` / `input()`。
