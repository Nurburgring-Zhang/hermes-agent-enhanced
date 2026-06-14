---
name: unified-collection-pipeline
description: Hermes unified collection + push pipeline skill — discover, fix, build, verify
triggers:
  - "采集系统大统一"
  - "推送系统大统一"
  - "推送重复"
  - "推送旧闻"
  - "重复推送"
  - "推送筛选"
  - "整合采集"
  - "统一情报系统"
---

# Unified Collection + Push Pipeline Skill

## When to use

## 触发条件
- 用户提及情报采集、推送、评分时
- 需要配置或调试采集管道时
- 检查情报系统运行状态时

When the user asks to:
- Expand, consolidate, or audit the intelligence collection system
- Add new platforms/sources to the collector
- Fix silent/dead collectors
- Debug RSS or API collection failures
- Optimize collector cron frequency

## ⚠️ First Thing: Read the Current State

```bash
# Read current collector code and registry
wc -l ~/.hermes/scripts/unified_collector_v5.py
grep -c "COLLECTORS\[" ~/.hermes/scripts/unified_collector_v5.py

# Check DB for last-run status per platform
python3 -c "
import sqlite3
db = sqlite3.connect('intelligence.db')
rows = db.execute('SELECT platform, COUNT(*), MAX(collected_at) FROM raw_intelligence GROUP BY platform ORDER BY MAX(collected_at) DESC').fetchall()
for p,c,l in rows: print(f'{p:25s}  {c:5d}条  {str(l)[:19]}')
db.close()
"

# Check cron
crontab -l | grep -iE 'collect|pipeline|unified_collector'

# Check collector_preferences.json for user interest directions
cat ~/.hermes/reports/collector_preferences.json
```

## ⚠️ 第一轮必须全面复盘 — 不要跳过

**格林主人最高指令**: 接到任何采集扩增/修复任务后，必须先系统排查：
1. 搜索历史会话中所有与采集相关的工作（`session_search` with keywords）
2. 读取当前数据库状态（`SELECT platform, COUNT(*), MAX(collected_at) ...`）
3. 读取当前 `collector_preferences.json` 确认偏好方向
4. 读取 `unified_collector_v5.py` 的 `COLLECTORS` 注册表
5. 检查cron（`crontab -l | grep -iE 'collect|pipeline'`）

**禁止**: 凭记忆或旧结论就开始改代码。

## 扩增计划格式 — 按偏好方向规划而不是按平台

当用户要求"扩大采集覆盖范围"时，按格林主人的偏好方向（P0/P1/P2）来规划，而不是列出一堆平台名：

```markdown
### 缺失的偏好方向
- **摄影/相机** — 无专属采集源 → 需加蜂鸟网/SonyRumors
- **格斗/UFC** — 无格斗新闻源 → 需加Sherdog/BloodyElbow
- **芯片/半导体** — 仅有关键词命中 → 需加SemEngineering/Tom's Hardware
- **旅游** — 无旅游攻略源 → 穷游/马蜂窝

### 恢复停摆平台
- GitHub Trending（search API失效）
- HuggingFace/掘金/虎嗅等（api/rss不通）
```

## 工作流程要求（格林主人指令2026-05-28固化）

每次接到采集扩展/修复/审计任务，必须执行以下 **4阶段复盘流程**：

### 阶段0: 全系统健康雷达扫描（重要！不要只盯着一个子系统）

当格林主人说"回顾历史，全面复盘，汇报进度，深度思考，全盘规划，全部能力，组合调用，继续执行，进度把控"这种全面指令时，**不要只回答当前问题**。必须做多系统并行扫描：

```bash
# 1. 记忆+技能清查
# 2. cronjob列表（crontab -l + cronjob list）
# 3. 采集系统（--stats + DB各平台统计）
# 4. 推送系统（检查cron是否存在 + --draft验证）
# 5. AI评分队列（检查待处理量）
# 6. 齿轮系统（wake_guide.json + gear_checkpoint.json）
# 7. 数据库综合状态（各表总量+今日量+标签分布）
# 8. 生产级引擎（production_loop/状态）
# 9. 自进化集群（log文件检查）
# 10. 上下文压缩系统（reports/context_* 检查）
```

**关键发现模式**：
- **cron缺失**：查看 `crontab -l | grep -iE 'push|score'` → 如果推送/评分cron不存在，这就是P0问题
- **评分积压**：`SELECT COUNT(*) FROM cleaned_intelligence WHERE ai_score_total IS NULL OR ai_score_total = 0` → 如果>1000条，必须增加评分cron
- **cron冗余**：`cronjob list` 显示的job数量与实际 `crontab -l` 数量相差过大 → 需要审计

### 阶段1: 全面回顾 (Recap)
- 搜索历史会话中所有与采集相关的前置工作和已解决问题
- 确认本次任务与历史上下文的关系（是新增、修复还是扩展？）
- 输出：明确的起点状态报告

### 阶段2: 深度根因分析 (Root Cause Analysis)
- 对于每个问题，追踪到代码级根因（不止"不工作了"，要解释*为什么*）
- 检查：数据库实际数据 vs 代码期望的格式是否一致
- 检查：网络环境限制（国内WSL）与采集器假设的差异
- 输出：每个问题的根因+修复方案

### 阶段3: 执行修复并验证 (Execute + Verify)
- 每步修复后立即验证：改了什么、怎么改、效果如何
- 用数据库查询确认数据确实变化了（`SELECT COUNT(*)` + `SELECT MAX(collected_at)`）
- 用 `todo` 工具跟踪所有子任务
- 输出：每个验证步骤的证据（SQL结果、日志片段）

### 阶段4: 汇报总结 (Report)
- 清晰的变更清单（改了哪些文件、哪些行）
- 验证结果表（平台|数据量|状态）
- 已知限制（这个会话解决了什么、没解决什么）
- 后续待办

### 汇报格式要求（格林主人偏好）
1. 使用Markdown表格（非纯文字堆叠）
2. 每个子系统的状态分3档：🟢正常 / 🔵有数据但偏弱 / 🔴有问题
3. 关键发现用 **加粗** + 数值证据
4. 如果找到多个问题，标 P0/P1/P2 优先级
5. 修复后必须给出**可验证的证据**（不是"已修好"，而是SQL返回的count值）
6. **绝对禁止只答一个问题忽略其他** — 当被问系统整体状态时，必须覆盖所有子系统，不能只盯着当前正在改的那个。格林主人曾因此发火("我问推送为什么不跑，你答采集扩增—必须精准对应问题，跟踪所有活跃任务")

## 核心架构（截至2026-05-28）

### 单一入口
所有采集通过 `scripts/unified_collector_v5.py` 统一管理。
`COLLECTORS` 字典注册了48个采集器，每个包含 `(函数, priority, timeout_seconds)`。

```python
COLLECTORS = {
    'source_name': (collect_function, priority_1to10, timeout_seconds),
    ...
}
```

- priority < 5 且 is_worth_collecting() 随机跳过50% → 低优平台
- priority >= 5 每一轮都跑
- 并行: `--parallel N` 控制并发线程数

### Cron调度（2026-05-28配置）
```cron
# 正常采集: 每3小时 (8并发)
0 */3 * * * cd ~/.hermes && python3 scripts/unified_collector_v5.py --collect --parallel 8 >> logs/pipeline_v3.log 2>&1

# 加重采集: 每6小时 (14并发，全量跑)
30 */6 * * * cd ~/.hermes && python3 scripts/unified_collector_v5.py --collect --parallel 14 >> logs/pipeline_v3.log 2>&1
```

### 三层过滤
采集器 → `collector_preferences.json`（P0/P1/P2偏好方向）→ `spam_filter_keywords`（黑名单）→ 内容质量预筛 → 入库

## 摸底阶段 (Discovery) — Before modifying

### 1. 平台可用性测试
```python
def test_fetch(url, name, timeout=8):
    """Quick test if a URL/RSS endpoint is reachable from this environment"""
    import urllib.request, re
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read().decode('utf-8', errors='replace')
        if '<rss' in data or '<feed' in data:
            n = len(re.findall(r'<item>|<entry>', data))
            return f'✅ RSS可用 ({n}条)'
        return f'⚠️ 有返回({len(data)}字符) 非RSS'
    except Exception as e:
        return f'❌ {e}'
```

### 2. 国内网络限制已知清单 (国内WSL环境)
| 类型 | 预期结果 |
|------|---------|
| 国内中文站RSS/API | ✅ 通常可用 |
| 海外RSS (Sherdog/BloodyElbow/PetaPixel/SemiEngineering) | ⚠️ 间歇性不可用，超时或403 |
| GitHub.com HTML | ⚠️ 有时限流，需备用API |
| 百度搜索 (s.weibo.com, baidu.com/s?wd=) | ❌ 无cookie时被反爬 |
| 境外API (Reddit/X/TikTok) | ❌ 大部分Network is unreachable |

### 3. 常用JSON/API端点测试方法
```python
def test_api(url, name):
    import json, urllib.request
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=8)
        data = json.loads(resp.read())
        if isinstance(data, list): return f'✅ [{name}] list({len(data)})'
        if isinstance(data, dict): return f'✅ [{name}] dict({len(data)} keys)'
    except Exception as e: return f'❌ [{name}] {e}'
```

## 新增平台的策略（国内网络约束下）

### 策略A: RSS/API直连（最佳）
- 先用 `test_fetch` 验证端点可用
- 只部署验证通过的RSS
- 已验证可用的国内RSS: IT之家、OSChina、InfoQ、TechMeme、FreeBuf、TMTPost、虎嗅(有时限流)、InfoQ、博客园

### 策略B: 数据库关键匹配（国内网络兜底）
当海外RSS不通时，从已有数据中按关键词匹配用户的偏好方向:
```python
rows = db.execute("""
  SELECT title, url, published_at FROM raw_intelligence
  WHERE (title LIKE '%关键词%' OR title LIKE '%关键词2%')
    AND platform NOT LIKE 'prefix_%'
  ORDER BY collected_at DESC LIMIT 15
""").fetchall()
```
此模式产出 `platform='xxx_match'` 类型的数据。
⚠️ 注意：这些数据之前已经入库（url_hash重复），所以匹配不会产生新条目，但会通过 `insert_batch` 重新标记标签。
更实用的做法是仅将匹配结果用于**内容标签和推送候选**，不依赖新增平台计数。

### 策略D: 社区论坛HTML爬取（国内格斗/体育信息源的workaround）
当RSS源完全不可用（国内门户已废弃RSS），且匹配法不够时，从社区论坛HTML页面按关键词提取内容：

```python
# 虎扑格斗专区示例
for src_url in ["https://bbs.hupu.com/mma", "https://bbs.hupu.com/boxing"]:
    import urllib.request, re
    req = urllib.request.Request(src_url, headers={"User-Agent":"Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=8)
    html = resp.read().decode('utf-8', errors='replace')
    for m in re.finditer(r'<a[^>]*href="(https?://bbs\.hupu\.com/\d+\.html)"[^>]*>\s*([^<]{10,80})</a>', html, re.DOTALL):
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        link = m.group(1)
        if title and len(title) > 8 and any(k in title for k in ['拳击','格斗','MMA','UFC','搏击','张伟丽','宋亚东','李景亮']):
            items.append(...)
```

⚠️ 策略D的注意点：
- 社区页面结构变化频繁，正则可能过时，需要2周验证一次
- 虎扑的某些内容是通过JS动态加载的，HTML爬取只能拿到静态部分
- 最好配合策略B（匹配法）一起使用，互相补充

### 策略E: HTML爬取 + GBK解码（中文老站专用）
适用于蜂鸟网(fengniao.com)这类还在用GBK编码的中文老站：
```python
# 必须绕过fetch()直接操作原始字节
req = urllib.request.Request("https://www.fengniao.com/", headers={...})
resp = urllib.request.urlopen(req, timeout=10)
raw_bytes = resp.read()
html = raw_bytes.decode('gbk', errors='replace')
# 然后用正则提取
titles = re.findall(r'<h2[^>]*>.*?<a[^>]*title="([^"]+)"', html, re.DOTALL)
```

## 采集器调试指南

### 问题: 新增采集器注册后不产出数据
1. 检查 `COLLECTORS` 注册的priority — priority=1的平台会被 `is_worth_collecting()` 以50%概率跳过
2. 检查函数是否已定义且import正常: `python3 -c "from scripts.unified_collector_v5 import *; print('OK')"`
3. 单测: `python3 -c "from scripts.unified_collector_v5 import *; items = collect_xxx(); print(len(items))"`
4. 检查 `insert_raw_item` 中的 `is_user_interest()` 是否过滤掉了
5. 检查 `insert_raw_item` 中的`is_collect_filtered()` 是否被黑名单拦截
6. 检查url_hash去重 — 如果url已经存在，`INSERT OR IGNORE` 不会报错但return False

### 问题: 全量采集超时
- 减少 `--parallel` 并发数（默认8，建议4-6）
- 超长采集器（CSDN、搜狗微信）设较长的timeout
- `collect_platform` 内部有15秒线程join超时

### 问题: collector_preferences.json 不生效
- 文件位置: `~/.hermes/reports/collector_preferences.json`
- 采集器在 `insert_raw_item()` 中调用 `is_user_interest()` 做过滤
- `is_worth_collecting()` 在collect_all()阶段做平台级跳过

### 问题: CRONTAB 更新后不生效
- 用 `crontab -l` 每次都输出完整内容并验证
- 用 sed 替换单个行容易出错 → 改 crontab 的可靠方法:
```bash
crontab -l > /tmp/cron_bak.txt
# 编辑 /tmp/cron_bak.txt
crontab /tmp/cron_bak.txt
crontab -l  # 验证
```

### 问题: 采集平台有数据但推送收不到
如果出现**某个平台数据量正常但用户收不到推送**的情况，检查以下管道断裂点：

**断裂点1 — category_tags → cleaned.tags 丢失（已修复2026-05-28）**

采集器向 `raw_intelligence.category_tags` 写入标签（如 `Photo|Camera|Match`），但 `unified_cleaning_pipeline.py` 的 SELECT 查询默认不包含 `category_tags` 列。INSERT 时用空的 `tags` 字段，导致所有标签丢失。推送系统从 `cleaned_intelligence.tags` 读取标签 → 摄影/格斗/芯片数据永远不会出现在推送候选池。

**检测方法**:
```sql
-- 检查cleaned数据是否有标签丢失
SELECT COUNT(*) FROM cleaned_intelligence c 
JOIN raw_intelligence r ON c.raw_id = r.id 
WHERE r.category_tags IS NOT NULL AND r.category_tags != '' 
AND (c.tags IS NULL OR c.tags = '' OR c.tags = 'General');
```
如果 >0 说明历史数据有标签丢失。

**修复**: 见 `hermes-cleaning-pipeline-v2` 技能中的修复记录。

**断裂点2 — 推送SQL标签名不匹配（已修复2026-05-28）**

推送SQL的 `get_candidates_balanced()` 中 `WHERE (tags LIKE '%Sports_Fight%' OR tags LIKE '%Beauty_Photo%' ...)` 不匹配从 `category_tags` 合并进来的 `Photo`/`Camera`/`Fight`/`Chip` 标签。需要加 `OR tags LIKE '%Photo%'` 等。

**检测方法**: 手动跑 `--draft` 看候选列表是否含有Photo/Fight标签的数据。

**断裂点3 — AI评分过低导致被推送过滤**

推送SQL有 `ai_score_total >= 15` 条件。摄影/格斗数据AI评分多在40-50分，而AI数据在86-98分。虽然有降级条件，但低分数据在300条候选中被排名压到末尾。

**检测方法**:
```sql
SELECT ai_score_total, tags, title FROM cleaned_intelligence 
WHERE is_processed=0 AND tags LIKE '%Photo%' OR tags LIKE '%Fight%'
ORDER BY ai_score_total DESC LIMIT 10;
```

**修复**: 推送SQL已加了 `importance_score>=50 OR personal_match_score>=10` 降级条件，但对于评分偏低的新方向数据，可考虑降低门槛。

### 问题: _match 类型采集器注册后不产出数据（或UPDATE无效）

**陷阱1 — url_hash 算法不匹配**：数据库中已有记录的 `url_hash` 是 **MD5**（由早期CSDN/其他采集器写入），但 `unified_collector_v5.py` 的 `url_hash()` 用 **SHA256[:32]**。导致 `WHERE url_hash=?` 的UPDATE永远匹配不上。

**修复**：match类型数据用 `WHERE url=?` 直接匹配URL，绕过hash差异。
```python
db.execute("UPDATE raw_intelligence SET ... WHERE url=?", (tags, item['url']))
```

**陷阱2 — is_user_interest() 过滤误杀**：match数据 content 为空（提取自已有记录），title 也可能较短不命中关键词。`insert_raw_item()` 中的 `is_user_interest()` 会返回False丢弃数据。

**修复**：match类型数据必须在进入 `is_user_interest()` 之前被拦截：
```python
source_type = item.get('source_type','terminal')
if source_type == 'match':
    # 直接更新标签，跳过所有过滤
    ...
    return new
```

### 问题: 自采集器（csdn/抖音/小红书等）返回格式与 v5 不兼容
独立采集器如 `csdn_blog_collector.collect_csdn_blogs()` 返回 `(saved, 0, 0)` 元组（它自己管理数据入库），但 `collect_platform` 期望 fn() 返回 items 列表。直接注册会导致 `'int' object has no attribute 'get'`。

**修复**：包装一层使其返回兼容格式：
```python
def wrap_csdn():
    try:
        saved, _, _ = collect_csdn_blogs()  # 自采集器已自行入库
    except:
        saved = 0
    return [{'platform': 'csdn', 'title': f'csdn collected {saved} items',
             'url': 'https://blog.csdn.net/', 'source_type': 'api'}]
```

### 问题: unified_collector_v5.py 的 collect_all() 报 "ValueError: too many values to unpack"
COLLECTORS 的元素是 (fn, priority, timeout) 三元组，但 `filtered` 列表构造和解包必须一致:
```python
# ✅ 正确
filtered.append((name, fn, pri))   # 三元组
futures = {executor.submit(collect_platform,name,fn,pri):name for name,fn,pri in filtered}
# ❌ 错误
futures = {executor.submit(...):name for name,(fn,pri) in filtered}
```

## 已注册采集器清单（48个，截至2026-05-28）

### 核心平台（priority 7-10，每轮必跑）
weibo_hot, zhihu_hot, toutiao_hot, bilibili_ranking, 36kr_newsflash,
ithome_rss, oschina_rss, hackernews, sogou_wechat, baidu_hot,
weibo_search, sina_tech, zhihu_questions, zhihu_daily, zhihu_topstory,
tieba, weibo_military, bilibili_tech, infoq, techmeme

### 已定义但前期停摆的平台（priority提升至7，已恢复）
github_trending, arxiv_ai/arxiv_papers, devto, freebuf, huxiu, ifanr,
tmtpost, juejin, tencent_cloud, huggingface, reddit_dev, segmentfault, cnblogs

### 新增平台（2026-05-28添加）
**摄影**: dpreview(photo_match+RSS), fengniao(蜂鸟HTML爬取), photo_rumors(SonyRumors)
**格斗**: sherdog(mma_match+RSS), bloodyelbow(mma_rss)
**芯片**: semiconductor(semi_match+SemiEngineering+RSS), hardware_news(Tom's Hardware)
**旅游**: qyer(穷游RSS — ✅ 已验证111+条入库)

### 独立采集器（通过subprocess调用）
weixin_accounts(MCP), xiaohongshu_search(v5), douyin_hot(每2h独立cron), csdn_blogs(每轮跑但时间长)

## 推送质量诊断（推重复/旧闻诊断方法）

当用户投诉"重复推送"或"旧闻太多"时，参见：
**📄 `references/push-quality-diagnostics.md`** — 完整诊断方法（2026-05-30新增）

### 快速诊断命令（从 ~/.hermes/ 运行）
```bash
python3 << 'PYEOF'
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('data/intelligence.db')
c = conn.cursor()

# 1. 检查去重时间窗口是否匹配
cutoff_6h = (datetime.now() - timedelta(hours=6)).isoformat()
cutoff_72h = (datetime.now() - timedelta(hours=72)).isoformat()
c.execute("SELECT COUNT(*) FROM push_records WHERE push_time >= ? AND push_time < ?", (cutoff_72h, cutoff_6h))
old_pushed = c.fetchone()[0]
print(f"[去重漏洞] 6-72h前被推送过的标题数(当前6h窗口外): {old_pushed}")

# 2. 重复推送统计
c.execute("SELECT title, COUNT(*) FROM push_records GROUP BY title HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 10")
dups = c.fetchall()
print(f"[重复推送] 共{len(dups)}个标题重复推送")
for t, cnt in dups:
    print(f"  [{cnt}x] {t[:50]}")

# 3. 候选池中的旧数据
c.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE collected_at >= ? AND published_at NOT LIKE '2026%' AND published_at != ''", (cutoff_72h,))
print(f"[旧数据] 候选池中非2026年老数据: {c.fetchone()[0]}条")

# 4. 发布时间解析异常
c.execute("SELECT COUNT(*) FROM cleaned_intelligence WHERE published_at GLOB '[A-Z][a-z][a-z],*'")
print(f"[时间解析] day-name格式异常记录数: {c.fetchone()[0]}")
conn.close()
PYEOF
```

### 三个核心bug模式
| Bug | 根因 | 修复 |
|-----|------|------|
| 同一标题跨天重复6次 | 6h去重窗口 vs 72h候选窗口 | 去重要扩大到72h，加每条标题最多推2次的硬限制 |
| 候选池混入2014年旧闻 | SQL按collected_at过滤而非published_at | 加 `published_at LIKE '2026%'` 条件 |
| cron DRY RUN不推送 | 命令缺少`--push`参数 | 检查cron job prompt是否含`--push` |

## 管道健康监测 — 双门检查

评分积压检测（`ai_score_total IS NULL`）会掩盖一个更深的问题：raw→cleaned的管道阻塞。当评分队列为空时，**不代表管道健康** — 可能只是原料没进清洗环节。

**每次管道检查必须验证两道门**:
```sql
-- 门1: 清洗管道
SELECT COUNT(*) FROM raw_intelligence r 
LEFT JOIN cleaned_intelligence c ON r.id = c.raw_id 
WHERE c.id IS NULL;  -- 应该 < 200

-- 门2: 评分管道  
SELECT COUNT(*) FROM cleaned_intelligence 
WHERE ai_score_total IS NULL OR ai_score_total = 0;  -- 应该 = 0
```

典型故障模式：CSDN独立采集器日积月累1,376条raw未清洗，而评分管道报"0条未评分"给人虚假安全感。

📄 **详细检测方法**: `references/raw-to-cleaned-pipeline-stall-detection.md`

## 已知当前限制（2026-05-28）
1. **海外RSS限流**: PetaPixel/Sherdog/BloodyElbow/SemiEngineering 等在国内网络下间歇超时
2. **百度搜索被反爬**: 无cookie的fetch返回空页面
3. **蜂鸟网HTML**: GBK编码需手动解码，HTML结构变化可能导致抓取失效
4. **内容深度**: CSDN有全文获取(10000+字符)，微博/头条等仅标题+摘要(平均<200字符)
5. **gitub_trending**: 改用HTML爬取github.com/trending，需要稳定的User-Agent
6. **小红书/微信公众号**: 依赖独立采集器subprocess，成功率不稳定

## 格林主人偏好方向（collector_preferences.json v3.0）
P0核心: AI/LLM/AIGC, 开源/Dev, 手机/消费电子, 芯片/半导体, 新能源/自动驾驶, 军事/国防, 机器人, 安全, 科技
P1高兴趣: 格斗/MMA/UFC/拳击, NBA/足球/F1, 摄影/相机/镜头, 电影/Netflix, 游戏/Steam, 科学/量子/生物, 太空/航天, 汽车/赛车, 绘画/AI绘画, 音乐
P2一般: 旅游/美食/探店, 历史/文化, 时尚/穿搭
丢弃: 股票/基金/理财, 房地产/房价, 娱乐八卦, 三手重绘

## Key Files
- `~/.hermes/scripts/unified_collector_v5.py` — **主采集器** (1911行，48个平台)
- `~/.hermes/reports/collector_preferences.json` — 偏好配置
- `~/.hermes/scripts/browser_collector.py` — 浏览器采集备选
- `~/.hermes/scripts/hermes_ultimate_collector.py` — 全能力聚合采集器
- `~/.hermes/scripts/csdn_blog_collector.py` — CSDN独立采集器
- `~/.hermes/scripts/douyin_account_collector.py` — 抖音独立采集
- `~/.hermes/scripts/xhs_collector_v5.py` — 小红书独立采集
- `~/.hermes/references/expanding_platforms_20260528.md` — 本会话中新增平台的详细部署记录
- `~/.hermes/references/collector-pitfalls-20260528.md` — 8个采集器陷阱的修复模式
- `~/.hermes/skills/intelligence/unified-collection-pipeline/references/health-radar-scan-20260528.md` — 全系统10维雷达扫描命令集（含关键发现检查清单）
- `~/.hermes/skills/intelligence/unified-collection-pipeline/references/cron-audit-methodology.md` — cron审计清理方法论（67→10的具体判断规则）
- `~/.hermes/skills/intelligence/unified-collection-pipeline/references/cleaning-category-tags-fix-20260528.md` — 清洗管道 category_tags 丢失的排查与批量修复完整记录
- `~/.hermes/skills/intelligence/unified-collection-pipeline/references/cron-cleanup-methodology-20260528.md` — cron审计清理方法论（67→10的具体判断规则+实战模板+坑点清单）
- `~/.hermes/skills/intelligence/unified-collection-pipeline/references/three-pipeline-break-pattern-20260528.md` — 数据管道三接口断裂模式（采集→清洗→评分→推送的排查流程）

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
