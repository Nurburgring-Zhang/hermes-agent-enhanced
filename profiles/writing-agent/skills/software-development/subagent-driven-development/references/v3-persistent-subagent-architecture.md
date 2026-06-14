# V3 持久化子Agent架构参考 (2026-05-20)

本文件记录 Hermes evolution_v3 中实现的**物理级子Agent管理系统**。
与 subagent-driven-development 的 delegate_task 子Agent不同，
这里实现的是自有生命周期、持久化状态、文件沙箱的独立Agent运行时。

## 架构对比: delegate_task vs 物理子Agent

| 维度 | delegate_task子Agent | evolution_v3子Agent |
|------|---------------------|---------------------|
| 生命周期 | 单个任务完成即销毁 | 持久化可跨会话恢复 |
| 上下文 | 一次性传递 | 独立上下文窗口+压缩 |
| 沙箱 | 无 | 文件系统隔离(3目录+ACL) |
| 监控 | 无 | 15秒心跳/120秒僵尸检测 |
| 持久化 | 无 | SQLite状态+任务队列 |
| Hooks | 无 | SubagentStart/Stop事件 |

## 文件位置

```
~/.hermes/evolution_v3/
  subagent_manager.py  (33KB 主管理器)
  hooks_engine.py      (27KB 事件引擎)
  v3_daemon.py         (8KB 守护进程)
```

## 子Agent定义注册

```python
from subagent_manager import SubAgentDefinition

definition = SubAgentDefinition(
    name="my_agent",
    description="自定义Agent描述",
    system_prompt="你是专业助手",
    allowed_tools=["terminal", "file", "search"],
    max_context_tokens=4096,
    timeout_seconds=300,
    sandbox_enabled=True,
)
manager.register_definition(definition)
```

## 生命周期

```python
# 启动
r = manager.spawn("agent_name", "task_id", "session_id")
# 自动执行10步模拟

# 停止
manager.stop_agent("agent_name", "task_id")

# 监控
manager.list_running()
manager.get_queue_stats()
manager.health_report()
```

## 沙箱

```python
s = runtime.sandbox
s.write_file("work/result.txt", "内容")
s.read_file("work/result.txt")
s.list_files()
s.stats()
s.cleanup()
```

路径穿越防护自动生效。
