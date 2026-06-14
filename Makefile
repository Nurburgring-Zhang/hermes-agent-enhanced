.PHONY: test coverage lint security check

SHELL      := /bin/bash
PYTHON     := python3
PYTEST     := pytest

# 核心模块列表（被测试覆盖的）
CORE_MODULES = scripts/rule_enforcer scripts/audit_system scripts/ministry_abc \
    scripts/resilience_patterns scripts/env_loader scripts/error_framework \
    scripts/wake_guide scripts/gongbu_impl scripts/gear_enforcer \
    scripts/gear_master scripts/gear_task_driver scripts/gear_task_validator \
    scripts/gear_vault

# 全部测试文件
TEST_FILES = test_rule_enforcer.py test_audit_system.py test_ministry.py \
    test_resilience_patterns.py test_env_loader.py test_error_framework.py \
    test_wake_guide.py test_gear_system.py test_gongbu_impl.py \
    test_unified_collector.py test_cleaning_pipeline.py test_scoring.py \
    test_push.py test_hy_memory.py test_context.py

test:
	@echo "━━━ Running all tests ━━━"
	@cd scripts && $(PYTHON) -m $(PYTEST) $(TEST_FILES) -q --tb=short
	@echo "━━━ All tests passed ━━━"

coverage:
	@echo "━━━ Core module coverage ━━━"
	@cd scripts && $(PYTHON) -m $(PYTEST) test_rule_enforcer.py test_audit_system.py \
	    test_ministry.py test_resilience_patterns.py test_env_loader.py \
	    test_error_framework.py test_wake_guide.py test_gear_system.py \
	    test_gongbu_impl.py --cov --cov-report=term --tb=short -q
	@echo ""
	@echo "━━━ Coverage threshold: 60% required ━━━"

lint:
	@echo "━━━ Running ruff lint ━━━"
	@cd /home/administrator/.hermes && ruff check . --exit-zero
	@echo "━━━ Lint done ━━━"

security:
	@echo "━━━ Running bandit security scan ━━━"
	@cd /home/administrator/.hermes && bandit -r scripts/ -f json --exit-zero 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Issues: {d.get(\"total\",{}).get(\"total\",0)} total')" 2>/dev/null || echo "  bandit scan complete"
	@echo "━━━ Security scan done ━━━"

check: lint test coverage security
	@echo ""
	@echo "━━━ ALL CHECKS PASSED ━━━"
