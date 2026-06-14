---
name: system-code-consolidation
description: 多脚本整合工作流 — 评估代码重叠 → 提取共享配置 → 合并 → 替换cron → 安全删除旧代码。适用于cron冗余、功能重复、碎片化代码库清理。
trigger: 代码碎片化、脚本重复、cron重叠、对话框弹出两次、多个脚本做同一件事、功能重复、新旧系统混跑、启动两遍自检
---

# 系统代码整合工作流

### Absorbed Skills (consolidated)

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `cron-audit-and-cleanup` | Subsection — Cron-level audit and cleanup (diagnose → group → keep best → safe-delete → verify) | `references/cron-audit-and-cleanup-skill.md` |

The absorbed skill covers the cron-job-layer audit workflow. Per the shared documentation between the two skills: when cron cleanup involves script code consolidation, start with cron-audit-and-cleanup (remove duplicate cron jobs), then use this skill (system-code-consolidation) to merge the underlying scripts. See `references/cron-audit-and-cleanup-skill.md` for the cron-specific audit protocol.

## 何时使用

## 触发条件
- 用户提及部署、安装、配置服务时
- 需要调试系统环境或依赖时
- 执行系统运维操作时


- 用户反馈"为什么启动了两遍"、"命令在后台运行" — 大概率是重复cron
- 发现多个脚**维护了同一份逻辑**（如 classify_task() 出现3次）
- 多个脚本写同一DB但表名不同（如 active_memory.db 有3套记忆表）
- cron列表中同一功能出现多次
- 系统有新旧两套架构同时在跑（短hex job_id vs UUID job_id）

## 工作流程（6步）

### 第一步：全景扫描
列出所有活跃cron及其调用的脚本：
```python
cronjob(action='list')  # 获取全部cron
```
标注每个cron的：job_id格式（短hex / UUID）、script路径、schedule、deliver、no_agent标记。

同时扫描 `scripts/` 和根目录，确认哪些脚本存在、行数、最后修改时间：
```bash
ls -la scripts/*.py
```

### 第二步：按功能分组 + 代码评估
按功能类型分组，对每组：
1. **read_file 所有涉及的脚本**，理解每个的功能
2. **评估代码质量**：真实实现 vs 占位符、错误处理、硬编码程度、重叠度
3. **列出重叠项**：常见的重叠模式：
   - **classify_task() 重复** — 多份独立维护的关键词→类型映射
   - **task_type→rules/tools/sections 映射重复** — 多份硬编码字典
   - **DB连接+表初始化重复** — 每脚本自己写 get_conn()/init_db()
   - **同功能不同命名** — ultimate-collector vs mega-collector

### 第三步：设计整合方案
决策树：
- **功能完全重叠**（如 auto_resume_check 被 task_monitor 覆盖）→ 直接删除，合并到目标
- **功能部分重叠**（如 slicer + auto_assoc 共享 classify_task 但输出不同）→ **提取共享配置为 JSON**，各自引用
- **功能互补但可整合**（如 guardian.py 采集 + ultimate_collector 更多源）→ 设计插件/调用链

关键原则：
1. **提取共享数据源** — 将硬编码的映射/配置抽成独立 JSON（如 task_type_config.json）
2. **只保留一个 classify_task()** — 三份映射表→一份数据源+一个分类函数
3. **备份旧代码** — 删除前必须备份到 `/mnt/d/Hermes/备份/`

### 第四步：实现整合
1. 创建共享配置 JSON（如 `reports/task_type_config.json`）
2. 创建整合后脚本（如 `context_pipeline.py` 合并 slicer+auto_assoc）
3. 新脚本支持 `--mode=xxx` 区分旧功能

### 第五步：替换cron + 删除旧代码
1. 删除旧cron job：
   ```python
   cronjob(action='remove', job_id='<old_id>')
   ```
2. 创建新cron job：
   ```python
   cronjob(action='create', name='...', script='scripts/new_script.py', schedule='* * * * *', no_agent=True, deliver='local')
   ```
3. 备份后删除旧脚本：
   ```bash
   cp scripts/old_script.py /mnt/d/Hermes/备份/ && rm scripts/old_script.py
   ```

### 第六步：验证
对每个整合步骤：
1. **手动运行新脚本** — 确认输出正常、无报错
2. **运行旧脚本的一个保留版本** — 确认行为一致
3. **如果有 cron，等待一次调度或手动触发** — 确认安静执行无异常

## 常见整合模式

### 模式A：映射表合并
```
旧: script_A.py 有 classify_task() + TASK_SECTION_MAP 字典
旧: script_B.py 有 classify_task() + TASK_SECTION_MAP 字典（90%相似）
新: reports/task_type_config.json（统一数据源）
新: script_merged.py 引用 task_type_config.json
```
适用于：上下文切分器、任务分类器、规则路由等。

### 模式B：采集器整合
```
旧: guardian.py cycle 模式调用 unified_v5（10平台）
旧: ultimate_collector.py 额外调用微信/小红书/RSS（20+源）
新: guardian.py 在 auto_collect() 中增加调用 ultimate_collector --all
```
适用于：采集管道、推送管道等有上下游关系的功能。

### 模式C：记忆系统合并
```
旧: structmem_memory.py 写 structmem_* 表（active_memory.db）
旧: lossless_claw_v2.py 写 mp_* 表（active_memory.db）
旧: hermes_memory_engine_v2.py 写 memory_* 表（active_memory.db）
新: 统一 schema 管理 + 单一写入入口
```
适用于：多套代码写同一DB但表名冲突时。

## 常见陷阱

### ⚠️ 同名文件不同目录
cron的 `script` 路径可能是 `task_monitor.py`（根目录）或 `scripts/task_monitor.py`。Hermes cron 默认 workdir 是 `~/.hermes`，两种写法都可能指向 `scripts/` 下的同一文件。**不要凭路径不同就以为是不同脚本**。

### ⚠️ no_agent vs agent 模式的 cron
`no_agent=true` 的 cron 输出直接到终端，不会进 Hermes 会话。多份同功能的 no_agent cron 就是"对话框弹出两次"的根本原因。
解决办法：同一脚本只保留一个 no_agent cron。

### ⚠️ 旧系统残留
Hermes cron 有两种 ID 格式：短hex（旧版）和 UUID（新版）。同功能可能各注册一次。顺便清理。

### ⚠️ 保守删旧
删除前一定要备份。即使新脚本已验证通过，旧脚本仍可能被其他 cron/脚本引用。先移除非关键路径的 cron，逐步替换。

### ⚠️ 验证不能跳过
用户明确要求"先验证，再继续"。每一轮整合后必须：
1. 跑新脚本看输出
2. 确认不产生多余输出（静默或只有 header）
3. 确认旧功能还在（输出结构与之前一致）

### ⚠️ 瀑布式版本清理（2026-05-27实战）
当清理同一功能的多个迭代版本（如微信采集器v3→v9共12个）：
1. 用 `ls -lt *.py | grep pattern` 按修改时间排序，识别最新版
2. 每个功能组保留最新1-2个版本
3. 备份所有删除文件到 `/mnt/d/Hermes/备份/`
4. 验证没有cron引用旧文件名：`grep -r "old_name" scripts/*.py`
5. 本次实战成果：减少54个文件，258→204

详见 `references/collector-version-waterfall-cleanup-20260527.md`

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
