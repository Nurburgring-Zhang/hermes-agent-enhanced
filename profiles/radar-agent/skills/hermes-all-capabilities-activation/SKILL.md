---
name: hermes-all-capabilities-activation
description: 全能力盘点+采集管道升级+新工具集成的工作流。扫描所有skills/scripts/模块，安装缺失采集工具，构建全能力聚合采集器，修复运行时问题，注册cron
version: 1.0.0
category: hermes
---

# Hermes 全能力激活 + 采集管道升级工作流

## 触发条件
当格林主人要求：
- "激活全部能力"
- "全能力扫描"
- "采集修复"
- "安装新工具/skills"
- "工具不存在就安装部署"

## 步骤

### Step 1: 全能力盘点
```bash
# 统计所有资源
find ~/.hermes/skills -name "SKILL.md" | wc -l      # skills数
ls ~/.hermes/scripts/*.py | wc -l                     # scripts数
ls ~/.hermes/evolution_v3/*.py | wc -l                # 进化模块
ls ~/.hermes/agents_company/*.py | wc -l              # agents模块
crontab -l | grep -c "^[0-9*]"                        # 系统cron
```

### Step 2: 检查ability_activator状态
```bash
cd ~/.hermes && python3 scripts/ability_activator.py
```
重点关注: `状态: ok` vs `状态: degraded`
- degraded → 检查 modules 下的 failed/missing 字段

### Step 3: 检查齿轮系统
```bash
tail -5 ~/.hermes/logs/gear_enforcer.log
tail -5 ~/.hermes/logs/gear_master.log
tail -5 ~/.hermes/logs/gear_task_driver.log
```

### Step 4: 安装采集工具（关键）
```bash
# 创建采集器目录
mkdir -p ~/.hermes/scripts/collectors

# 微信公众号采集 (WECHAT-MP-MCP)
cd ~/.hermes/scripts/collectors
git clone https://github.com/fdslk/WECHAT-MP-MCP.git wechat-mp-mcp
# 安装到Hermes venv（关键！不要用系统pip）
/home/administrator/.hermes/hermes-agent/venv/bin/pip3 install -e wechat-mp-mcp/

# 小红书采集 (xiaohongshu-skill)
git clone https://github.com/DeliciousBuding/xiaohongshu-skill.git xiaohongshu-skill

# 多平台爬虫
git clone https://github.com/wzk1015/Scraper.git scraper-multi

# 小红书API库
/home/administrator/.hermes/hermes-agent/venv/bin/pip3 install xhs

# 通用网页提取
/home/administrator/.hermes/hermes-agent/venv/bin/pip3 install trafilatura newspaper3k readability-lxml feedparser
```

**⚠️ 关键陷阱**: Hermes的venv在 `/home/administrator/.hermes/hermes-agent/venv/`，系统pip可能被PEP668限制。必须用 `venv/bin/pip3` 安装。

### Step 5: 构建全能力聚合采集器
创建 `~/.hermes/scripts/hermes_ultimate_collector.py`，整合以下能力并行执行：

| 能力 | 函数 | 依赖 | 类型 |
|------|------|------|------|
| unified_collector_v5 (35+平台) | `run_unified_collector()` | subprocess调用 | HTTP+API |
| 微信MCP公众号 | `collect_wechat_mp()` | wechat_mp_mcp | 登录态API |
| 小红书 | `collect_xiaohongshu()` | xhs库/xiaohongshu-skill | API+Playwright |
| RSS增强 | `collect_rss_feeds()` | feedparser | RSS |
| Playwright浏览器 | `collect_via_browser()` | playwright | 浏览器自动化 |
| 通用网页提取 | `collect_web_article()` | trafilatura/readability | HTML提取 |

**关键实现细节（含真实踩坑记录）：**\n- 使用`ThreadPoolExecutor(max_workers=4)`并行跑前4个能力\n- **shebang必须用venv的Python**（`#!/home/administrator/.hermes/hermes-agent/venv/bin/python3`），否则找不到xhs/wechat_mp_mcp等库\n- unified_v5用subprocess调（不是import），否则35个platform的import会冲突\n- subprocess的timeout要给300s（unified_v5跑全平台需要时间）\n- RSS用feedparser直接读，速度快\n- Playwright eval的JS要用 `() => { ... }` 箭头函数+forEach（不能用 `.slice()` 链式调用）\n\n**⚠️ 实际踩坑记录（2026-05-24验证）：**\n1. **xhs库class名**：`from xhs import XhsClient`（不是Client）。方法名`get_note_by_keyword()`（不是search_note）。需要有效cookie，否则返回None。\n2. **微信MCP类名**：`WeixinClient`（不是WeChatClient）。没有Storage类，用`from wechat_mp_mcp.auth import load_auth`获取已保存的登录态。路径要加`src/`。\n3. **小红书skill相对引用**：`from .client import ...`需要在项目根目录下import。修复方法：`for f in *.py; do sed -i 's/from \\.client/from client/g' \"$f\"; done`。搜索函数是`search.search(kw)`（不是search_notes）。\n4. **unified_v5快速模式**：别用`--collect --parallel 8`（跑35个平台超时），改为单独跑10个核心平台`--platform platform_name`，每个给60s timeout。总耗时从超时降到20s。\n5. **delegate_task子Agent报错**：`web_search`工具在Hermes中可能不存在，用`interne搜索`或`AnySearch`替代。子Agent搜微信方案时记得给`toolsets=["web"]`权限。\n6. **system vs venv pip**：系统pip被PEP668限制，必须用`/home/administrator/.hermes/hermes-agent/venv/bin/pip3`安装包。

### Step 6: 注册cron + 集成到Omni Loop
```bash
# 注册独立cron（每15分钟全能力采集）
cronjob action=create name="ultimate-collector" schedule="*/15 * * * *" script="hermes_ultimate_collector.py"

# 替换Omni Loop的step1
# 将 omni_loop.py 中的 unified_collector_v5.py --collect 替换为 hermes_ultimate_collector.py --all
# 注意：timeout要从180s加到300s
```

### Step 7: 修复G6齿轮链验证
如果wake_guide显示"齿轮系统验证失败"，检查 `gear_task_validator.py`：
- 常见bug：第432行 `r["verification"]["chain_complete"]` 在 `verify_gear_chain` 返回early return（`{"status":"failed","reason":...}`）时没有 `chain_complete` 键
- 修复：改用 `.get("verification",{}).get("chain_complete", False)`

### Step 8: 注册新技能
```bash
# 每个新安装的工具/采集器注册为正式skill
skill_manage action=create name=wechat-mp-collector ...
skill_manage action=create name=xiaohongshu-collector ...
skill_manage action=create name=ultimate-collector ...
```

## 已知问题 & 故障排查

### 1. xhs库 'NoneType' object is not callable
- 原因：cookie已过期
- 解决：需要重新扫码登录。xhs库的 `XhsClient()` 默认用保存的cookie，过期后会返回None

### 2. wechat_mp_mcp ImportError
- 原因：shebang用了系统python3（`#!/usr/bin/env python3`）而不是venv的python3
- 解决：改成 `#!/home/administrator/.hermes/hermes-agent/venv/bin/python3`
- 注意：也要加 `sys.path.insert(0, "collectors/wechat-mp-mcp/src")`

### 3. xiaohongshu-skill 'attempted relative import'
- 原因：search.py内部用了相对import（`from .client import ...`），直接import会失败
- 解决：需要从项目根目录启动，或者patch去掉相对import

### 4. Playwright `TypeError: ...slice is not a function`
- 原因：`document.querySelectorAll()` 返回NodeList，不是Array，没有`.slice()`方法
- 解决：用`Array.from()`或用`forEach()`自己构建数组

### 5. pip install超时
- feedparser/trafilatura/newspaper3k这些库依赖比较多，网络可能超时
- 但检查发现这些库可能实际上**已经在venv里装好了**（`/home/administrator/.hermes/hermes-agent/venv/bin/pip3 list | grep xxx`）
- 策略：先`pip list`确认已有，不需要重装

### 6. xiaohongshu-skill搜索返回0篇（但有浏览器输出"检测到登录弹窗"）
- 原因：小红书对无头浏览器有反爬，虽然会自动移除登录弹窗，但搜索结果DOM可能被拦截
- 策略：尝试用`xhs`库API方案（需有效cookie），或者手动保存Cookie
- 好消息：Playwright会自动保存Cookie到`/home/administrator/.xiaohongshu/cookies.json`

## 🔴 关键避坑（2026-05-24实战更新）

### 1. 数据库路径问题 — 最高频错误！
系统存在**3个** intelligence.db：
- `/home/administrator/.hermes/intelligence.db` — ✅ **真库！23398+篇数据**
- `/home/administrator/.hermes/scripts/intelligence.db` — ❌ 空库（新旧脚本误用）
- `/home/administrator/.hermes/outputs/intelligence.db` — ❌ 可能无raw_intelligence表

**规则**：所有采集器写入前必须确认 DB_PATH 指向 `~/.hermes/intelligence.db`

```python
# 正确做法
DB_PATH = "/home/administrator/.hermes/intelligence.db"
# 不要用相对路径或 Path.home() / ".hermes" / "intelligence.db" 的变体
```

### 2. 齿轮守护进程淹没输出
系统有 `gear_enforcer`（每1分钟）、`task_monitor`（每10分钟）、`ability_activator`（每小时）等后台进程。**任何后台运行的新采集器输出都会被这些进程的日志淹没。**

**解决方案**：采集器写入独立日志文件：
```python
import logging
log_file = f"mega_collector_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(filename=log_file, level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger('mega_collector')
def log(msg): print(msg); logger.info(msg)
```

### 3. GitHub仓库源码布局不一致
不同采集器的Python源码位置：

| 仓库 | 源码位置 | import方式 |
|------|----------|-----------|
| wechat-mp-mcp | `src/wechat_mp_mcp/` | `pip install -e .` 装到venv |
| xiaohongshu-skill | `scripts/` | `sys.path.insert(0, "scripts/")` |
| TikTokDownloader(DouK) | `src/` (包名DouK-Downloader) | `pip install -e .` 需Python 3.12+ |
| MediaCrawler | 根目录下`main.py`+子模块 | `pip install -e .` 装到venv |
| scraper-multi | 根目录`wx_scraper.py`等 | `sys.path.insert(0, ".")` |

**规则**：先 `ls` 看结构，再决定是 `pip install -e` 还是 `sys.path.insert`

### 4. PEP668 — 永不用系统pip
Ubuntu 24.04 的 Python 3.12 系统pip被PEP668限制。Hermes venv在：
```bash
/home/administrator/.hermes/hermes-agent/venv/bin/pip3  # ✅ 用这个
/home/administrator/.hermes/hermes-agent/venv/bin/python3  # ✅ 用这个跑脚本
```

### 5. Python版本兼容性
- Hermes venv: Python 3.11.15
- TikTokDownloader(DouK v5.8+): 需要 Python 3.12+
- 系统自带 Python 3.12: `/usr/bin/python3.12`

**解决方案**：为Python 3.12依赖的项目创建独立venv：
```bash
python3.12 -m venv /path/to/project/venv312
/path/to/project/venv312/bin/pip3 install -e .
```

### 6. 验证真实运行状态 — 数据库是唯一真理
不要只看 import 成功就以为能力在跑。**真实验证方法：**
```sql
-- 查数据库总篇数
SELECT COUNT(*) FROM raw_intelligence;
-- 查今日各来源新增
SELECT source, COUNT(*) FROM raw_intelligence WHERE date(collected_at)=date('now') GROUP BY source ORDER BY 2 DESC;
-- 查最新入库时间
SELECT MAX(collected_at) FROM raw_intelligence;
```

如果今日新增在持续增长（如CSDN半小时+800篇），说明unified_v5的cron在正常工作。
如果某个来源永远为0，说明该采集器有问题（需要登录/反爬/IP被封）。

### 7. 系统已有长期运行进程（不要重复启动）
| 进程 | 启动时间 | 运行时长 | 功能 |
|------|----------|----------|------|
| eternal_loop.py | May 11 | 13天+ | 全能循环 |
| Playwright Chrome | May 16 | 8天+ | 浏览器采集引擎 |
| hermes main agent | May 21 | 3天+ | 主代理 |
| guardian.py heal | cron每15min | 持续 | 守护神自愈 |
| guardian.py cycle | cron每2h | 持续 | 采集清洗 |
| guardian.py push | cron 8/12/18/0 | 持续 | 推送 |

**不要**额外启动重复的守护进程，否则会有资源竞争和日志混乱。

### 7b. Full system audit — 5-part systematic audit pattern
When asked to audit ALL capabilities (scripts + skills + evolution_v3 + agents_company + cron), use this method:

#### Step 1: Count and syntax-check ALL 5 components
```bash
# 5-part audit: scripts | skills | evolution_v3 | agents_company | cron

# === PART 1: SCRIPTS (use find, not ls — scripts/ has subdirectories) ===
find ~/.hermes/scripts -name '*.py' -not -path '*/__pycache__/*' -not -path '*/.git/*' | wc -l
# Then syntax-check ALL:
for f in $(find ~/.hermes/scripts -name '*.py' -not -path '*/__pycache__/*' -not -path '*/.git/*'); do
  python3 -m py_compile "$f" 2>/dev/null || echo "FAIL: $f"
done

# === PART 2: SKILLS ===
find ~/.hermes/skills -name 'SKILL.md' -not -path '*/.git/*' | wc -l
# Note: not all SKILL.md files auto-register to skills_list
# Look for blank directories (feeds/, gifs/, worldmonitor/ etc) — they have SKILL.md but are placeholder stubs

# === PART 3: EVOLUTION_V3 ===
ls ~/.hermes/evolution_v3/*.py | wc -l
for f in ~/.hermes/evolution_v3/*.py; do
  python3 -m py_compile "$f" 2>/dev/null || echo "FAIL: $f"
done

# === PART 4: AGENTS_COMPANY ===
find ~/.hermes/agents_company -name '*.py' -not -path '*/__pycache__/*' | wc -l
for f in ~/.hermes/agents_company/*.py; do
  python3 -m py_compile "$f" 2>/dev/null || echo "FAIL: $f"
done

# === PART 5: CRON (BOTH system + internal) ===
# System crontab:
crontab -l | grep -v "^#" | grep -v "^$" | wc -l
# Internal cron jobs:
python3 -c "
import json
with open('/home/administrator/.hermes/cron/jobs.json') as f:
    raw = f.read()
data = json.loads(raw)
jobs = data.get('jobs', json.loads(raw) if isinstance(json.loads(raw), list) else list(json.loads(raw).values()))
total = len(jobs); enabled = sum(1 for j in jobs if j.get('enabled'))
print(f'Total: {total}, Enabled: {enabled}')
"
```

#### Step 2: Script & cron cross-reference — find unactivated capabilities
This is the KEY audit step — scripts that exist but aren't referenced by ANY cron:

```bash
cd ~/.hermes/scripts
echo "=== SCRIPTS NOT REFERENCED BY ANY CRON ==="
for f in *.py; do
  base=$(basename "$f" .py)
  in_internal=$(grep -c "$base" ~/.hermes/cron/jobs.json 2>/dev/null)
  in_system=$(crontab -l 2>/dev/null | grep -c "$base")
  if [ "$in_internal" -eq 0 ] && [ "$in_system" -eq 0 ]; then
    lines=$(wc -l < "$f")
    echo "UNREFERENCED: $f ($lines lines)"
  fi
done
```

**Critical filter**: ignore `<100` line scripts (test helpers, debug tools). Focus on `>200` line scripts that ARE core capabilities (runner engines, isolation layers, enhanced collectors).

#### Step 3: Evolution_v3 reference audit
```bash
cd ~/.hermes
for f in evolution_v3/*.py; do
  base=$(basename "$f" .py)
  refs=$(grep -r "$base" cron/jobs.json evolution_v3/ 2>/dev/null | grep -v '.pyc' | grep -v '__pycache__' | wc -l)
  if [ "$refs" -eq 0 ]; then
    echo "NOT_REFERENCED: $base"
  fi
done
```
Files with 0 references are test files — safe to ignore.

#### Step 4: Gear cron cross-check
The 7 gear scripts (G0-G6) MUST be in system crontab (not just internal cron), because they power the wake/resume/guardian layers:

```bash
for g in gear_enforcer gear_master gear_task_driver gear_vault gear_context_compressor gear_task_validator hermes_super_guardian; do
  count=$(crontab -l | grep -c "$g")
  echo "$g: cron_entries=$count"
done
```

**Known gaps found in practice (2026-05-24):**
- `gear_vault.py` (G0 gear registry) — was missing from ALL crons. Fix: `*/5 * * * * cd ~/.hermes && python3 scripts/gear_vault.py health >> logs/gear_vault.log 2>&1`
- `gear_context_compressor.py` (G3 context compression) — was missing from ALL crons. Fix: `*/15 * * * * cd ~/.hermes && python3 scripts/gear_context_compressor.py status >> logs/gear_compressor.log 2>&1`

#### Step 5: TikTokDownloader f-string syntax errors (recurring pattern)
TikTokDownloader (DouK v5.8+) uses Python 3.12+ features that break on Python 3.11. The SPECIFIC pattern is:

```
# ❌ FAILS on Python 3.11:
PROJECT_NAME = f"DouK-{VERSION_MAJOR}.{VERSION_MINOR} {"Beta" if BETA else "Stable"}"
# ✅ FIX: extract the nested expression to a variable:
_version_label = "Beta" if BETA else "Stable"
PROJECT_NAME = f"DouK-{VERSION_MAJOR}.{VERSION_MINOR} {_version_label}"
```

**5 affected files in `collectors/TikTokDownloader/src/`:**
| File | Line | Error | Fix |
|------|:----:|-------|-----|
| `custom/internal.py` | 9 | f-string with nested `{...}` ternary | Extract to var |
| `config/parameter.py` | 349 | f-string with nested `{...}` dict lookup | Extract to var |
| `manager/recorder.py` | 87 | f-string with nested `{self.path.resolve()}` | Extract to var |
| `module/ffmpeg.py` | 49 | f-string with `\"` backslash | Extract to var |
| `interface/info.py` | 71 | f-string nesting f-string | Extract to var |

This pattern is safe to fix by extracting to variables — it changes zero runtime behavior.

#### Step 6: Verify real database growth (not just import success)
```sql
SELECT COUNT(*) FROM raw_intelligence;
SELECT source, COUNT(*) FROM raw_intelligence WHERE date(collected_at)=date('now') GROUP BY source ORDER BY 2 DESC;
SELECT MAX(collected_at) FROM raw_intelligence;
```

#### Common failure pattern in agents_company scripts (OpenClaw migration artifact)
Multiple files have corrupted shebang lines:
```
#!/usr/bin/env python3
!/usr/bin/env python3"""           # ← THIS LINE is wrong
#!/usr/bin/env python3
"""
```
Fix: delete the duplicate corrupt line. Files affected: rebuild_company.py, run_automatic.py, sync_employees.py

#### Another failure pattern: docstring → SQL code boundary corruption
In `unified_gateway.py`: a class docstring (triple-quoted) didn't close properly, so SQL CREATE TABLE code ended up inside the docstring. Fix: restructure the class boundary, move `conn.execute(...)` into `_init_database()` method.

#### Skill-to-script mismatch (harmless reference pattern)
Some ML skills (segment-anything, vllm, gguf, modal, trl-fine-tuning, etc.) reference scripts like `export_onnx_model.py` or `hello_gpu.py` that don't exist under `~/.hermes/scripts/`. These are **third-party example/documentation references** — NOT Hermes capabilities. Safe to ignore.

### 8. ECC (Ensemble Coding Companion) Installation Pattern (189k⭐)
```bash
# When git clone fails due to TLS issues (common with GitHub from some networks):
# Method 1: try multiple clone attempts
for i in 1 2 3; do git clone --depth 1 https://github.com/affaan-m/ECC.git && break; sleep 5; done

# Method 2: use API tarball (fallback)
curl -sL https://api.github.com/repos/affaan-m/ECC/tarball | tar xz --transform='s|[^/]*|ECC|'

# Install dependencies
cd ECC && npm install --production

# Register as skill
mkdir -p ~/.hermes/skills/ecc
cat > ~/.hermes/skills/ecc/SKILL.md << 'EOF'
---
name: ecc
description: ECC Agent性能优化系统(189k Stars)。软件开发优先能力，多Agent组合使用。
category: software-development
---
# ECC
Agent harness optimization: skills/memory/security/research-first dev.
Composable with agents-company/autonomous-systems.
EOF

# Register cron for auto-optimization (every 4 hours)
cronjob action=create name=ecc-optimize-daemon schedule="0 */4 * * *" prompt="ECC optimize cycle"

# Verify
skill_view name=ecc  # should show readiness_status: available
```

### 9. Database schema awareness — critical for collector scripts
The REAL intelligence.db schema (at `~/.hermes/intelligence.db`) has NO `summary` or `language` columns:
```
id|title|content|url|source|platform|author|author_id|category|tags|hot_score|view_count|like_count|collect_count|comment_count|share_count|published_at|collected_at|raw_data|url_hash|source_type|category_tags
```
**Rule**: Always use `PRAGMA table_info(raw_intelligence)` before writing INSERT statements in collectors. Don't assume schema.

## 最终状态检查清单
- [ ] `ability_activator.py` 输出"状态: ok"
- [ ] `task_monitor.py` 输出"全部通过"
- [ ] `gear_enforcer.py` 输出"全部通过"
- [ ] ultimate_collector运行后DB有新数据：`SELECT source, COUNT(*) FROM raw_intelligence WHERE date(collected_at)=date('now','localtime') GROUP BY source`
- [ ] 数据源数≥22个（基础16个 + 新增RSS 4个 + 浏览器2个）
- [ ] 新注册的skills在 `~/.hermes/skills/` 下有SKILL.md

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
