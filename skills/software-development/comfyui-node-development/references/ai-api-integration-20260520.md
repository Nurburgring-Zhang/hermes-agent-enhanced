# AI API Integration in ComfyUI Nodes (2026-05-20)

## Architecture

ComfyUI nodes that call external LLM APIs for prompt generation/rewriting need careful error handling because:
1. ComfyUI's `execution.py` catches most exceptions but the node itself must not hang
2. API failures should degrade gracefully, not crash the workflow
3. Network timeouts in ComfyUI block all node execution

## The _call_ai Pattern

```python
_last_ai_error = ""

def _call_ai(self, api_url, api_key, model_name, system_prompt, user_content,
             temperature=0.8, max_tokens=2048, retry=2):
    self._last_ai_error = ""
    if not api_url:
        self._last_ai_error = "未设置API地址"
        return None

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if model_name:
        payload["model"] = model_name

    for attempt in range(retry + 1):
        if attempt > 0:
            _time.sleep(2 ** attempt)
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=(10, 60)) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            if "error" in result:
                err = result["error"]
                msg = str(err.get("message", err)) if isinstance(err, dict) else str(err)
                self._last_ai_error = f"API错误: {msg[:100]}"
                # 401/403/404: don't retry
                if isinstance(err, dict) and err.get("code") in (401, 403, 404):
                    break
                continue
            
            # Extract content from response
            content = None
            if "choices" in result:
                for c in result["choices"]:
                    content = (c.get("message", {}).get("content") or 
                              c.get("text") or 
                              c.get("delta", {}).get("content"))
                    if content:
                        break
            if content:
                return content.strip().strip('"').strip("'").strip()

        except urllib.error.HTTPError as e:
            code_map = {401:"API密钥无效", 403:"无权限", 404:"API地址不存在",
                       429:"请求频率超限", 500:"服务端错误", 502:"网关错误", 503:"服务不可用"}
            self._last_ai_error = f"{code_map.get(e.code, f'HTTP {e.code}')}: ..."
            if e.code in (401, 403, 404): break

        except urllib.error.URLError as e:
            reason = str(e.reason)
            if "timed out" in reason.lower():
                self._last_ai_error = "连接超时"
            elif "refused" in reason.lower():
                self._last_ai_error = "连接被拒绝(服务未启动)"
            else:
                self._last_ai_error = f"连接失败: {reason[:80]}"

        except json.JSONDecodeError:
            self._last_ai_error = "API返回非JSON数据"

    return None
```

## Design Decisions

1. **urllib.request not requests** — avoids adding a dependency to ComfyUI nodes
2. **Separate connect/read timeouts** — `timeout=(10, 60)` prevents hanging on slow connections
3. **Exponential backoff** — `2^attempt` seconds between retries (2s, 4s)
4. **No-retry codes** — 401/403/404 won't resolve with retry
5. **User-facing error storage** — `_last_ai_error` gets included in output STRING
6. **Choice parsing** — handles both `/v1/chat/completions` (message.content) and `/v1/completions` (text) formats
7. **Default temperature 0.8** — balances creativity and coherence for prompt generation

## Supported API Endpoints

| Provider | URL |
|----------|-----|
| Ollama (local) | http://localhost:11434/v1/chat/completions |
| LM Studio (local) | http://localhost:1234/v1/chat/completions |
| OpenRouter | https://openrouter.ai/api/v1/chat/completions |
| DeepSeek | https://api.deepseek.com/v1/chat/completions |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions |
| SiliconFlow | https://api.siliconflow.cn/v1/chat/completions |
