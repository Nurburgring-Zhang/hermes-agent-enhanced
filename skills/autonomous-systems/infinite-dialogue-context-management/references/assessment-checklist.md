# 上下文压缩系统 完整评估清单

## 用途
每次格林主人问"xx系统完美实现了吗？"时，对照此清单逐项检查，**不要凭感觉回答"都好了"**。

## 检查步骤

### Step 1: 确认问的到底是哪个系统
写下来，不要急着答。
- 问的是推送系统 → 检查cron_push.log + push_records表
- 问的是上下文压缩 → 检查cron + 对话层钩子
- 问的是采集系统 → 检查raw_intelligence表

### Step 2: cron层检查
```bash
crontab -l | grep <系统名>
ls -la logs/<系统名>.log
tail -5 logs/<系统名>.log
```

### Step 3: 对话层检查（关键！）
- 有没有启动钩子？(init_hermes_context.sh / session_init_check.py)
- 有没有替换SOUL.md的机制？
- 如果答案是"没有"→ 系统未完成

### Step 4: 数据库/文件层检查
- 输出文件新鲜度（stat --format='%y' <file>）
- 数据库记录

## 常见的"伪完成"模式
1. cron在跑 → ✅ 但文件没人读 → ❌
2. 脚本存在 → ✅ 但没部署到cron → ❌
3. 输出数据对 → ✅ 但没用于对话层 → ❌
4. 以前能跑 → ✅ 但中断后没恢复 → ❌

## 记忆固化规则
每次发现系统未完成时，在MEMORY里记录精确的缺失项。
不要更新MEMORY说"xx系统完成了"，要更新为"xx系统：cron层完成，对话层未接入"。
