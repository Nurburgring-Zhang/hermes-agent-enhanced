# Kanban Codex Lane — Hermes+Codex Dual-Lane Convention

## Overview

Hermes is always the task owner. It calls `kanban_show`, decides whether Codex is appropriate, creates or selects an isolated workspace, starts and monitors Codex, reconciles any diff, runs verification, and writes the final `kanban_complete` or `kanban_block` handoff. Codex is an input lane only.

## When to Use the Codex Lane

Use when ALL of these are true:
- The Kanban task is a coding, refactor, documentation, or mechanical migration task with clear acceptance criteria
- A bounded diff can be evaluated by Hermes in one run
- The repo can be copied or checked out in an isolated git worktree/branch
- Hermes can run the relevant tests itself after Codex exits
- The prompt can state all safety constraints and files that must not change

Do NOT use when:
- The task requires human judgment not already captured in the Kanban body
- The change touches secrets, credential stores, private user data, or production order-entry systems
- A small direct edit is faster and safer than spawning another agent
- The task is research-only and should produce a written handoff rather than a diff

## Ownership Rules

1. **Hermes owns the Kanban lifecycle.** Codex must never call `kanban_complete`, `kanban_block`, `kanban_create`, gateway messaging, or any Hermes board CLI.
2. **Hermes owns final acceptance.** Treat Codex commits/diffs as untrusted patches until reviewed and verified.
3. **Hermes owns test execution.** Codex may run tests, but those runs are advisory; repeat required verification from Hermes.
4. **Hermes owns safety.** If Codex changes safety boundaries, risk gates, live trading behavior, or secrets handling, reject the lane.
5. **Hermes owns cleanup.** Kill stuck Codex processes and remove temporary worktrees.

## Required Worktree and Branch Pattern

```bash
TASK_ID="${HERMES_KANBAN_TASK:-t_manual}"
REPO="/path/to/repo"
BASE="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
SAFE_TASK="$(printf '%s' "$TASK_ID" | tr -cd '[:alnum:]_-')"
BRANCH="codex/${SAFE_TASK}/$(date -u +%Y%m%d%H%M%S)"
WORKTREE="/tmp/${SAFE_TASK}-codex-lane"

git -C "$REPO" fetch --all --prune
git -C "$REPO" worktree add -b "$BRANCH" "$WORKTREE" "$BASE"
```

Cleanup after reconciliation:
```bash
git -C "$REPO" worktree remove "$WORKTREE"
git -C "$REPO" branch -D "$BRANCH"
```

## Mode Selection

Use `codex exec` for bounded one-shot edits:
```python
terminal(
    command="codex exec --full-auto '$(cat /tmp/codex_prompt.md)'",
    workdir=WORKTREE,
    background=True, pty=True, notify_on_complete=True,
)
```

Use Codex `/goal` only for broader multi-step work that benefits from durable objective tracking.

## Prompt Construction

Every Codex prompt must include:
- `task_id`, title, and full Kanban acceptance criteria
- Repo path, worktree path, branch name, and allowed file scope
- Explicit statement: Hermes owns Kanban lifecycle; Codex is an input lane only
- Required output: concise summary, files changed, commits, tests run, and known risks
- Prohibited actions: secrets access, external messaging, board mutation, unrelated refactors
- Verification commands Codex may run and commands Hermes will run afterward

## `kanban_complete` Metadata Schema

Include this under `metadata.codex_lane` for every task where the lane was considered:

```json
{
  "codex_lane": {
    "used": true,
    "mode": "exec | goal | skipped",
    "worktree": "/absolute/path/to/worktree",
    "branch": "codex/t_caa69668/20260508100000",
    "result": "accepted | rejected | partial | timed_out",
    "accepted_commits": ["<sha1>"],
    "rejected_reason": "concrete reason",
    "tests_run": [
      {"command": "scripts/run_tests.sh", "exit_code": 0, "owner": "hermes"}
    ],
    "artifacts": ["/absolute/path/to/log-or-patch"]
  }
}
```

For tasks that intentionally skip Codex, set `used: false` with a `rejected_reason`.

## Reconciliation Checklist

- [ ] `git status --short --branch` shows only expected files
- [ ] `git diff` was reviewed by Hermes
- [ ] No secrets, credentials, generated caches, or local artifacts included
- [ ] Safety constraints preserved
- [ ] Hermes ran canonical tests itself
- [ ] Accepted commits were applied to the Hermes-owned workspace/branch

## Common Pitfalls

1. Treating Codex self-report as verification — always inspect the diff and rerun tests
2. Running Codex in the user's dirty main checkout — always isolate in a worktree
3. Letting Codex own Kanban — Codex may summarize, Hermes writes board state
4. Using `/goal` for quick edits — prefer `codex exec`
5. Killing a stuck lane without recording why in `rejected_reason`
6. Accepting broad unrelated cleanup because tests pass — cherry-pick only scoped changes

*Absorbed from `kanban-codex-lane` skill. Full template at `kanban-worker/templates/pmb-codex-lane-prompt.md` (original template preserved at `kanban-codex-lane/templates/pmb-codex-lane-prompt.md` before archival).*
