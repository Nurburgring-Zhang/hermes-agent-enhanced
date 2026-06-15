# 推送前安全扫描 — 完整协议

> 来源: 2026-06-15 实战 — 25个nvapi-密钥差点泄漏到公共仓库
> 更新: 2026-06-15 — profiles/plugins config.yaml 暴露

## 强制协议（每次push前必须执行）

```bash
# === STEP 1: 扫描所有git跟踪文件中的真实密钥 ===
git ls-files | xargs grep -l "nvapi-[a-zA-Z0-9]\{20,\}\|sk-[a-zA-Z0-9]\{20,\}\|ghp_[a-zA-Z0-9]\{20,\}\|AIzaSy" 2>/dev/null

# === STEP 2: 扫描所有config.yaml文件（含子目录） ===
git ls-files | grep "config.yaml$" | while read f; do
  if grep -q "nvapi-\|sk-[a-zA-Z0-9]\{20,\}\|ghp_\|AIzaSy" "$f" 2>/dev/null; then
    echo "🔴 KEY LEAK: $f"
    grep -n "nvapi-\|sk-\|ghp_\|AIzaSy" "$f"
  fi
done

# === STEP 3: 扫描.env文件 ===
git ls-files | grep "\.env$" | while read f; do
  echo "🔴 ENV FILE IN GIT: $f (should be in .gitignore)"
done

# === STEP 4: 如果发现密钥，立即处置 ===
# 4a. 移除git追踪
git rm --cached <file>
# 4b. 添加到.gitignore
echo "path/to/*/config.yaml" >> .gitignore
echo "**/.env" >> .gitignore
# 4c. 提交
git add .gitignore && git commit -m "security: remove leaked keys before push"

# === STEP 5: 最终确认 ===
LEAKS=$(git ls-files | xargs grep -l "nvapi-\|sk-[a-zA-Z0-9]\{20,\}\|ghp_[a-zA-Z0-9]\{20,\}\|AIzaSy" 2>/dev/null | wc -l)
echo "Leaks remaining: $LEAKS (must be 0)"
```

## 常见密钥位置（按风险排序）

| 位置 | 风险 | .gitignore状态 |
|------|------|---------------|
| `config.yaml` (根) | 🔴 极高 | 必须在.gitignore |
| `.env` (根) | 🔴 极高 | 必须在.gitignore |
| `profiles/*/config.yaml` | 🔴 高 | 必须在.gitignore |
| `plugins/*/config.yaml` | 🔴 高 | 必须在.gitignore |
| `profiles/*/.env` | 🔴 高 | 必须在.gitignore |
| `config.yaml.example` | 🟡 中 | 可跟踪(值必须为"") |
| SKILL.md参考中的密钥 | 🟢 低 | 示例密钥(明确标注) |

## .gitignore 必须覆盖的模式

```gitignore
# 敏感配置
config.yaml
/config.yaml.bak*
.env
.env.*
!config.yaml.example
!*.env.example

# 子目录配置 (易遗漏!)
profiles/*/config.yaml
profiles/*/.env
plugins/*/config.yaml

# 密钥和凭证
auth.json
keys/
vault/
*.pem
*.key
!*.example.key
```

## 事后验证

```bash
# 推送后验证: clone到临时目录检查
cd /tmp && git clone <repo> test-clone
cd test-clone
git ls-files | xargs grep -l "nvapi-\|sk-[a-zA-Z0-9]\{20,\}" | wc -l
# 必须输出 0
rm -rf /tmp/test-clone
```
