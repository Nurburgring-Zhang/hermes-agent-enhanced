---
name: hermes-system-self-audit
description: Hermes系统全功能模块自检与健康审计 — 部署后必须验证，cron必须巡查
---

# Hermes 系统自检与健康审计

## 核心教训（2026-05-31 固化）

**"只部署不验证=白做"** — 这是Hermes最致命的系统级错误模式。

## 已发现的系统故障模式

### 模式1：cron被auto-paused无声无息
- 自进化引擎(self_evolve)检测到"Script not found"时会auto-pause cronjob
- **但不会推送告警！** 只标记`state: paused`
- 导致context_packer/surgical_slicer/gear_enforcer/hy-memory全部静默停止
- 修复后必须检查`cronjob list`看是否有paused状态的job

### 模式2：记忆数据库缺失（Hy-Memory全链路）
- L1/L2/L3 cron在跑但数据库不存在 = 写到空数据库
- 表现：日志显示运行成功但`COUNT(*) = 0`
- 修复：`python3 scripts/init_active_memory_db.py`
- 检查命令：`ls ~/.hermes/data/active_memory.db && python3 -c "import sqlite3; c=sqlite3.connect('...'); print(c.execute('SELECT COUNT(*) FROM memory_facts').fetchone()[0])"`

### 模式3：备份恢复后方法签名丢失
- 从旧备份恢复代码后，`get_prompt(self, kwargs)` 被恢复成旧版位置参数
- ComfyUI需要`def get_prompt(self, **kwargs)`
- 验证命令：`grep -n 'def get_prompt\|def IS_CHANGED' __init__.py`
- 两行都必须是`**kwargs`

### 模式4：部署脚本存在但cron未部署
- 脚本文件存在，甚至cronjob列表中有条目，但`enabled: false, state: paused`
- 检查：`cronjob action=list` 看所有job的enabled+paused状态
- 恢复：`cronjob action=update job_id=xxx schedule="* * * * *"`

## 全系统检查清单

### 每轮对话开始时（步骤0强制）
```
1. cronjob list 检查是否有paused的key job
2. 检查active_memory.db各表是否有数据
3. 检查wake_guide.json是否有中断任务
4. 检查最近一次context_packer/context_index是否新鲜
```

### 部署新功能后的验证步骤
```
1. 语法验证：python3 -m py_compile
2. 功能验证：实际运行一次
3. cron验证：cronjob list确保enabled=true, state=scheduled
4. 输出验证：检查生成的文件内容是否正确
5. 过1分钟后二次验证：cron实际执行日志
```

### 备份恢复后的必须检查
```
1. grep -n 'def IS_CHANGED\|def get_prompt' 检查**kwargs
2. cronjob list检查所有job状态
3. 运行一次自检脚本
```

## 排查工具

```bash
# 查看所有cron状态
cronjob list | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'{j[\"name\"]}: {\"paused\" if not j[\"enabled\"] else \"ok\"}') for j in d['jobs']]"

# 检查active_memory.db表数据量
python3 -c "
import sqlite3, os
db='/home/administrator/.hermes/data/active_memory.db'
if os.path.exists(db):
    c=sqlite3.connect(db)
    for t in [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]:
        cnt=c.execute(f'SELECT COUNT(*) FROM \"{t}\"').fetchone()[0]
        print(f'{t}: {cnt}')
"

# 检查context压缩文件新鲜度
ls -la ~/.hermes/reports/context_*.json ~/.hermes/reports/surgical_*.json 2>/dev/null

# 全功能审计
python3 ~/.hermes/scripts/context_selfcheck.py 2>/dev/null || echo "自检脚本不可用"
```

## 记忆规则 vs 知识库规则

| 存储位置 | 内容类型 | 示例 |
|---------|---------|------|
| memory | 用户偏好/规则/习惯 | "格林主人要求改前先备份" |
| skill (如本skill) | 系统级排查方法/已发现故障模式 | "cron auto-paused无声无息" |
| skill (comfyui-node-kwargs-bug) | 具体bug案例 | kwargs错误的根因+修复+验证 |

## 触发条件

- 部署新功能后
- 从备份恢复后
- 对话中报告系统故障时
- 怀疑cron未正常工作时
