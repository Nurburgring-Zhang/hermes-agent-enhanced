# Skill Consolidation Methodology

Applied during the 406-skill classification and merge analysis (2026-06-08).

## When to Consider Merging Skills
Two or more skills should be merged when:
1. They describe **different aspects of the same system** — e.g. hy-memory-p0-integration, structmem, lossless-claw-v1, lossless-claw-v2 all describe the unified memory core.
2. They form **sequential steps in the same pipeline** — e.g. skill-evolver → darwin-evolver → executor → fix-actions is one evolution cycle, not four independent capabilities.
3. They are **old versions superseded by a newer one** — e.g. wechat-collector v3/v7/v9 when v9 is the only active version.
4. They are **auto-generated duplicates** — self-evolution engine created skills that duplicate human-created ones.

## Merge Criteria
Only merge if the result has HIGHER clarity and LOWER decision cost:
- Agent must not spend more time choosing between merged sections than it spent choosing between separate skills
- Each section within a merged skill must have a clear, distinct trigger
- The merged skill's description must be at least as searchable as the originals

## Anti-Patterns (Do NOT Merge)
- Different technical approaches to the same output (e.g. garden-web-video's screenshot approach vs hyperframes' native render) — they serve different constraints
- Infrastructure vs application layers (e.g. comfyUI video engine vs ai-short-drama-pipeline)
- New independent threat domains (e.g. supply-chain-security is not a subset of the general security skill)
