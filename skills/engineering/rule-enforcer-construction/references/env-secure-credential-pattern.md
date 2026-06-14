# Env-Secure Credential Pattern

## Background

Phase-0 of the system-wide commercial-grade audit (2026-06-12) discovered that config.yaml contained 6 API keys in plaintext — 4 NVIDIA keys, 1 DeepSeek key, 1 custom provider key. Also pushplus.token was in the clear.

## Principle

Config files in version control must never contain secrets. All credentials must be injected at runtime via environment variables, loaded from a .env file that is git-ignored and permissions-restricted (chmod 600).

## Implementation Architecture

```
.env (git-ignored, 600)     -> os.environ at startup
       |
config.yaml (git-tracked)   -> ${ENV_VAR_NAME} references
       |
scripts/env_loader.py       -> model_tools.py startup hook loads .env
       |
resolve_config_env()        -> model_tools.py startup replaces ${ENV} in config dicts
```

## Key Mapping Table

| config.yaml Location | Env Variable |
|---|---|
| providers.nvidia-deepseek.api_key | NVIDIA_DEEPSEEK_API_KEY |
| providers.nvidia-glm.api_key | NVIDIA_GLM_API_KEY |
| providers.nvidia-kimi.api_key | NVIDIA_KIMI_API_KEY |
| providers.google-gemini.api_key | NVIDIA_NEMOTRON_API_KEY |
| providers.deepseek.api_key | DEEPSEEK_API_KEY |
| custom_providers[1].api_key | DEEPSEEK_CUSTOM_API_KEY |
| pushplus.token | PUSHPLUS_TOKEN |

## Testing

```python
import yaml
from env_loader import init_env, resolve_config_env
init_env()
with open('config.yaml') as f: cfg = yaml.safe_load(f)
resolved = resolve_config_env(cfg.get('providers', {}))
for name, p in resolved.items():
    if isinstance(p, dict) and p.get('api_key'):
        ak = p['api_key']
        if ak and (ak.startswith('nvapi-') or ak.startswith('sk-')):
            print(f'  {name}: key resolved ({len(ak)} chars)')
```

## Pitfalls

1. Hermes does not support ${ENV} in YAML natively — resolve_config_env() must run in Python code (injected at model_tools.py startup)
2. .env must be chmod 600
3. model_tools.py env_loader import is wrapped in try/except — verify it's present after each upgrade
4. Dont use ${ENV} inside JSON-encoded YAML strings (like fallback_providers inline JSON) — JSON parser sees it as literal text
5. After each Hermes upgrade, re-inject the env_loader startup block and re-import Path

## Files Created

- /home/administrator/.hermes/scripts/env_loader.py (3262 bytes)
- /home/administrator/.hermes/.env (chmod 600)
- /home/administrator/.hermes/.gitignore
