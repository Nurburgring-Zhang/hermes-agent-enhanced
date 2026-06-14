# Hermes Agent 商用级开发计划 v1.0

## P0优先级开发清单 — 共8个Phase

### P0-Phase1: SQL注入修复
- 文件: agents_company/token_compression.py (6处), token_compression_v2.py (1处), skills/long-task-guardian/long-task-guardian.py (3处)
- 修复方式: 参数化查询 + 表名白名单验证
- 验收: 所有f-string拼接的表名改为白名单+参数化, 验证无SQL注入路径

### P0-Phase2: 六部真实实现
- 新建: scripts/ministry_types.py, scripts/ministry_exceptions.py, scripts/ministry_abc.py
- 新建: scripts/gongbu_impl.py (工部Playwright真实实现)
- 验收: 4个模块import通过, 工部browser_navigate真实打开网页返回内容

### P0-Phase3: bare except修复
- 文件: gear_master.py (4处), status_reporter.py (8处), super_guardian.py (8处), unified_gateway.py (1处)
- 修复方式: bare except → except Exception + logging
- 验收: 零bare except残余

### P0-Phase4: 死代码清理
- 文件: force_compressor.py, pipeline_engine.py/v2/v3, unified_collector.py, start_all.py
- 修复方式: 确认引用关系后删除或合并
- 验收: 无死代码引用

### P1-Phase5: 路径标准化
- 文件: 25个脚本中的Path("/home/administrator") → Path.home() / ".hermes"
- 验收: 零硬编码路径

### P1-Phase6: 测试体系
- 新建: scripts/test_rule_enforcer.py, scripts/test_gear_enforcer.py, scripts/test_dual_review.py
- 验收: pytest通过

### P1-Phase7: logging基础设施
- 文件: 核心守护模块(gear_master/status_reporter/super_guardian) → logging
- 验收: 零print()在核心模块

### P2-Phase8: 版本管理
- 新建: pyproject.toml, __version__
- 验收: python -c "import version" 正常
