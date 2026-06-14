# Context System Consolidation — 2026-05-27

## Original State (4 scripts → overlapping)
| Script | Lines | Function |
|--------|-------|----------|
| context_packer.py | 338 | 动态提取+分层压缩 SOUL.md (85.7%压缩率) |
| context_index_system.py | 274 | 拆分章节+轻量索引 (~2120tokens) |
| surgical_context_slicer.py | 339 | 手术刀式切分 (~539tokens) — **已删除** |
| context_auto_assoc.py | 279 | 自动关联+预加载 (~3195tokens) — **已删除** |

## Problem: 3-way duplicated mapping table
classify_task() + task_type→rules/tools/sections 映射在 **slicer + auto_assoc + packer 各维护一份**。
差异率 ~5%，但修改一处要同步改三处。

## Solution
1. **Extract shared config**: `reports/task_type_config.json` (12 task types, 5314 bytes)
2. **Merge into one pipeline**: `scripts/context_pipeline.py` with `--mode=surgical|auto`
3. **Remove old cron**: 2 deleted (slicer, auto_assoc) + 1 duplicated (context-index-system wrapper)
4. **Add new cron**: context-pipeline (每1分钟, no_agent=true)

## Key design choices
- `classify_task()` now lives in one place (context_pipeline.py), reads config from JSON
- `find_section_file()` uses triple-fallback: glob → stem-include → exact path
- Both old scripts backed up to `/mnt/d/Hermes/备份/context_old_scripts_20260527/`

## Remaining scripts still active
- `context_packer.py` — kept (orthogonal: extract+compress)
- `context_index_system.py` — kept (orthogonal: chapter splitting)
- `context_pipeline.py` — NEW (replaces slicer+auto_assoc)
