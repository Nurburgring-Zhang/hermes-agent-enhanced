---
name: cron-audit-and-cleanup
description: 系统审计并清理 Hermes cron job 中的重复/冗余条目。诊断→分组→择优保留→安全删除→验证的完整工作流。
trigger: cron 冗余、对话框弹出两次、cron 冲突、'这个命令在后台运行'等类似查询
---

# Cron 审计与清理工作流

## 何时使用

## 触发条件
- 用户提及部署、安装、配置服务时
- 需要调试系统环境或依赖时
- 执行系统运维操作时

- 用户抱怨对话框弹出多次/频率异常
- 新 cron 加入后发现旧版未移除
- 定期系统维护时对 cron 做健康检查

## 与其他技能的关系
- **system-code-consolidation** — 当 cron 清理涉及**脚本代码整合**（合并重复功能脚本、提取共享配置、删除旧代码）时，先按本技能清理 cron，再按 system-code-consolidation 做代码整合。两技能互补。
- 本技能只负责 cron 层面的审计和删除，不涉及脚本代码层面的合并。

## 工作流程

### 第一步：全面列表
```
cronjob action=list
```
输出所有 cron jobs，注意两份关键信息：`job_id`（UUID 或短hex）、`script` 字段、`schedule`、`deliver`、是否 `no_agent=true`

### 第二步：按功能分组
逐一识别每组 cron 的功能类型。常见重复类型：
- **task-monitor** → 同一脚本多份注册
- **context-index-system** → 不同路径注册同一功能
- **ability-activator** → 新旧系统各一份
- **guardian-{cycle,heal,push}** → 新旧各一份
- **ultimate-collector / mega-collector** → 名异实同
- **ai-scoring / ai-scoring-backfill** → 重复

### 第三步：择优策略
多份重复时保留哪一份的决策优先级：
1. **`no_agent=true` + `workdir` 设置** — 最稳定，纯脚本模式无依赖
2. **`deliver=local`** — 安静执行，不推送消息到 origin
3. **脚本路径在 `scripts/` 下** — 最新版路径规范
4. **有 `last_run_at` + `last_status` 历史** — 已验证可运行
5. **UUID 格式较新的 job_id** — 通常表示较新的注册

### 第四步：安全删除
```python
cronjob(action='remove', job_id='<id>')
```
删除前再次确认不会影响主功能。一次删一种类型，分步验证。

### 第五步：验证
运行保留的 cron 确认工作正常：
```python
cronjob(action='run', job_id='<kept_id>')
```
确认无报错，输出正常。

## 常见陷阱

### ⚠️ 脚本路径歧义
cron 的 `script` 字段可能是相对路径（`task_monitor.py`）或带 `scripts/` 前缀（`scripts/task_monitor.py`）。Hermes cron 默认 workdir 是 `~/.hermes`，所以两种写法都可能指向 `scripts/` 下的同一文件。**不要凭路径不同就以为是不同脚本**，要核对文件名+内容。

### ⚠️ no_agent=true 脚本模式
脚本模式 cron（`no_agent=true`）直接运行 `.py` 文件，输出到终端（**不通过 Hermes agent 会话**）。这会导致：
- 多份同名 cron → 对话框弹出多次
- 输出带 `[wake_init]` 等前缀 → 用户看到"启动了两遍自检"

**解决方案：** 同一脚本只保留一个 `no_agent=true` 的 cron job。

### ⚠️ 检查旧系统残留
Hermes cron 有两种 ID 格式：
- 短 hex（如 `3c0084b57096`）— 旧版格式
- UUID（如 `567f1c990fc5`）— 新版格式  
同功能在新旧系统各注册一次是常见原因。

### ⚠️ 文件不存在的 cron
列表中可能有脚本路径指向不存在的文件（如 `omni_health_monitor.py` 不存在但仍有 cron）。这类 cron 实际上每次运行都会失败，应一并清理。

### ⚠️ 功能已被覆盖的 cron
如 `auto_resume_check`（每5分钟检查任务状态）功能完全被 `task_monitor`（每10分钟检查+恢复+7规则自检）覆盖。前者可安全删除。

## 优先级顺序
1. **直接影响用户体验的**（对话框弹出多次）— 最高优先级
2. **同一脚本多份运行** — 次高（浪费资源）
3. **文件不存在仍调度的** — 中等（静默失败）
4. **不活跃的旧系统残留** — 低优先级

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
