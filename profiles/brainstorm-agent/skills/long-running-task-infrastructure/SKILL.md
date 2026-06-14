---
name: long-running-task-infrastructure
description: >-
  长程复杂多进程任务基础设施 — 段切换检查点/记忆分层/段摘要传递/
  token优化/长程漂移检测/任务队列管理。
  Hermes在持续多天/多段对话中的可靠性保障。
category: autonomous-systems
---

# 长程复杂多进程任务基础设施

## 核心问题域

Hermes在进行长程复杂任务时（持续多天、多段、多子进程），需要6类基础设施保障：

| 问题 | 症状 | 解决方案 |
|------|------|---------|
| 段切换失忆 | 段2不知道段1做了什么 | 段摘要传递到cross_session_cache |
| 检查点丢失 | 中断后所有进度丢失 | segment_manager自动保存到checkpoint_recorder |
| token膨胀 | 每轮重复注入固定信息 | 摘要行提取+按需索引 |
| 记忆空转 | L1/L2/L3无新数据 | post_conversation触发L1提取 |
| 任务漂移 | 做到一半偏离目标 | gear_enforcer每5段检测漂移 |
| 多进程瓶颈 | delegate_task只能并行3个 | task_queue_manager(并发5,重试3) |

## 1. 段摘要传递（segment_manager + cross_session_cache）

### 机制

当segment_manager达到50轮阈值触发`_rotate_segment()`时:
1. 生成交接笔记(handoff) — 包含本段完成的任务和关键决策
2. 同步到cross_session_cache.json — `csc["last_segment_handoff"] = handoff`
3. 保存到checkpoint_recorder — `checkpoint_recorder.py save "segment_X" "描述"`
4. 重置段状态 — turn_in_segment=0, 清空当前段任务列表

### 关键代码

```python
def _rotate_segment(self):
    handoff = self._generate_handoff(old_segment)
    # 保存到cross_session_cache
    csc["last_segment_handoff"] = handoff
    csc["last_segment_id"] = old_segment
    csc["new_segment_id"] = new_segment
    # 保存到checkpoint_recorder
    subprocess.run(["python3", "checkpoint_recorder.py", "save", ...])
```

### 陷阱

- 检查点只在段达到50轮时才会触发。当前段如果只有几轮，检查点不会自动产生。
- 手动测试: `python3 checkpoint_recorder.py save "test" "description"`
- 手动查看: `python3 checkpoint_recorder.py status`

## 2. 强制上下文token优化

### 原理

PRE插件的21个输出全部注入system prompt。但11个插件输出固定信息(4740 chars/2844 tokens)。
优化策略: 只提取每行中的关键摘要。

### 优化方法

```python
def _run_script_module_subprocess(mod, contexts):
    out = subprocess.run([sys.executable, mod_path], ...)
    lines = [l.strip() for l in out.split('\n') if l.strip()]
    # 找有关键词的行作为摘要
    for l in lines:
        if any(kw in l for kw in ['✅', '❌', '⚠️', '→', 'task_type',
                                   'session_count', 'signal=']):
            summary = l[:150]
            break
    contexts.append(f"[{mod_name}] {summary}")
```

forced_executor的输出同样压缩:
```
旧: 500+chars详细报告(系统强制执行报告+各阶段详情+武器列表)
新: 一行摘要+核心约束
```

### 效果

| 指标 | 优化前 | 优化后 | 节省 |
|------|-------|-------|------|
| 每轮注入 | 6767 chars (4060 tokens) | 2045 chars (1227 tokens) | **69%** |
| 50轮一段 | ~338K chars (~203K tokens) | ~102K chars (~61K tokens) | **~142K tokens** |

### 核心约束保留清单

压缩后必须保留的核心约束:
- `🔴X武器×Y阶段已系统执行`
- `基于结果汇报,禁止输出示例,禁止说我来执行`
- 武器库数量
- 安全检查结果
- 段状态

## 3. 长程漂移检测

### 机制

gear_enforcer的Phase 0中, 每5段调用一次meta_thinker_auto()。

```python
if current_seg > 0 and current_seg % 5 == 0 and seg_turns == 0:
    mt_result = meta_thinker_auto()
    drift_score = mt_result.get("drift_score", 0)
    if drift_score > 0.5:
        log("⚠️ 漂移分数={drift_score:.2f} > 0.5")
```

### 触发条件

- 段数 > 0
- 段数能被5整除
- 该段刚开始(turns_in_segment == 0)

### meta_thinker.py

位置: `scripts/meta_thinker.py`
已有漂移检测和自动恢复逻辑, gear_enforcer中已引用。

## 4. 任务队列管理器

### 原理

delegate_task只能并行3个, 没有持久化、重试、依赖管理。
task_queue_manager.py填补这个空白。

### 架构

```
SQLite (reports/task_queue.db)
  └── tasks 表: id, name, command, status, priority, retries, depends_on
  └── task_log 表: task_id, ts, message

gear_enforcer每轮 → task_queue_manager process
  → 检查运行中的任务数(MAX=5)
  → 取出待处理任务(按优先级)
  → 检查依赖是否完成
  → 后台线程执行
```

### 命令

```bash
python3 scripts/task_queue_manager.py submit <name> "<command>" [priority]
python3 scripts/task_queue_manager.py process     # 队列处理
python3 scripts/task_queue_manager.py status      # 查看所有任务
python3 scripts/task_queue_manager.py cancel <id>
python3 scripts/task_queue_manager.py retry <id>
```

### 配置

```python
MAX_CONCURRENT = 5   # 最多5个并行任务
MAX_RETRIES = 3       # 最多重试3次
```

## 5. lossless_claw无损压缩

### 接入

注册到post_conversation, 每次对话后自动运行。

```python
def _run_lossless_compression(mod, contexts):
    compressor = mod.LosslessClawCompressor()
    compressor.status()   # 检查是否需要压缩
    compressor.compress() # 执行压缩
```

### 文件

- 代码: `scripts/lossless_claw.py` (13136 bytes)
- 触发: 在`agent_enhancement_manager.py`的PLUGIN_REGISTRY + _PLUGIN_CALLERS中注册

## 6. 记忆分层修复(L1提取)

### 问题

L1提取仅靠cron每2h触发, 但检测到0条新事实 -> L2/L3从未触发。

### 修复

在`agent_enhancement_manager.py`的post_conversation中添加:

```python
def _run_l1_extractor(mod, user_message):
    # 尝试调用extract()传入用户消息
    if hasattr(mod, 'extract'):
        result = mod.extract(user_message)
    # 降级: 调用main() --auto
    subprocess.run([sys.executable, mod_path, '--auto'], ...)
```

### 注册

```python
_PLUGIN_CALLERS["l1_extractor"] = lambda mod, ctx: _run_l1_extractor(mod, user_message)
```

## 触发条件

加载此技能的触发词:
- 长程任务/长对话/多天任务/持续任务
- 段切换/段摘要/段失忆
- 检查点/断点/checkpoint_recorder
- token节省/压缩/上下文太大/system prompt膨胀
- 漂移检测/纠偏/meta_thinker
- 多进程/并行任务/队列管理/task_queue
- 无损压缩/lossless_claw
- 记忆分层空转/L1空转/L2空转/L3空转

## 关键陷阱

1. **检查点自动触发条件**: 只在segment_manager达到50轮时触发。手动测试: `checkpoint_recorder.py save`
2. **漂移检测触发条件**: 段数≥5且能被5整除且该段刚开始。当前段2, 距触发还差3段。要等。
3. **task_queue_manager的后台线程**: 使用`threading.Thread(daemon=True)` — Hermes主进程退出时线程也会退出。确保任务足够短(不超过主进程生命周期)。
4. **token优化保留核心约束**: 压缩到2045 chars后, 强制约束"基于结果汇报,禁止输出示例"必须保留。不能为了省token丢掉约束。
5. **L1提取的两种方式都要**: cron触发(读日志)+post_conversation触发(实时)。只做一个不够。
