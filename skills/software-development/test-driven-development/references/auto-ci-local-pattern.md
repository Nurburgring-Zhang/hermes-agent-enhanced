# 本地自动CI模式

## 场景
GitHub无法推送（WSL网络限制/企业防火墙/token权限不足），但仍然需要自动化CI验证。

## 方案
auto_ci.py 在本地运行完整的lint→test→coverage→security链，通过cron每30分钟自动触发。

## 使用方式

```bash
# 单次运行
python3 scripts/auto_ci.py

# 循环模式(每30分钟, 最多10次)
python3 scripts/auto_ci.py --loop 30 --max-loops 10

# cron注册(每30分钟自动)
cronjob(action='create', schedule='30m', script='scripts/auto_ci.py', no_agent=True)
```

## 输出

```
2026-06-14 [INFO] CI 结果: ✅ 全部通过
  ✅ lint (0.8s)
  ✅ test_core (37.7s)
  ✅ coverage (23.8s)
  ✅ security (15.1s)
```

结果写入 `logs/auto_ci/ci_results.jsonl`。

## 完整CI链(77秒)

1. `ruff check . --exit-zero` — 代码风格(0.8s)
2. `pytest <15个测试文件> -q --tb=short` — 686个测试(37.7s)
3. `pytest <9个核心模块> --cov --cov-fail-under=60 -q` — 覆盖率门禁(23.8s)
4. `bandit -r scripts/ --exit-zero` — 安全扫描(15.1s)

## CI文件清单

| 文件 | 必须 | 用途 |
|------|------|------|
| Makefile | ✅ | make test/coverage/lint/security/check |
| .github/workflows/ci.yml | 可选 | GitHub Actions配置 |
| .bandit.yml | ✅ | bandit排除配置 |
| .ruff.toml | ✅ | ruff风格配置 |
| pyproject.toml | ✅ | 项目元数据 |
| scripts/pytest.ini | ✅ | pytest配置 |
| scripts/auto_ci.py | ✅ | 本地自动CI(~500行) |

## 注意事项
- auto_ci.py必须在PyPI依赖全部安装的环境中运行
- 测试文件必须使用pytest框架，不能是unittest手动脚本
- coverage门禁(`--cov-fail-under=60`)在覆盖率不足时返回非0退出码，导致CI失败
