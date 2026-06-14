---
name: hermes-upgrade-workflow
description: Hermes Agent非破坏性升级工作流 - 在WSL2中安全升级Hermes同时保留所有自定义文件(自定义Commands/Devices/RAG/Security/Expert System)，零数据丢失。版本: 1.0. 创建: 2026-04-22.
triggers:
  - "升级Hermes"
  - "hermes upgrade"
  - "迁移Hermes"
  - "update hermes"
---

# Hermes 非破坏性升级工作流

## 核心原则

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


**永远不要用 `git reset --hard`**。自定义文件在 `hermes_cli/` 和 `tools/` 目录中，git不追踪这些文件，但reset会清空工作区。

## 标准升级流程

### Step 1: 备份所有自定义文件
```bash
# 在git repo根目录执行
BACKUP_DIR=~/.hermes/hermes-agent/pre-upgrade-backup-$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp hermes_cli/monitoring_commands.py $BACKUP_DIR/ 2>/dev/null
cp hermes_cli/main.py $BACKUP_DIR/ 2>/dev/null
cp tools/device_tools.py $BACKUP_DIR/ 2>/dev/null
cp tools/rag_memory_tool.py $BACKUP_DIR/ 2>/dev/null
cp load_security.py $BACKUP_DIR/ 2>/dev/null
cp -r expert_system.py $BACKUP_DIR/ 2>/dev/null
```

### Step 2: 检查git状态
```bash
cd ~/.hermes/hermes-agent
git remote -v
git branch -vv
git rev-list --left-right --count HEAD...origin/main  # 看落后多少commit
```

### Step 3: 非破坏性合并
```bash
git fetch origin
git merge origin/main
# OR: git merge origin/main --no-edit
```
如果merge失败（冲突），用 `git merge --abort` 中止，手动解决后重试。

### Step 4: 验证升级成功
```bash
hermes --version
git log --oneline -3
```

### Step 5: 检查自定义文件状态
```bash
git status --short
```
- `??` 开头的是未追踪文件（自定义文件，正常）
- `hermes_cli/main.py` 如果变成repo版本（检查内容是否包含自定义commands）

### Step 6: 恢复被覆盖的文件
如果 `main.py` 被git覆盖：
```bash
cp pre-upgrade-backup-YYYYMMDD_HHMMSS/main.py hermes_cli/main.py
```

### Step 7: 运行健康检查
```bash
hermes doctor
hermes doctor --fix  # 自动修复配置版本迁移等
```

## 关键发现（经验教训）

### Hermes git repo位置
- 在 `~/.hermes/hermes-agent/`，不是 `~/.hermes/`
- 自定义文件在 `hermes_cli/` 和 `tools/` 目录中

### 被覆盖的高风险文件
| 文件 | 风险 | 恢复方式 |
|------|------|----------|
| `hermes_cli/main.py` | **高** — 最易被覆盖 | 从备份恢复 |
| `hermes_cli/monitoring_commands.py` | 低 — git不追踪 | 自动保留 |
| `tools/device_tools.py` | 低 — git不追踪 | 自动保留 |
| `tools/rag_memory_tool.py` | 低 — git不追踪 | 自动保留 |
| `load_security.py` | 低 — git不追踪 | 自动保留 |

### 常见hermes doctor警告（可忽略）
- `MiniMax (China) HTTP 404` — 检测端点问题，不影响实际使用
- `ripgrep not found` — 可选依赖
- `docker not found` — 禁用Docker是硬性规则
- `npm vulnerability` — WhatsApp bridge等可选组件

### 需要关注的hermes doctor警告
- `Config version outdated (v12 → v22)` — 运行 `hermes doctor --fix` 自动迁移
- `tinker-atropos not found` — 可选子模块
- `Browser tools (node binary missing)` — WSL2常见问题，用Python API补救

## 配置迁移
hermes doctor --fix 会自动处理：
- `stt.model` → provider-specific config
- `compression.summary_*` → `auxiliary.compression`
- Config v12 → v22

## 升级后验证清单
- [ ] `hermes --version` 显示新版本
- [ ] `git rev-list --left-right --count HEAD...origin/main` 显示 `0 0`
- [ ] 自定义文件存在于 `hermes_cli/` 和 `tools/` 目录
- [ ] `hermes doctor` 无致命错误
- [ ] Hermes正常响应命令

---

_本Skill基于2026-04-22实际升级经验创建。_

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
