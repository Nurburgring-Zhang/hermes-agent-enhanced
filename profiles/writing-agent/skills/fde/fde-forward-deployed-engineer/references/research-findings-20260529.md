# FDE Research Findings (2026-05-29)

## Source Papers

### SkillOpt: Executive Strategy for Self-Evolving Agent Skills
- arXiv:2605.23904 | MSRA | May 22, 2026
- **Core insight**: Treat skill documents as external trainable state. Apply DL training loop concepts to text-space skill optimization.
- **6 components**: Rollout batch → Minibatch reflection → Bounded text updates (LR) → Validation gate → Reject buffer → Epoch slow/meta update
- **Results**: 52/52 cells best/tied-best. +23.5 avg on GPT-5.5. Small models benefit most (nano: 30.8→80.2, ×2.6)
- **Transfer**: Cross-model, cross-harness (Codex↔Claude Code), cross-benchmark all positive

### From Raw Experience to Skill Consumption
- arXiv:2605.23899 | MSRA | May 22, 2026
- **Core insight**: 75% helpful, 25% cause negative transfer
- **Format doesn't predict utility**: Friedman test p>0.34 across all 4 tested formats
- **LLM judge can't pick better skill**: 46.4% accuracy (random), 15.8% on high-gap pairs
- **Meta-skill validated rubric**: 3 dimensions that actually predict utility → raises judge accuracy 46.4%→73.8%

### Industry Trends
- OpenAI: $4B Deployment Company, acquired Tomoro (150 FDEs)
- Anthropic: $1.5B entity with Blackstone/Goldman
- Google Cloud: CEO personally recruiting FDEs, 59 open positions
- Shanghai Jiao Tong: First FDE training program in China

## Key Decisions Made

1. **mlops reference skills NOT converted to workflow** — format doesn't predict utility (p>0.34). They are reference docs not workflow steps.
2. **Type-aware validation gate**: workflow 80% / reference 60% / mlops_ref 0%
3. **Cron collision avoidance**: L1→45min, L2→15min (offset from collection at 0min)
4. **LLM dual-track**: Every module has LLM path + rule fallback. Never say "no LLM" — Hermes is built on LLM.
