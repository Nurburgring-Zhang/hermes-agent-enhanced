# Governance Rule Propagation — Multi-Layer Embedding Pattern

## When to Use

When the user demands a NEW permanent governance-level rule that must be:
- Highest priority / override all other rules
- Active in every session, every conversation, every task
- Not reliant on a single file or mechanism

## The 5-Layer Embedding Pattern

This pattern was demonstrated on 2026-06-01 with the Anti-Hallucination Rule (§0).

### Layer 1: SOUL.md — Permanent Injunctions
**File**: `~/.hermes/SOUL.md` under `## 永久禁令`
Insert as §0 (highest priority, numbered 0). Full text with 5 enforcement bullets.
```
0. **反幻觉铁律** — 这是最高优先级的强制规则，凌驾于所有其他规则之上。
```

### Layer 2: context_sections/ — All Chapter Files
**Directory**: `~/.hermes/reports/context_sections/`
Each file is independent content. Insert a `> 🔴🔴🔴` prefixed block at the very TOP of every file.

### Layer 3: Core Scripts — docstring
**Directory**: `~/.hermes/scripts/`
Insert as docstring block at script top — after shebang, before imports. Use this template:
```python
"""
🔴🔴🔴 反幻觉铁律：严禁任何不加核实的猜想、胡编乱造、自己瞎编！
必须核实才能说/必须验证才能写/必须确认才能断言/不知道就说不知道
这是最高优先级规则，凌驾于所有其他规则之上。
"""
```

### Layer 4: auto_engine — Same docstring
**File**: `~/.hermes/auto_engine/self_evolution_engine.py`
Same as Layer 3.

### Layer 5: Memory — Permanent Fact
```
memory tool → replace/remove older entry → add compact summary
```
Keep under 100 chars. Example:
```
反幻觉铁律20260601: 最高优先级规则，严禁不加核实的猜想...已写入SOUL+24章节+16脚本。
```

### Layer 6: green-master-rules Skill — §0
**File**: `~/.hermes/skills/governance/green-master-rules/SKILL.md`
Add as `## 🔴🔴🔴 规则0：<规则名>` right after trigger conditions. Include the implantation scope.

## Verification Script

```bash
echo "=== SOUL.md ===" && head -35 ~/.hermes/SOUL.md 
echo "=== 章节文件 ===" && for f in ~/.hermes/reports/context_sections/*.md; do grep -q "反幻觉铁律" "$f" && echo -n "✅ " || echo -n "❌ "; basename "$f"; done
echo "=== 脚本 ===" && for f in task_boundary.py auto_recall.py ...; do grep -q "反幻觉铁律" ~/.hermes/scripts/"$f" && echo -n "✅ " || echo -n "❌ "; echo "$f"; done
```

## Key Lessons
1. **context_sections files are INDEPENDENT** — each must be edited separately, not relying on inclusion from SOUL.md
2. **Shebang handling** — scripts starting with `#!/usr/bin/env python3` need the docstring inserted AFTER the shebang line
3. **Memory is limited (2200 chars)** — compact to <100 chars; verify before add
4. **Always run syntax check after modifying scripts** — `py_compile.compile()` on each modified file
5. **sync context_index.json** after modifying context_sections — `python3 scripts/context_reconstructor.py all`
