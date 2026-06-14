# Hermes Agent 商用级开发 — 子Agent任务拆解

## 并行执行计划

### Agent-1: Phase1-SQL注入修复
- 目标: 修复3个文件共10处f-string拼接
- 文件: agents_company/token_compression.py, token_compression_v2.py, skills/long-task-guardian/long-task-guardian.py
- 工具: patch/terminal
- 验收: grep -rn "f.*execute" 零结果

### Agent-2: Phase2-六部真实实现
- 目标: 创建4个新模块(types/exceptions/abc/gongbu_impl)
- 路径: scripts/ministry_*.py + scripts/gongbu_impl.py
- 工具: write_file/terminal
- 验收: python3 -c "from scripts.gongbu_impl import GongBu" 成功

### Agent-3: Phase3-bare except修复
- 目标: 修复5个核心文件的bare except
- 文件: gear_master.py, status_reporter.py, super_guardian.py, unified_gateway.py, token_compression_v2.py
- 工具: patch/terminal
- 验收: grep -n "except:" 零结果

### Agent-4: Phase4-死代码清理
- 目标: 清理force_compressor/pipeline_v1-v3/unified_collector/start_all
- 工具: terminal(grep确认引用) + patch/delete
- 验收: 无死代码引用

### Agent-5: Phase5-路径标准化
- 目标: 25处Path("/home/administrator") → Path.home()
- 工具: patch
- 验收: grep -rn '"/home/administrator"' 零结果

### Agent-6: Phase6-测试体系
- 目标: 创建pytest框架+3个核心模块测试
- 文件: scripts/test_rule_enforcer.py, test_gear_enforcer.py, test_dual_review.py
- 工具: write_file/terminal
- 验收: pytest scripts/test_rule_enforcer.py -v 通过

### Agent-7: Phase7-logging
- 目标: gear_master/status_reporter/super_guardian 3个核心文件print→logging
- 工具: patch
- 验收: 零print()在核心守护模块

### Agent-8: Phase8-版本管理
- 目标: pyproject.toml + __version__
- 工具: write_file
- 验收: python3 -c "import version; print(version.__version__)" 正常
