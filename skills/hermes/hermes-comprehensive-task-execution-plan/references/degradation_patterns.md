# 退化模式与自动修复对照表

## 已发现的退化模式

| 模式 | 表现 | 根因 | 修复方案 | 首次发现 |
|------|------|------|---------|---------|
| cron静默丢失 | 上下文脚本不在crontab，但齿轮仍报healthy | self_evolve auto-paused / 升级覆盖 | 从齿轮注册表重挂 | 2026-05-27 |
| 源文件只剩字节码 | .py源文件消失，只剩__pycache__ | 多次patch+脚本替换导致源文件被删 | 从备份恢复或重写 | 2026-06-01 |
| index sections=0 | context_index.json的sections列表为空 | 脚本输出格式不包含sections字段；cron覆盖了手动修复 | 修复脚本输出格式 + auto_healer自动重建 | 2026-06-01 |
| 备份恢复丢kwargs | ComfyUI get_prompt/IS_CHANGED签名变成位置参数 | 备份文件是旧版本 | grep验证方法签名 | 2026-05-31 |
| 硬盘挂载丢失 | /mnt/m/ 等挂载点不可用 | WSL重启后自动挂载失败 | 检查fstab | — |

## 自动修复对照表

| 检测到的异常 | 修复动作 | 脚本/命令 |
|-------------|---------|----------|
| context_index sections为空 | 重建索引 | `python3 context_index_system.py auto` |
| 关键脚本文件丢失 | 从备份恢复 | 扫描/mnt/d/Hermes/备份/ |
| cron丢失 | 从cron_backup重挂 | `crontab`命令重新添加 |
| 齿轮不健康 | 重启齿轮 | 重新运行gear_enforcer |
| wake_guide未更新 | 检查gear_enforcer是否运行 | 重新启动cron服务 |

## 修复失败策略

- 连续3次修复失败 → 推送微信告警
- 停止自动修复（防止越修越坏）
- 齿轮降级到degraded模式
- 等待用户介入
