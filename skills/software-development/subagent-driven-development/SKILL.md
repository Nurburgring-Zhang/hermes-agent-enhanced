---
name: subagent-driven-development
description: "Execute plans via delegate_task subagents (2-stage review)."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development]
---

# Subagent-Driven Development

## Overview

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## When to Use

Use this skill when:
- You have an implementation plan (from writing-plans skill or user requirements)
- Tasks are mostly independent
- Quality and spec compliance are important
- You want automated review between tasks

**vs. manual execution:**
- Fresh context per task (no confusion from accumulated state)
- Automated review process catches issues early
- Consistent quality checks across all tasks
- Subagents can ask questions before starting work

## The Process

### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list:

```python
# Read the plan
read_file("docs/plans/feature-plan.md")

# Create todo list with all tasks
todo([
    {"id": "task-1", "content": "Create User model with email field", "status": "pending"},
    {"id": "task-2", "content": "Add password hashing utility", "status": "pending"},
    {"id": "task-3", "content": "Create login endpoint", "status": "pending"},
])
```

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context:

```python
delegate_task(
    goal="Implement Task 1: Create User model with email and password_hash fields",
    context="""
    TASK FROM PLAN:
    - Create: src/models/user.py
    - Add User class with email (str) and password_hash (str) fields
    - Use bcrypt for password hashing
    - Include __repr__ for debugging

    FOLLOW TDD:
    1. Write failing test in tests/models/test_user.py
    2. Run: pytest tests/models/test_user.py -v (verify FAIL)
    3. Write minimal implementation
    4. Run: pytest tests/models/test_user.py -v (verify PASS)
    5. Run: pytest tests/ -q (verify no regressions)
    6. Commit: git add -A && git commit -m "feat: add User model with password hashing"

    PROJECT CONTEXT:
    - Python 3.11, Flask app in src/app.py
    - Existing models in src/models/
    - Tests use pytest, run from project root
    - bcrypt already in requirements.txt
    """,
    toolsets=['terminal', 'file']
)
```

#### Step 2: Dispatch Spec Compliance Reviewer

After the implementer completes, verify against the original spec:

```python
delegate_task(
    goal="Review if implementation matches the spec from the plan",
    context="""
    ORIGINAL TASK SPEC:
    - Create src/models/user.py with User class
    - Fields: email (str), password_hash (str)
    - Use bcrypt for password hashing
    - Include __repr__

    CHECK:
    - [ ] All requirements from spec implemented?
    - [ ] File paths match spec?
    - [ ] Function signatures match spec?
    - [ ] Behavior matches expected?
    - [ ] Nothing extra added (no scope creep)?

    OUTPUT: PASS or list of specific spec gaps to fix.
    """,
    toolsets=['file']
)
```

**If spec issues found:** Fix gaps, then re-run spec review. Continue only when spec-compliant.

#### Step 3: Dispatch Code Quality Reviewer

After spec compliance passes:

```python
delegate_task(
    goal="Review code quality for Task 1 implementation",
    context="""
    FILES TO REVIEW:
    - src/models/user.py
    - tests/models/test_user.py

    CHECK:
    - [ ] Follows project conventions and style?
    - [ ] Proper error handling?
    - [ ] Clear variable/function names?
    - [ ] Adequate test coverage?
    - [ ] No obvious bugs or missed edge cases?
    - [ ] No security issues?

    OUTPUT FORMAT:
    - Critical Issues: [must fix before proceeding]
    - Important Issues: [should fix]
    - Minor Issues: [optional]
    - Verdict: APPROVED or REQUEST_CHANGES
    """,
    toolsets=['file']
)
```

**If quality issues found:** Fix issues, re-review. Continue only when approved.

#### Step 4: Mark Complete

```python
todo([{"id": "task-1", "content": "Create User model with email field", "status": "completed"}], merge=True)
```

### 3. Final Review

After ALL tasks are complete, dispatch a final integration reviewer:

```python
delegate_task(
    goal="Review the entire implementation for consistency and integration issues",
    context="""
    All tasks from the plan are complete. Review the full implementation:
    - Do all components work together?
    - Any inconsistencies between tasks?
    - All tests passing?
    - Ready for merge?
    """,
    toolsets=['terminal', 'file']
)
```

### 4. Verify and Commit

```bash
# Run full test suite
pytest tests/ -q

# Review all changes
git diff --stat

# Final commit if needed
git add -A && git commit -m "feat: complete [feature name] implementation"
```

## Task Granularity

**Each task = 2-5 minutes of focused work.**

**Too big:**
- "Implement user authentication system"

**Right size:**
- "Create User model with email and password fields"
- "Add password hashing function"
- "Create login endpoint"
- "Add JWT token generation"
- "Create registration endpoint"

## Red Flags — Never Do These

- Start implementation without a plan
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Make subagent read the plan file (provide full text in context instead)
- Skip scene-setting context (subagent needs to understand where the task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues → implementer fixes → review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is PASS** (wrong order)
- Move to next task while either review has open issues
- **Assume parallel subagents produce consistent naming conventions** — see Pitfalls below
- **Batch-dispatch parallel subagents without a naming convention spec in the context** — see Pitfalls below

## Handling Issues

### If Subagent Asks Questions

- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### If Reviewer Finds Issues

- Implementer subagent (or a new one) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

### If Subagent Fails a Task

- Dispatch a new fix subagent with specific instructions about what went wrong
- Don't try to fix manually in the controller session (context pollution)

## Pitfalls from Real Sessions

### Subagent Edit Collision — HTML Template JS Corruption

**Risk:** When multiple subagents inject JS code into the same inline HTML template (e.g., a Python `r"""..."""` string), they routinely cause:
- **Bracket mismatch** — Deleting Python source lines from within an HTML string breaks `{`/`}` balance in the JS output
- **Syntax errors in object literals** — `//` comments injected inside `const NT={...}` (JS object literals) cause `invalid decimal literal` errors
- **Duplicate function definitions** — `execNode` gets overwritten 3+ times cascading from previous injections
- **Missing function hoisting** — Injecting functions inside conditional blocks or try/catch makes them non-global, breaking `onclick="functionName()"` in HTML

**Detection:** After any subagent that modifies an HTML template file:
```bash
# 1. Extract the JS from the HTML template
python3 -c "
import re
with open('api/canvas_web.py') as f:
    content = f.read()
match = re.search(r'HTML_TEMPLATE = r\"\"\"(.*?)\"\"\"', content, re.DOTALL)
if match:
    html = match.group(1)
    scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
    if scripts:
        js = scripts[0]
        opens = js.count('{')
        closes = js.count('}')
        print(f'JS brackets: {opens}:{closes} ({\"OK\" if opens==closes else \"MISMATCH\"})')
        
        # Check object literal comments
        import ast
        try:
            ast.parse(js)
            print('JS AST: OK')
        except SyntaxError as e:
            print(f'JS AST ERROR: {e.msg} at line {e.lineno}')
        
        # Check key globals
        for fn in ['switchTab', 'execNode', 'addLog', '_cv_api']:
            print(f'  {\"OK\" if fn in js else \"MISSING\"}: {fn}')
"
```

**Prevention — Pre-edit Bracket Snapshot:**
Before dispatching a subagent to patch an HTML template, take a bracket snapshot:
```bash
grep -o '{' api/canvas_web.py | wc -l  # count {
grep -o '}' api/canvas_web.py | wc -l  # count }
```
After the subagent returns, verify counts haven't diverged. A difference >0 in { vs } means the HTML template JS is now broken.

**Prevention — Object Literal Comment Rule:**
In task context, specify: "JS object literal `=` {...} does NOT support `//` comments. Use `/* ... */` instead."

**Recovery — Paren/Bracket Rebalance:**
When JS brackets are off:
```bash
python3 -c "
with open('file.py') as f:
    lines = f.readlines()
# Find and remove isolated } on their own line near the edit point
for i in range(len(lines)-1, -1, -1):
    stripped = lines[i].strip()
    if stripped ==  '}':
        lines.pop(i)
        break
with open('file.py', 'w') as f:
    f.writelines(lines)
"
```

### Parallel Subagent Naming Convention Drift

**Risk:** When dispatching 3+ parallel subagents to extract functions from a monolith into separate modules, different subagents produce inconsistent naming:

- Some prefix with `_` (private), some don't
- Parameter names differ: `random_topic_fn` vs `random_topic` vs `random_topic_fn=`
- Function signatures diverge between modules that should share the same pattern

**Mitigation — Naming Convention Spec in Context:**

When dispatching parallel extraction tasks, include a **naming convention block** in every subagent's context:

```yaml
NAMING CONVENTION (MANDATORY):
  - All extracted functions: lowercase_with_underscores
  - Internal/helper functions: _prefixed_with_underscore
  - Public entry-point functions: NO underscore prefix
  - Parameter names for injected dependencies: suffix with _fn (e.g. call_ai_fn, random_topic_fn)
  - All parameter names: snake_case, no abbreviations
```

After all parallel tasks complete, always run a **post-pass audit**:

```bash
# Check all modules' function names match expected convention
grep -n '^def ' modes_*.py

# Check function signatures for fn-suffix consistency
grep -n 'fn=' __init__.py

# Verify all module name-imports match in __init__.py
```

## Efficiency Notes

**Why fresh subagent per task:**
- Prevents context pollution from accumulated state
- Each subagent gets clean, focused context
- No confusion from prior tasks' code or reasoning

**Why two-stage review:**
- Spec review catches under/over-building early
- Quality review ensures the implementation is well-built
- Catches issues before they compound across tasks

**Cost trade-off:**
- More subagent invocations (implementer + 2 reviewers per task)
- But catches issues early (cheaper than debugging compounded problems later)

## Integration with Other Skills

### With writing-plans

This skill EXECUTES plans created by the writing-plans skill:
1. User requirements → writing-plans → implementation plan
2. Implementation plan → subagent-driven-development → working code

### With test-driven-development

Implementer subagents should follow TDD:
1. Write failing test first
2. Implement minimal code
3. Verify test passes
4. Commit

Include TDD instructions in every implementer context.

### With requesting-code-review

The two-stage review process IS the code review. For final integration review, use the requesting-code-review skill's review dimensions.

### With systematic-debugging

If a subagent encounters bugs during implementation:
1. Follow systematic-debugging process
2. Find root cause before fixing
3. Write regression test
4. Resume implementation

## Example Workflow

```
[Read plan: docs/plans/auth-feature.md]
[Create todo list with 5 tasks]

--- Task 1: Create User model ---
[Dispatch implementer subagent]
  Implementer: "Should email be unique?"
  You: "Yes, email must be unique"
  Implementer: Implemented, 3/3 tests passing, committed.

[Dispatch spec reviewer]
  Spec reviewer: ✅ PASS — all requirements met

[Dispatch quality reviewer]
  Quality reviewer: ✅ APPROVED — clean code, good tests

[Mark Task 1 complete]

--- Task 2: Password hashing ---
[Dispatch implementer subagent]
  Implementer: No questions, implemented, 5/5 tests passing.

[Dispatch spec reviewer]
  Spec reviewer: ❌ Missing: password strength validation (spec says "min 8 chars")

[Implementer fixes]
  Implementer: Added validation, 7/7 tests passing.

[Dispatch spec reviewer again]
  Spec reviewer: ✅ PASS

[Dispatch quality reviewer]
  Quality reviewer: Important: Magic number 8, extract to constant
  Implementer: Extracted MIN_PASSWORD_LENGTH constant
  Quality reviewer: ✅ APPROVED

[Mark Task 2 complete]

... (continue for all tasks)

[After all tasks: dispatch final integration reviewer]
[Run full test suite: all passing]
[Done!]
```

## Remember

```
Fresh subagent per task
Two-stage review every time
Spec compliance FIRST
Code quality SECOND
Never skip reviews
Catch issues early
```

**Quality is not an accident. It's the result of systematic process.**

## Further reading (load when relevant)

When the orchestration involves significant context usage, long review loops, or complex validation checkpoints, load these references for the specific discipline:

- **`references/context-budget-discipline.md`** — Four-tier context degradation model (PEAK / GOOD / DEGRADING / POOR), read-depth rules that scale with context window size, and early warning signs of silent degradation. Load when a run will clearly consume significant context (multi-phase plans, many subagents, large artifacts).
- **`references/gates-taxonomy.md`** — The four canonical gate types (Pre-flight, Revision, Escalation, Abort) with behavior, recovery, and examples. Load when designing or reviewing any workflow that has validation checkpoints — use the vocabulary explicitly so each gate has defined entry, failure behavior, and resumption rules.

Both references adapted from gsd-build/get-shit-done (MIT © 2025 Lex Christopherson).

## Persistent (Physical) SubAgents

The `subagent-driven-development` skill covers **logical** subAgents dispatched via `delegate_task`.
An alternative **physical** subAgent architecture with isolated runtime, sandbox, heartbeat, and task queue
is documented in `references/v3-persistent-subagent-architecture.md`.

**Key difference:** delegate_task subAgents = stateless, task-scoped, no sandbox.  
Physical subAgents (evolution_v3) = stateful, persistent, sandboxed, cross-session.

Use delegate_task for coding tasks. Use physical subAgents when you need:
- Long-running persistent workers
- File system isolation
- Heartbeat monitoring and zombie detection
- Hooks event integration (SubagentStart/Stop)

## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
