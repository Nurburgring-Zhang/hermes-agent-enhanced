# CaMeL Injection Patterns Reference

> Last updated: 2026-05-31
> Source: `agent/camel_guard.py` from nativ3ai/hermes-agent-camel

## 5 Core Injection Patterns

| Pattern ID | Regex | Detection Target |
|-----------|-------|------------------|
| `ignore_previous_instructions` | `ignore (previous\|all\|above\|prior) instructions` | Agent told to ignore system prompt |
| `hide_from_user` | `do not tell the user` | Agent told to conceal actions |
| `secret_exfiltration` | `(reveal\|show\|print\|dump).*(system prompt\|api key\|token\|secret\|credential)` | Credential theft |
| `system_prompt_override` | `system prompt override` | System prompt overwrite attempt |
| `embedded_side_effect_instruction` | `send_message\|tweet\|email\|dm\|post this` | Hidden action embedding |

## Output Hijack Patterns

```python
_OUTPUT_INSTRUCTION_PATTERNS = [
    r"\b(?:begin|start)\s+your\s+reply\s+with:\s*(.+)$",
    r"\b(?:prefix|start)\s+your\s+output\s+with:\s*(.+)$",
    r"\brespond\s+with:\s*(.+)$",
    r"\boutput\s+exactly:\s*(.+)$",
    r"\bthen\s+write:\s*(.+)$",
    r"\bwrite:\s*(.+)$",
]
```

## Output Analysis Context Detection

```python
_OUTPUT_ANALYSIS_CONTEXT_RE = re.compile(
    r"\b(quote|repeat|show\s+the\s+hidden|extract\s+the\s+hidden|"
    r"what\s+does\s+the\s+hidden|analyze\s+the\s+hidden|"
    r"explain\s+the\s+hidden|classify\s+the\s+hidden|prompt injection)\b"
)
```

## Tool Guardrail Thresholds (tool_guardrails.py)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `exact_failure_warn_after` | 2 | Same tool+same args failed N times → warn |
| `exact_failure_block_after` | 5 | Same tool+same args failed N times → block |
| `same_tool_failure_warn_after` | 3 | Same tool different args failed N times → warn |
| `same_tool_failure_halt_after` | 8 | Same tool different args failed N times → halt |
| `no_progress_warn_after` | 2 | Idempotent tool same result N times → warn |
| `no_progress_block_after` | 5 | Idempotent tool same result N times → block |

## ToolCallSignature

Uniquely identifies a tool call by name + canonical args hash (SHA256):

```python
@dataclass(frozen=True)
class ToolCallSignature:
    tool_name: str
    args_hash: str
    
    @classmethod
    def from_call(cls, tool_name, args):
        canonical = json.dumps(args, sort_keys=True, separators=(",", ":"))
        return cls(tool_name=tool_name, args_hash=sha256(canonical))
```

## Trust Boundary Model

```
Trusted Control Inputs:    Untrusted Data Inputs:
• system prompt            • tool execution results
• approved skills          • retrieved context
• user turns               • external API responses
                           • web search results
                           • file contents
```
