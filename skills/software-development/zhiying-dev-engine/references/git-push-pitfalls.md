# Git Push 故障模式与SSH认证（WSL环境）

## 故障模式：WSL→GitHub连接失败

### 症状
```bash
$ git push -u origin main
fatal: unable to access 'https://github.com/...': Failed to connect to github.com port 443
```

WSL的HTTPS出站可能被企业网络/代理限制。

### 解决方案：SSH key认证

**第一步：生成SSH key**
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
```

**第二步：启动ssh-agent并添加key**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

**第三步：让用户添加到GitHub**
1. 打开 https://github.com/settings/ssh/new
2. Title: `hermes-enhanced-ci`
3. Key type: `Authentication Key`
4. Key: `cat ~/.ssh/id_ed25519.pub` 的输出
5. Add SSH key

**第四步：验证**
```bash
ssh -T git@github.com
# 期望输出: Hi username! You've successfully authenticated...
```

**第五步：切换remote并推送**
```bash
git remote set-url origin git@github.com:username/repo.git
git push -u origin main
```

### 注意
- `gh` CLI（GitHub CLI）需要在WSL中单独安装，不能依赖Windows的gh
- 使用 `https://` URL + token 在WSL中可能触发交互式密码提示导致超时
- Git credential store 在WSL中可能为空，Windows的credential不共享到WSL

## 密钥扫描清单（推送前必做）

推送代码到公开仓库前，必须执行以下检查：

```bash
# 1. 扫描 nvapi- (NVIDIA API key)
git grep -n "nvapi-" -- . | grep -v "check_script" || echo "OK"

# 2. 扫描 sk- 模式
git grep -n "sk-[A-Za-z0-9]\{20,\}" -- . | grep -v "check_script" || echo "OK"

# 3. 扫描 PUSHPLUS_TOKEN 硬编码备选值
grep -rn "PUSHPLUS_TOKEN" --include="*.py" . | grep -v "#" | grep -v 'os.environ' | grep -v 'getenv' || echo "OK"

# 4. 检查 .gitignore 是否覆盖了 config.yaml / .env / auth.json
grep -E "^config\.yaml$|^\.env$|^auth\.json$" .gitignore

# 5. 确认 git ls-files 中没有密钥文件
git ls-files config.yaml .env auth.json 2>/dev/null || echo "密钥文件未被git跟踪"
```

### 历史教训
2026-06-14: 3个文件中`os.environ.get("PUSHPLUS_TOKEN", "硬编码token")`的备选值硬编码了PushPlus token。
修复：将所有`"a8f1526d8ec84ef59aa37fe72fa1ab7f"`替换为`""`，耗时2分钟。
检测方法：`git grep -n "a8f1526d"` 直接定位。

## 本地CI（GitHub Actions不可用时的替代方案）

当无法推送触发GitHub Actions时，使用 `auto_ci.py` 作为本地替代：

```bash
# 单次运行
python3 /home/administrator/.hermes/scripts/auto_ci.py

# 循环模式（每30分钟自动跑）
python3 /home/administrator/.hermes/scripts/auto_ci.py --loop 30 --max-loops 10

# 注册为cron
cronjob action=create \
  schedule="30m" \
  name="Auto CI" \
  script="scripts/auto_ci.py" \
  workdir="/home/administrator/.hermes" \
  no_agent=true
```

auto_ci.py执行链：`lint → test(686个) → coverage(70%门禁) → security(bandit)`
完整CI链耗时约77秒，结果写入 `logs/auto_ci/ci_results.jsonl`。
