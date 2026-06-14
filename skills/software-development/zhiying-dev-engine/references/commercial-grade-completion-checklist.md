# 商用级AI Agent框架 — 完备化实战检查清单

> 来源: 2026-06-15 Hermes Agent Enhanced 1311测试/Sprint3完整交付实战
> 对标: CrewAI / AutoGen / LangGraph / Dify / Coze

## 安全基线（零容忍）

| # | 检查项 | 命令 | 目标 |
|---|--------|------|------|
| 1 | shell=True | `grep -rn "shell=True" scripts/ | grep -v test_\|# nosec` | 0 |
| 2 | bare except | `grep -rn "except:" scripts/*.py | grep -v "Exception\|ValueError\|..."` | 0 |
| 3 | API密钥泄露 | `grep -rn "sk-\|ghp_\|AIzaSy\|nvapi-" scripts/` | 0 (排除test文件) |
| 4 | bandit HIGH | `bandit -r scripts/ --severity high | grep -v RedCrack\|vendor` | 0 核心模块 |
| 5 | 假实现函数 | `grep -Pzo "(?s)def \w+\([^)]*\):\s*pass" scripts/<核心>.py` | 0 |
| 6 | vault密钥入git | `git ls-files vault/` | 0 |

## 测试体系

| # | 检查项 | 标准 |
|---|--------|------|
| 1 | 核心模块≥10条测试 | 每个test_*.py≥10 |
| 2 | CI全绿 | lint+test+coverage+security |
| 3 | 覆盖率门禁 | cov-fail-under=30 (阶段一) → 60 (最终) |
| 4 | 回归无退化 | 新测试不破坏已有测试 |

## 代码质量

| # | 检查项 | 标准 |
|---|--------|------|
| 1 | 核心模块ruff F/E/W | 0 (10/10干净) |
| 2 | print→logging | 核心模块0 print |
| 3 | MD5→SHA256 | 安全相关哈希全部替换 |

## 功能模块

| 层级 | 模块 | 状态 |
|------|------|------|
| L1 基础 | 规则引擎/弹性/审计/错误/env_loader | ✅ |
| L2 安全 | security_sandbox/prompt_guard/secret_manager | ✅ |
| L3 编排 | 三省六部/role_orchestrator/workflow_state_machine | ✅ |
| L4 测试 | 1311+ tests/CI auto_ci.py | ✅ |
| L5 API | api_gateway.py (FastAPI+JWT+RateLimiter) | ✅ |
| L5 Git | git_workflow.py (PR review+commit msg) | ✅ |
| L5 插件 | plugin_manager.py (registry+hooks+hot-reload) | ✅ |
| L6 Web | 仪表盘 | P2 待实现 |

## 常见修复模式速查

### 1. cd in subprocess → cwd参数
```python
# ❌ subprocess.run("cd scripts && python3 ...".split())
# ✅ subprocess.run(["python3", "-m", "pytest", ...], cwd="/path/to/scripts")
```

### 2. write_file覆盖 → patch精确修改
```python
# ❌ write_file(path, 新头部)  # 会丢失文件其余内容
# ✅ patch(path, old_string="import logging", new_string="import logging\nlogger = ...")
```

### 3. logger未定义
```python
# 在 import logging 后补:
logger = logging.getLogger(__name__)
```

### 4. 动态测试发现（避免硬编码文件列表）
```python
from glob import glob
test_files = [Path(f).name for f in glob("scripts/test_*.py")]
cmd = ["python3", "-m", "pytest"] + test_files + ["-q"]
subprocess.run(cmd, cwd="scripts")
```

### 5. 紧急git恢复
```bash
git checkout -- scripts/broken_file.py  # 恢复到上次commit
wc -l scripts/broken_file.py            # 验证完整
```

## 交付前最终检查

- [ ] CI 4/4全部通过
- [ ] 核心测试≥1311 passing
- [ ] 无shell=True/bare except/密钥泄露
- [ ] 核心模块ruff F/E/W干净
- [ ] 0假实现/占位符
- [ ] README/CONTRIBUTING/SECURITY完整
- [ ] vault不在git中
- [ ] .gitignore完整
- [ ] 自上次commit后无退化
