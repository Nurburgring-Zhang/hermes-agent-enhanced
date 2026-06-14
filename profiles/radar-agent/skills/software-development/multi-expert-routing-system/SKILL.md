---
name: multi-expert-routing-system
description: Implement a multi-expert agent system with automatic routing, isolated workspaces/memory, and inter-expert collaboration. Complete implementation from concept to integration.
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["multi-agent", "routing", "expert-system", "isolation", "collaboration"]
---

# Multi-Expert Agent System

Complete implementation of a multi-expert agent system with routing, isolation, and collaboration capabilities.

## When to Use

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


When you need to implement a system where multiple specialized AI agents (experts) handle different types of tasks, with:
- Automatic routing based on message content
- Isolated workspaces and memory per expert
- Expert-to-expert collaboration
- Configuration-driven expert definitions
- CLI management commands

## Approach

### 1. Analyze Existing Configuration

Read the source configuration (OpenClaw format in this case) to identify experts:

```python
with open(openclaw_config_path, 'r') as f:
    config = json.load(f)
agents_list = config.get("agents", {}).get("list", [])
```

Each agent has:
- `id` - unique identifier
- `model` - model to use
- `workspace` - working directory
- `tools` - tool whitelist/allow list
- Optional: `default`, `name`, `description`

### 2. Design Expert Configuration Structure

Create a configuration dataclass:

```python
@dataclass
class ExpertConfig:
    id: str
    name: str
    description: str
    model: str
    tools_whitelist: List[str]
    workspace: str
    memory_path: str
    capabilities: List[str]
    routing_keywords: List[str]
    default: bool = False
```

### 3. Create Manager Class

The `ExpertManager` handles:
- Loading config from OpenClaw or Hermes config
- Creating/maintaining expert definitions
- Routing logic (keywords + complexity)
- Workspace and database initialization

Key methods:

```python
def route_message(self, message: str) -> ExpertConfig:
    """Route to appropriate expert based on keywords, complexity, or default"""

def initialize_expert_workspace(self, expert: ExpertConfig):
    """Create workspace dir and SQLite memory database"""

def _init_memory_db(self, db_path: Path):
    """Initialize SQLite with memories, sessions, knowledge tables"""
```

### 4. Expert Session Isolation

Create `ExpertSession` class that:
- Encapsulates expert's workspace and memory path
- Provides `get_enabled_tools()` to filter tools by whitelist
- Saves/loads memories and sessions to expert's private database

```python
class ExpertSession:
    def __init__(self, expert: ExpertConfig, session_id: str = None):
        self.expert = expert
        self.workspace = Path(expert.workspace)
        self.memory_path = Path(expert.memory_path)

    def get_enabled_tools(self, all_tools: Dict) -> List[str]:
        """Filter available tools by expert's whitelist"""
```

### 5. Routing Strategy

Three-tier priority:
1. **Expert Match** - keyword matching in message
2. **Smart Routing** - complexity analysis for non-matching messages
3. **Default Expert** - fallback

Keyword matching:
```python
def _match_by_keywords(self, message: str) -> Optional[ExpertConfig]:
    message_lower = message.lower()
    for expert in self.experts.values():
        for keyword in expert.routing_keywords:
            if keyword.lower() in message_lower:
                return expert
    return None
```

Complexity heuristic:
```python
def _is_complex_task(self, message: str) -> bool:
    complex_indicators = ["plan", "步骤", "analyze", "代码", "implement", ...]
    complexity_score = sum(1 for ind in complex_indicators if ind in message_lower)
    return complexity_score >= 2 or len(message) > 200
```

### 6. Expert Collaboration

Enable experts to delegate to each other:

```python
def request_expert_assistance(
    requesting_expert: ExpertConfig,
    task: str,
    target_expert_id: str,
    context: Dict = None
) -> Dict:
    """Create subagent with target expert's configuration"""
    subagent = AIAgent(
        model=target_expert.model,
        workspace=str(target_expert.workspace),
        memory_path=target_expert.memory_path,
        ...
    )
    result = subagent.chat(task)
    return {"success": True, "expert": target_expert_id, "response": result}
```

### 7. Configuration Structure

Extend `~/.hermes/config.yaml`:

```yaml
agents:
  defaults:
    model: {primary, fallbacks}
    workspace: ~/.hermes/workspace
    memory_search: {enabled, provider, model}
  list:
  - id: main
    name: 通用主代理
    model: openrouter/qwen/qwen3.6-plus:free
    workspace: ~/.hermes/workspace/main
    memory: ~/.hermes/memory/main.sqlite
    tools:
      allow: [web_search, exec, ...]  # or profile: full
    capabilities: [general, conversation, ...]
    routing_keywords: [帮助, help, ...]
    default: true
  # ... other experts
```

### 8. Database Schema

Each expert gets a private SQLite database:

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    expert_id TEXT NOT NULL,
    messages TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 9. CLI Integration

Add commands to `COMMAND_REGISTRY`:

```python
CommandDef("agents", "Manage expert agents: list, switch, test", "Agents",
           args_hint="[list|switch|test] [expert_id]",
           subcommands=("list", "switch", "test", "info")),
CommandDef("expert", "Set expert for this session", "Agents",
           args_hint="[expert_id]", cli_only=True),
```

Implement handlers in `HermesCLI.process_command()`:

```python
elif canonical == "agents":
    self._handle_agents_command(cmd_original)
```

### 10. Main Loop Integration

In the message processing flow:
1. Route message to expert: `expert, session_id = route_to_expert(message)`
2. Filter tools by expert's whitelist
3. Create AIAgent with expert's model, workspace, memory_path
4. Optionally set expert as default for session

## Implementation Notes

- **Workspace Isolation**: Each expert has `~/.hermes/workspace/{expert_id}` for file operations
- **Memory Isolation**: Each expert gets `~/.hermes/memory/{expert_id}.sqlite` for private data
- **Tool Filtering**: Tools are filtered based on `tools.allow` list; `profile: full` enables all
- **Global Sharing**: Experts can still access global memory via shared providers if configured
- **Session Persistence**: Each expert's conversations are saved to their own database
- **Subagent Delegation**: Use `request_expert_assistance()` to call other experts

## Pitfalls

1. **Module Import Paths**: When adding new modules to hermes-agent, ensure Python path includes agent directory.

2. **Config YAML Syntax**: Use `yaml.dump()` with `default_flow_style=False, sort_keys=False` for readable output.

3. **Database Locks**: SQLite databases can lock if multiple agents write to same file. Isolation prevents this.

4. **Tool Name Mapping**: OpenClaw tool names may differ from Hermes tool names. Map carefully:
   - OpenClaw: `web_search` → Hermes: `web_search`
   - OpenClaw: `exec` → Hermes: `terminal`
   - Validate against `get_tool_definitions()` keys

5. **Model Format**: OpenClaw uses `provider/model` format. Hermes typically uses the same. Ensure consistency.

6. **CLI Import Order**: Import expert_system after other Hermes modules to avoid circular dependencies.

## Testing

1. Initialize workspaces:
```bash
python ~/.hermes/scripts/init_experts.py
```

2. Verify config:
```bash
cat ~/.hermes/config.yaml
```

3. Test agents command (once fully integrated):
```bash
/agents list
/agents switch dev-expert
/agents test main
```

4. Test routing:
```bash
"帮我分析这个数据集"  # Should route to analyst-expert
"扫描这个代码的安全性"  # Should route to security-expert
"搜索最新的研究论文"  # Should route to research-expert
```

## Reusable Patterns

This system can be adapted to any multi-agent framework:
- Replace `AIAgent` with your agent class
- Adjust configuration loading for your format
- Modify routing logic for your domain
- Customize database schema as needed
- Extend collaboration to more sophisticated protocols

## Reference Implementation

Full code in:
- `~/.hermes/hermes-agent/expert_system.py` - core system
- `~/.hermes/config.yaml` - agents section
- `~/.hermes/scripts/init_experts.py` - initialization
- `~/.hermes/hermes-agent/hermes_cli/commands.py` - CLI commands
- `~/.hermes/hermes-agent/cli.py` - (partial) integration
## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
