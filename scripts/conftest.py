"""pytest 配置文件 — Hermes 脚本单元测试共享 fixtures"""
import logging
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def caplog_fix(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture(scope="module")
def re_module():
    for mod in list(sys.modules.keys()):
        if "rule_enforcer" in mod:
            del sys.modules[mod]
    import rule_enforcer
    return rule_enforcer


@pytest.fixture
def anti_hallucination(re_module):
    return re_module.AntiHallucination


@pytest.fixture
def backup_guard(re_module):
    return re_module.BackupGuard


@pytest.fixture
def delivery_enforcer(re_module):
    return re_module.DeliveryEnforcer


@pytest.fixture
def three_phase(re_module):
    return re_module.ThreePhaseDevEnforcer


@pytest.fixture
def dual_review_module():
    """Fixture providing the dual_review_engine module for tests."""
    import dual_review_engine
    return dual_review_engine
