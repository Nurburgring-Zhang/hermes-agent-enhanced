---
name: python-project-setup-with-uv
description: Install and configure Python projects with incomplete dependency declarations using uv package manager
tags: [devops, python, uv, dependencies, setup]
---
# Skill: Python Project Setup with UV

## When to Use

## 触发条件
- 用户提及部署、安装、配置服务时
- 需要调试系统环境或依赖时
- 执行系统运维操作时

Use this skill when installing/cloning a Python project that has incomplete dependency declarations in pyproject.toml or requirements.txt, and the project fails to run due to missing packages.

## Prerequisites
- Python 3.12+ with uv installed
- The project uses a virtual environment (uv-managed)

## Steps

### 1. Clone and Initial Setup
```bash
git clone <repo-url> && cd <repo-name>
cp .env.example .env  # If present, fill in API keys later
uv sync  # Install declared dependencies
```

### 2. Identify Missing Dependencies
Read the project's main file to see what imports are actually used:

```bash
# Look for import statements in key files
grep -r "^import \|^from " --include="*.py" | head -20
```

Or test imports directly:
```bash
.venv/bin/python -c "import anthropic; import PIL; import reportlab; ..."
```

Common packages for AI/generative projects:
- `anthropic` - Claude API
- `fal-client` - fal.ai
- `elevenlabs` - ElevenLabs API
- `PIL`/`pillow` - Image processing
- `reportlab` - PDF generation
- `ebooklib` - ePub creation
- `numpy`, `pandas` - Data science

### 3. Add Missing Dependencies
```bash
uv add <package-name>
# For PIL, install pillow:
uv add pillow
```

Add multiple at once:
```bash
uv add pillow reportlab ebooklib anthropic fal-client elevenlabs
```

### 4. Verify Installation
```bash
.venv/bin/python -c "import <module>; print('OK')"
```

### 5. Test the Project
Run the main script or test command to ensure it works:
```bash
uv run python <main-script>.py
```

## Pitfalls

- **Import name ≠ package name**: PIL is imported as `PIL` but installed via `pillow`
- **Virtual env location**: Use `.venv/bin/python` not just `python` when testing
- **API keys required**: Many AI projects need keys in `.env` before they'll run
- **Optional dependencies**: Some packages are optional (art/audiobook features) - install as needed

## Notes
This approach assumes the project uses uv. For pip-based projects, use `pip install -r requirements.txt` first, then supplement with `pip install <missing>`.
## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
