# context_index_system — 索引-复原式上下文系统

## 位置
`~/.hermes/scripts/context_index_system.py`

## ⚠️ 诚实声明（2026-05-27更新）

**此系统cron层完美运行，但对话层从未真正接入！**

✅ cron层：5个脚本每1分钟跑，文件新鲜度~6秒
❌ 对话层：没有启动钩子用索引摘要代替SOUL.md
❌ context_reconstructor.py 不存在（无法按ID复原）
❌ session_init_check + context_selfcheck 不在cron中

调用本skill时，如果格林主人问"实现了没有"——必须诚实地回答这个差距。

## 原理（设计目标）

第一轮对话全量传入SOUL.md。
1. 按`##`章节分割SOUL.md → 14个独立章节文件
2. 每个章节存为 `reports/context_sections/<ID>.md`
3. 生成索引摘要 → `reports/context_index.json`

后续轮次只传入索引摘要(~2000 tokens)。
AI需要某个规则的完整原文时，从本地章节文件读取。

## 章节文件（14个）

| 文件 | 内容 | 大小 |
|------|------|:----:|
| 零_齿轮强制恢复协议.md | G0-G8完整齿轮链 | 2861字 |
| 一核心身份.md | 核心身份 | 161字 |
| 二永久禁令.md | 5条永久禁令 | 473字 |
| 三九面人格.md | 九面人格（占位） | 45字 |
| 四5大行为准则.md | 5大行为准则 | 349字 |
| 五multiagent调度.md | Multi-Agent调度 | 204字 |
| 六pipeline_v4.md | Pipeline v4流水线 | 739字 |
| 七关键文件索引.md | 关键文件索引 | 927字 |
| 八_七条永久执行规则.md | **8条永久规则原文** | **3127字** |
| 九_oi项目全量优化.md | OI 50项方案索引 | 7157字 |
| _skills组合并行链式调用.md | Skills编排规则 | 807字 |
| _低分数据自动清理.md | 低分清理规则 | 590字 |
| _强制声明.md | 系统底层声明 | 2103字 |
| _采集质量预筛.md | 采集预筛规则 | 444字 |

## 使用方式

```bash
# 构建章节文件（仅首次需要）
python3 ~/.hermes/scripts/context_index_system.py build

# 构建索引摘要（cron每1分钟执行）
python3 ~/.hermes/scripts/context_index_system.py index

# 按ID阅读完整章节
python3 ~/.hermes/scripts/context_index_system.py resolve 八_七条永久执行规则
python3 ~/.hermes/scripts/context_index_system.py resolve 齿轮

# 一次完成：建章节+建索引
python3 ~/.hermes/scripts/context_index_system.py auto
```

## 索引摘要内容

1. `[核心身份]` — 一句话
2. `[永久禁令]` — 5条精简
3. `[5大行为准则]` — 5条精简
4. `[全能力自动激活]` — 一句话
5. `[8条永久规则]` — 每条标题+核心指令
6. `[齿轮系统]` — 一行摘要
7. `[当前任务]` — 从wake_guide/task_current读取
8. `[关键章节索引]` — 前8个最常用章节路径

## 索引摘要约2000 tokens，包含：
- 所有规则的核心指令（够AI做90%的决策）
- 每个规则的完整原文路径（AI需要时从本地读取）
- 当前任务进度
- 齿轮系统摘要

## 信息复原机制

AI处理过程中的信息查找：
1. 看到 `[规则7(禁止降级): 严禁一切降级/模拟/占位]`
2. 如果需要规则7的原文细节
3. 执行 `read_file("~/.hermes/reports/context_sections/八_七条永久执行规则.md")`
4. 拿到2205字完整原文，包含所有禁止项

同理可查：齿轮完整协议(2861字)、OI 50项方案(7157字)、Pipeline流程(739字)等
