# 批量化测试生成模式

## 场景
代码库>1000个.py文件, 400K+行, 测试从43→686个。

## 分层策略

| 层 | 范围 | 测试数 | 覆盖率 |
|----|------|--------|--------|
| L1 核心 | rule_enforcer/audit/ministry/gear/env_loader/error_framework/wake_guide/gongbu_impl | 9模块~200测试 | 70% |
| L2 业务 | unified_collector/cleaning/scoring/push | 4模块~271测试 | 逻辑覆盖 |
| L3 记忆 | hy_memory/context | 2模块~127测试 | 逻辑覆盖 |
| L4 汇总 | 全部 | 686测试 | 70%核心+门禁60% |

## 分批执行模式

```
Batch 1 (3 agents并行): rule_enforcer+audit+ministry → 验证
Batch 2 (3 agents): env_loader+error_framework+wake_guide → 验证
Batch 3 (3 agents): gear_system+gongbu_impl → 验证
Batch 4 (3 agents): unified_collector+cleaning+scoring → 验证
Batch 5 (2 agents): push+hy_memory → 验证
Batch 6 (1 agent): context → 验证
```

## 测试文件模板

```python
import pytest, os, json
from pathlib import Path

class TestModule:
    def test_import(self):
        from scripts.module import Class  # import成功=测试通过
    
    def test_basic_operation(self, tmp_path):
        result = Class().method()
        assert result is not None
    
    def test_edge_case(self, monkeypatch):
        monkeypatch.setenv("KEY", "val")
        # ...
```

## 每个测试文件必须覆盖
- import验证
- 基本操作
- 边界/异常
- 配置/环境变量
- 至少15个测试用例

## 验证清单
- [ ] 每个测试文件单独运行通过
- [ ] 全部686个一起运行通过
- [ ] 覆盖率核心模块>=70%
- [ ] --cov-fail-under=60 通过
