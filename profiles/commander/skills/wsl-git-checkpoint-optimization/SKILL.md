---
name: wsl-git-checkpoint-optimization
description: Fix checkpoint_manager failures on WSL Windows filesystem (/mnt/c). Checkpoint git operations timeout or fail with Permission denied on Windows system directories (Microsoft/Protect/Recovery, config/BFS, LogFiles/WMI, WebThreatDefSvc). This skill diagnoses, patches, and prevents recurrence.
tags: [wsl, checkpoint, git, windows, permissions]
---

# WSL Git Checkpoint Optimization

## When to Use

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Use this skill when:
- errors.log shows `checkpoint_manager: Git command failed (rc=128)` with Permission denied
- Errors mention paths like `Microsoft/Protect/Recovery/`, `config/BFS/`, `LogFiles/WMI/`, `WebThreatDefSvc/`
- Checkpoint shadow repos exist for `/mnt/c/...` paths
- `HERMES_CHECKPOINT_TIMEOUT` env var needs adjustment for WSL paths

## Symptoms

```
ERROR [checkpoint_manager]: Git command failed: git add -A (rc=128)
stderr=warning: could not open directory 'config/BFS/': Permission denied
warning: could not open directory 'LogFiles/WMI/RtBackup/': Permission denied
warning: could not open directory 'WebThreatDefSvc/': Permission denied
error: open("Microsoft/Protect/Recovery/Recovery.dat"): Permission denied
fatal: adding files failed
```

These errors recur every 1-2 minutes in WSL and clutter errors.log.

## Root Cause

1. **CheckpointManager tracks `/mnt/c/Users/Administrator/Desktop`** — the Windows Desktop mounted via WSL
2. When `git add -A` runs, it traverses the entire Desktop directory tree
3. Windows shell folder symlinks in `C:\Users\Administrator\` expose Windows system directories
4. These Windows system directories require SYSTEM-level permissions that WSL user doesn't have
5. The shadow repo's `info/exclude` file does NOT include Windows system directory patterns

## Fix Steps

### Step 1: Patch DEFAULT_EXCLUDES in checkpoint_manager.py

File: `/home/administrator/.hermes/hermes-agent/tools/checkpoint_manager.py`

Add Windows system directory patterns to `DEFAULT_EXCLUDES` list (around line 39):

```python
DEFAULT_EXCLUDES = [
    "node_modules/",
    "dist/",
    "build/",
    ".env",
    ".env.*",
    ".env.local",
    ".env.*.local",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "*.log",
    ".cache/",
    ".next/",
    ".nuxt/",
    "coverage/",
    ".pytest_cache/",
    ".venv/",
    "venv/",
    ".git/",
    # --- WSL Windows system directory excludes ---
    "Microsoft/Protect/",
    "config/BFS/",
    "LogFiles/WMI/",
    "WebThreatDefSvc/",
    "*.dat",
]
```

### Step 2: Delete old shadow repo to force reinit

The shadow repo's `info/exclude` is only written once during `_init_shadow_repo()`. If the shadow repo already exists, patching DEFAULT_EXCLUDES alone won't take effect until the shadow repo is regenerated.

Delete the Desktop checkpoint shadow repo (it will be recreated automatically on next checkpoint):

```python
# Python one-liner to remove the Desktop checkpoint shadow repo
import shutil, hashlib
desktop_path = "/mnt/c/Users/Administrator/Desktop"
shadow_dir = "/home/administrator/.hermes/checkpoints/" + hashlib.sha256(desktop_path.encode()).hexdigest()[:16]
shutil.rmtree(shadow_dir, ignore_errors=True)
print(f"Removed shadow repo: {shadow_dir}")
```

Also remove the system32 zombie checkpoint:
```python
import shutil
shutil.rmtree("/home/administrator/.hermes/checkpoints/adedf164c939009f", ignore_errors=True)
print("Removed system32 zombie checkpoint")
```

### Step 3: Set environment variable (fallback approach)

```bash
# Optionally increase timeout for WSL paths
export HERMES_CHECKPOINT_TIMEOUT=60
```

### Step 4: Verify the fix

```bash
tail -f /home/administrator/.hermes/logs/errors.log | grep "checkpoint_manager"
```

## Verification

- [ ] Patch applied to checkpoint_manager.py DEFAULT_EXCLUDES
- [ ] Old shadow repos deleted (forced reinit with new excludes)
- [ ] system32 zombie checkpoint removed
- [ ] No new `Permission denied` or `rc=128` errors for checkpoint_manager after 5 minutes
- [ ] `HERMES_CHECKPOINT_TIMEOUT` env var set if needed

## Known Issues

- After patching DEFAULT_EXCLUDES, existing shadow repos still have the OLD exclude files (without Windows patterns). The shadow repo must be deleted to force reinit.
- The `.gitignore` approach (writing .gitignore to the actual working directory) is NOT recommended — it would modify the user's Desktop files.
- CheckpointManager's `ensure_checkpoint()` does NOT support dynamic per-directory timeout. The global `HERMES_CHECKPOINT_TIMEOUT` env var affects ALL checkpoints.

## Related

- Skill: `systematic-python-source-patching` — for safely editing checkpoint_manager.py
- Location: `/home/administrator/.hermes/hermes-agent/tools/checkpoint_manager.py` (684 lines)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
