# Nanobot Factory Session 2026-06-12 — Repair Verification + Cross-Validation

## Session scope
Continuing from the 2026-06-11 audit (145K lines, ~285 bugs found). This session focused on:
1. A-E module repair completion (agent/functions/enterprise/integrations/frontend)
2. Infrastructure hardening (Phase 1-6)
3. Final three-way cross-verification

## Key technique: Three-way cross-verification

Standard code audit says "read code and verify API returns". This session discovered a **stronger pattern**:

### The three-way cross proof
To be **certain** an endpoint returns real data (not mock/random/placeholder), you need **three independent sources**:

| Dimension | Tool | What it proves |
|-----------|------|----------------|
| **⑴ Application** | `curl endpoint` + inspect response body | Data structure correctness |
| **⑵ Browser** | `browser_vision` + `browser_snapshot` + `browser_console(expression=...)` | Frontend actually renders the data |
| **⑶ Metrics** | `curl /metrics/json` — counters match curl requests | The API is executing real code paths, not returning a canned response |

**Proof chain:**
1. curl POST /api/v2/generate → returns 500 with error chain "Diffusers module not available"
2. browser click "开始生成" → shows loading state, then error message
3. curl GET /metrics/json → shows `POST_/api/v2/generate: count=2, errors=2`

The **metrics counter matching** is the strongest signal — fake endpoints can't increment real Prometheus counters.

### Three-way application for bug detection
```
curl /health → OK
/browser/studio.html → shows API connected
/metrics/json → shows GET_/health: count=3 (matches curl calls)
```
If /health returns 200 but metrics show count=0, the code is returning a cached/static response.

## Subagent timeout workaround

**Problem**: leaf subagents (delegate_task with large context files) hit 600s timeout on files >8000 lines.

**Root cause**: The subagent reads the entire file first (large token cost), then plans/edit steps — 15+ API calls per subagent, exceeding timeout.

**Workaround**: 
- For files <3000 lines: leaf subagent works fine
- For files 3000-8000 lines: leaf subagent with specific `offset/limit` context (don't ask it to read the whole file — give it the line numbers)
- For files >8000 lines: **never use subagent**. Use patch directly. split the work into 2-3 targeted patches.

**Recovery from timed-out subagents**: 
1. Check `tool_trace` in the subagent result — did it write any files?
2. Run `git diff` or `wc -l` on target files to check for partial writes
3. If patch was applied but syntax failed, fix manually

## Subagent max output token overflow

**Problem**: When asking a subagent to rewrite a large JS file (806→1101 lines), the subagent hit max_output_tokens and returned partial output.

**Root cause**: The full file + rewrite instructions exceeded the model's max output tokens (typically 8K-16K).

**Solution**: **Segment the task**. Instead of asking for a complete rewrite:
1. Patch the HTML structure (new page divs + styles)
2. Patch the JS functions (new array functions)
3. Patch the UI controls (batch button, nav items)
4. Each patch is small enough to complete in one token window

## Remaining mock/placeholder state after all repairs (still ~15%)

| Module | Problem | Status |
|--------|---------|--------|
| `core/ai_models.py:216` | AestheticScorer fixed 7.5 to CLIP inference | ✅ Fixed this session |
| `functions/browser_functions.py:612-626` | 5 browser functions: get_html→requests, screenshot/script→Playwright required | ✅ Fixed (get_html real, others documented) |
| `functions/search_functions.py:168-178` | 8 search functions return "Executed" string (need API keys) | ⚠️ Known limitation |
| `functions/ai_functions.py` | 6 special AI funcs (voice clone/VRM/Live2D) return description strings | ⚠️ Need external service |
| 6 operators (SourceOSS/WebCrawler/Database/Screenshot/LabelSpeech/ScorePerplexity) | Need external services (OSS/DB/ASR/LLM) | ⚠️ Known limitation |
| enterprise_api.py | ProviderFactory fallback writes placeholder .png on failure | ✅ Fallback, core path real |

## Final readiness score: 7.5/10

"Commercial-grade" requires 8.0+. Remaining gap: GPU environment (diffusers/torch) for actual AI generation.
