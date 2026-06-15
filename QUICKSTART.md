# Hermes Agent Enhanced -- 5分钟快速上手

> 目标：在 5 分钟内完成环境搭建、导入验证、并运行第一个 Loop/ Actor。

## 前提条件

- Python >= 3.10
- Git
- 至少一个 LLM API Key（DeepSeek / OpenAI / Anthropic）

## Step 1: 克隆并安装（60 秒）

```bash
# 1. 克隆仓库
git clone git@github.com:Nurburgring-Zhang/hermes-agent-enhanced.git
cd hermes-agent-enhanced

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -e .

# 4. 验证版本
python3 -c "import hermes_agent; print(hermes_agent.__version__)"
# 输出: 0.16.0
```

## Step 2: 配置 API Key（30 秒）

```bash
# 设置至少一个 API Key
export DEEPSEEK_API_KEY="your-deepseek-key"
# 或
export OPENAI_API_KEY="your-openai-key"
# 或
export ANTHROPIC_API_KEY="your-anthropic-key"

# 验证 Key 可用
python3 -c "
import os
keys = [k for k in ['DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY'] if os.getenv(k)]
print(f'Available keys: {len(keys)}') if keys else print('WARNING: No API keys found!')
"
```

## Step 3: 第一个 Actor（60 秒）

创建文件 `my_first_actor.py`：

```python
#!/usr/bin/env python3
"""我的第一个 Hermes Actor"""

from scripts.actor_base import Actor, Event

# 1. 定义 Actor
class GreeterActor(Actor):
    def __init__(self):
        super().__init__(
            actor_id="greeter",
            name="Greeter",
            capabilities=["greeting.hello"],
            description="A friendly greeter actor",
        )

    def handle(self, event: Event):
        name = event.payload.get("name", "World")
        return {"greeting": f"Hello, {name}!"}

# 2. 创建并测试
greeter = GreeterActor()
event = Event(type="greeting.hello", payload={"name": "Hermes"})

# 直接调用（单 Actor）
result = greeter.handle_with_metrics(event)
print(f"Result: {result}")
print(f"Metrics: {greeter.metrics.success_rate * 100:.1f}% success")
```

运行:

```bash
cd ~/.hermes/scripts
python3 ../../my_first_actor.py
# 输出:
# Result: {'greeting': 'Hello, Hermes!'}
# Metrics: 100.0% success
```

## Step 4: Actor + SynapseBus（60 秒）

创建 `my_first_bus.py`：

```python
#!/usr/bin/env python3
"""Actor 通过 SynapseBus 通信"""

from scripts.actor_base import Actor, Event
from scripts.synapse_bus import SynapseBus

# 1. 创建总线
bus = SynapseBus()

# 2. 注册 Actor
class EchoActor(Actor):
    def __init__(self):
        super().__init__("echo", "Echo", ["echo.message"])

    def handle(self, event: Event):
        return {"echo": event.payload.get("message", "")}

bus.register_actor(EchoActor(), ["echo.message"])

# 3. 发射事件
results = bus.emit("echo.message", {"message": "Hello Bus!"})
print(f"Results: {results}")

# 4. 查看 Actor 列表
for actor in bus.list_actors():
    print(f"  Actor: {actor.id} ({actor.status.value})")
```

运行:

```bash
cd ~/.hermes/scripts
python3 ../../my_first_bus.py
# 输出:
# Results: [('echo', {'echo': 'Hello Bus!'})]
#   Actor: echo (active)
```

## Step 5: 第一个 Loop（90 秒）

创建 `my_first_loop.py`：

```python
#!/usr/bin/env python3
"""第一个 Loop Engineering 循环"""

import asyncio
from scripts.loop_engine import (
    LoopEngine, LoopDefinition,
    TaskNode, TaskEdge, TaskGraph,
    TriggerConfig, TriggerType,
)

# 1. 创建引擎
engine = LoopEngine()

# 2. 定义任务图
nodes = [
    TaskNode(id="step1", name="Fetch Data", description="获取数据"),
    TaskNode(id="step2", name="Process", description="处理数据",
             depends_on=["step1"]),
    TaskNode(id="step3", name="Notify", description="发送通知",
             depends_on=["step2"]),
]
edges = [
    TaskEdge(from_node="step1", to_node="step2"),
    TaskEdge(from_node="step2", to_node="step3"),
]
graph = TaskGraph(loop_id="demo_loop", nodes=nodes, edges=edges)

# 3. 创建 Loop 定义
loop_def = LoopDefinition(
    loop_id="demo_loop",
    name="Demo Loop",
    description="My first loop",
    trigger=TriggerConfig(trigger_type=TriggerType.MANUAL),
    task_graph=graph,
)

# 4. 注册并执行
engine.register_loop(loop_def)

async def main():
    result = await engine.run_loop("demo_loop")
    print(f"Success: {result.success}")
    print(f"Completed: {result.completed_nodes}")
    print(f"Duration: {result.total_duration_seconds}s")
    print(f"Errors: {result.errors}")

asyncio.run(main())
```

运行:

```bash
cd ~/.hermes/scripts
python3 ../../my_first_loop.py
# 输出:
# Success: True
# Completed: ['step1', 'step2', 'step3']
# Duration: 0.01s
# Errors: []
```

## Step 6: 使用公共工具库（30 秒）

```python
#!/usr/bin/env python3
"""使用 hermes_utils 公共工具"""

from scripts.hermes_utils import (
    safe_to_dict, truncate, format_duration,
    ErrorMessages, get_hermes_logger,
)

# 1. 使用统一序列化
from dataclasses import dataclass
@dataclass
class MyData:
    name: str
    value: int

d = MyData("test", 42)
print(f"safe_to_dict: {safe_to_dict(d)}")

# 2. 字符串工具
print(f"truncate: {truncate('long text here', 8)}")

# 3. 时间格式化
print(f"format_duration: {format_duration(125.7)}")

# 4. 统一错误消息（带 Action 建议）
print(f"Error example: {ErrorMessages.CONFIG_NOT_FOUND}")

# 5. 日志
logger = get_hermes_logger("my_app")
logger.info("Hello from my app!")
```

## 常见问题

### Q: ImportError: No module named 'scripts'
**A:** 确保在 `~/.hermes/` 目录下运行，或将 scripts 加入 `PYTHONPATH`:
```bash
export PYTHONPATH="$HOME/.hermes:$PYTHONPATH"
```

### Q: ModuleNotFoundError: No module named 'pydantic'
**A:** 运行 `pip install -e .` 安装所有依赖。

### Q: API 调用失败
**A:** 检查 API Key 是否正确设置:
```bash
echo $DEEPSEEK_API_KEY | head -c 10
# 应输出 Key 的前10个字符
```

## 下一步

- 完整文档详见 [README.md](README.md)
- API 参考详见 [API_REFERENCE.md](API_REFERENCE.md)
- 弹性模式详见 `scripts/resilience_patterns.py`
- 三省六部详见 `scripts/synapse_bus.py` + `scripts/actor_base.py`
- 质量报告详见 [QUALITY_REPORT.md](QUALITY_REPORT.md)

---

*Hermes Agent Enhanced -- 构建可靠的AI Agent系统*
