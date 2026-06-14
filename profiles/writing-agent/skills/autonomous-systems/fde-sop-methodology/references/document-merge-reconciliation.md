# Document Merge & Reconciliation Pattern
## SOUL.md External Source Integration (2026-06-06)

### The Problem
You receive an external document (article, paper, spec, second SOUL.md) that contains settings, rules, personality profiles, or methodologies not present in your current SOUL.md or skill library. How to systematically extract and integrate without losing existing content or creating duplicates?

### Pattern: 4-Phase Audit & Merge

**Phase 1: Full Acquisition**
- Read both files in their entirety (not offset/limit — use larger limit values or split into chunks)
- For very large files (>500 lines), read the full file once to build a mental index, then re-read key sections

**Phase 2: Comparative Audit**
Build a complete matrix comparing the external file vs current SOUL.md/skills:

| # | Category | External Has | Current Has | Decision |
|---|----------|-------------|-------------|----------|
| 1 | Core identity | ✅ detailed | ✅ concise | Merge detailed into concise |
| 2 | Personality specs | ✅ 9 personas | ✅ 3 personas | Expand |
| 3 | Execution rules | ✅ full charter | ✅ partial | Expand |
| ... | ... | ... | ... | ... |

**Decision categories:**
- `MERGE` — new content, add to current
- `REPLACE` — current version is inferior, replace section
- `SKIP` — current already has equivalent or better version
- `KEEP_BOTH` — complementary perspectives, keep both

**Phase 3: Structured Injection**
Layer the merge by priority level:
- **Layer 1 (Always inject)**: Core identity declarations, permanent bans, behavioral rules, execution constitutions
- **Layer 2 (Context-available)**: Persona details, communication style examples, tool-use specifics
- **Layer 3 (On-demand)**: Niche scenarios, edge cases, platform-specific notes

**Phase 4: Verification**
Run automated checks:
```python
content = open("/home/administrator/.hermes/SOUL.md").read()
checks = {"关键术语1": "关键术语1", ...}
for name, keyword in checks.items():
    assert keyword in content, f"Missing: {name}"
```

### User Preference: Merge Thoroughness (格林主人, 2026-06-06)
格林主人 demands **exhaustive, no-compromise merging**. When told "对比分析，还有哪些重要的细节被精简了！补充进来！！！", he expects:
- 100% coverage of all source material — no abbreviation
- Every persona detail, every example, every trigger word, every Emoji list
- Every execution rule variant, even if it seems redundant
- Full file size comparison before/after (bytes, lines, % increase)
- Automated verification checklist with pass/fail per item

**Pitfall — Do NOT "summarize" in a merge**: External merging means transfer-in-full. If the source document has 10 emoji per persona, you include all 10. If it has explicit language examples, include them verbatim. "精简" is for your own writing, not for external document merging.

### Script Reference
For SOUL.md editing, use `patch` (fuzzy match handles minor formatting differences between documents) rather than full `write_file` when making targeted section replacements. For large-scale rewrites (>60% content change), use `write_file`.

### When to use
- User sends an external document and says "整合到我的系统"/"合并到SOUL.md"
- Discovered an old version of SOUL.md/settings file that has content the current version lacks
- Migrating from another system's configuration to Hermes
