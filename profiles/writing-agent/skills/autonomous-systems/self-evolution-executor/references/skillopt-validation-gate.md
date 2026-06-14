# SkillOpt Validation Gate for Evolution Tasks

Based on Microsoft Research SkillOpt (arXiv:2605.23904, May 2026).

## Why Apply Here

Evolution tasks involve modifying skills, scripts, and configurations — exactly the kind of "external state" changes SkillOpt was designed to control.

## Process

When any self-evolution task proposes a change:

### 1. Baseline
Before applying any change, measure current performance:
```bash
# For a skill: count recent successful uses
python3 -c "
import json, subprocess
# Check wake_guide or cron logs for skill effectiveness
"
```

### 2. Apply with Learning Rate
Maximum 3 changes per cycle. Never batch-apply 10+ edits.

### 3. Validate
After applying, verify the system hasn't degraded:
- Check relevant cron jobs still parse correctly (`crontab -l`)
- Verify scripts have no syntax errors (`python3 -c "import py_compile; py_compile.compile(...)"`)
- Run a quick functional test

### 4. Accept/Reject
- Accept: if validation passes AND improvement is measured
- Reject: if validation fails; record what was rejected in `~/.hermes/rejection-buffer.jsonl`

## Pitfall

Evolution tasks are particularly vulnerable to "looks right but silently degrades" — because they're automated, there's no human catching subtle regression. The validation gate is what prevents this.
