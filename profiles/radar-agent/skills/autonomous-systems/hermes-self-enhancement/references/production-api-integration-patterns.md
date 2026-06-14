# Production-Grade AI API Integration Patterns

**Context**: Hermes runs AI API calls from cron-spawned subprocesses (not from within Hermes Agent itself). These subprocesses inherit NO environment variables and must independently load credentials, handle provider payment limits, and parse inconsistent AI JSON output.

**Scope**: All scripts that call external AI APIs (`hermes_ai_scoring.py`, `production_auto.py`, `product_delivery.py`, `ai_score_backfill.py`).

---

## Pattern 1: Env Loading for Cron Subprocesses

### Problem
Cron subprocesses do not inherit environment variables from Hermes Agent's `.env` file. AI API keys are unreachable.

### Solution
Each script that makes API calls must independently load `.env` at module level:

```python
from pathlib import Path

HERMES = Path.home() / ".hermes"
_env_path = HERMES / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _k, _v = _k.strip(), _v.strip()
            if _v and _v != "***" and (_k not in os.environ or not os.environ[_k]):
                os.environ[_k] = _v
```

### Pitfall: `log()` not yet defined
If this code runs before the `log()` function is defined (line 71+), calling `log()` here causes `AttributeError`. Solve by defining a simple `_early_log()` ahead of the env loader:

```python
def _early_log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
```

Use `_early_log()` for module-level setup failures, not `log()`.

### Also attempt config.yaml
DeepSeek API keys may be in `config.yaml` under `custom_providers`:

```python
try:
    import yaml
    _cfg_path = HERMES / "config.yaml"
    if _cfg_path.exists():
        with open(_cfg_path, encoding='utf-8') as _f:
            _cfg = yaml.safe_load(_f) or {}
        for _p in _cfg.get("custom_providers", []):
            if _p.get("name") == "deepseek" and _p.get("api_key"):
                if not os.environ.get("DEEPSEEK_API_KEY"):
                    os.environ["DEEPSEEK_API_KEY"] = _p["api_key"]
                if not os.environ.get("OPENROUTER_API_KEY"):
                    os.environ["OPENROUTER_API_KEY"] = _p["api_key"]
except Exception as e:
    _early_log(f"WARNING config.yaml加载失败: {e}")
```

---

## Pattern 2: Multi-Provider API Key Search

### Problem
Different environments have different API keys available. A script that hardcodes one provider (e.g., `OPENROUTER_API_KEY`) fails silently when that key is absent but another key (e.g., `DEEPSEEK_API_KEY`) is available.

### Solution
Search all known key names in priority order:

```python
def get_api_key() -> tuple:
    """
    Returns (api_key, api_url, model).
    Priority: DeepSeek > OpenRouter > Anthropic > OpenAI
    """
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return (key, "https://api.deepseek.com/v1/chat/completions", "deepseek-chat")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return (key, "https://openrouter.ai/api/v1/chat/completions", "openrouter/auto")
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return (key, "https://api.anthropic.com/v1/messages", "claude-sonnet-4-20250514")
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return (key, "https://api.openai.com/v1/chat/completions", "gpt-4o-mini")
    return ("", "", "")
```

### Model Naming Convention
| Provider | URL | Model |
|----------|-----|-------|
| DeepSeek (direct) | `api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| OpenRouter (auto) | `openrouter.ai/api/v1/chat/completions` | `openrouter/auto` |
| Anthropic | `api.anthropic.com/v1/messages` | `claude-sonnet-4-20250514` |
| OpenAI | `api.openai.com/v1/chat/completions` | `gpt-4o-mini` |

---

## Pattern 3: OpenRouter `openrouter/auto` for Payment-Limited Accounts

### Problem
OpenRouter accounts with limited credits (e.g., $270 total usage, daily ~$0.01) can only afford ~500-1000 output tokens on models like `deepseek/deepseek-chat`. Requests with `max_tokens=1500` or long prompts trigger HTTP 402.

### Solution
Use `openrouter/auto` instead of a fixed model. This routes to the cheapest available model (often `openai/gpt-oss-120b` which is free or near-free) and avoids 402 errors:

```python
model_to_use = "openrouter/auto"  # NOT "deepseek/deepseek-chat"
```

### Verified Token Budget
With `openrouter/auto`, max_tokens up to 4000 works (tested). Real product-generation requests (595-byte prompt) succeed with:
- prompt_tokens: ~154-165
- completion_tokens: ~375-970
- Total: ~529-1135 tokens

### Safe defaults for all scripts
```python
"max_tokens": 1000  # safe for openrouter/auto, generous for product gen
```

---

## Pattern 4: HTTP Error 401/402/403 Skip-Retry

### Problem
401 (auth failure), 402 (payment required), and 403 (forbidden) are **permanent** errors. Retrying them 3 times with sleep intervals wastes 15-30 seconds per batch.

### Solution
Check HTTP status code before deciding to retry:

```python
except urllib.error.HTTPError as e:
    if e.code in (401, 402, 403):
        raise RuntimeError(f"API永久错误({e.code}): {e.reason}")  # or log and return fallback
    if attempt < max_retries:
        time.sleep(3 * attempt)
        continue
    raise RuntimeError(f"API请求全部失败: {e}")
```

For script-internal functions (not main entry points), return empty results on permanent errors rather than crashing:

```python
except urllib.error.HTTPError as e:
    if e.code in (401, 402, 403):
        log(f"⚠️ API永久错误({e.code})，跳过")
        return []  # empty but graceful
```

---

## Pattern 5: Multi-Type JSON Parsing for AI-Generated Content

### Problem
Different AI models (even the same model across different runs) return JSON in different formats:
- `target_audience`: str, dict `{"primary": "..."}`, or list `["user1", "user2"]`
- `risks`: list of dicts, str, or None
- `mvp_features`: list of dicts or list of strings
- markdown code blocks wrapped or plain JSON

### Solution: Three-Level Defense

**Level 1 — Markdown stripping:**
```python
cleaned = re.sub(r'^```(?:json)?\s*', '', ai_response.strip())
cleaned = re.sub(r'\s*```$', '', cleaned)
```

**Level 2 — Parse and verify:**
```python
try:
    parsed = json.loads(cleaned)
except json.JSONDecodeError:
    match = re.search(r'\[\s*\{.*\}\s*\]', ai_text, re.DOTALL)
    if match:
        parsed = json.loads(match.group())
```

**Level 3 — Field-level type normalization (use in all consumers):**
```python
def normalize_target_audience(ta):
    """Normalize str/list/dict to string — AI output varies by model."""
    if isinstance(ta, str):
        return ta
    if isinstance(ta, dict):
        return ta.get("primary", "")
    if isinstance(ta, (list, tuple)):
        return ", ".join(str(x) for x in ta[:3])
    return ""

def normalize_risks(risks):
    """Normalize None/list/str to list of dicts."""
    if risks is None:
        return []
    if isinstance(risks, str):
        return [{"type": "风险", "description": risks}] if risks.strip() else []
    if isinstance(risks, list):
        return risks
    return []
```

---

## Pattern 6: `ai_scored_at IS NULL` vs `ai_score_total = 0`

### Problem
When selecting items for AI scoring, using `WHERE ai_score_total IS NULL OR ai_score_total = 0` fails after rule-based scoring has set `ai_score_total` on ALL items. The real signal for "not yet AI-scored" is `WHERE ai_scored_at IS NULL`.

### Correct query
```sql
SELECT id, title, COALESCE(content, '') as content, ...
FROM cleaned_intelligence
WHERE ai_scored_at IS NULL
  AND LENGTH(COALESCE(content, '')) >= 30
  AND title IS NOT NULL AND title != ''
ORDER BY LENGTH(COALESCE(content, '')) DESC, importance_score DESC
```

The `ai_scored_at IS NULL` check is the canonical filter for "needs real AI scoring" and should be used in all scoring scripts.

---

## Pattern 7: Retry with Exponential Backoff + Error Discrimination

### Template
```python
max_retries = 3
last_error = None
for attempt in range(1, max_retries + 1):
    try:
        req = urllib.request.Request(api_url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
        return response_data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        last_error = e
        if e.code in (401, 402, 403):
            log(f"⚠️ API永久错误({e.code})，跳过")
            return None  # permanent, don't retry
        if attempt < max_retries:
            time.sleep(3 * attempt)  # exponential backoff: 3, 6, 9 seconds
        continue
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        last_error = e
        if attempt < max_retries:
            time.sleep(2 * attempt)
        continue

log(f"❌ 所有重试失败: {last_error}")
return None
```

### Timeout recommendations
| Operation | Timeout (seconds) |
|-----------|-------------------|
| Simple scoring (2 items) | 30 |
| Batch scoring (5 items) | 60 |
| Product generation (1 item) | 60 |
| Semantic verification | 60 |
| Any with 3 retries | total ≤ 180 |
