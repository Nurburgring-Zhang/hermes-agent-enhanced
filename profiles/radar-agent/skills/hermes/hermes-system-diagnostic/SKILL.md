---
name: hermes-system-diagnostic
description: "Hermes Agent系统性全面诊断与自检流程。用于对Hermes全系统进行深度诊断，发现问题并修复。诊断范围：Skills/Agents/Expert System/Intelligence/Memory/Workflow Handlers/Cron Jobs/auto_engine。关键陷阱：execute_code沙箱路径(/tmp/hermes_sandbox_xxx/)与实际HERMES路径(/home/administrator/.hermes)不一致，诊断Skills/Handlers必须用terminal或正确设置sys.path。"
version: 1.0.0
tags: ["hermes", "diagnostic", "system-health", "debugging"]
---

# Hermes System Diagnostic Skill

## 触发条件
- "全面自检"、"系统诊断"、"检查所有能力"
- 新增模块后需要验证完整性
- 系统行为异常需要定位问题

## 前置准备

### 0a. 对话层压缩初始化 + 全局检索
在执行任何诊断前，先运行以下两项确保获得完整系统视图：

```bash
# 最简化的全系统快照
echo "=== Skills ===" && find ~/.hermes/skills -name SKILL.md | wc -l
echo "=== Scripts ===" && ls ~/.hermes/scripts/*.py | wc -l
echo "=== Agents ===" && ls ~/.hermes/agents_company/employees/ 2>/dev/null | wc -l
echo "=== Experts ===" && ls ~/.hermes/agents_company/experts/ 2>/dev/null | wc -l
echo "=== DBs ===" && find ~/.hermes -name '*.db' -type f 2>/dev/null | wc -l
echo "=== Active Memory DB ===" && python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.hermes/active_memory.db')
if os.path.exists(db):
    conn = sqlite3.connect(db)
    tables = [t[0] for t in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
    for t in tables:
        c = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
        print(f'  {t}: {c} rows')
    conn.close()
"
echo "=== Cron ===" && crontab -l | wc -l && echo "lines"
echo "=== Wake Guide ===" && cat ~/.hermes/reports/wake_guide.json 2>/dev/null | python3 -c "
import sys,json; d=json.load(sys.stdin)
for k in ['gear_health','ai_scoring_pending','ai_scoring_today','push_today','push_fail_today','interrupted_task']:
    print(f'  {k}: {str(d.get(k,\"?\"))[:80]}')
" 2>/dev/null || echo "  wake_guide: NOT FOUND"
```

### 0b. LLM桥状态快速检查
诊断LLM可用性是排查许多AI功能退化的第一步（特别是L3画像、AI评分降级等）：

```bash
echo "=== LM Studio (8080) ===" && curl -s http://localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"local","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' 2>/dev/null | python3 -c "import sys; d=__import__('json').load(sys.stdin); print('OK' if 'choices' in d else 'FAIL')" 2>/dev/null || echo "LM Studio: NOT RUNNING"
echo "=== Ollama (11434) via WSL ===" && curl -s http://172.31.32.1:11434/api/tags 2>/dev/null | python3 -c "import sys; d=__import__('json').load(sys.stdin); print(f'{len(d.get(\"models\",[]))} models')" 2>/dev/null || echo "Ollama via WSL host: NOT RUNNING"
echo "=== Ollama (11434) via localhost ===" && curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import sys; d=__import__('json').load(sys.stdin); print(f'{len(d.get(\"models\",[]))} models')" 2>/dev/null || echo "Ollama localhost: NOT RUNNING"
```

**WSL→Windows Ollama陷阱**：Ollama安装在Windows上时绑定到`127.0.0.1`，从WSL访问需要使用Windows宿主IP（通常`172.31.32.1`或`172.x.x.x`）。`llm_bridge.py`已修复添加WSL宿主IP自动检测和fallback。

## 诊断维度（10项）

### 1. Skills
```bash
find ~/.hermes/skills -name SKILL.md | wc -l
# 正常值：>100 files

# 检查SKILL.md完整性（有些目录是辅助文件无SKILL.md）
find ~/.hermes/skills -mindepth 2 -type d | while read d; do
  [ -f "$d/SKILL.md" ] || echo "MISSING SKILL.md: $d"
done
```

### 2. Expert System
```bash
ls ~/.hermes/agents_company/experts/ | wc -l
# 正常：390
# 每个专家应有：identity.yaml, experience.yaml, skills.yaml, sop.yaml, tools.yaml
ls ~/.hermes/agents_company/experts/expert_001/  # 样例
```

### 3. Agents Company
```bash
ls ~/.hermes/agents_company/employees/ | wc -l
# 正常：130（12个部门）
ls ~/.hermes/agents_company/employees/01_marketing_01/  # 样例
```

### 4. Workflow Handlers
```bash
ls ~/.hermes/agents_company/handlers/*.py 2>/dev/null | wc -l
```

### 5. Intelligence DB — Full Stats
```python
import sqlite3, os
db = os.path.expanduser('~/.hermes/intelligence.db')
conn = sqlite3.connect(db)

# 表结构
for tname in [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    cnt = conn.execute(f"SELECT COUNT(*) FROM [{tname}]").fetchone()[0]
    print(f"  {tname}: {cnt}")

# 评分覆盖度
total = conn.execute('SELECT COUNT(*) FROM cleaned_intelligence').fetchone()[0]
scored = conn.execute('SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NOT NULL AND ai_score_total != ""').fetchone()[0]
print(f"  Scored: {scored}/{total} ({scored/total*100:.1f}%)")

# 评分分布
for s in [0,20,40,60,80]:
    rows = conn.execute(f"SELECT COUNT(*) FROM cleaned_intelligence WHERE CAST(ai_score_total AS REAL) >= {s} AND CAST(ai_score_total AS REAL) < {s+20}").fetchone()[0]
    print(f"  {s}-{s+19}: {rows}")

# 推送统计
today = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
today_push = conn.execute('SELECT COUNT(*) FROM push_records WHERE push_time >= ?', (today,)).fetchone()[0]
total_push = conn.execute('SELECT COUNT(*) FROM push_records').fetchone()[0]
print(f"  Push today: {today_push}, Total: {total_push}")

conn.close()
```

### 6. Memory System — active_memory.db
```python
import sqlite3, os
db = os.path.expanduser('~/.hermes/active_memory.db')
if os.path.exists(db):
    conn = sqlite3.connect(db)
    for tname in [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        cnt = conn.execute(f"SELECT COUNT(*) FROM [{tname}]").fetchone()[0]
        if cnt > 0:
            print(f"  {tname}: {cnt}")
    conn.close()

# 关键表应有数据：
# memory_semantic (69+ facts), memory_scene (16+ scenes), 
# memory_profile (3+ profiles), memory_episodic (78+ episodes),
# structmem_events (8000+ events), mem0_meta (15000+ memories)
```

### 7. Cron Jobs
```bash
crontab -l | grep -v '^#' | grep -v '^$' | wc -l
crontab -l | grep -v '^#' | grep -v '^$'  # 列出所有
```

### 8. auto_engine
```bash
ls ~/.hermes/auto_engine/*.py
python3 -c "import sys; sys.path.insert(0,'/home/administrator/.hermes/auto_engine'); from self_evolution_engine import *; print('self_evolution_engine OK')" 2>/dev/null || echo "self_evolution_engine FAIL"
```

### 9. Production Loop
```python
import sqlite3, os, json

# production_loop files
print("=== Production Engine Files ===")
for f in sorted(os.listdir(os.path.expanduser('~/.hermes/production_loop'))):
    if not f.startswith('_'): print(f"  {f}")

# loop_state.db tasks
db = os.path.expanduser('~/.hermes/state/loop_state.db')
if os.path.exists(db):
    conn = sqlite3.connect(db)
    for tname in [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        cnt = conn.execute(f"SELECT COUNT(*) FROM [{tname}]").fetchone()[0]
        print(f"  {tname}: {cnt}")
    conn.close()

# production_loop audit
pa = os.path.expanduser('~/.hermes/reports/production_loop_audit.json')
if os.path.exists(pa):
    with open(pa) as f:
        d = json.load(f)
    print(f"  engine_running: {d.get('engine_running','?')}")
    print(f"  unfinished_tasks: {d.get('unfinished_tasks','?')}")
    camel = d.get('camel_guard', {})
    if camel:
        print(f"  CaMeL: injection_events={camel.get('injection_events','?')}, status={camel.get('status','?')}")
```

### 10. Gears System
```python
import json, os
wg = os.path.expanduser('~/.hermes/reports/wake_guide.json')
if os.path.exists(wg):
    with open(wg) as f:
        d = json.load(f)
    print(f"  gear_health: {d.get('gear_health','?')}")
    print(f"  gear_heartbeat: {d.get('gear_heartbeat_minutes','?')} min")
    print(f"  g6_validation: {str(d.get('g6_validation','?'))[:80]}")

# gear_registry
gr = os.path.expanduser('~/.hermes/reports/gear_registry.json')
if os.path.exists(gr):
    with open(gr) as f:
        d = json.load(f)
    tasks = d.get('tasks', {}) if isinstance(d, dict) else {}
    print(f"  gear_tasks: {len(tasks)} registered")
    for k,v in list(tasks.items())[:3]:
        print(f"    {k}: {v.get('status','?')}")

## 深度审计扩展（新增 ⚠️ 核心方法论）

### 10. 声明vs.实现一致性审计

Hermes系统中，**代码注释/日志声称的功能经常与实际执行路径不一致**。这是系统退化的主要根因。每次诊断必须做：

#### 10.1 追踪关键函数的完整调用链
```
用户看到的特性 → omni_loop/guardian调度 → 实际调用的脚本 → 脚本内部实现
```
关键做法：
- 从入口开始追踪：`omni_loop.py`的step列表 → 每个step调用的命令 → 被调用脚本的具体函数
- 找到**实际被执行的那行代码**，而不是看docstring声称了什么

#### 10.2 API密钥审计
AI功能退化的首要原因就是API key缺失/过期。审计每一步：
```bash
# 检查所有环境变量
echo "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:+SET}"  # :+SET 安全显示
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+SET}"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:+SET}"
echo "DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:+SET}"

# 检查所有config.yaml中的key
grep -A2 'api_key\|token\|secret' ~/.hermes/config.yaml 2>/dev/null
```
**关键判断逻辑**：找到脚本中检查API key的分支逻辑(通常是`if not api_key:`)，确认所有AI功能走的是哪个分支。

#### 10.3 日志模式识别
AI评分/产品生成/需求挖掘等功能的退化模式在日志中有明确信号：
```
⚠️ 未配置API密钥，使用增强版规则评分替代   → AI评分被降级为规则匹配
TASK_ENHANCED_RULES                        → 规则评分完成（非AI评分）
TASK_AI_SCORED                             → 真正的AI评分完成（正常信号）
```
审计时搜索这些模式。识别"降级模式"比检查"是否有AI代码存在"更重要。

#### 10.4 硬编码模板检测
当脚本中有类似模式的代码，说明功能被降级为硬编码模板：
```python
# 疑似硬编码模板的信号：
product_spec['features'] = ['固定的功能1', '固定的功能2', ...]  # 不是AI生成的
tech_stack = ['Python', 'Hermes Agent', ...]  # 每种产品都一样
```
验证方法：看脚本中是否生成了prompt但从未发送给任何API（send/post/delegate_task），产生的输出是否所有条目都一样。

#### 10.5 闭环完整性审计
验证全流程闭环完整性（信息采集→清洗→AI评分→需求挖掘→专家匹配→产品生成→测试迭代→交付）：
- 每个环节是否有真实的产出文件
- 产出文件是否包含真实的变化内容（不是每个时间戳都一样）
- 测试+交付环节是否存在（通常缺失）

### 12. 上下文压缩/索引系统审计

验证对话层是否真正使用索引系统而非SOUL.md全文。

```bash
# 检查5个cron
crontab -l | grep -E "context_packer|surgical|auto_assoc|cross_session|index_system"

# 检查文件新鲜度
ls -la reports/context_index.json reports/context_pack.json reports/surgical_context.json

# 复原验证
python3 scripts/context_reconstructor.py verify

# 记忆规则
python3 -c "
import sqlite3
c = sqlite3.connect('active_memory.db')
for r in c.execute(\"SELECT content FROM memory_entries WHERE content LIKE '%索引%'\"):
    print('记忆规则:', r[0][:80])
c.close()
"

# 检查各模式可用
python3 scripts/context_reconstructor.py list
python3 scripts/context_reconstructor.py search 备份
```

**对话层风险提示**：cron层完美运行≠对话层激活。用`grep`检查当前对话的system prompt是否包含索引摘要而不是SOUL.md全文。

| 模式 | 日志信号 | 根源 |
|------|----------|------|
| AI评分被规则替代 | `⚠️ 未配置API密钥` | 环境变量缺失 |
| 产品方案硬编码 | features/tech_stack固定不变 | 代码从未发送prompt给LLM |
| 采集器静默 | 7天+无数据 | 网络不可达/反爬升级 |
| 全量采集超时 | exit code 124 | 采集器超时设置过短 |
| 推送基于假评分 | 规则分冒充AI分排序 | AI评分断点向上游传播 |
| 重复内容漏网 | 18组重复标题未被过滤 | 去重逻辑不够严格 |

## 能力激活审计

### ability_activator报degraded的排查

当ability_activator报告状态为degraded时：

**步骤1：看报告**
检查 `reports/ability_activation_report.json` 中的 `overall` 字段（ok/degraded）、`agents_company.failed`（语法错误列表）、`cron_schedule.missing`（缺失cron列表）

**步骤2：修复语法错误**
用 Python 的 ast.parse 检查失败模块的语法
最常见的错误：缩进问题导致 try 块提前关闭
修复方法：用 read_file 查看上下文，用 patch 修复缩进层次

**步骤3：处理缺失cron**
⚠️ **重要区分**：ability_activator检测的是系统crontab中的条目。Hermes实际有两套cron系统：
1. 系统crontab — 少数核心cron
2. Hermes内部cron系统 — 通过cronjob工具注册的大量job

如果缺失cron已通过cronjob注册了，则是假警报。验证方法：用cronjob列表查看内部cron是否在运行。

## 常见问题与修复

### 问题1：execute_code沙箱路径错误
execute_code在`/tmp/hermes_sandbox_xxx/`下运行，看不到真实的`~/.hermes/`。
**解决方案**：用terminal()做文件操作诊断，或在execute_code中用`Path.home()`而非硬编码路径。

### 问题2：__init__.py显示0 imports
**原因**：沙箱环境执行`__init__.py`时，`os.listdir()`可能读到错误的`agents_company/handlers/`路径。
**验证方法**：用terminal+head/cat直接查看文件内容。

### 问题3：Handler 13缺失
**症状**：`handler_13_quality_assurance.py`不存在。
**修复**：创建完整的QA handler文件，包含handle_quality_assurance函数。

### 问题4：SQL拼写错误
**症状**：`sqlite3.OperationalError: near "REVERAGE"`
**原因**：`INSERT OR REVERAGE`应为`INSERT OR REPLACE`
**修复**：patch文件

### 问题5：Relative import失败
**症状**：`attempted relative import with no known parent package`
**原因**：模块作为独立脚本运行时，`.`相对导入无效。
**修复**：将`from .module_name`改为`from module_name`

## 关键路径速查

| 资源 | 路径 |
|------|------|
| Skills SKILL.md | `~/.hermes/skills/<category>/<name>/SKILL.md` |
| Skill count | `find ~/.hermes/skills -name SKILL.md \| wc -l` |
| Agents Employees | `~/.hermes/agents_company/employees/` (130 dirs) |
| Experts | `~/.hermes/agents_company/experts/` (390 dirs) |
| Main Intelligence DB | `~/.hermes/intelligence.db` (13表) |
| Active Memory DB | `~/.hermes/active_memory.db` (35表, 含memory_semantic/scene/profile/structmem等) |
| Mem0 | `~/.hermes/memory/mem0_data/mem0_store.db` (15,495条) |
| Reports | `~/.hermes/reports/` (wake_guide, gear_registry, production_loop_audit, self_evolve_*) |
| Scripts | `~/.hermes/scripts/` (279个) |
| auto_engine | `~/.hermes/auto_engine/` (12 files) |
| Production Loop | `~/.hermes/production_loop/` (7 files) |
| Loop State | `~/.hermes/state/loop_state.db` |
| Agent Company Tools | `~/.hermes/agents_company/` (60+ files) |
| Cron | `crontab -l` (36 lines) |
| Ollama (from WSL) | `http://172.31.32.1:11434` (NOT localhost) |
| LM Studio (WSL) | `http://localhost:8080` (需要Windows GUI启动API) |

### 问题6：Ollama从WSL不可达（localhost:11434超时）
**症状**：`_call_local_llm()` 尝试Ollama全部超时，所有LLM功能降级
**根因**：Ollama安装在Windows上，绑定到Windows的`127.0.0.1`。从WSL中`localhost`指向WSL自身，不指向Windows。
**修复**：
1. 找到WSL宿主IP：`grep nameserver /etc/resolv.conf` 或 `cat /etc/resolv.conf`（通常`172.31.32.1`或`172.x.x.x`）
2. 在llm_bridge.py中添加WSL宿主IP自动检测和多主机fallback
3. Ollama端口从`localhost:11434`改为`172.31.32.1:11434`

### 问题7：cleaned_intelligence 零分数据（ai_score_total=0）
**症状**：评分覆盖度100%但含大量0分数据（热点标签、短内容、纯元数据）
**根因**：某些平台（微博/抖音/百度热点）采集的元数据条目（Label/Score格式）无实质内容，评分脚本无法评分留了0分
**诊断**：
```sql
SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0;
SELECT source, COUNT(*) FROM cleaned_intelligence WHERE ai_score_total = 0 GROUP BY source;
```
**修复**：归档到archive_cleaned + 删除
```python
items = conn.execute("SELECT id, title, source FROM cleaned_intelligence WHERE ai_score_total = 0").fetchall()
# 对于content长度<50的hot-label条目，直接归档
for item in items:
    conn.execute("INSERT INTO archive_cleaned (title, source, ai_score_total, archived_at) VALUES (?,?,0,?)", (item[1], item[2], now))
    conn.execute("DELETE FROM cleaned_intelligence WHERE id = ?", (item[0],))
conn.commit()
```

### 问题8：production_loop遗留测试任务
**症状**：状态数据库agent_tasks中有来自5月25-26日的测试任务，状态永远pending
**诊断**：
```sql
SELECT * FROM agent_tasks WHERE task_id LIKE 'test_%';
```
**修复**：直接删除测试任务
```sql
DELETE FROM agent_tasks WHERE task_id LIKE 'test_%';
DELETE FROM agent_checkpoints WHERE session_id LIKE 'test_%';
DELETE FROM agent_state_transitions WHERE session_id LIKE 'test_%';
```

### 问题9：脚本源文件丢失只剩__pycache__字节码
**症状**：`ls`命令显示脚本目录下有`.pyc`编译文件但`.py`源文件不存在。cron也显示在跑但实际执行的是旧字节码。`ability_activator`不报错因为系统能import旧字节码。

**根因**：文件系统操作（批量sed/错误的写入/文件移动）误删了源文件，但Python自动保留了`__pycache__`中的`.pyc`缓存。下次重新导入时Python仍能找到字节码，但`cat/read_file`这类操作看不到源文件。

**诊断**：
```bash
# 检查是否有.pyc文件但.py文件缺失
for f in ~/.hermes/scripts/*.py; do
    base=$(basename "$f")
    pyc="__pycache__/${base}c"
    [ -f "$f" ] || echo "❌ 源文件丢失: $base"
done
```
更精确的检查：
```bash
find ~/.hermes/scripts/__pycache__ -name '*.pyc' | while read pyc; do
    basename_py=$(basename "$pyc" .cpython-*.pyc).py
    [ -f "$(dirname $(dirname $pyc))/$basename_py" ] || echo "❌ ${basename_py%.py}: 源文件丢失，仅剩字节码"
done
```

**注意**: 这个检查仅用于`scripts/`目录（源文件）。`skills/`目录中的引用/模板/脚本文件可能设计上就是字节码，不适用此规则。

**修复**：重写源文件或从git恢复

## 输出格式

诊断后输出：
```
╔══════════════════════════════╗
║  HERMES SYSTEM DIAGNOSTIC  ║
╠══════════════════════════════╣
║  ✅ Skills:      149 files  ║
║  ✅ Experts:     390 / 30   ║
║  ✅ Employees:   130 / 12   ║
║  ✅ Handlers:    19/19      ║
║  ✅ Intelligence: 17,816    ║
║  ✅ Cron:        12 jobs    ║
║  ⚠️  Issues:     [list]     ║
╚══════════════════════════════╝
```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
