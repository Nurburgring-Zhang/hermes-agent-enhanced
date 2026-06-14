# GitHub Publishing Pattern

## Sanitization Checklist (pre-commit)

Before pushing to GitHub, run through this list:

```
[ ] API keys:       grep -rn "sk-[a-zA-Z0-9]\{32\}" . | grep -v "sk-xxxxxxxx"
[ ] WSL IPs:        grep -rn "172\.31\.32\.1" . | grep -v "WSL_HOST"
[ ] Absolute paths: grep -rn "/home/" . | grep -v "Path.home()"  
[ ] Usernames:      grep -rn "/home/[a-z]" .  (should only appear in Path.home() context)
[ ] .pyc files:     find . -name "__pycache__" -exec rm -rf {} +
[ ] Personal tokens: grep -rn "github_pat_" .
```

## Directory Structure for Open-Source Enhancement Pack

```
hermes-enhancement-pack/
├── README.md              # Project intro + quickstart + architecture + usage numbers
├── deploy.py              # One-command deploy (detects ~/.hermes/, copies files, adds cron, runs tests)
├── config_enhancement.yaml # Config fragment (no API keys, use placeholders)
├── agent/                 # Core agents (monitor, reflector, router)
├── tools/                 # Utilities (progress tracker)
├── scripts/               # All enhancement scripts
├── production_loop/       # Reliability engine
├── auto_engine/           # Self-evolution
├── evolution_v3/          # V3 modules
└── skills/                # Skill definitions
```

## Model Naming Convention (User Preference)

Use **abstract tiers**, not vendor model names:

| In docs/code | Don't use |
|:-------------|:----------|
| `model_tier="value"` | deepseek-v4-flash |
| `model_tier="performance"` | deepseek-v4-pro |
| "通用模型" / "通用省钱" | "flash" / "轻量" |
| "强力模型" / "强力高质量" | "pro" / "旗舰" |

The `model_router.py` implementation maps tiers to actual models internally. External consumers only see tiers.

## User Preference: Code Tasks Use Strongest Model

For code/development tasks, always route to the strongest available model. Code-dedicated models (deepseek-coder, codellama) should NOT be used — the general strongest model is better for all code work.

## Git Commands

```bash
git init
git add .
git commit -m "Initial release: ..."
git remote add origin https://<user>:<token>@github.com/<user>/<repo>.git
git push -u origin main
```
