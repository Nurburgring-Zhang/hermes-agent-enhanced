# Hermes Agent Enhanced — 安装指南

## 环境要求

- **Python**: >= 3.10 (推荐 3.11+)
- **操作系统**: Linux / macOS / Windows (WSL)
- **Git**: 任意版本
- **pip**: >= 23.0

## 从源码安装

### 1. 克隆仓库

```bash
git clone https://github.com/Nurburgring-Zhang/hermes-agent-enhanced.git
cd hermes-agent-enhanced
```

### 2. 创建虚拟环境 (推荐)

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# 或
venv\Scripts\activate      # Windows
```

### 3. 安装核心依赖

```bash
# 方式A: 可编辑安装 (开发模式, 推荐)
pip install -e .

# 方式B: 从 requirements.txt 安装
pip install -r requirements.txt

# 方式C: 标准安装
pip install .
```

### 4. 安装可选依赖

```bash
# 开发工具 (pytest, black, ruff, mypy)
pip install -e ".[dev]"

# Web服务 (fastapi, uvicorn)
pip install -e ".[web]"

# 数据库 (asyncpg, alembic)
pip install -e ".[db]"

# 全部可选依赖
pip install -e ".[dev,web,db]"
```

## 验证安装

### 检查版本

```bash
hermes-enhanced-version
# 输出: 0.16.0-enhanced
```

### 导入测试

```python
import scripts
print(scripts.__version__)
# 输出: 0.16.0-enhanced

from scripts.error_framework import HermesError
print("Import OK")
```

### 运行测试

```bash
# 运行全部测试
cd scripts && python -m pytest -v

# 运行单个测试文件
cd scripts && python -m pytest test_error_framework.py -v

# 使用 Makefile
make test
```

### 运行代码检查

```bash
# Lint
make lint

# 覆盖率
make coverage

# 完整检查 (lint + test + coverage + security)
make check
```

## 入口点命令

安装后以下命令可用:

| 命令 | 说明 |
|------|------|
| `hermes-enhanced-version` | 显示版本号 |
| `hermes-auto-ci` | 运行自动CI (lint→test→coverage→security) |
| `hermes-audit` | 运行审计日志系统 |
| `hermes-gear` | 运行Gear强制执行器 |

## 常见问题

### Q: pip install 报 "externally-managed-environment"

在 Ubuntu/Debian 系统上使用虚拟环境:

```bash
sudo apt install python3-venv python3-full
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Q: 依赖安装失败

某些依赖(如 playwright)需要系统库:

```bash
# Ubuntu/Debian
sudo apt install libgbm1 libnspr4 libnss3 libatk-bridge2.0-0

# 安装 Playwright 浏览器
playwright install chromium
```

### Q: 导入 scripts 模块失败

确保在项目根目录执行安装命令, 且当前工作目录正确。

## 项目结构

```
hermes-agent-enhanced/
├── scripts/          # 核心Python包 (340+模块)
├── skills/           # 技能模块 (378+)
├── plugins/          # 系统插件
├── profiles/         # 多Profile配置
├── pyproject.toml    # 项目元数据
├── requirements.txt  # 依赖列表
├── MANIFEST.in       # 分发清单
├── Makefile          # 构建/测试命令
└── README.md         # 项目文档
```

## 许可

MIT License — Copyright (c) 2024-2026 Nous Research
