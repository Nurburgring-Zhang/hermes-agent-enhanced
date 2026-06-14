# 商用级测试覆盖率体系

## 核心原则
商用级 ≠ 100%覆盖率。而是：核心模块 > 60%，全量不做虚标门禁。

## 覆盖率门禁标准

| 范围 | 目标 | 计量方式 |
|------|------|---------|
| 核心模块(规则引擎/六部/弹性模式/审计/错误处理/环境加载) | >=70% | pytest --cov --cov-fail-under=60 |
| 情报采集管道(采集/清洗/评分/推送) | >=50% | 单独cov统计 |
| 记忆上下文系统(三层记忆/压缩/上下文) | >=50% | 单独cov统计 |
| 全量1422个.py文件 | 不做门禁 | 含大量外部依赖采集器，纯UT不可行 |

## Makefile命令
make test -> 686个测试全部通过
make coverage -> 核心模块70%
make lint -> ruff通过
make security -> bandit通过
make check -> lint+test+coverage+security 全串行通过

## GitHub Actions CI（4步并行）
jobs: lint -> test -> coverage (60% gate) -> security

## 测试文件分布(686个测试)

| 模块组 | 测试数 |
|--------|--------|
| 规则引擎+弹性模式 | 89 |
| 审计+错误处理 | 67 |
| 六部模块 | 100 |
| 齿轮系统 | 54 |
| 环境加载 | 24 |
| 情报采集管道 | 271 |
| 记忆上下文 | 127 |
| 合计 | 686 |

## Common pytest failures
- pytest-asyncio 0.23.2 + pytest 9.0.3: AttributeError: 'Package' object has no attribute 'obj' -> 直接删除pytest-asyncio
- 测试文件底部的sys.exit()在模块级别导致pytest收集0个 -> 包在if __name__下
- 新建测试文件后缓存旧__pycache__ -> find . -name "*.pyc" -delete
