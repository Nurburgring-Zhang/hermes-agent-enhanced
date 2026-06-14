# WSL 网络检索故障排查与修复（2026-06-09）

## 问题现象
Python urllib / curl 在国内 WSL 环境下对 DuckDuckGo 超时，但 Google/Baidu 可通。
DNS 可解析但 HTTPS 连接超时 — 非 DNS 问题，是墙 + WSL NAT 的复合问题。

## 修复方案

### 方案1：Bing 替代 DuckDuckGo（推荐）
DuckDuckGo 在国内被墙，直接改用 Bing：
```bash
curl -sL --connect-timeout 8 -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.bing.com/search?q=<关键词>"
```

### 方案2：搜狗搜索（国内可用备选）
```bash
curl -sL --connect-timeout 8 "https://www.sogou.com/web?query=<关键词>"
```

### 方案3：百度搜索（结果质量较低）
```bash
curl -sL --connect-timeout 8 "https://www.baidu.com/s?wd=<关键词>"
```

### 方案4：Python urllib 强制 IPv4
```python
import socket
old = socket.getaddrinfo
def force_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return old(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = force_ipv4
```

## Python urllib vs curl 行为差异
- WSL 中 curl 可用但 Python urllib 可能不可用（Python IPv6优先导致超时不回退）
- 执行 web_search 时 if urllib 失败自动 fallback 到 curl subprocess
- 用 `execute_code` 中的 `hermes_tools.terminal` 调用 curl 做 web 搜索更可靠

## Bing 搜索结果解析（Python）
```python
import re, subprocess
url = f"https://www.bing.com/search?q={query}"
resp = subprocess.run(['curl', '-sL', url, '-H', 'User-Agent: Mozilla/5.0'], capture_output=True, text=True, timeout=10)
results = re.findall(r'<h2[^>]*>.*?<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', resp.stdout, re.DOTALL)
```
