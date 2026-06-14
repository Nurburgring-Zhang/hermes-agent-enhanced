---
name: npm-mcp-server-setup
description: Install and configure npm-based MCP servers when npm install times out or fails silently. Detect broken node_modules, extract packages manually, retry installs in background, rebuild native modules, and register with mcporter.
version: 1.0.0
tags: [MCP, npm, nodejs, mcporter, troubleshooting]
author: Hermes
---

# npm MCP Server Setup — Troubleshooting & Installation

## Problem Statement

## 触发条件
- 用户提及部署、安装、配置服务时
- 需要调试系统环境或依赖时
- 执行系统运维操作时


When running `npm install` for MCP servers in this environment (WSL2, network-limited):
- `npm install` often **times out** after 60-300s
- It may report "added X packages" but **silently miss critical dependencies**
- The broken state isn't obvious until the server fails at runtime with `MODULE_NOT_FOUND`

## Detection: Is node_modules broken?

```bash
# Check if a critical package directory is empty (indicates broken install)
ls /path/to/node_modules/@modelcontextprotocol/sdk/
# If empty or only has package.json but no dist/ → BROKEN

# More thorough check
find /path/to/node_modules -maxdepth 3 -name "index.js" | wc -l
# Low count vs expected = broken

# Try running the server
node /path/to/server/dist/index.js
# MODULE_NOT_FOUND = broken node_modules
```

## Workflow: Fix broken npm install

### Step 1: Use `npm pack` as workaround (when direct install times out)

```bash
cd /tmp
npm pack <package>@<version>        # Downloads .tgz to /tmp
mkdir -p /tmp/<package-dir>
tar xzf /tmp/<package>-<version>.tgz -C /tmp/<package-dir> --strip-components=1
ls /tmp/<package-dir>               # Verify contents
```

Example for `supermemory-mcp`:
```bash
cd /tmp
npm pack supermemory-mcp
mkdir -p /tmp/sm-mcp
tar xzf supermemory-mcp-*.tgz -C /tmp/sm-mcp --strip-components=1
```

### Step 2: Retry npm install with `--loglevel=error` + background monitoring

```bash
cd /path/to/<package>
npm install --loglevel=error 2>&1 &
NPM_PID=$!
echo "npm PID: $NPM_PID"

# Poll every 15s
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
    sleep 15
    if ! kill -0 $NPM_PID 2>/dev/null; then
        echo "npm finished"
        break
    fi
    echo "still running... (${i}x15s)"
done

# Verify critical modules installed
ls node_modules/@modelcontextprotocol/sdk/dist/
```

### Step 3: Rebuild native modules

```bash
cd /path/to/<package>
npm rebuild better-sqlite3   # Common for MCP servers with SQLite
# Or: npm rebuild <native-module-name>
```

### Step 4: Verify server starts

```bash
node /path/to/<package>/dist/index.js --help
# Should output server info, NOT MODULE_NOT_FOUND
```

## Register with mcporter (stdio transport)

```bash
mcporter config add <name> --command "node" --arg "/path/to/<package>/dist/index.js" --scope home
mcporter list
# Should show: <name> (N tools, Xms)
```

For HTTP MCP servers:
```bash
mcporter config add <name> --url "https://host/mcp" --description "description"
```

## Complete Working Example: supermemory-mcp 1.1.0

```bash
# 1. Download package
cd /tmp && npm pack supermemory-mcp

# 2. Extract (if install times out, do this manually)
mkdir -p /tmp/sm-mcp
tar xzf supermemory-mcp-*.tgz -C /tmp/sm-mcp --strip-components=1

# 3. Install dependencies (run in background, monitor progress)
cd /tmp/sm-mcp && npm install --loglevel=error &
NPM_PID=$!
for i in $(seq 1 12); do
    sleep 15
    if ! kill -0 $NPM_PID 2>/dev/null; then echo "done"; break; fi
    echo "running..."
done

# 4. Rebuild native modules
cd /tmp/sm-mcp && npm rebuild better-sqlite3

# 5. Verify server
node /tmp/sm-mcp/dist/index.js  # → "SuperMemory MCP Server v2.1 running"

# 6. Register with mcporter
mcporter config add supermemory --command "node" --arg "/tmp/sm-mcp/dist/index.js" --scope home

# 7. Verify mcporter sees it
mcporter list  # → "supermemory (6 tools, 0.1s) ✔"
```

## Pitfalls

1. **`npm install` reports success but critical dirs are empty** — Always verify runtime, not just exit code
2. **`node_modules` exists but is incomplete** — `npm pack` + manual tar extract is more reliable for flaky networks
3. **Native modules (better-sqlite3, etc.) need rebuilding** — Use `npm rebuild <module>`
4. **mcporter stdio servers need `--scope home`** — Without this, config goes to project dir which may not be loaded
5. **`--arg` vs `--stdio` flag** — Use `--arg` for the script path when using `node /path/to/script.js`
6. **Server process must stay running** — mcporter connects to a long-running stdio server process

## Related Skills

- `mcporter` — MCP server registration and management
- `whisper` — faster-whisper as alternative to openai-whisper

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
