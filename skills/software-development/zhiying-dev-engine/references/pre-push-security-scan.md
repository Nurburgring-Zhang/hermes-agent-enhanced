# 推送前安全扫描清单 (Pre-Push Security Scan)

> 来源: 2026-06-15实战 — 25个nvapi-密钥差点推送到公共GitHub仓库

## 强制协议

每次 `git push` 前必须执行以下扫描。未扫描禁止推送。

### Step 1: 真实密钥模式扫描
```bash
git ls-files | xargs grep -l "nvapi-[a-zA-Z0-9]\{20,}\|sk-[a-zA-Z0-9]\{20,}\|ghp_[a-zA-Z0-9]\{20,}\|AIzaSy" 2>/dev/null
```
期望输出: 空（无匹配）

### Step 2: 配置文件密钥检查
```bash
git ls-files | grep "config.yaml$" | while read f; do
  if grep -q "nvapi-\|sk-[a-zA-Z0-9]\{20,}\|ghp_\|api_key.*[a-zA-Z0-9]\{20,}" "$f" 2>/dev/null; then
    echo "KEY LEAK: $f"
    grep -n "nvapi-\|sk-[a-zA-Z0-9]\{20,}" "$f"
  fi
done
```
期望输出: 空（无泄漏）

### Step 3: 环境文件检查
```bash
git ls-files | grep -E "\.env$|\.pem$|id_rsa|id_ed25519|credentials\.json"
```
期望输出: 空（无敏感文件）

### Step 4: vault/密钥文件检查
```bash
git ls-files | grep -E "vault/|secrets/|keys/"
```
密码管理器可以跟踪，但加密密钥文件必须排除。

## 常见泄漏点

| 路径模式 | 可能包含 | 处理 |
|---------|---------|------|
| `profiles/*/config.yaml` | nvapi-/openai/anthropic API keys | .gitignore + git rm --cached |
| `plugins/*/config.yaml` | 插件API密钥 | .gitignore + git rm --cached |
| `.env` | 所有环境变量 | .gitignore（永久） |
| `config.yaml` | 主配置文件 | .gitignore（永久） |
| `vault/.encryption_key` | Fernet加密密钥 | .gitignore |
| `*.pem`, `id_rsa*` | SSH/TLS私钥 | .gitignore（永久） |

## 发现泄漏后的处理

```bash
# 1. 从git追踪中移除
git rm --cached <leaked_file>

# 2. 加入.gitignore
echo "<leaked_pattern>" >> .gitignore

# 3. 提交
git add .gitignore && git commit -m "security: remove leaked keys from tracking"

# 4. 如果已推送到远程：轮换所有泄漏的密钥
#    （git filter-branch或BFG可以清理历史，但远程缓存可能仍存在）

# 5. 重新扫描
git ls-files | xargs grep -l "nvapi-\|sk-[a-zA-Z0-9]\{20,}\|ghp_" | wc -l
# 必须输出 0
```

## .gitignore 最低要求

```gitignore
# 密钥文件 — 永不跟踪
.env
.env.*
!.env.template
!.env.example
config.yaml
!config.yaml.example
*.pem
*.key
id_rsa*
id_ed25519*
credentials.json
vault/.encryption_key
vault/secrets.enc
profiles/*/config.yaml
!profiles/*/config.yaml.example
```

## 教训

- 扫描所有 `config.yaml` 文件，不仅扫描主配置
- Agent超时≠失败——可能已完成部分工作，需要验证实际状态
- `config.yaml.example` 中所有 `api_key` 必须是 `""`（空字符串）
- 真实密钥仅存在于 `~/.hermes/config.yaml` 和 `~/.hermes/.env`（权限600）
