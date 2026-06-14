# 上下文压缩配置（2026-06-11 上线 — force_compressor插件强制执行）

## 核心变更：skill定义 + cron脚本 → 系统插件强制压缩

**之前：**
- lossless-claw-compression / lossless-claw-v2 / infinite-dialogue-context-management 等4个skill定义完善
- context_packer.py cron每1分钟运行，生成压缩包
- context_auto_assoc.py 生成章节索引
- 但所有产出**没人用** — context_packer.json生成了但不注入到对话上下文

**现在：**
- force_compressor 插件通过 pre_context_load + post_tool_call 双hook注入
- pre_context_load: 每轮对话开始前强制读context_packer.json，注入压缩指令集
- post_tool_call: 每5轮Level 1差分压缩 | 每30分钟Level 2统计 | 每日03:00 Level 3归档
- cron每1分钟检测插件激活状态

## 三层压缩策略

### Level 1 (每5轮 — 差分压缩)
- 触发：post_tool_call hook检测到turn_count % 5 == 0
- 方法：差分压缩（仅存储变化部分）
- 目标：压缩当前会话上下文

### Level 2 (每30分钟 — 统计压缩)
- 触发：时间差 > 1800秒
- 方法：基于频率和重要性的选择性压缩
- 保留高频引用段完整，压缩低频段

### Level 3 (每日03:00 — 归档压缩)
- 触发：cron定时
- 方法：完整归档 + 老化清理
- 超过7天的低价值段自动归档

## 校验和验证
每次压缩生成SHA256校验和，下次加载时验证无损。
发现异常自动回滚到上一个有效版本。

## 段式切换架构（每50轮）
不追求"每轮都小"，而是"每N轮重建上下文"。
每段~50轮，段切换时通过三明治协议传递三层信息：
1. 任务断点（wake_guide.json）
2. 关键决策链（最近10条任务+最近5条决策）
3. 完整轨迹归档（到文件，按需读取）

## 不可绕过条款
- force_compressor 通过pre_context_load hook注入Hermes系统底层
- cron每分钟检测插件状态，未激活自动重启
- 不可关闭/绕过
- 违反者视为系统严重缺陷

## 相关文件
- ~/.hermes/plugins/force_compressor/__init__.py — 插件代码
- ~/.hermes/scripts/context_packer.py — 上下文打包脚本(cron每1分钟)
- ~/.hermes/scripts/compression_fidelity_validator.py — 校验和验证(cron每10分钟)
- ~/.hermes/scripts/gear_context_compressor.py — 齿轮压缩器(cron每5分钟)
- ~/.hermes/reports/context_pack.json — 压缩产出
- ~/.hermes/logs/compressor/ — 压缩日志