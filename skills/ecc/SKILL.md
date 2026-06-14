---
name: ecc
description: ECC (Ensemble Coding Companion) — Agent性能优化系统(189k Stars)。软件开发优先能力，多Agent多子Agent组合使用。自动增强skill直觉、跨会话记忆、安全审计。
version: 1.0.1
category: software-development
related_skills: [agents-company, autonomous-systems, software-development]
setup_required: true
setup_steps:
  - npm install --production
---

# ECC — Agent性能优化系统

## 来源

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

GitHub: https://github.com/affaan-m/ECC (189,660⭐)
本地: `~/.hermes/scripts/collectors/ECC/`

## 能力
- **Skills直觉** — 自动发现和加载最合适的skill
- **跨会话记忆** — 持久化Agent记忆
- **安全审计** — 命令执行安全检查
- **研究优先开发** — 收集上下文→生成研究报告
- **多Agent协同** — 多个Agent/子Agent共享ECC上下文

## 激活

```bash
cd ~/.hermes/scripts/collectors/ECC
npm install --production
```

已通过以下方式注册：
1. ✅ SKILL.md → `~/.hermes/skills/ecc/`
2. ✅ Cron → 每4小时自动优化 (job_id: `8e345889fd7e`)
3. ✅ 激活标记 → `~/.hermes/reports/ecc_activated.json`

## 组合使用（多Agent模式）

ECC被设定为**软件开发优先能力(P0)**，可与其他skills组合：

```python
# 与agents-company组合
skill_view('ecc')
skill_view('agents-company')
# → 主Agent加载ECC优化skil选择，子Agent通过ECC共享上下文

# 与autonomous-systems组合
skill_view('ecc')
skill_view('autonomous-systems')
# → ECC增强系统直觉，autonomous-systems提供编排

# 多子Agent同步
# 每个子Agent独立加载ECC，共享安全策略和记忆
```

## 验证
```bash
skill_view('ecc')
# readiness_status 应为 available
ls ~/.hermes/scripts/collectors/ECC/SOUL.md  # ECC核心理念
```

## 安装故障排查
| 问题 | 解决 |
|------|------|
| git clone TLS错误 | 用API tarball: `curl -sL https://api.github.com/repos/affaan-m/ECC/tarball \| tar xz` |
| npm install慢 | 用 `--production` 只装生产依赖 |
| skill不显示 | 先调用一次 `skill_view('ecc')` 触发加载 |

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
