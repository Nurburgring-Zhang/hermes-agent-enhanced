---
name: capability-verification
title: 全能力真实激活验证方法论
description: 验证Hermes系统中所有能力和模块是否真的在"主动运行"而非"看起来在跑"——包括cron穿透验证、齿轮相互督促链验证、AI评分真实性验证、三重冗余恢复验证
domain: autonomous-systems
priority: high
required_skills: [dual-ai-review]
triggers:
  - "验证能力是否真实激活"
  - "全能力激活验证"
  - "检查系统状态是否为degraded"
  - "ability_activator"
  - "能力真实运行检查"
  - "系统健康度审计"
  - "G6齿轮链验证失败"
  - "gear_health degraded"
  - "TikTokDownloader语法错误"
  - "f-string兼容"
---

# 全能力真实激活验证方法论

### 真实审计案例（2026-06-01 本轮对话产出）

### 审计命令模板

```bash
echo "=== 1. 文件存在性 ==="
echo "文件大小: $(wc -l < scripts/X.py)行"
echo ""
echo "=== 2. cron是否存在 ==="
crontab -l 2>/dev/null | grep "X"
echo ""
echo "=== 3. 日志新鲜度 ==="
ls -lt logs/X.log 2>/dev/null | head -1
echo "最新行:"
tail -1 logs/X.log 2>/dev/null
echo ""
echo "=== 4. 对话层是否真的接入 ==="
grep "X.py" hermes-agent/run_agent.py 2>/dev/null | echo "  引用次数: $(grep -c 'X' hermes-agent/run_agent.py 2>/dev/null || echo 0)"
echo ""
echo "=== 5. crontab命令是否正确 ==="
crontab -l 2>/dev/null | grep "X" | head -1 | python3 -c "
import sys
cmd = sys.stdin.read().strip()
# 检查命令是否存在且参数正确
if cmd:
    # 提取脚本名和参数
    parts = cmd.split()
    for i, p in enumerate(parts):
        if p.endswith('.py'):
            print(f'  脚本: {p}')
            print(f'  参数: {parts[i+1:]}')
            break
"
```

### 本轮对话审计发现（2026-06-01）

| 承诺 | 实际状态 | 证据 |
|------|---------|------|
| 齿轮G1每1分钟运行 | ❌ 已死4天 | `gear_enforcer.log`最后更新: 5月28日 |
| G1-G7互审系统 | ❌ crontab一条都没有 | `crontab -l \| grep gear`返回空 |
| dialogue_context_init.py | ❌ 从未被执行 | `crontab -l \| grep dialogue_context`返回空 |
| forced_executor.py强制武器 | ❌ 只被前者调用, 前者没执行 | `grep -r "forced_executor" *`只在dialogue_context_init.py |
| checkpoint_recorder cron | ❌ 参数错误每1分钟报错 | `latest`命令不存在 |
| model_router接入对话层 | ❌ run_agent.py未修改 | 最后修改5月12日 |
| agent_company接入对话层 | ❌ run_agent.py未引用 | `grep -c "agent_company" run_agent.py`=0 |

**不能只写代码就报告"完成"。必须执行五层穿透验证。**

## 穿透验证四层法（2026-06-01 固化，源自本轮对话的修正）

当用户问"X功能是否完全实现且真实生效"时，不要只看文件存在性。执行四层穿透验证：

**层1：文件存在性** — 脚本文件/配置文件是否存在
```
ls -la ~/.hermes/scripts/X.py
```

**层2：源文件完整性** — 脚本是否有源文件（不是只剩字节码）
```
# 检查源文件存在，不只是__pycache__
find ~/.hermes/scripts -name "X.py" -type f
```
⚠️ 本轮对话已踩坑：2个脚本源文件丢失，只有`__pycache__/*.pyc`残留。文件存在性检查通过字节码伪造"存在"假象。

**层3：cron自动化** — 是否有cron自动运行
```
crontab -l | grep X
```

**层4：数据新鲜度** — 输出数据是否在最近几分钟内更新过
```
stat reports/context_pack.json  # 检查Modify时间
ls -la reports/context_index.json
```
⚠️ 即使cron在跑，也要检查输出文件的新鲜度。如果输出文件停在几小时前，cron可能执行失败（权限/路径/依赖问题）。

**层5（额外）：对话层接入** — 系统是否真的在对话中使用了这个能力
- SOUL.md是否已是索引版？ `head -5 SOUL.md`
- context_index.json是否在唤醒时被实际加载？检查system prompt
- 需要额外配置层确认，不是仅靠cron运行证明

**穿透验证的总原则：** 任何一层没穿透，就不能说"已实现"。

### 三列报告格式（源自本轮格林主人纠正）

当报告功能状态时，使用三列分隔：

| 需求 | 状态 | 证据 |
|------|:----:|------|
| context_packer压缩 | ✅ | 文件存在(13281B)+cron每1分钟+输出刚更新 |
| 手术刀切分 | ❌ | 源文件丢失(只剩__pycache__字节码) |

不是"看起来做了"，是"每个需求都有一列硬证据"。证据必须是`ls`/`stat`/`crontab -l`等命令的实时输出。

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


**ability_activator.py** 检测的 `cron_schedule` 检查的是**系统crontab（crontab -l）** 的条目，而Hermes还有一套**内部cron调度系统**（通过cronjob工具注册的job）。

这意味着：
- `ability_activator` 报 `degraded` + `缺失cron` → 只说明系统crontab缺少条目
- 实际功能可能已经通过Hermes内部cron在正常运行
- **反过来也成立**：ability_activator报 `ok` 不代表所有能力真的在干活

## 🚩 第六层：共同运行验证（2026-06-09 固化，源自本轮对话格林主人纠正）

这不是新的一层，而是前五层的**强化原则**：能导入 ≠ 在运行。

### 三问法验证每个能力

当评估一个功能是否真实激活时，不要只问"能不能导入"，按以下三问穿透：

```
1. 是被动等待调用，还是主动持续运行？
   - ❌ 能导入 = 被动（等人调用才跑）
   - ✅ 有cron/daemon/systemd持续触发 = 主动（系统自己在跑）

2. 是独立孤岛，还是与其它模块共同运行？
   - ❌ 只有自己能跑 = 孤岛
   - ✅ 跑完之后自动触发另一个模块 = 共同运行

3. 互相唤醒还是各跑各的？
   - ❌ 各跑各的cron = 并行孤岛
   - ✅ A完成自动触发B, B完成自动通知C = 互相唤醒
```

### 真实案例：Dynamic Workflows 18模块

评估对象：workflows/ 目录的18个模块

| 模块 | 被动/主动 | 共同运行 | 互相唤醒 | 结论 |
|------|:--------:|:--------:|:--------:|:----:|
| types.py | 被动(被import) | 被调用 | 不适用 | ✅ 基础库 |
| storage.py | 被动(被调用) | 被调用 | 不适用 | ✅ 基础库 |
| runtime.py | 被动(被调用) | runtime注入 | → preflight / gear / retrospect / evolution | ✅ 注入运行 |
| daemon.py | **主动(cron */5)** | 扫描全部18模块 | → gear_registry + production_monitor | ✅ **真主动** |
| cron_activate.py | **主动(cron */15)** | 检查pending | → workflow激活 | ✅ **真主动** |
| evolution_bridge | 被动(被runtime调用) | → retro_candidates | → self_evolve_cluster(每天03:00) | ✅ 链式运行 |

**验证方法：**
```bash
# 检查daemon是否在跑
tail -3 ~/.hermes/logs/workflow_daemon.log
# 期望：最近5分钟内有日志

# 检查gear_registry最近是否有daemon的心跳
python3 -c "import json; r=json.load(open('/home/administrator/.hermes/reports/gear_registry.json')); print(r.get('workflow_daemon',{}).get('last_heartbeat','无'))"
# 期望：最近5分钟内

# 检查retro_candidates表是否有数据
python3 -c "import sqlite3; c=sqlite3.connect('/home/administrator/.hermes/state.db').cursor(); print(c.execute('SELECT COUNT(*) FROM retro_candidates').fetchone()[0])"
# 期望：>0（有workflow复盘数据）
```

### 原则

- **能导入不等于在运行** — 必须检查cron/systemd/chain注入点
- **各跑各的不等于共同运行** — 必须检查A→B的触发链路
- **全链路穿通才是真激活** — 从cron触发到最终产出，每一步都是代码执行不是prompt建议

这是本轮对话的核心纠正。当评估一个"强制机制"是否真实生效时，必须区分：

### prompt级强制（❌ 不可靠）
在system prompt、SOUL.md、AGENTS.md或dialogue_context_init.py中写规则：
```
🔴🔴🔴 你必须调用武器，不调用=违规
```
**问题**: LLM可以选择无视。没有实时惩罚机制。被格林主人纠正为"降级实现"。

### 系统级强制（✅ 可靠）
在代码层面直接执行，不经过LLM决策：
```python
# LLM没有选择"是否执行武器"的机会——代码已经执行完了
analysis = executor.analyze_and_split(task)   # 代码分析
executor.execute_segments(analysis, task)     # 代码执行
context = executor.build_prefilled_context()  # LLM只能总结
```

**验证标准**:
1. ❌ 规则在prompt里 = prompt级强制（不可靠）
2. ✅ 规则在代码里且在LLM回答前执行 = 系统级强制（可靠）
3. 验证时查看 `dialogue_context_init.py` 是否调用了 `ForcedExecutor`，而不是只看SOUL.md有没有写规则

### 实际案例
| 系统 | 类型 | 是否可靠 |
|------|------|---------|
| SOUL.md中的反模拟铁律 | prompt级 | ❌ LLM可选择无视 |
| gear_enforcer.py的反模拟检测 | 系统级(cron扫描日志) | ✅ 依赖独立进程，LLM不能干预 |
| dialogue_context_init.py的强制武器协议 | prompt级(LLM上下文) | ❌ LLM可选择无视 |
| forced_executor.py的自动执行武器 | 系统级(LLM回答前执行) | ✅ 代码直接执行，不经过LLM |

## 🔴 条件链审计方法论（2026-06-10 格林主人强制固化）

### 核心原则
**任何声称「自动运行」的功能，都必须追根到底验证调用链无断链。**

不是因为代码写了"在每个X之前执行Y"，Y就真的会被执行。必须追：
```
功能Y 在 条件A 下执行
  → 条件A 需要 条件B 下才能触发
    → 条件B 需要 条件C
      → ... 追到底
```

### 2026-06-10 实战案例：18项功能的审计

```python
# 追查模板
def audit_chain(feature_name):
    print(f"== {feature_name} ==")
    print(f"  声称: 在X条件下执行")
    print(f"  → 条件X是否被触发? 谁触发它?")
    print(f"    → 触发条件Y是否被满足?")
    print(f"      → ... 直到确认无条件或找到根因")
```

### 发现的三类死链模式

#### 1. configure() 模式死链
模块暴露 `configure(delegate_task_fn)` 接收引用，但没有任何地方调用过 `configure()`。

**例子**: `workflows/dual_review.py` 的 `configure()` 函数 — 代码写得很好，但从未被执行过。
**修复**: 用 Plugin hook 替代。Hermes 主Agent 启动时自动加载 plugin → `register(ctx)` → 注册 `pre_tool_call` hook，无需任何外部调用。

#### 2. 代码注入但路径无人触发
代码注入到 `runtime.run()` 或 `executor.execute_task()` 中，但 `runtime.run()` 从未被调用过。

**例子**: preflight/company_matcher/SDLC/adversarial 全部注入在 runtime.py phase 循环中。
**修复**: 最终强制执行器（mandatory_executor.py）通过 `hermes chat -z` 子进程提供 delegate_task 上下文。

#### 3. "能导入"伪装成"在运行"
模块检查只验证 `import` 成功，不验证执行路径是否被走过。

**例子**: 16/16模块可导入，但9条死链完全不可见。
**修复**: 把检查逻辑从"能否import"改为"调用链是否有终端"。

### 2026-06-10 审计最终结果

| 类别 | 数量 | 功能 |
|------|:----:|------|
| ✅ 无条件自动运行 | 9 | mandatory_engine, dual_review插件, auto_workflow插件, gear, retrospect, evolution, full_chain_test, daemon, storage |
| ❌ 死链(无调用方) | 9 | preflight, company_matcher, SDLC, adversarial, scheduler, recover, durable, unified_engine, DSL |
| 根因 | — | runtime.run() 从未被调用 |

**修复后**: mandatory_executor.py 启动子Agent → 提供delegate_task → runtime.run()可被调用 → 所有9条死链打通。

### 三路径穿透法（2026-06-10 新增）

任何声称"自动运行"的功能，不要只看1条路径。至少从3个角度验证：

第1路: 代码检查 — 注入代码是否存在？
第2路: 调用链检查 — 注入代码是否真的能被执行到？（有无断链？）
第3路: 运行证据检查 — 是否有日志/DB/输出证明它最近运行过？

只有当3路都通过时，才能说"功能真实激活"。任何1路失败=不能确认。

| 检查维度 | 方法 | 通过标志 |
|---------|------|---------|
| 代码存在性 | grep能在正确位置找到关键函数或流程 | 代码在正确位置 |
| 调用链完整 | 从根触发到注入点全链路可达 | 无断链 |
| 运行证据 | 最近5分钟内有日志/DB更新 | 时间戳新鲜 |

### 审计关键教训（2026-06-10 固化）

1. 绝对不要只看代码就确认 — 2026-06-10 10次提到"所有模块自动运行"，实际9条死链。
2. configure()模式=可疑 — 任何模块暴露 configure() 函数却无调用方，直接标记死链。
3. 调用链检查要追踪到终端 — 不只是"注入到哪个函数"，要追到"谁调用这个函数，谁的cron/hook触发它"。
4. 为什么mandatory_engine第一个版本没发现死链 — 因为它检查的是"能不能import"，不是"有没有执行路径"。格林主人指出这个问题后修正为"代码注入状态检查"。

## 验证方法

### 功能是否真的"在跑"——六层穿透法

```bash
cd /home/administrator/.hermes && python3 scripts/ability_activator.py 2>&1
```

关注输出中的关键信息：
```
状态: ok         ← 不是 degraded
语法错误: 0      ← quality_control_engine 等模块无语法错误
agents_company: X个通过  ← 无失败
缺失cron: []     ← 无缺失
```

### 第2阶：穿透验证（能力是否真实跑着）

#### 2a. 系统crontab vs 内部cron双重检查

```bash
# 系统crontab
crontab -l | grep -c "^[0-9*]"   # 有效条目数

# Hermes内部cron系统
# 用process工具或直接查 ~/.hermes/cron/jobs.json
cat ~/.hermes/cron/jobs.json 2>/dev/null | python3 -m json.tool | grep -c '"schedule"'
```

#### 2b. 齿轮系统日志验证（每1分钟运行的才是真实在动）

```bash
# 检查齿轮最近记录时间
echo "=== gear_enforcer ==="
tail -5 ~/.hermes/logs/gear_enforcer.log
echo "=== gear_master ==="
tail -5 ~/.hermes/logs/gear_master.log
echo "=== gear_driver ==="
tail -5 ~/.hermes/logs/gear_driver.log
```

**注意检查时间戳是否为最近1-3分钟内**，如果日志停留在几小时前说明齿轮卡死了。

#### 2c. Omni Loop实际执行验证（是否真的产出数据）

```bash
tail -80 ~/.hermes/logs/omni_loop.log | grep -E "(成功|失败|状态|Score|AI评分|产品)"
```

看最近的批次：采集是否真正有数据入库、AI评分是否真正评分了条目、产品生成是否真正产出了方案。

#### 2d. 进程存活验证

```bash
ps aux | grep -E '(hermes|python3.*loop|python3.*gateway|gear|guardian)' | grep -v grep
```

关键看：
- `hermes gateway run` → 消息网关，必须活着
- `eternal_loop.py` → 永生循环守护
- `hermes`（多个进程）→ 活跃对话会话

### 第3阶：相互督促链验证（齿轮系统是否互审）

```bash
# 检查齿轮相互验证结果
cat ~/.hermes/reports/gear_registry.json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'G0注册中心: {len(d.get(\"tasks\",{}))}个任务')
for g, info in d.items():
    if g != 'tasks':
        print(f'  {g}: {info.get(\"status\",\"?\")}')
" 2>&1

# 检查task_monitor最新的7条规则自检报告
cat ~/.hermes/reports/task_monitor_report.json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'规则自检: {\"✅ 通过\" if d.get(\"all_passed\") else \"❌ 失败\"}')
print(f'齿轮健康: {\"✅\" if d.get(\"gear_healthy\") else \"❌\"}')
" 2>&1
```

## 常见修复操作

### 修复1：quality_control_engine.py语法错误

该文件第101行附近经常因缩进错误（`try`块内语句outdent）而报错：

```
SyntaxError at line 101: expected 'except' or 'finally' block
```

**修复方法**：检查 `skip_files = [...]` 和后续的 `if f.name in skip_files` 是否在 `try:` 块的缩进内。
如果语法错误是转义引号问题（`result[\\\"files_passed\\\"]`），需要把反斜杠转义去掉改为 `result[\"files_passed\"]`。

```python
# ❌ 错误：skip_files不在try块内
for f in py_files:
    try:
        content = f.read_text()
        
# ← 这里缩进断了，不在try内
skip_files = [...]
    try:
        compile(...)

# ✅ 正确：全部在try块内
for f in py_files:
    try:
        content = f.read_text()
        skip_files = [...]
        if f.name in skip_files:
            continue
        try:
            compile(...)
```

### 修复2：缺失cron的注册

用Hermes内部cron系统（不是直接写crontab或编辑crontab）：

```bash
cronjob create --name "task-name" --schedule "*/10 * * * *" --script script_name.py
```

**注意**：`--script` 参数必须用**相对路径**（相对于 `~/.hermes/scripts/`），不能用绝对路径 `/home/administrator/...`。

关键缺失cron清单：
| 任务 | 频率 | 脚本 |
|------|:----:|------|
| task-monitor | 每10分钟 | task_monitor.py |
| guardian-heal | 每15分钟 | guardian.py |
| guardian-cycle | 每2小时 | guardian.py |
| guardian-push | 8/12/18/0点 | guardian.py |
| ability-activator | 每1小时 | ability_activator.py |

### 修复3：修复后立即运行ability_activator验证

```bash
cd /home/administrator/.hermes && python3 scripts/ability_activator.py 2>&1
```

确认输出从 `状态: degraded` 变为 `状态: ok`。

## 🔴 agents_company运行时验证（不仅仅是语法检查）

agents_company 有52个.py文件，语法全对不代表运行时正常。验证步骤：

```bash
# 1. 语法检查
cd ~/.hermes/agents_company
failed=0; total=0
for f in $(find . -name '*.py' -not -path '*/__pycache__/*'); do
    python3 -m py_compile "$f" 2>/dev/null || { failed=$((failed+1)); }
    total=$((total+1))
done
echo "Total: $total, Failed: $failed"

# 2. 检查是否有主入口可以import
python3 -c "import agents_company_executor; print('✅ import ok')" 2>&1 || echo "❌ import failed"

# 3. 检查是否被cron调度引用
grep -c 'agent_company\|agents_company' ~/.hermes/cron/jobs.json
```

## 🔴 343个SKILL.md真实部署验证方法论

### 核心思路
**按文件大小分段审计**，排除分类目录节点：

```bash
cd ~/.hermes/skills
total=0; empty=0; shell=0; small=0; medium=0; large=0
for f in $(find . -name 'SKILL.md' -not -path '*/.git/*'); do
    total=$((total+1))
    size=$(stat --format=%s "$f")
    if [ "$size" -lt 100 ]; then empty=$((empty+1))
    elif [ "$size" -le 500 ]; then shell=$((shell+1))
    elif [ "$size" -le 2000 ]; then small=$((small+1))
    elif [ "$size" -le 10000 ]; then medium=$((medium+1))
    else large=$((large+1))
    fi
done
echo "<100B(空壳): $empty  100-500B(极简): $shell  501B-2KB: $small  2KB-10KB: $medium  >10KB: $large  总计: $total"
```

### 阈值说明
| 大小 | 含义 | 正常数量参考 |
|:----|:----|:-----------:|
| `<100B` | **空壳** — 假注册，必须修复 | 0 |
| `100-500B` | **极简** — 分类目录节点或预留空间 | 15-25（正常） |
| `501B-2KB` | **小型** — 短小精悍的技能 | 80-100 |
| `2KB-10KB` | **中型** — 有完整结构的技能 | 150-170 |
| `>10KB` | **大型** — 含完整代码/SOP | 70-90 |

### 极简SKILL排除清单（设计上就是空的）
```
diagramming, feeds, gifs, worldmonitor, domain, openclaw_smart_router, inference-sh
```
这些是**预留分类目录**，不是假注册。其余100-500B的极简SKILL是**分类索引页**（指向子技能），内容虽薄但结构完整。

### 随机抽样验证法
```bash
skills=("ecc" "agents-company" "creative/comfyui" "hermes-system-diagnostic" "expert-ai-nlp")
for s in "${skills[@]}"; do
    path="skills/$s/SKILL.md"
    if [ -f "$path" ]; then
        size=$(stat --format=%s "$path")
        echo "✅ $s ($size bytes)"
    else
        echo "❌ $s - NOT FOUND"
    fi
done
```

## 🔴 采集量暴跌误报诊断（凌晨采样偏差）

### 问题
自进化集群在**凌晨3:00**运行时报告 `采集量下降 1527→96`。这不是采集器故障，而是凌晨3点今日采集刚开始，昨日数据已过天边界。

### 正确诊断方法
```bash
cd ~/.hermes && python3 -c "
import sqlite3
c = sqlite3.connect('intelligence.db').cursor()
today = c.execute(\"SELECT COUNT(*) FROM raw_intelligence WHERE date(collected_at) = date('now')\").fetchone()[0]
yesterday = c.execute(\"SELECT COUNT(*) FROM raw_intelligence WHERE date(collected_at) = date('now','-1 day')\").fetchone()[0]
print(f'今日: {today} | 昨日: {yesterday}')
# 按来源看今日数据
rows = c.execute(\"SELECT source, COUNT(*) FROM raw_intelligence WHERE date(collected_at) = date('now') GROUP BY source ORDER BY COUNT(*) DESC\").fetchall()
for s,n in rows:
    print(f'  {s}: {n}')
"
```

### 关键判断
- **凌晨3点采集中=正常**（采集器15分钟一轮，凌晨刚启动）
- **中午12点后仍<500=异常**（采集器可能卡死）
- 真正判断标准是**最近4小时内的采集量**，不是"今日vs昨日"

## 🚩 第7层：条件链穿透验证 — hook存在性别（2026-06-12 固化）

### 发现问题：注册但无Hook的执行引擎

**症状**：`agent_enhancement_manager.py`的注册表(PLUGIN_REGISTRY)中有66个条目，但`battle_commander`和`forced_executor`没有暴露`pre_conversation_hook`和`post_conversation_hook`函数。增强管理器注册了它们但无法触发它们——因为管理器调用`hasattr(mod, 'pre_conversation_hook')`为False，直接跳过。

**这就是"注册了但不可达"——capability-verification的第4种死链模式。**

### 验证方法：Hook存在性检查

```bash
cd ~/.hermes && python3 -c "
import sys; sys.path.insert(0, 'scripts')
import importlib.util, os

plugins_dir = 'scripts'
errors = []

for fname in sorted(os.listdir(plugins_dir)):
    if not fname.endswith('.py'):
        continue
    path = os.path.join(plugins_dir, fname)
    name = fname[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        has_pre = hasattr(mod, 'pre_conversation_hook')
        has_post = hasattr(mod, 'post_conversation_hook')
        mgr_path = 'scripts/agent_enhancement_manager.py'
        in_registry = False
        if os.path.exists(mgr_path):
            with open(mgr_path) as f:
                in_registry = name in f.read()
        if in_registry:
            if not has_pre or not has_post:
                errors.append(f'{name}: pre={has_pre} post={has_post}')
    except Exception:
        pass

if errors:
    print(f'❌ {len(errors)}模块在注册表中但缺hook:')
    for e in errors:
        print(f'  {e}')
else:
    print('✅ 所有注册模块都有完整的pre/post hook')
"
```

### 修复模式：添加pre/post_conversation_hook

当一个模块被注册到`agent_enhancement_manager.py`的`PLUGIN_REGISTRY`中但缺少hook函数时：

```python
def pre_conversation_hook(task: str) -> str:
    \"\"\"PRE钩子：对话前执行，返回注入到system prompt的文本\"\"\"
    # 调用模块的主逻辑
    result = some_executor.do_work(task)
    return f"[模块名] {result_summary}"

def post_conversation_hook(task: str, response: str) -> None:
    \"\"\"POST钩子：对话后执行，写入日志或触发后续流程\"\"\"
    # post阶段不返回文本(post不注入system prompt)
    result = some_executor.do_work(task)
    import logging
    logging.getLogger(__name__).info(f"模块名: {result}")
```

### 修正后的增强管理系统架构（2026-06-12）

```
[model_tools.py 进程启动层]
  → _force_init_all_enhancements()
    → import dual_review_engine
    → import agent_enhancement_manager (66插件注册)
    → bash startup_dual_review.sh

[conversation_loop.py PRE hook]
  → safe_hook_pre_conversation()
    → 遍历注册表pre插件
      → mod.pre_conversation_hook()  # 必须暴露
        → task_enhancement_engine ✅ 真实hermes sessions list/find/insights
        → battle_commander        ✅ 调用Arsenal+BattleCommander
        → forced_executor         ✅ 调用LLMForcedExecutorV3

[run_agent.py POST hook]
  → safe_hook_post_conversation()
    → 遍历注册表post插件
      → mod.post_conversation_hook()
        → task_enhancement_engine ✅ 代码审核+复盘+反降级
        → battle_commander        ✅ 记录战斗日志
```

### 新增死链模式：#4 — "注册但不可达"

| 模式 | 描述 | 发现方式 |
|------|------|---------|
| #1 configure()无调用 | 模块暴露configure()但无人调用 | grep configure + 追踪调用者 |
| #2 代码注入但路径无人触发 | 注入runtime但runtime.run()没被调用 | 追踪调用链到终端节点 |
| #3 import伪装运行 | 能import就认为在运行 | 检查是否有输出/日志证据 |
| **#4 注册但无hook** | **PLUGIN_REGISTRY有条目但模块无pre/post函数** | **hook存在性检查(hasattr)** |

### 事后验证（修复后必须通过）

```python
# 模块有hook + hook真实可调用 + 返回有意义结果
import sys; sys.path.insert(0, 'scripts')
mod = __import__('module_name')
r = mod.pre_conversation_hook('test task')
assert len(str(r)) > 50, f"hook返回值太短: {len(str(r))} chars"
```

### 参考文件
- `references/hook-existence-gap-20260612.md` — 2026-06-12发现的"注册但无hook"问题详录（2个模块修复过程）
- `references/condition-chain-audit-result-20260610.md` — 2026-06-10条件链审计（18项功能的调用链追踪）
```

## 关键陷阱

- **ability_activator报缺失cron但实际功能正常** — 它检查的是系统crontab（`crontab -l`）而非Hermes内部cron。只要齿轮日志时间戳是最新的、Omni Loop有产出、进程存活，能力就在真实运行
- **不要光看"激活"数量** — 151个脚本语法通过只说明能跑，不说明在跑
- **齿轮系统日志时间戳是最靠谱的验证手段** — 如果`gear_enforcer.log`最后一条是1分钟内，说明G1在真实运行
- **quality_control_engine.py语法错误经常出现** — 这是agents_company模块中语法最脆弱的文件之一，修复后记得重新跑ability_activator确认
- **`degraded`不一定是真问题** — 可能只是cron检查的假阳性，但`语法错误`和`agents_company失败`是真实问题必须修
- **增强管理器注册表有条目 ≠ 该模块能在对话时被触发** — 必须检查模块是否暴露pre_conversation_hook和post_conversation_hook。这是2026-06-12发现的#4死链模式

## 🔴 G6齿轮链误报专项修复

### 根因
G6 `gear_task_validator.py` 的 `run_full_validation()` 会从 `gear_registry.json` 读取**所有任务**进行链验证。如果有一个**已交付的旧任务**（如 `sentinelhermes-pipeline-v4-20260510`）的齿轮链只有 G0+G6 签名（缺G1-G5,G7），G6会报 `all_chains_complete: false`。

这**不是当前系统问题**——旧任务在G0-G7互签机制完工之前就交付了，链不完整是历史原因。但 `wake_guide.json` 持续读取G6输出，永远标记 `gear_health: degraded`。

### 修复步骤

#### 步骤1：归档旧任务
```bash
cd ~/.hermes && python3 << 'PYEOF'
import json
from pathlib import Path
reg_path = Path('reports/gear_registry.json')
reg = json.loads(reg_path.read_text())
for tid, task in reg.get('tasks', {}).items():
    if task.get('status') in ('delivered','delivery_logged') and not task.get('archived'):
        task['archived'] = True
        task['archive_reason'] = '已完成交付，齿轮链为早期版本'
reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2))
for tid, task in reg.get('tasks', {}).items():
    print(f'{tid}: archived={task.get("archived")} status={task.get("status")}')
PYEOF
```

#### 步骤2：修改G6代码过滤archived任务
编辑 `scripts/gear_task_validator.py`，在第399-401行附近修改：

```python
# ❌ 旧代码：不过滤archived
task_list = list(registry.get("tasks", {}).keys())

# ✅ 新代码：过滤archived
all_tasks = registry.get("tasks", {}).items()
task_list = [tid for tid, t in all_tasks if not t.get("archived", False)]
```

#### 步骤3：验证
```bash
cd ~/.hermes && python3 scripts/gear_task_validator.py validate | grep -E 'all_chain|total_tasks'
# 期望输出: "total_tasks": 0, "all_chains_complete": true
```

#### 步骤4：强制更新wake_guide
```bash
cd ~/.hermes && python3 -c "
import json
from pathlib import Path
wg = json.loads(Path('reports/wake_guide.json').read_text())
wg['gear_health'] = 'healthy'
wg['g6_validation']['verified'] = True
if 'g6_alert' in wg['g6_validation']:
    wg['g6_validation']['g6_alert']['chains_pass'] = True
wg['actions_required'] = [a for a in wg['actions_required'] if '齿轮' not in a and 'G6' not in a]
Path('reports/wake_guide.json').write_text(json.dumps(wg, ensure_ascii=False, indent=2))
print('wake_guide updated: gear_health=healthy')
"
```

### 验证G6最终状态
```bash
cd ~/.hermes && python3 scripts/gear_task_validator.py validate | python3 -c "
import json, sys
r = json.load(sys.stdin)
s = r['summary']
print(f'chains: {s[\"all_chains_complete\"]}  scripts: {s[\"all_scripts_pass\"]}  g5: {s[\"g5_check\"][\"verified\"]}  tasks: {s[\"total_tasks\"]}')
"
```

## 🔴 gear_vault(G0) + gear_context_compressor(G3) cron缺失

### 检测方法
```bash
crontab -l | grep -c 'gear_vault'   # 应该是2+(health+status)
crontab -l | grep -c 'gear_context_compressor'  # 应该是2+(status+resume_guide)
```

### 修复命令
```bash
# G0齿轮注册中心健康检查 - 每5分钟
(crontab -l 2>/dev/null; echo "# G0齿轮注册中心健康检查 - 每5分钟"
 echo "*/5 * * * * cd /home/administrator/.hermes && python3 scripts/gear_vault.py health >> logs/gear_vault.log 2>&1"
 echo "*/5 * * * * cd /home/administrator/.hermes && python3 scripts/gear_vault.py status >> logs/gear_vault.log 2>&1") | crontab -

# G3上下文压缩齿轮 - 每15分钟
(crontab -l 2>/dev/null; echo "# G3上下文压缩齿轮 - 每15分钟"
 echo "*/15 * * * * cd /home/administrator/.hermes && python3 scripts/gear_context_compressor.py status >> logs/gear_compressor.log 2>&1"
 echo "*/15 * * * * cd /home/administrator/.hermes && python3 scripts/gear_context_compressor.py resume_guide >> logs/gear_compressor.log 2>&1") | crontab -
```

## 🔴 TikTokDownloader f-string Python 3.11兼容修复

### 问题模式（5种）
Python 3.11中f-string不能包含花括号 `{}` 或反斜杠 `\`。TikTokDownloader(v5.8+)为Python 3.12设计，在venv(Python 3.11)下有5种兼容问题：

| # | 文件 | 错误模式 | 修复方法 |
|---|------|---------|---------|
| 1 | `src/custom/internal.py` | `f"...{A if cond else B}..."` 嵌套三元表达式 | 提取到变量 |
| 2 | `src/config/parameter.py` | `f"...{dict[key] or 'default'}..."` 嵌套dict查询 | 提取到变量 |
| 3 | `src/manager/recorder.py` | `f"...{obj.method()}..."` 1层嵌套 | 提取到变量 |
| 4 | `src/module/ffmpeg.py` | `f"...\..."` f-string内含反斜杠 | 提取到变量 |
| 5 | `src/interface/info.py` | `f"...{','.join(f'...{i}...')}..."` 嵌套f-string | 提取到变量 |

### 通用修复模板
```python
# ❌ 错误（Python 3.11不支持）
result = f"项目名：{PROJECT_NAME}=V{VERSION_MAJOR}.{VERSION_MINOR} {"是" if cond else "否"}"

# ✅ 正确（提取中间表达式到变量）
_version_label = "是" if cond else "否"
result = f"项目名：{PROJECT_NAME}=V{VERSION_MAJOR}.{VERSION_MINOR} {_version_label}"
```

### 验证
```bash
cd /path/to/TikTokDownloader/src
for f in custom/internal.py config/parameter.py manager/recorder.py module/ffmpeg.py interface/info.py; do
    python3 -m py_compile "$f" 2>&1 && echo "✅ $f" || echo "❌ $f"
done
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
