# Hermes增强版独立仓库管理模式

## 场景
增强代码在 `~/.hermes/scripts/` 下，但 `~/.hermes/` 本身不是git仓库。原版hermes-agent在 `~/.hermes/hermes-agent/` 下有独立的git。

## 初始化

```bash
cd /home/administrator/.hermes
git init && git checkout -b main
# .gitignore已存在(排除config.yaml/ .env/ *.db/ __pycache__/ logs/)
git add scripts/*.py scripts/*.md Makefile .github/ .bandit.yml .ruff.toml pyproject.toml SOUL.md AGENTS.md .gitignore config.yaml.example
git commit -m "Hermes Agent Enhanced v0.16.0-enhanced"
```

## 推送

```bash
# 创建GitHub仓库 API
curl -H "Authorization: token <token>" \
     -d '{"name":"hermes-agent-enhanced","private":false}' \
     https://api.github.com/user/repos

# SSH推送（需要先将SSH key添加到GitHub）
git remote add origin git@github.com:Nurburgring-Zhang/hermes-agent-enhanced.git
git push -u origin main
```

## 文件大小
- 332文件, 99,360行代码
- 核心模块: rule_enforcer(1459行) / audit_system(866行) / resilience_patterns(442行) / ministry_abc(919行) / error_framework(551行) / env_loader(101行)
- 测试文件: 15个, ~686测试

## CI触发
推送至main后, .github/workflows/ci.yml 自动触发4步并行:
lint → test → coverage(60%门禁) → security
