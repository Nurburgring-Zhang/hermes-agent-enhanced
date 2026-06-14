# 上下文索引-复原系统

## 核心思路
**第一轮全量传入 → 后续只传索引摘要 → 需要时从本地文件复原完整原文**

## 为什么需要这个
- SOUL.md 21,312 tokens，每轮对话全量传入很快撑爆token窗口
- 但所有章节原文都是必须保留的（信息无损），不能简单摘掉
- 方案：建立章节索引，AI只需带轻量标签，需要细节时从文件拉取

## 三个组件

### 1. context_index_system.py（章节分割+索引构建）
```
位置: ~/.hermes/scripts/context_index_system.py
cron: 每1分钟
输出: reports/context_index.json + reports/context_sections/ (14个md文件)
```

功能：
- 将SOUL.md按`## `分割为14个独立章节文件
- 每个章节文件存为 `reports/context_sections/<id>.md`
- 构建轻量索引摘要（~2000 tokens），包含：
  - 核心身份+永久禁令+行为准则（一行）
  - 8条永久规则（每条一行摘要）
  - 关键章节索引（文件路径+tokens数，AI按需读取）
  - 当前任务进度（从wake_guide/task_current读取）

用法：
```bash
# 首次构建章节文件
python3 ~/.hermes/scripts/context_index_system.py build

# 构建索引摘要
python3 ~/.hermes/scripts/context_index_system.py index

# 根据ID读取完整章节
python3 ~/.hermes/scripts/context_index_system.py resolve <section_id>

# 自动：build+index
python3 ~/.hermes/scripts/context_index_system.py auto
```

索引摘要示例：
```
## [8条永久规则]
  规则0(自主能力基线): 多路方案→核实质量→环境无关判断
  规则1(任务前回顾): 先查历史会话+全网信息+制定规划
  ...
## [关键章节索引]
  八、七条永久执行规则 → context_sections/八_七条永久执行规则.md (3127tokens)
  零、齿轮强制恢复协议 → context_sections/零_齿轮强制恢复协议.md (3849tokens)
```

### 2. context_auto_assoc.py（任务自动关联引擎）
```
位置: ~/.hermes/scripts/context_auto_assoc.py
cron: 每1分钟
输出: reports/context_auto_assoc.json + .md
```

功能：
- 分析当前任务意图（从wake_guide/task_current）
- 自动分类为 fix/push/develop/review/research/memory/security/collect/score/general
- 预加载与该任务类型相关的章节关键行摘要（不是全文）
- 跨轮次延续：上一轮用过的章节自动带入下一轮
- 工具完整语法保留（terminal含background参数说明等）

典型输出（fix任务）：
```
# Hermes 上下文索引（自动关联版）
任务类型: fix | 延续上一轮: 否

## [核心身份] Hermes - 格林主人的数字伙伴
## [永久禁令] 1禁批量 2禁降级 3禁Docker 4禁虚假 5必复盘
## [8条永久规则] 规则1~规则7

## [已预加载] (3个章节)
  八_七条永久执行规则: 597tokens → 完整: reports/context_sections/...(3127tokens)
  零_齿轮强制恢复协议: 779tokens → 完整: reports/context_sections/...(3849tokens)
  二永久禁令: 386tokens → 完整: reports/context_sections/...(473tokens)

## [工具] (7个)
  - terminal: 执行shell命令。背景用background=true
  - delegate_task: 多Agent并行调度。goal+context+toolsets。最多3子任务
  ...

## [当前任务]
  ID: self_enhance_1779860703
  下一步: continue_closed_loop
```

### 3. cross_session_cache.py（跨轮次缓存+输出更新）
```
位置: ~/.hermes/scripts/cross_session_cache.py
输出: reports/cross_session_cache.json
```

功能：
- 记录本轮对话用到了哪些章节
- 记录轮次计数（session_count自动递增）
- 从AI回复中自动提取"已完成项"和"下一步计划"
- 自动更新 task_current.json 和 wake_guide.json

## 对话流程

### 第一轮
```
auto_assoc分析任务意图 → 分类任务类型
  → 预加载相关章节的关键行摘要
  → 构建索引(1388t) + 预加载摘要(1762t) = 3150t
  → 传入AI
  → AI如需规则全文，从context_sections/<id>.md拉取
```

### 后续轮次
```
cross_session_cache检测到上一轮用过的章节
  → auto_assoc延续这些章节（continuity=True）
  → 只传增量变化 + 已用章节
  → AI回复后自动提取进度更新
```

## 测试结果（2026-05-27）
- 6组测试全部通过
- 10种任务类型全覆盖
- 信息无损验证11/11（核心身份/禁令/规则/工具/任务/齿轮/全文可达）
- 并发稳定性10次连续0错误
- 5轮真实对话模拟全部成功
- 单次执行<0.02秒

## 与旧系统的关系
- context_packer.py → 保留为降级方案（旧压缩器）
- surgical_context_slicer.py → 保留为降级方案（旧切分器）
- context_auto_assoc.py → 当前主方案（新关联引擎，推荐使用）
