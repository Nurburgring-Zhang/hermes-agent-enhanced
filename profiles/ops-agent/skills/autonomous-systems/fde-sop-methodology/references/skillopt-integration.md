# SkillOpt Integration Reference

## Source
Microsoft Research — arXiv:2605.23904 (May 2026)
"SkillOpt: Executive Strategy for Self-Evolving Agent Skills"

## Core Components (Implemented in `scripts/skillopt_trainer.py`)

| Component | File | CLI |
|-----------|------|-----|
| Validation gate | `SkillOptTrainer.validate_skill()` | `skillopt_trainer.py validate <name>` |
| Rejection buffer | `add_to_reject_buffer()` → `skillopt_buffer.jsonl` | `skillopt_trainer.py buffer` |
| Text learning rate | `DEFAULT_TEXT_LR=3` in config | `--lr L` flag |
| Protected region | `skillopt_protected.json` | auto on `train()` |
| Negative transfer scan | `scan_negative_transfer()` | `skillopt_trainer.py risks` |
| Epoch training | `train_skill()` | `skillopt_trainer.py train <name>` |

## Validation Criteria (5 dimensions, threshold 0.80)

1. **Trigger conditions** (0.20): Does the skill specify when to activate?
2. **Procedure steps** (0.30): ≥3 numbered/ordered steps?
3. **Error handling** (0.20): Known issues and recovery?
4. **Verification steps** (0.15): How to confirm it works?
5. **Rollback plan** (0.15): How to revert if it breaks?

## Integration Pattern

```python
from scripts.skillopt_trainer import SkillOptTrainer

trainer = SkillOptTrainer()

# Step 1: Validate current version (baseline)
baseline = trainer.validate_skill("my-skill")

# Step 2: Apply modifications with learning rate (max 3 rules)

# Step 3: Re-validate
result = trainer.validate_skill("my-skill", test_count=5)

# Step 4: Accept or reject
if result["passed"] and result["score"] >= baseline["score"]:
    # Accept — improvement confirmed
    pass
else:
    # Reject — record to buffer
    trainer.add_to_reject_buffer("my-skill", 
        old_content, new_content, f"Score {result['score']:.2f} < baseline {baseline['score']:.2f}")
```

## Auto-validation on Create

When creating a new SKILL.md via `skill_manage(action='create')`:
- The FDE template already scores 1.00/1.00 on validation
- After any `skill_manage(action='patch')`: run `validate` to check for regression
- Track scores over time in `skillopt_validation.jsonl`

## Scan Results (2026-05-29)

Scanned 121 high-priority skills:
- 53 passed (complete)
- 68 failed (missing fields)
- Most common missing: rollback plan (89x), trigger conditions (56x)
- Zero negative transfer detected yet (insufficient history)
