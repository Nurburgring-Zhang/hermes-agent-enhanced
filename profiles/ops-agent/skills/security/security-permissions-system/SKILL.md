---
name: security-permissions-system
description: Complete security & permissions infrastructure for AI agent systems with RBAC, execution approvals, sandbox isolation, encrypted credentials, and audit logging.
version: 1.0.0
author: Hermes Security Team
license: MIT
dependencies:
  - cryptography>=41.0.0
  - pyyaml>=6.0
  - sqlite3 (stdlib)
metadata:
  hermes:
    tags: [Security, RBAC, Sandbox, Credentials, Audit, Approval Workflow]
---

# Security & Permissions System Implementation

**Skill for building a comprehensive security infrastructure for AI agent systems**

## When to Use

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Use this skill when you need to:
- Add security controls to an AI agent or automation system
- Implement RBAC (Role-Based Access Control) with fine-grained permissions
- Add approval workflows for dangerous operations
- Isolate untrusted code execution in sandboxes
- Securely manage credentials and secrets
- Enable comprehensive security auditing and monitoring
- Integrate security into an existing system without breaking changes

## Architecture Overview

The system consists of 8 coordinated modules:

### 1. exec_approvals.py
Dangerous command detection and approval workflow.

**Features**:
- 30+ regex patterns (rm -rf, sudo, curl|bash, find -exec, etc.)
- Risk levels: Critical/High/Medium/Low
- Multi-level approval: session-based, permanent, time-limited
- Auto-approval based on role/tool/pattern
- SQLite audit trail
- CLI: `/approve`, `/deny`, `/list`, `/request`, `/status`

**Integration**:
```python
requires, risk_level, reasons = approval_sys.requires_approval(
    command=command, user=current_user, role=user_role, tool=tool_name
)
if requires:
    request = approval_sys.workflow.request_approval(...)
    # Block execution until APPROVED
```

### 2. sandbox.py
Isolated execution environment for untrusted code.

**Features**:
- Docker container or chroot jail isolation
- Resource limits: CPU, memory, disk, timeout
- Malware detection: pattern scanning, entropy analysis, file size checks
- Auto-cleanup, session tracking

**Configuration**:
```yaml
sandbox:
  cpu_limit: 1.0
  memory_limit: 512  # MB
  disk_limit: 1024   # MB
  timeout_seconds: 300
  network_enabled: false
  read_only_root: true
```

### 3. credentials.py
Encrypted credential management.

**Features**:
- AES-256-CBC encryption with PBKDF2 key derivation
- Master key stored in `~/.hermes/security/master.key` (600 perms)
- Access control lists: users, roles, tools
- Versioned rotations with audit trail
- Auto-injection to environment variables

**Schema**:
```python
@dataclass
class Credential:
    id: str
    name: str
    type: CredentialType  # api_key, password, token, certificate
    encrypted_value: str
    salt: str
    iv: str
    access_control: {"users": [], "roles": [], "tools": []}
    rotation_policy: Optional[Dict]
    version: int
```

### 4. permissions.py
RBAC system with 5 default roles and 128+ permissions.

**Roles** (descending priority):
- `admin` (100): All permissions
- `superuser` (90): Almost all, no security override
- `user` (50): Standard tools, no exec/cred read
- `restricted` (10): Read-only + memory search
- `guest` (1): Read-only only

**Tool Registry**:
```yaml
permissions:
  tools:
    exec:
      required_permissions: ["tool:exec"]
      denied_roles: ["restricted", "guest"]
      risk_level: "critical"
      requires_sandbox: true
      requires_approval: true
```

**Decorator**:
```python
@require_permission(Permission.TOOL_EXEC.value, tool='exec')
def execute_command(self, command):
    pass
```

### 5. audit.py
Centralized security event logging.

**Features**:
- JSON-structured events
- Separate logs per source, daily rotation + gzip
- Query interface (filter by user, source, severity, time)
- Statistics (success rates, top users, event distribution)
- Anomaly detection (high failures, repeated denials, excessive elevation)
- Security monitor with real-time alerting

**Event Schema**:
```python
@dataclass
class SecurityEvent:
    timestamp: float
    event_type: str
    severity: str  # low, medium, high, critical
    user: str
    source: str    # exec_approvals, sandbox, credentials, permissions
    resource: str  # Tool, credential, command
    action: str
    result: str    # success, failure, partial
    details: Dict
```

### 6. integration.py
Bridge between Hermes core and security modules.

**SecurityEnforcer**:
- `before_tool_execute()`: Pre-checks (permissions, approvals, sandbox, credentials)
- `after_tool_execute()`: Audit logging
- `check_tool_permission()`: RBAC lookup
- `request_approval_if_needed()`: Approval trigger
- `execute_in_sandbox_if_needed()`: Sandbox execution
- `inject_credentials()`: Auto-inject secrets to env vars

**Hermes Patching**:
```python
original_handle = model_tools.handle_function_call

def secure_handle(function_name, arguments, task_id):
    tool_name = function_name.split('.')[-1]
    command = arguments.get("command") if function_name == "terminal" else None
    
    allowed, context = before_tool_hook(tool_name, command, arguments)
    if not allowed:
        return {"error": context["reason"]}
    
    try:
        result = original_handle(function_name, arguments, task_id)
        after_tool_hook(tool_name, True, result)
        return result
    except Exception as e:
        after_tool_hook(tool_name, False, error=e)
        raise

model_tools.handle_function_call = secure_handle
```

### 7. startup_hook.py
Auto-loading mechanism for Hermes.

```python
# Add to Hermes startup:
import load_security  # Auto-initializes

# Sets HERMES_SECURITY_ENABLED=true
# Patches model_tools.handle_function_call
```

### 8. security_cli.py
Unified management CLI:

```
security status                    # Component health
security approvals list           # View/manage requests
security sandbox list             # Active sandbox sessions
security sandbox exec <cmd>       # Test in sandbox
security creds store/get/list     # Credential lifecycle
security perms check <user> <tool> # Test permissions
security perms user create <name> # User management
security audit stats              # Dashboard
security audit query              # Search events
security audit anomalies          # Detect suspicious patterns
security config show/test         # Configuration
security elevate request <role>  # Session elevation
```

## Configuration

**File**: `~/.hermes/config/security.yaml`

**Sections**:
```yaml
exec_approvals:
  mode: smart  # manual, smart, off
  timeout_seconds: 60
  auto_approve_roles: [admin, superuser]
  require_approval_roles: [user, restricted]
  working_hours: "09:00-17:00"
  rate_limit_per_hour: 100

sandbox:
  backend: auto  # docker, chroot, auto
  cpu_limit: 1.0
  memory_limit: 512  # MB
  disk_limit: 1024   # MB
  timeout_seconds: 300
  network_enabled: false
  read_only_root: true
  malware_detection: true

credentials:
  encryption_key: "~/.hermes/security/master.key"
  rotation_policy:
    api_keys: "90d"
    passwords: "30d"
  access_log_retention_days: 365

permissions:
  default_user_role: restricted
  role_hierarchy:
    - admin
    - superuser
    - user
    - restricted
    - guest
  session_elevation_timeout: 3600  # 1 hour
  cache_permission_results: true
  cache_ttl_seconds: 60

audit:
  log_directory: "~/.hermes/logs/security"
  retention_days: 365
  compression: gzip
  sources:
    - exec_approvals
    - sandbox
    - credentials
    - permissions
  alert_on:
    - severity: critical
    - failure_rate: 0.1  # >10% failures
    - repeated_denials: 5

openclaw:
  map_agent_tools: true
  agent_tools_whitelist: []
  migrate_exec_approvals_json: true

integration:
  fail_closed: true  # Deny all if security unavailable
  patch_hermes_core: true
  pre_hook_timeout: 5
  post_hook_async: true
```

## Implementation Steps

1. **Create directory structure**:
```bash
mkdir -p ~/.hermes/security
mkdir -p ~/.hermes/config
mkdir -p ~/.hermes/logs/security
```

2. **Copy all 8 modules** to `~/.hermes/security/`

3. **Create security.yaml** in `~/.hermes/config/`

4. **Initialize master key**:
```bash
python3 -c "from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC; from cryptography.hazmat.primitives import hashes; import os, base64; kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=os.urandom(16), iterations=100000); key = base64.urlsafe_b64encode(kdf.derive(b'hermes-security-key')); open(Path.home()/.hermes/security/master.key,'wb').write(key)"
chmod 600 ~/.hermes/security/master.key
```

5. **Create default users**:
```bash
python3 ~/.hermes/security/security_cli.py perms user create admin --role admin
python3 ~/.hermes/security/security_cli.py perms user create user --role user
```

6. **Integrate with Hermes**: Add to `~/.hermes/hermes-agent/run_agent.py`:
```python
import load_security  # Top of file
```

7. **Test**: `python3 ~/.hermes/security/test_suite.py`

## Related Skills & Complementary Systems

- `hermes-camel-guard` — CaMeL信任边界安全护栏。与本skill互补：本skill是主动安全控制(RBAC+审批+凭据管理)，CaMeL是被动安全防御(信任边界+注入检测+工具循环防护)。两者结合形成Hermes安全防御体系的"主动+被动"双保险。
- `task-retrospect` — 复盘引擎可消费安全日志中的事件，将安全事件纳入质量评估

## Key Design Principles

- **Defense in depth**: 5 independent security layers
- **Fail-safe**: Default deny when security unavailable (configurable)
- **Immutable audit**: Append-only logs, never modify
- **Encryption at rest**: All credentials encrypted with master key
- **Least privilege**: Default role is `restricted`, not `admin`
- **Complete traceability**: Every action → user, session, IP
- **No bypass**: All tool executions must pass through hooks

## Performance

- Permission cache (60s TTL): ~1ms lookup
- Approval lookup: ~5ms (SQLite indexed)
- Sandbox startup: 100-500ms (Docker)
- Credential decrypt: ~5ms (AES-256)
- Audit logging: async, non-blocking

## Verification Checklist

- [ ] All modules import without errors
- [ ] Permission checks for all 4 default roles
- [ ] Dangerous commands trigger approval
- [ ] Safe commands auto-approve (no spam)
- [ ] Sandbox executes with resource limits
- [ ] Malware detector blocks obfuscation
- [ ] Credentials encrypt/decrypt correctly
- [ ] Access logs record all credential usage
- [ ] Audit log rotation works
- [ ] Integration patches Hermes without breaking tools
- [ ] All CLI commands function
- [ ] Configuration validates as YAML
- [ ] All test groups pass

## Troubleshooting

**All commands fail with "permission_denied"**
→ Create user: `security perms user create <name> --role user`

**Sandbox not available**
→ Install Docker or run as root for chroot fallback

**Approvals not triggering**
→ Check tool.requires_approval in config; ensure role in `require_approval_roles`

**Performance degradation**
→ Enable permission caching; increase `cache_ttl_seconds`

**Audit logs not rotating**
→ Check write permissions on `~/.hermes/logs/security/`

## Advanced: Adding Custom Tools

```yaml
permissions:
  tools:
    my_tool:
      description: "Custom data processing tool"
      required_permissions: ["tool:my_tool:execute"]
      denied_roles: ["restricted", "guest"]
      risk_level: "medium"
      requires_sandbox: false
      requires_approval: false
      credential_requirements: ["api:my_service"]
```

Then add permission to roles:
```yaml
permissions:
  role_permissions:
    user:
      allow: ["tool:my_tool:execute"]
```

## Advanced: Custom Dangerous Patterns

```python
# In exec_approvals.py
DANGEROUS_PATTERNS.append(
    (r'\bmy_dangerous_cmd\b.*-(?:force|delete)\b', RiskLevel.HIGH, "Custom destructive tool")
)
```

## Security Guarantees

1. **No bypass**: All tool calls go through `before_tool_hook`
2. **Fail-closed**: If security unavailable, default DENY
3. **Immutable audit**: Append-only, never modify after write
4. **Encryption at rest**: AES-256 for all credentials
5. **Least privilege**: Default role is restricted
6. **Complete traceability**: Every action linked to user, session, IP
7. **Defense in depth**: 5 independent security layers

## Migration from Existing OpenClaw

The system integrates gracefully:
- Reads existing `exec-approvals.json` (can migrate to DB)
- Maps OpenClaw agent tool allow lists to Hermes permissions
- Respects OpenClaw's `tools.deny` as overrides
- Can run alongside existing security during transition

**Steps**:
1. Deploy new security modules in parallel
2. Run in `debug.bypass_approvals_for_admin: true` initially
3. Monitor audit logs for false positives/negatives
4. Gradually tighten policies
5. Switch to production mode after validation

## Files Created

- `~/.hermes/security/exec_approvals.py`
- `~/.hermes/security/sandbox.py`
- `~/.hermes/security/credentials.py`
- `~/.hermes/security/permissions.py`
- `~/.hermes/security/audit.py`
- `~/.hermes/security/integration.py`
- `~/.hermes/security/startup_hook.py`
- `~/.hermes/security/load_security.py`
- `~/.hermes/security/security_cli.py`
- `~/.hermes/security/test_suite.py`
- `~/.hermes/config/security.yaml` (config)
- `~/.hermes/logs/security/` (audit logs)

## Testing

```bash
cd ~/.hermes/security
python3 test_suite.py
```

Expected: All 8 test groups pass after initial bug fixes (imports corrected in permissions, sandbox, credentials, integration).

---
**Skill Version**: 1.0  
**Last Updated**: 2026-04-08  
**Compatible With**: Hermes >= 2026.4+, OpenClaw >= v5
## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
