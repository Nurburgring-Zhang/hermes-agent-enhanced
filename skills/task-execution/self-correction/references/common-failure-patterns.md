# Common Failure Patterns (collected 2026-06-15/16)

## Pattern 1: Port bind failure after kill
**Symptom**: `[Errno 98] error while attempting to bind on address ('127.0.0.1', 8001): address already in use`
**Root cause**: `fuser -k` or `pkill -f` didn't kill all old processes. Multiple server.py instances competing for same port.
**Fix**: `pkill -9 -f "python3 server.py"` (specific process name only!) then `fuser 8001/tcp 2>/dev/null || echo "free"`
**Prevention**: Always verify port free before launch. Use `process(wait)` with 15s timeout to check for "Application startup complete" in startup log.

## Pattern 2: Element Plus icon not exported
**Symptom**: Build error: `"Stop" is not exported by "@element-plus/icons-vue"`
**Root cause**: Different versions of element-plus export different icon sets. `Stop` exists in some but not all.
**Fix**: Remove the unavailable icon import. Replace with emoji or SVG.
**Prevention**: Check icon exists in installed version before import. Build after any icon import change.

## Pattern 3: execute_code f-string shell escaping
**Symptom**: `SyntaxError: unexpected character after line continuation character` when running curl + python3 inline parsing in execute_code
**Root cause**: Nested `\\\"` escaping in Python f-string + shell double-quotes + json parsing quotes overload
**Fix**: Move shell command to terminal() command parameter, not execute_code f-string
**Prevention**: Simple commands (>3 parts) go in terminal(). Complex pipelines go in terminal(). Only simple tools go in execute_code.

## Pattern 4: write_file on existing large file
**Symptom**: 945-line file becomes 23 lines after write_file
**Root cause**: write_file is FULL REPLACE, not insert. Writing partial content destroys rest of file.
**Fix**: Restore from git: `git checkout -- <file>`
**Prevention**: Use patch(old_string, new_string) for changes to existing files <5 lines. For larger changes, read_file full content first, modify, then write_file full content.

## Pattern 5: Subagent path drift
**Symptom**: Subagent analyzes wrong project directory, returns irrelevant results
**Root cause**: goal description relative path is ambiguous; subagent finds a different same-named directory
**Fix**: Include ABSOLUTE project root path in goal. Verify output paths match after return
**Prevention**: `toolsets=["terminal","file"]` to prevent web search drift. Post-return path verification mandatory.

## Pattern 6: Same file modified by two subagents
**Symptom**: Build breakage from conflicting changes in same file
**Root cause**: Two parallel delegate_tasks both patched the same .vue file independently
**Fix**: Check which version to keep, re-apply needed changes from the dropped version
**Prevention**: File allocation table — each file assigned to exactly one subagent per batch

## Pattern 7: Large file (10,000+ lines) partial read → failed patch
**Symptom**: `Could not find a match for old_string` even though the string exists in the file
**Root cause**: read_file with offset/limit returned only part of the file; the old_string exists in an unread section
**Fix**: Read the exact line range with grep -n first, then read_file with precise offset/limit
**Prevention**: Before patching any file over 200 lines, grep -n the target string to confirm location. For files over 5,000 lines, always use grep -n before patch.

## Pattern 8: uvicorn --access-log not a valid flag
**Symptom**: `Error: Got unexpected extra argument`
**Root cause**: uvicorn's `--access-log` flag expects a boolean (no value path). The standard library changed between versions.
**Fix**: Omit --access-log entirely, or check uvicorn --help for flags supported in the installed version.
**Prevention**: After writing deploy.sh, do a dry-run to validate every flag. uvicorn's flag set is smaller than expected.

## Pattern 9: server.py function-level import duplicates and scope pollution
**Symptom**: After adding multiple new API routes in server.py, `NameError: name 'JSONResponse' is not defined` despite import at file top
**Root cause**: New route blocks use `from fastapi.responses import JSONResponse` at function scope (lazy import) but when 4+ route blocks are added in sequence, some accidentally end up outside the import scope or imports get duplicated
**Fix**: After any batch of route additions, grep -n 'import' server.py at the block to confirm the import exists
**Prevention**: Each new route block MUST verify its own imports exist. Add unused imports at file top, not in middle of file.
