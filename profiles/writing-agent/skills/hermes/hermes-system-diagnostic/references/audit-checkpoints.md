# Hermes 全流程审计检查清单

## 使用方式
用于对 Hermes 全系统进行端到端的治理审计。每个检查点都需要**实际文件系统证据**（路径+内容），不能基于记忆或代码注释。

## 审计步骤（5步法）

### Step 1: 采集审计
```bash
# 1a. 列出所有采集器
find ~/.hermes/scripts/ -name '*collect*.py' -o -name '*fetch*.py' | sort

# 1b. 检查采集器最后修改时间（确定哪个是活跃版本）
ls -lt ~/.hermes/scripts/unified_collector*.py

# 1c. 检查 crontab 中的采集调度
crontab -l | grep -i 'collect\|fetch\|omni_loop\|guardian.*cycle'

# 1d. 检查原始数据量和时间范围（intelligence.db）
sqlite3 ~/.hermes/intelligence.db "SELECT MIN(published_at), MAX(published_at), COUNT(*) FROM raw_intelligence"

# 1e. 检查静默源（7天+无数据）
sqlite3 ~/.hermes/intelligence.db "SELECT source, MAX(date(published_at)), COUNT(*) FROM raw_intelligence GROUP BY source HAVING MAX(date(published_at)) < date('now','-7 days')"

# 1f. 检查数据质量（空内容占比）
sqlite3 ~/.hermes/intelligence.db "SELECT ROUND(100.0*SUM(CASE WHEN length(content)<50 THEN 1 ELSE 0 END)/COUNT(*),1) as pct_short FROM raw_intelligence"
```

### Step 2: 清洗过滤审计
```bash
# 2a. 检查清洗日志的最近运行
tail -5 ~/.hermes/logs/cleaning_$(date +%Y%m%d).log

# 2b. 清洗效率（new_cleaned / total_processed）
grep '清洗完成' ~/.hermes/logs/cleaning_$(date +%Y%m%d).log | tail -1

# 2c. 检查白名单过滤是否过严
grep 'whitelist_filtered' ~/.hermes/logs/cleaning_$(date +%Y%m%d).log | tail -1

# 2d. 检查重复内容是否漏网
sqlite3 ~/.hermes/intelligence.db "SELECT title, COUNT(*) as c FROM cleaned_intelligence GROUP BY title HAVING c > 5 ORDER BY c DESC LIMIT 5"
```

### Step 3: AI评分审计（最关键 — 验证声明vs.实现）
```bash
# 3a. 检查评分的实际模式（true AI vs. rules）
grep '未配置API\|AI评分模式\|增强规则\|TASK_ENHANCED\|TASK_AI_SCORED' ~/.hermes/logs/ai_scoring_$(date +%Y%m%d).log

# 3b. 检查API key环境变量
echo "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:+SET}"
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+SET}"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:+SET}"

# 3c. 追踪评分调用链：调用方脚本→实际评分函数
grep 'step.*评分\|scoring\|hermes_ai_scoring\|--ai' ~/.hermes/scripts/omni_loop.py

# 3d. 检查评分脚本中的API key检查分支逻辑
grep -A5 'if not api_key' ~/.hermes/scripts/hermes_ai_scoring.py | head -10
grep -A5 'if not api_key' ~/.hermes/scripts/ai_scoring_daemon.py | head -10

# 3e. 评分覆盖度
sqlite3 ~/.hermes/intelligence.db "SELECT COUNT(*), SUM(CASE WHEN ai_score_total IS NOT NULL THEN 1 ELSE 0 END) FROM cleaned_intelligence"
```

### Step 4: 下游产品链路审计（需求挖掘+专家匹配+产品生成）
```bash
# 4a. 需求挖掘报告检查
ls -lt ~/.hermes/outputs/requirement_mining/ | head -3
cat ~/.hermes/outputs/requirement_mining/requirements_$(date +%Y%m%d)*.json | python3 -m json.tool 2>/dev/null | head -20

# 4b. 产品方案质量检查—看features/tech_stack是否所有文件都一样
md5sum ~/.hermes/outputs/auto_production/product_*.json | sort | head -10
# 如果所有md5sum都不同但features内容一样 → 硬编码模板

# 4c. 检查production_auto.py中是否真的调用了AI
grep -c 'delegate_task\|subprocess.*run\|requests.post\|urllib.*request\|openai' ~/.hermes/scripts/production_auto.py
# 如果返回0 → 从未调用AI

# 4d. 专家分析报告质量
ls -t ~/.hermes/outputs/agent_matching/deep_reports/ 2>/dev/null | head -3

# 4e. 检查测试+交付环节是否存在
find ~/.hermes/scripts/ -name '*test*' -o -name '*qa*' -o -name '*deliver*' | head -10
```

### Step 5: 推送审计
```bash
# 5a. 最近推送记录
sqlite3 ~/.hermes/intelligence.db "SELECT id, title, pushed_at, status FROM push_records ORDER BY id DESC LIMIT 5"

# 5b. 每日推送量趋势
sqlite3 ~/.hermes/intelligence.db "SELECT substr(pushed_at,1,10) as d, COUNT(*) FROM push_records GROUP BY d ORDER BY d DESC LIMIT 14"

# 5c. push_records的status分布
sqlite3 ~/.hermes/intelligence.db "SELECT status, COUNT(*) FROM push_records GROUP BY status"
```

## 全流程闭环检查确认表

| # | 环节 | 文件/数据源 | 验证项 | Done |
|---|------|------------|--------|------|
| 1 | 采集 | raw_intelligence | 24h内有新数据 | ☐ |
| 2 | 清洗 | cleaned_intelligence | 数据近实时更新 | ☐ |
| 3 | AI评分 | ai_score_total字段 | 检查是AI分还是规则分 | ☐ |
| 4 | 需求挖掘 | requirements_*.json | 每30分产出新报告 | ☐ |
| 5 | 专家匹配 | deep_analysis_*.json | 产出深度分析报告 | ☐ |
| 6 | 产品生成 | product_*.json | `features`是否差异化 | ☐ |
| 7 | 测试迭代 | 不存在→标记缺失 | 检查是否有测试脚本 | ☐ |
| 8 | 推送 | push_records | 定时推送且成功 | ☐ |

## 常见退化信号速查

```
日志中的关键词                    → 退化类型
────────────────────────────────────────────────
"未配置API密钥"                   → AI功能降级为规则
"Network is unreachable"          → 海外采集死亡
"返回124"                        → 采集超时(timeout)
"TASK_ENHANCED_RULES"            → AI评分被规则替代
"TASK_OK:0"                      → 管道空跑（无产出）
"连续批次无新数据"                → 清洗空跑
"enhanced_rule_scores"           → 所有AI评分都是规则
"product_*.json 所有features相同" → 产品方案硬编码
"status='pending'"                → 队列积压未处理
```

## 证据记录模板

每次审计结果应记录为：
```
## 审计时间: YYYY-MM-DD HH:MM
## 环节: [采集/清洗/AI评分/需求/匹配/产品/测试/推送]
## 证据路径: [实际文件路径]
## 发现: [具体问题]
## 严重度: [🔴阻断/🟡高/🟢低]
## 根因: [API key/硬编码/超时/网络/去重]
## 修复动作: [修复方法]
```
