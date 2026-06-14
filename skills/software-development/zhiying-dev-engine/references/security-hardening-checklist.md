# 大规模代码库安全加固 — 实战检查清单与时序

> 来源: 2026-06-15 Hermes Agent Enhanced security hardening

## 安全加固标准流程

### Phase 1: 扫描
1. `bandit -r scripts/ -f json -o /tmp/bandit.json` 全量安全扫描
2. `grep -rn "shell=True" scripts/*.py | grep -v test_ | grep -v '# nosec'` 命令注入检测
3. `grep -rn "except:" scripts/*.py | grep -v "Exception\|ValueError\|..."` bare except检测
4. `grep -rn "sk-\|ghp_\|AIzaSy\|nvapi-" scripts/ | grep -v test_` 密钥泄露检测

### Phase 2: 优先级分类
- 排除 vendor/third_party 目录（RedCrack, TikTokDownloader, MediaCrawler等）
- 核心模块 HIGH → P0 立即修复
- 核心模块 MEDIUM → P1 本周修复
- LOW/第三方 → P2 记录不退修

### Phase 3: 批量修复
- MD5 → SHA256: `hashlib.md5(data.encode()).hexdigest()` → `hashlib.sha256(data.encode()).hexdigest()`
- bare except → `except Exception as e: logger.warning(f"Unexpected error in {__file__}: {e}")`
- shell=True → `subprocess.run(cmd.split(), ...)` + `cwd=` 参数

### Phase 4: 验证
- `bandit -r scripts/ --severity high | grep -c "Issue:"` 确认核心=0
- `grep -rn "except:" scripts/*.py | grep -v "Exception\|ValueError\|..." | wc -l` 确认=0
- `python3 -c "import scripts.<module>"` 逐模块验证语法

## 常见修复陷阱

### write_file 全文覆盖陷阱
write_file 是全文替换，对已存在的大文件只做小修改时必须用 patch。
否则23行写回945行文件=922行丢失。恢复: `git checkout -- <file>`

### logging import 缺失
print→logging 替换时，添加了 `logger.warning()` 但忘记确认 `logger` 已定义。
修复：用 patch 在 `import logging` 后追加 `logger = logging.getLogger(__name__)`

### cd in subprocess
`subprocess.run("cd scripts && ...".split())` 失败因为cd是shell内建命令。
修复：用 `cwd=str(HERMES/"scripts")` 替代。
