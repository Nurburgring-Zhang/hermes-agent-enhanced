# NVIDIA + OpenRouter Free API Configuration Reference

**Date:** 2026-06-06
**Context:** Added 4 NVIDIA providers and 4 OpenRouter free models as fallback chain for Hermes Agent.

## Provider / API Key Mapping

### NVIDIA (build.nvidia.com)

| Provider ID | API Key (truncated) | Model | Tested |
|-------------|-------------------|-------|--------|
| `nvidia-deepseek` | `nvapi-xtR0GK...zYae` | deepseek-ai/deepseek-v4-pro | ✅ Passed |
| `nvidia-glm` | `nvapi-EYANMn...dRDw` | z-ai/glm-5.1 | ⏳ Timed out (NVIDIA slow) |
| `nvidia-kimi` | `nvapi-nP_P15...xILZ` | moonshotai/kimi-k2.6 | ⏳ Not tested |
| `nvidia-nemotron` | `nvapi-03Q5ii...8rck` | nvidia/nemotron-3-ultra-550b-a55b | ✅ Passed |

All share the same base_url: `https://integrate.api.nvidia.com/v1`

### OpenRouter Free Models

| Model | Free Tier Limit |
|-------|----------------|
| moonshotai/kimi-k2.6:free | Rate-limited, last resort |
| sourceful/riverflow-v2.5-pro:free | Rate-limited, last resort |
| nvidia/nemotron-3-ultra-550b-a55b:free | Rate-limited, last resort |
| openrouter/owl-alpha | Rate-limited, last resort |

## Fallback Chain Priority

```
deepseek-chat (primary) →  nvidia-deepseek(v4-pro) → nvidia-glm(glm-5.1) → nvidia-kimi(k2.6) → nvidia-nemotron(ultra w/thinking) → openrouter/kimi-k2.6:free → openrouter/riverflow:free → openrouter/nemotron:free → openrouter/owl-alpha
```

On 429/rate-limit: 60s cooldown, then `_fallback_index++` advances to next in chain.

## Key Technical Details

### config.yaml `providers:` format (v12+)
```yaml
providers:
  <provider-key>:
    api: <base_url>
    api_key: <key or key_env reference>
    default_model: <model-slug>
    name: <display-name>
    # Optional:
    extra_body: {<per-model extras>}
    key_env: <ENV_VAR_NAME>  # read key from env instead
    api_mode: chat_completions  # or codex_responses, anthropic_messages
    context_length: 131072
    transport: chat_completions  # alias for api_mode
```

### How Runtime Resolution Works

1. `resolve_runtime_provider(requested='nvidia-deepseek')` called
2. `_resolve_named_custom_runtime()` checks if requested resolves to "custom"
3. `_get_named_custom_provider('nvidia-deepseek')` iterates `config['providers']` dict
4. Matches by provider_key or normalized name → returns `{base_url, api_key, model, ...}`
5. Returns dict with `provider: "custom"`, the key, url, and model

### `hermes config set` Quirk

`hermes config set providers '{...}'` writes the value as a JSON string, not a YAML block. To fix:
```python
import yaml, json
with open('config.yaml') as f: cfg = yaml.safe_load(f)
cfg['providers'] = json.loads(cfg['providers'])  # if string
with open('config.yaml', 'w') as f: yaml.dump(cfg, f)
```

### Verification Snippet

```python
from openai import OpenAI
from hermes_cli.runtime_provider import resolve_runtime_provider

r = resolve_runtime_provider(requested='nvidia-deepseek')
assert r['base_url'] == 'https://integrate.api.nvidia.com/v1'
assert r['api_key'].startswith('nvapi-')
assert r['model'] == 'deepseek-ai/deepseek-v4-pro'

client = OpenAI(base_url=r['base_url'], api_key=r['api_key'])
r = client.chat.completions.create(
    model=r['model'],
    messages=[{'role':'user','content':'test'}],
    max_tokens=10
)
print(f"OK: {r.choices[0].message.content}")
```
