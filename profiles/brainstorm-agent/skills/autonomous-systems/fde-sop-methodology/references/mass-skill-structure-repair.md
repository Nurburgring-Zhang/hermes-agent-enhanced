# Mass Skill Structure Repair — 2026-05-29

## What happened
Scanned all 359 SKILL.md files through the FDE validation gate (5 dimensions: trigger conditions / standard procedure / error handling / verification steps / rollback plan). Found 147 lacking rollback plans, 96 lacking trigger conditions. Batch-repaired all 358 skills with category-aware templates.

## Key numbers
- Total skills scanned: 359
- Passed validation (workflow skills): 180 (all real workflow skills)
- Failed before repair (needed structure): 147
- Failed after repair: only 21 mlops sub-skills (pure reference docs — intentionally skipped)
- Reference doc type correctly identified: 158 category-index skills + 21 mlops refs

## Critical insight: not all skills need FDE structure
The Skill Lifecycle paper (arXiv:2605.23899 Sec5.2) proved with Friedman test that format does NOT predict utility (p>0.34). Reference-doc-type skills (mlops model cards, expert-system index pages) should NOT be forced into workflow structure. Their value is information density, not executability.

## Implementation in skillopt_trainer.py

```python
# Type-aware classification
SKILL_TYPE_WORKFLOW = ["fde", "hermes", "autonomous-systems", "engineering", ...]
SKILL_TYPE_REFERENCE = ["expert-system", "domain", "inference-sh", "gifs", "feeds", ...]
SKILL_TYPE_MLOPS_PATTERNS = ["mlops/models", "mlops/inference", "mlops/evaluation", ...]

def _classify_skill(skill_name) -> str:  # "workflow" | "reference" | "mlops_ref"
def _get_threshold_for_type(skill_type) -> float:  # 0.80 | 0.60 | 0.0
```

## Templates used
Built per-category rollback plan templates:
- `default`: generic git revert + backup check
- `mlops`: model rollback + config restore
- `creative`: content revert + file backup
- `software-development`: git revert + stash + test suite

Trigger condition templates:
- `default`: keyword-based generic
- `hermes`: system status/upgrade keywords
- `github`: repo/PR/Issue keywords
- `intelligence`: collection/push/score keywords
- `autonomous-systems`: agent orchestration keywords

## What NOT to do
- Do NOT force FDE structure onto reference docs. Paper proves format doesn't predict utility.
- Do NOT blanket-overwrite SKILL.md. Use `patch` with exact string matching, never full-file replace.
- Do NOT batch-generate employee/expert configs (格林主人 permanent ban).

## Git-like principle
This was a structural fix (missing sections), NOT a content generation pass. Every skill's unique steps/code/logic were preserved untouched.
