# SkillOpt Integration: Validation Gate Methodology

Based on Microsoft Research paper **SkillOpt: Executive Strategy for Self-Evolving Agent Skills** (arXiv:2605.23904, May 2026).

## Core Insight

"Train" the skill document as **external model state** — apply the same discipline that makes weight-space optimization reproducible, to text-space skill editing.

## The 6-Component Cycle

| Component | Equivalent in DL | FDE Implementation |
|---|---|---|
| Rollout batch | Training data batch | Run current skill on 3-5 test tasks |
| Mini-batch reflection | Backpropagation | Split trajectories into success/failure groups, extract "keep" vs "fix" |
| Text learning rate | Step size control | **Max 3 rules modified per cycle** |
| Validation gate | Early stopping | Accept ONLY if strict improvement over baseline |
| Rejection buffer | Hard negative memory | Rejected edits → negative feedback for future cycles |
| Epoch slow update | Momentum | Compare pre/post epoch performance, protect long-term beneficial rules |

## Implementation in Hermes

### Step-by-step for `skill_manage(action='patch')`

```
1. IDENTIFY skill to patch
2. ROLLOUT: Run skill on 3-5 test scenarios, collect trajectories
3. REFLECT: Analyze trajectories (success=keep, failure=fix)
4. PLAN: Identify ≤3 changes to make (learning rate budget)
5. APPLY: skill_manage(action='patch', old_string=new_string)
6. VALIDATE: Run skill on test set again → score must improve
7. ACCEPT/REJECT: 
   - If score improved → commit
   - If not → write to rejection_buffer.jsonl
8. EPOCH: After 5+ cycles, compare epoch-level performance

### Rejection Buffer Format

```jsonl
{"timestamp": "...", "skill": "xxx", "rejected_changes": [{"old": "...", "new": "..."}], "reason": "validation failed: score dropped from 0.8 to 0.6"}
```

Store at: `~/.hermes/history/skillopt-rejection-buffer.jsonl`

## Caution

**Validation gate is the most critical component.** Without it, seemingly reasonable edits can silently degrade performance. Always measure.
