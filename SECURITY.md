# 安全策略 (Security Policy)

## 报告漏洞

如果你发现安全漏洞，请**不要**提交公开Issue。

请发送加密邮件至项目维护者：

- **Email**: 参见 pyproject.toml 中 authors 联系方式
- **GitHub**: 通过 GitHub Security Advisory 功能私密报告
  - 仓库地址: https://github.com/Nurburgring-Zhang/hermes-agent-enhanced
  - Security tab → Report a vulnerability

我们会在48小时内确认收到报告，并在修复后发布安全公告。

## 支持的版本

| 版本 | 状态 | 支持至 |
|------|------|--------|
| 0.16.0 (enhanced) | ✅ 当前活跃 | 持续更新 |
| 0.15.x 及更早 | ❌ 不再支持 | — |

## 安全最佳实践

### API Key 管理

- 所有API Key必须通过环境变量加载，严禁硬编码
- 使用 `env_loader.py` 统一管理
- .env文件永不提交到版本控制（已在.gitignore）

```bash
# 正确做法
export DEEPSEEK_API_KEY=sk-xxxx
# .env 文件 (不提交)
DEEPSEEK_API_KEY=sk-xxxx
```

### 双AI互审

- `dual_review_engine.py` 提供高风险操作自动拦截
- 以下操作会被 pre_tool_call 自动拒绝：
  - 文件删除操作 (rm -rf, os.remove, shutil.rmtree)
  - 数据库删除 (DROP TABLE, DELETE FROM without WHERE)
  - 系统命令注入风险
  - 未经验证的代码执行 (eval, exec)

### 审计追踪

- `audit_system.py` 记录所有工具调用和模型交互
- 审计日志位于 `logs/` 目录，不可篡改
- 每次修改操作前自动备份（rule_enforcer R3规则）

### 模型安全

- 模型路由自动切换链遇连续失败自动降级
- fallback机制确保服务连续性
- 输出验证：反幻觉铁律（R1）强制要求每次输出有真实依据

### 依赖安全

```bash
# 定期扫描依赖漏洞
pip-audit
# 或
safety check
```

### 建议

1. 生产环境使用独立的API Key，限制权限范围
2. 定期轮换API Key
3. 审查审计日志，关注异常模式
4. 保持依赖更新到最新安全版本
5. 非必要不开放网络访问
6. 使用独立用户运行Hermes Agent，最小权限原则
