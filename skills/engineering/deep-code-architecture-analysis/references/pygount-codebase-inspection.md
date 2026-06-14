# Codebase Inspection with pygount

Analyze repositories for lines of code, language breakdown, file counts, and code-vs-comment ratios using `pygount`.

## When to Use
- User asks for LOC (lines of code) count
- User wants a language breakdown of a repo
- User asks about codebase size or composition
- User wants code-vs-comment ratios
- General "how big is this repo" questions

## Prerequisites

```bash
pip install --break-system-packages pygount 2>/dev/null || pip install pygount
```

## 1. Basic Summary (Most Common)

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl everything and hang.

## 2. Common Folder Exclusions

| Project Type | Exclusion Pattern |
|---|---|
| Python | `.git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache` |
| JavaScript/TypeScript | `.git,node_modules,dist,build,.next,.cache,.turbo,coverage` |
| General catch-all | `.git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party` |

## 3. Filter by Specific Language

```bash
# Only count Python files
pygount --suffix=py --format=summary .

# Only count Python and YAML
pygount --suffix=py,yaml,yml --format=summary .
```

## 4. Detailed File-by-File Output

```bash
# Default format shows per-file breakdown, sorted by code lines desc
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

## 5. Output Formats

| Format | Command |
|--------|---------|
| Summary table | `pygount --format=summary .` |
| JSON (programmatic) | `pygount --format=json .` |

## 6. Interpreting Results

Summary table columns: **Language**, **Files**, **Code**, **Comment**, **%**.

Special pseudo-languages:
- `__empty__` — empty files
- `__binary__` — binary files (images, compiled, etc.)
- `__generated__` — auto-generated files
- `__duplicate__` — files with identical content
- `__unknown__` — unrecognized file types

## Pitfalls

1. **Always exclude .git, node_modules, venv** — otherwise pygount crawls everything.
2. **Markdown shows 0 code lines** — pygount classifies all Markdown as comments.
3. **JSON files show low code counts** — for accurate JSON line counts, use `wc -l`.
4. **Large monorepos** — use `--suffix` to target specific languages rather than scanning everything.

*Absorbed from `codebase-inspection` skill.*
