# Hermes Upgrade & Comparative Analysis Workflow

## When to use

- User says "对比原版" (compare against upstream)
- User asks for upgrade pre-actions
- Tasks beginning with "hermes update" 
- Anything asking "what enhancements did we add compared to upstream"

## Pre-upgrade backup

1. Create timestamped backup dir under `/mnt/d/Hermes/备份/hermes_pre_upgrade_<timestamp>/`
2. Backup all custom files:
   - `~/.hermes/SOUL.md` / `AGENTS.md` / `config.yaml`
   - All 5+ modified upstream files (check via `git status --short` in hermes-agent dir)
   - `~/.hermes/scripts/rule_enforcer.py` and other key scripts
   - `~/.hermes/plugins/` directories
   - crontab: `crontab -l > backup/crontab_backup.txt`
   - skills list: `ls ~/.hermes/skills/ > backup/skills_list.txt`

## Upgrade procedure

### Problem: `hermes update --check` may timeout
On some networks (especially WSL behind proxy/firewall), the check command hangs past 120s.

### Workaround: Direct git approach (more reliable)
```bash
# 1. Stash local modifications
cd ~/.hermes/hermes-agent
git stash push -m "增强备份 YYYY-MM-DD" -- <modified_files>

# 2. Pull upstream
git pull origin main --ff-only

# 3. Re-apply custom modifications
git stash pop
```

### Verify after upgrade
```bash
hermes --version
# Should show: Hermes Agent v0.16.0 · upstream <new_hash>
# Check: "up to date with 'origin/main'"
```

## Comparative analysis: 3-parallel-delegate pattern

Run 3 delegate_task subagents in parallel:

### Agent 1: Enhancement catalog (current system)
- Scan `~/.hermes/` directory structure
- Inventory: scripts (~293), plugins (13), skills (180), cron (137 lines), workflows (26 modules)
- Categorize into ~20-25 logical categories
- Output: complete list of all custom enhancements with file counts, code sizes, injection points

### Agent 2: Upstream baseline (upstream commit)
- Clone or inspect upstream repo at current HEAD
- Document: default interfaces (CLI/TUI/Desktop), skills (~18), tools, plugins (framework only), memory, MCP, gateway, cron, ACP, config structure
- Output: baseline capabilities list

### Agent 3: Gap analysis (diff comparison)
- `cd ~/.hermes/hermes-agent && git diff --stat HEAD`
- Count: modified files, new untracked files, overall diff volume
- Classify: which subsystems have the most custom additions
- Output: structured diff summary with comparison metrics

### Cross-validation
- Merge 3 reports into consolidated comparison table
- Report format: | Capability | Upstream v0.16.0 | Enhanced | Multiplier |
- Include: total custom code estimate, layer architecture diagram

## Report template structure

```
# Hermes Agent Enhancement Comparison
## Version: Upstream <commit> → Current <version>
## Overview (headline stats)
## 23+ Category deep dive (each: Upstream vs Enhanced)
## Architecture diagram comparison
## Core enhancement summary
## P0 gaps (what still needs work)
```
