# 贡献指南 (Contributing Guide)

感谢你对 Hermes Agent Enhanced 的关注！

## 如何提交贡献

### 1. Fork 并 Clone

```bash
git clone git@github.com:Nurburgring-Zhang/hermes-agent-enhanced.git
cd hermes-agent-enhanced
git checkout -b feature/your-feature-name
```

### 2. 开发环境

```bash
pip install -e .[dev]
# 或手动安装开发依赖
pip install pytest pytest-cov ruff mypy
```

### 3. 代码风格

- 遵循 PEP 8，使用 ruff 格式化
- 类型注解：所有公共函数必须标注类型
- 文档字符串：每个模块/类/公共方法使用三重引号docstring
- 命名规范：snake_case（变量/函数），PascalCase（类），UPPER_CASE（常量）
- 行宽：120字符

运行格式检查：

```bash
ruff check scripts/
ruff format scripts/
mypy scripts/ --ignore-missing-imports
```

### 4. 测试要求

- 新增代码必须有对应测试
- 运行测试套件确认全部通过：

```bash
pytest scripts/ -v
pytest scripts/ --cov=scripts --cov-report=term-missing
```

- 核心模块（rule_enforcer, ministry_abc, resilience_patterns, audit_system, error_framework）覆盖率需 >= 80%
- 测试文件命名：test_<module_name>.py
- 测试函数命名：test_<feature>_<scenario>_<expected_result>

### 5. 提交PR

1. 确保所有测试通过，无lint错误
2. 撰写清晰的PR标题和描述
3. 关联相关Issue（如有）
4. PR描述必须包含：
   - 改动原因
   - 改动内容摘要
   - 测试结果（粘贴测试输出）
5. 必须通过 CI 检查（auto_ci.py 完整链路）

### 6. Commit 规范

```
<type>: <简短描述>

类型:
  feat     — 新功能
  fix      — Bug修复
  refactor — 重构
  docs     — 文档
  test     — 测试
  chore    — 杂项

示例:
  feat: 添加R14三阶段开发流程
  fix: 修复audit_system时间戳时区问题
  docs: 更新README核心模块表格
```

### 7. 模块开发指南

新增核心增强模块时，必须在模块头部包含：

```python
"""
模块名称 — 简短描述

对标: <参考系统>
注入方式: <如何被加载>
触发时机: <何时执行>
"""
```

### 8. 问题反馈

- Bug报告：提Issue，附带复现步骤和日志
- 功能建议：在Issue中描述使用场景和预期行为
- 安全问题：参见 SECURITY.md，请勿公开提Issue

## Code of Conduct

- 尊重所有贡献者
- 建设性反馈，对事不对人
- 保持专业和友善
