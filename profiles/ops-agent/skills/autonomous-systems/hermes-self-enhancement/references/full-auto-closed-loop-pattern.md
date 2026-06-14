# 全自动闭环循环模式 (Closed-Loop Auto-Enhancement)
## 从本会话(2026-05-18)实战验证的设计模式

### 问题
实现了N个脚本,每个单独测试通过,但实际运行时需要手动触发。
用户要求"全自动运行",而"能手动调用"不等于"全自动"。

### 解决方案: 双层cron物理强制

#### 上层: gear_enforcer.py v2.0 (每1分钟)
```
文件: ~/.hermes/scripts/gear_enforcer.py (425行)
cron: * * * * *
```

7阶段全自动, 不依赖Hermes记忆:

```
Phase 1: ContextManager 热/温/冷自动更新
  → 读取 current_context.txt → context_manager.py add
  → 每5轮自动触发压缩

Phase 2: MetaThinker 漂移检测
  → 读取 task_goal.txt
  → 读取 current_context.txt
  → meta_thinker.py check
  → drift_score > 0.5 → 触发 ContextEquilibria 自动恢复

Phase 3: MemoryOrchestrator 三引擎存储
  → 三引擎并行存储(LCM DAG + Mem0 + Hindsight)
  → LCM DAG 摘要节点自动创建(每5条消息)

Phase 4: EncryptionLayer + AuditLogger
  → 检查加密队列 → 自动加密敏感文件
  → 写入每日审计摘要
  → 验证审计链完整性

Phase 5-6: LCM DAG校验 + 三引擎健康检查

Phase 7: 中断任务检测恢复
  → 检查 gear_checkpoint.json + task_current.json
  → 发现中断 → 写 GEAR_INTERRUPT_ALERT.json
```

#### 下层: self_enhance_loop.py (每5分钟)
```
文件: ~/.hermes/scripts/self_enhance_loop.py (361行)
cron: */5 * * * *
```

8步闭环, 更深入、更完整:

```
Step 1: ContextManager热/温/冷
Step 2: 三引擎并行存储
Step 3: LCM DAG自动摘要
Step 4: MetaThinker漂移检测 + 分数解析
Step 5: ContextEquilibria自动恢复(漂移>0.5时)
Step 6: EncryptionLayer加密敏感文件
Step 7: AuditLogger写入本轮操作 + 链验证
Step 8: 最终完整性校验(3/3引擎+上下文)
```

#### 闭环架构图

```
物理层(cron)
  ├─ * * * * * gear_enforcer.py (轻量,7阶段)
  │   ├─ ContextManager更新
  │   ├─ 漂移检测+恢复
  │   ├─ 三引擎存储
  │   ├─ 加密+审计
  │   ├─ LCM DAG校验
  │   ├─ 三引擎健康
  │   └─ 中断检测
  │
  ├─ */5 * * * * self_enhance_loop.py (完整,8步)
  │   ├─ ContextManager
  │   ├─ 三引擎存储
  │   ├─ LCM摘要
  │   ├─ 漂移检测
  │   ├─ 自动恢复
  │   ├─ 加密
  │   ├─ 审计
  │   └─ 完整性校验
  │
  └─ 其他监控齿轮
      ├─ G8: 三引擎健康(5min)
      ├─ G6: 全链验证(30min)
      ├─ LCM DAG: verify(30min)
      ├─ MetaThinker: 日志摘要(30min)
      └─ AuditLogger: 摘要(6h)

检测→执行→审计→校验
        ↕
  恢复→再检测→再执行
```

### 关键实现细节

#### gear_enforcer.py 的 context_manager_auto 方法

关键设计: **每次读取 current_context.txt + 哈希比较去重**

```python
def context_manager_auto(self):
    ctx_file = REPORTS / "current_context.txt"
    if not ctx_file.exists():
        return
    
    content = ctx_file.read_text()
    current_hash = str(hash(content))
    last_hash_file = REPORTS / ".last_context_hash.txt"
    if last_hash_file.exists() and last_hash_file.read_text() == current_hash:
        return  # 无变化,跳过
    
    # 解析 USER:/ASSISTANT: 格式
    run("context_manager.py", ["add", user_msg, assistant_msg])
    last_hash_file.write_text(current_hash)  # 标记已处理
```

#### meta_thinker_auto 方法

**关键**: 读取 `task_goal.txt` + 自动调用 check + 解析返回结果中的 drift_score

```python
def meta_thinker_auto(self):
    task_info = get_active_task()
    if not task_info["task_id"]:
        return
    goal_file = REPORTS / "task_goal.txt"
    if not goal_file.exists():
        return
    goal = goal_file.read_text().strip()
    r = run("meta_thinker.py", ["check", "--goal", goal[:200], "--context", ctx[:500]])
    # 解析 stdout 中的漂移分数
    for line in r["stdout"].split('\n'):
        if "综合漂移分数" in line:
            drift_score = float(line.split(':')[1].strip())
    if level in ("critical", "fail"):
        run("context_equilibria.py", ["restore", task_info["task_id"], "--goal", goal[:200]])
```

#### self_enhance_loop.py 的加密方法

**关键**: 自动查找并加密敏感检查点文件

```python
def step_6_encrypt_sensitive(self):
    sensitive_files = [
        REPORTS / "gear_checkpoint.json",
        REPORTS / "task_current.json",
    ]
    for f in sensitive_files:
        if f.exists() and f.stat().st_size > 100:
            run("encryption_layer.py", ["encrypt", str(f)])
```

### 避免的陷阱

1. **❌ "实现了脚本,测试通过了,以为自动完成了"**  
   → 必须注册cron + 验证cron可执行

2. **❌ 只注册一个cron,但脚本只包含部分功能**  
   → 两个cron互补: 1分钟轻量 + 5分钟完整

3. **❌ 依赖Hermes主动调用来触发闭环**  
   → cron是物理层, Hermes不工作时也能运行

4. **❌ 测试失败时不区分是功能问题还是测试匹配问题**  
   → 先手动验证功能, 确认再修测试case

### 本会话验证结果

```
gear_enforcer v2.0:  7阶段全部通过, 1分钟一次
self_enhance_loop:   8步全部通过, 5分钟一次
持续运行时间: 立即生效(cron已注册)
输出日志: logs/gear_enforcer.log, logs/self_enhance_loop.log
运行历史: reports/self_enhance_report.json, reports/closed_loop_history.json
```
