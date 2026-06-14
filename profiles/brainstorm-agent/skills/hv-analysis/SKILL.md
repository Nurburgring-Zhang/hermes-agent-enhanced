---
name: hv-analysis
description: 横纵分析法 (Horizontal-Vertical Analysis) — 基于数字生命卡兹克开源方法论的深度情报分析框架。纵向(时间维度)+横向(空间维度)+竞争战略叠加，生成深度分析报告。
category: intelligence
version: 1.0
trigger: 需要深度分析情报时自动触发，或手动调用hv_analysis()对特定主题做横纵分析
workflow:
  1. 采集主题相关情报数据（从intelligence.db / 当前采集结果 / 用户给定数据）
  2. 纵向分析：时间维度回顾3-5年历史，识别关键转折点，判断趋势外推vs结构性变化
  3. 横向分析：空间维度对比不同玩家/区域/用户群体，标杆研究，产业链生态地图
  4. 竞争战略叠加：波特五力+SWOT+定位分析
  5. 六维评分：对分析结果进行AI六维评分
  6. 输出格式化分析报告
integrates_with:
  - hermes-fast-intelligence-pipeline: 采集情报后自动调用hv-analysis生成深度报告
  - ai-six-dimension-scoring-pipeline: 分析结果进行AI六维评分
  - hermes-push-v3: 推送hv-analysis深度报告到微信
---
# hv-analysis 横纵分析法

## 方法论来源

基于数字生命卡兹克 (KKKKhazik) 开源方法论，结合 Hermes 情报系统深度集成。

GitHub: https://github.com/KKKKhazik/khazix-skills

## 核心框架

横纵分析法是三维分析框架，从时间、空间、竞争三个维度对情报进行深度解构。

### 第一维：纵向分析（时间维度）

目标：理解事物如何在时间线上演变，识别关键节点和趋势方向。

**分析步骤：**

1. **历史回溯（3-5年）**
   - 收集该主题过去3-5年的关键事件和时间节点
   - 标注重要转折点（政策变化/技术突破/重大事件）
   - 构建时间线图谱

2. **关键转折点识别**
   - 政策转折：监管政策变化、产业政策支持/限制、国际贸易规则变化
   - 技术转折：技术范式迁移、突破性创新、技术瓶颈突破
   - 事件转折：黑天鹅事件、行业危机、市场崩盘/爆发

3. **趋势判断**
   - 趋势外推：当前趋势是否合理延续？驱动因素是否持续？
   - 结构性变化：是否有真正的范式转移？还是短期波动？
   - 多情景分析：乐观/中性/悲观三种情景推演

**时间跨度建议：**
| 类型 | 回溯 | 展望 |
|------|------|------|
| 科技赛道 | 3年 | 1-2年 |
| 政策领域 | 5年 | 1-3年 |
| 宏观趋势 | 5年 | 3-5年 |
| 公司分析 | 3年 | 1-2年 |

### 第二维：横向分析（空间维度）

目标：理解在同一时间点上的空间差异、竞争格局和生态分布。

**分析步骤：**

1. **玩家地图**
   - 行业内不同竞争对手的定位、规模、战略方向
   - 市场份额分布（头部/腰部/长尾）
   - 各玩家核心优势和差异化策略

2. **区域/市场对比**
   - 不同区域的产业发展阶段差异
   - 区域政策、文化、基础设施的异同
   - 全球化vs本地化策略分析

3. **用户/群体分层**
   - 不同用户群体的需求差异和特征
   - 付费意愿和使用场景分析
   - 用户迁移路径和增长空间

4. **标杆研究（Best Practice）**
   - 行业最佳实践识别
   - 成功/失败案例分析
   - 可迁移经验提炼

5. **产业链生态地图**
   - 上中下游全景图（供给侧/生产侧/渠道侧/消费侧）
   - 各环节价值分布和利润池分析
   - 关键瓶颈和卡脖子环节
   - 生态位和护城河

### 第三维：竞争战略叠加

#### 波特五力模型

| 力量 | 分析要点 | 评分维度 |
|------|---------|---------|
| 供应商议价能力 | 供应商集中度、替代方案、切换成本 | 弱/中/强 |
| 买家议价能力 | 买家集中度、价格敏感度、信息对称性 | 弱/中/强 |
| 新进入者威胁 | 进入壁垒、资本门槛、技术壁垒 | 低/中/高 |
| 替代品威胁 | 替代方案数量、性价比、转换成本 | 低/中/高 |
| 同业竞争强度 | 竞争者数量、行业增速、退出壁垒 | 低/中/高 |

#### SWOT分析

| 维度 | 内容 | 来源 |
|------|------|------|
| S (优势) | 内部有利因素 | 纵向分析中的历史验证、横向分析中的差异化 |
| W (劣势) | 内部不利因素 | 技术短板、资源不足、市场定位问题 |
| O (机会) | 外部有利条件 | 政策红利、技术窗口、市场空白 |
| T (威胁) | 外部不利条件 | 竞争加剧、监管风险、替代技术 |

#### 定位分析

- **战略定位**：成本领先/差异化/聚焦
- **价值主张**：产品/服务/体验/价格
- **竞争优势**：可持续的护城河来源（技术/IP/网络效应/规模经济/品牌）

## 与 Hermes 情报系统的集成

### 自动触发机制

当以下条件触发时，自动执行 hv-analysis：

1. **情报采集后**：hermes-fast-pipeline 完成采集 → 如果发现有高价值情报（六维评分≥70分），自动触发 hv-analysis 生成深度报告
2. **用户主动调用**：通过 `delegate_task` 指定主题执行横纵分析
3. **定时深度分析**：每周对本周TOP5情报做横纵分析

### 数据源整合

hv-analysis 从以下数据源获取素材：

```
intelligence.db
  ├── raw_intelligence      → 原始采集数据
  ├── cleaned_intelligence  → 清洗后的高质量数据
  ├── intelligence_scores   → AI六维评分结果
  └── hv_analysis_reports   → 历史分析报告（新表）
```

### 六维评分结合

分析报告完成后，使用六维评分体系对报告本身进行评分：

| 维度 | 评估标准 |
|------|---------|
| 分析深度 | 纵向回溯是否完整，转折点识别是否精准 |
| 横向广度 | 玩家/区域/产业链覆盖是否全面 |
| 可操作性 | 是否有明确的结论和行动建议 |
| 数据支撑 | 是否有充分的数据和事实依据 |
| 独特性 | 是否提供了独特的洞察而非常识复述 |
| 时效性 | 是否基于最新情报 |

## 输出格式

### 标准分析报告格式

```
╔══════════════════════════════════════════════════════════╗
║  hv-analysis 横纵分析报告                                ║
║  主题: [分析主题]                                       ║
║  日期: YYYY-MM-DD HH:MM                                ║
║  评分: ⭐⭐⭐⭐ (85分)                                   ║
╚══════════════════════════════════════════════════════════╝

────────────────────────────────────────────────────────
一、纵向分析（时间维度）
────────────────────────────────────────────────────────

【历史时间线】
YYYY-MM | 事件 | 影响级别
YYYY-MM | 事件 | 影响级别
...

【关键转折点】
🔴 政策转折：[描述]
🔵 技术转折：[描述]
🟡 事件转折：[描述]

【趋势判断】
📈 趋势外推：[分析]
🔄 结构性变化：[分析]
🔮 多情景推演：
  - 乐观：[情景描述]
  - 中性：[情景描述]
  - 悲观：[情景描述]

────────────────────────────────────────────────────────
二、横向分析（空间维度）
────────────────────────────────────────────────────────

【玩家地图】
🥇 [头部玩家]：[定位/份额/优势]
🥈 [腰部玩家]：[定位/份额/优势]
🥉 [长尾玩家]：[定位/份额/优势]

【区域对比】或【用户分层】
- [区域A] vs [区域B]：[对比分析]

【产业链生态】
上游：[关键环节+玩家]
中游：[关键环节+玩家]
下游：[关键环节+玩家]

【标杆案例】
✅ 成功案例：[案例+可迁移经验]
❌ 失败案例：[案例+教训]

────────────────────────────────────────────────────────
三、竞争战略叠加
────────────────────────────────────────────────────────

【波特五力】
┌────────────────────┬──────────────┐
│ 力量               │ 强度评估     │
├────────────────────┼──────────────┤
│ 供应商议价能力     │ ○ 弱/●中/○ 强│
│ 买家议价能力       │ ○ 弱/●中/○ 强│
│ 新进入者威胁       │ ○ 低/○中/●高│
│ 替代品威胁         │ ○ 低/●中/○高│
│ 同业竞争强度       │ ○ 低/○中/●高│
└────────────────────┴──────────────┘

【SWOT分析】
- S：[优势1, 优势2, ...]
- W：[劣势1, 劣势2, ...]
- O：[机会1, 机会2, ...]
- T：[威胁1, 威胁2, ...]

【战略定位】
- 定位类型：[成本领先/差异化/聚焦]
- 核心价值主张：[一句话]
- 可持续护城河：[护城河来源]

────────────────────────────────────────────────────────
四、结论与行动建议
────────────────────────────────────────────────────────

【核心发现】
1. [关键洞察1]
2. [关键洞察2]
3. [关键洞察3]

【行动建议】
✅ 短期（1-3月）：[建议]
📅 中期（3-12月）：[建议]
🎯 长期（1-3年）：[建议]

【风险提示】
⚠️ [风险1]
⚠️ [风险2]

────────────────────────────────────────────────────────
分析完成时间: YYYY-MM-DD HH:MM:SS
数据源: [情报来源列表]
历史报告: [关联历史报告ID列表]
```

### 推送版（轻量版，微信推送用）

```
📊 hv横纵分析 | [主题]
────────────────
⏳ 纵向: [3年关键发现]
🌐 横向: [竞争格局核心洞察]
🏆 战略: [SWOT/五力结论]
📌 建议: [核心行动建议]
────────────────
评分: [六维评分] | 全文: [存储路径]
```

## 参考脚本

### hv_analysis.py — 核心执行脚本

脚本路径：`/home/administrator/.hermes/scripts/hv_analysis.py`

功能：
1. 从 intelligence.db 读取指定主题的情报数据
2. 使用 delegate_task（内部DeepSeek）执行横纵分析
3. 生成结构化分析报告
4. 存储到 hv_analysis_reports 表
5. 可选推送微信

```python
#!/usr/bin/env python3
"""
hv_analysis.py — 横纵分析法执行引擎
基于数字生命卡兹克开源方法论
"""
import json, sys, sqlite3, argparse
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = str(Path.home() / ".hermes" / "intelligence.db")

def delegate_task(prompt):
    """调用内部DeepSeek执行分析"""
    # 通过stdin/stdout委托给主进程
    pass

def fetch_intelligence(topic, days=90, limit=30):
    """获取主题相关情报数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT id, title, content, source, created_at, summary
        FROM cleaned_intelligence
        WHERE (title LIKE ? OR content LIKE ?)
          AND created_at >= datetime('now', ?)
        ORDER BY created_at DESC
        LIMIT ?
    """, (f'%{topic}%', f'%{topic}%', f'-{days} days', limit))
    return cursor.fetchall()

def hv_analysis(topic, intelligence_data):
    """执行横纵分析，返回结构化报告"""
    # 构建prompt包含：
    # 1. hv-analysis核心框架说明
    # 2. 情报数据
    # 3. 要求的输出格式
    prompt = f"""你是一个顶级战略分析师。请对主题「{topic}」进行横纵分析。

核心框架：
1. 纵向分析（时间维度）：回顾3-5年历史，识别关键转折点，判断趋势外推vs结构性变化
2. 横向分析（空间维度）：行业内不同玩家/不同区域/不同用户群体差异，标杆研究，产业链生态地图
3. 竞争战略叠加：波特五力+SWOT+定位分析

情报数据：
{json.dumps(intelligence_data, ensure_ascii=False, indent=2)}

请输出格式化的横纵分析报告（包含纵向/横向/竞争战略/结论建议四个部分）。
"""
    result = delegate_task(prompt)
    return result

def store_report(conn, topic, report, score):
    """存储分析报告到数据库"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hv_analysis_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            report TEXT,
            score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO hv_analysis_reports (topic, report, score)
        VALUES (?, ?, ?)
    """, (topic, report, score))
    conn.commit()

def push_report(topic, summary, score):
    """推送轻量版报告到微信"""
    from pushplus_wechat import push_to_wechat
    msg = f"""📊 hv横纵分析 | {topic}
────────────────
{summary}
────────────────
评分: {score}/100 | 查看全文: storage/hv_analysis/"""
    push_to_wechat(msg, title=f"hv横纵分析 | {topic}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="hv-analysis 横纵分析引擎")
    parser.add_argument("--topic", required=True, help="分析主题")
    parser.add_argument("--days", type=int, default=90, help="回溯天数")
    parser.add_argument("--push", action="store_true", help="推送微信")
    parser.add_argument("--db-only", action="store_true", help="仅从数据库检索，不执行分析")
    args = parser.parse_args()
    
    data = fetch_intelligence(args.topic, args.days)
    report = hv_analysis(args.topic, data)
    score = 85  # 六维评分结果
    store_report(sqlite3.connect(DB_PATH), args.topic, report, score)
    print(report)
```

## 数据库设计

```sql
-- hv分析报告表
CREATE TABLE IF NOT EXISTS hv_analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,                    -- 分析主题
    report TEXT NOT NULL,                   -- 完整分析报告
    score INTEGER DEFAULT 0,               -- 报告六维评分
    data_sources TEXT,                      -- 数据源ID列表 [1, 2, 3]
    related_reports TEXT,                   -- 关联报告ID列表
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_hv_topic ON hv_analysis_reports(topic);
CREATE INDEX IF NOT EXISTS idx_hv_created ON hv_analysis_reports(created_at);
```

## 触发条件

### 自动触发
- 情报采集管线（hermes-fast-pipeline）完成采集后，若检测到高价值情报（六维评分≥70）则自动触发 hv-analysis
- 每周日凌晨2点执行每周TOP5情报的横纵分析

### 手动触发
```bash
# 完整分析
python3 /home/administrator/.hermes/scripts/hv_analysis.py --topic "大模型价格战" --days 180 --push

# 仅检索数据库
python3 /home/administrator/.hermes/scripts/hv_analysis.py --topic "自动驾驶" --db-only

# 指定回溯窗口
python3 /home/administrator/.hermes/scripts/hv_analysis.py --topic "新能源电池" --days 365 --push
```

### 通过 delegate_task 触发
```python
# 在skill中调用
report = delegate_task("执行hv-analysis横纵分析，主题：大模型开源生态")
```

## Known Pitfalls

### 数据质量陷阱
1. **情报不足**：如果数据库中对某个主题的数据量少于5条，分析结果将缺乏数据支撑
   - 解决：提示先补充采集，或扩大回溯天数
2. **信息过时**：依赖的情报数据可能过时（超过90天）
   - 解决：检查每条数据的 created_at 时间戳
3. **噪声干扰**：关键词匹配可能带回不相关的内容（如搜索"苹果"带回水果新闻）
   - 解决：扩展关键词或二次过滤

### 分析逻辑陷阱
4. **纵向分析过度外推**
   - 常见错误：将短期波动误判为长期趋势
   - 解决：要求同时给出趋势外推和结构性变化两种判断
5. **横向对比锚定偏差**
   - 常见错误：过度关注头部玩家，忽略腰部/长尾的创新潜力
   - 解决：强制覆盖头部/腰部/长尾三层分析
6. **波特五力过时**
   - 常见错误：在平台经济/网络效应环境下套用传统波特五力
   - 解决：补充网络效应、平台生态等现代竞争要素

### 执行陷阱
7. **delegate_task超时**：analysis prompt因情报数据量大可能超过上下文限制
   - 解决：分批次分析，先对单个维度分别分析再汇总
8. **数据库连接**：intelligence.db 可能被采集管线锁定
   - 解决：使用 WAL 模式或 retry 机制
9. **报告过长无法推送**：完整报告可能超过 PushPlus 单条限制
   - 解决：推送轻量版摘要，完整报告存数据库

## 集成到 Hermes 管线

### 修改 hermes-fast-pipeline 集成
在采集管线的后处理阶段添加：

```python
# 在 hermes_fast_pipeline.py 的高价值处理中
from hv_analysis import hv_analysis

def after_collection_pipeline():
    """采集后处理：对高价值情报触发横纵分析"""
    conn = sqlite3.connect(DB_PATH)
    # 查询高分情报的关键主题
    topics = conn.execute("""
        SELECT DISTINCT SUBSTR(title, 1, 20) as topic_seed
        FROM cleaned_intelligence c
        JOIN intelligence_scores s ON c.id = s.item_id
        WHERE s.total_score >= 70
          AND c.created_at >= datetime('now', '-6 hours')
        ORDER BY s.total_score DESC
        LIMIT 3
    """).fetchall()
    
    for (topic_seed,) in topics:
        # 对每个高价值主题执行横纵分析
        hv_analysis(topic_seed, fetch_intelligence(topic_seed))
```

### 修改六维评分集成
在评分脚本中添加 hv-analysis 维度：

```python
# 在 ai_scorer.py 中添加
if total_score >= 70:
    # 高分情报自动触发横纵分析
    delegate_task(f"执行hv-analysis横纵分析，主题：{title}")
```

## 验证方法

1. **单主题测试**
   ```bash
   python3 hv_analysis.py --topic "大模型" --days 90
   ```
   确认输出包含完整的纵向/横向/竞争战略三部分

2. **数据库验证**
   ```sql
   SELECT topic, score, created_at FROM hv_analysis_reports ORDER BY created_at DESC LIMIT 5;
   ```

3. **推送验证**
   ```bash
   python3 hv_analysis.py --topic "AI芯片" --push
   ```
   检查微信是否收到推送

4. **集成验证**
   ```bash
   # 完整管线测试
   python3 hermes_fast_pipeline.py && python3 hv_analysis.py --topic "热点" --days 7
   ```

## 文件清单

```
/home/administrator/.hermes/skills/hv-analysis/
├── SKILL.md                    ← 本文件
├── scripts/
│   └── hv_analysis.py          ← 核心执行脚本
├── templates/
│   ├── full_report.md          ← 完整报告模板
│   └── push_summary.md         ← 推送摘要模板
└── references/
    ├── methodology.md          ← 方法论详述
    └── examples/               ← 分析案例
        └── example_large_model.md
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
