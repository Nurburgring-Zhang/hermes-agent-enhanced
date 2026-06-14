# 路径标准化大规模替换模式
## 基于2026-06-13 Phase-5实战（352文件自动修改）

## 问题
Hermes增强版有25+个脚本硬编码 `/home/administrator` 路径，使用 `Path("/home/administrator/.hermes")` 而非 `Path.home() / ".hermes"`。手动逐个修改不现实。

## 方案：Python自动替换脚本

```python
# replace_paths.py — 一次性替换整个代码库
import re, os
from pathlib import Path

ROOT = Path("/home/administrator/.hermes")
PATTERNS = [
    # 1. Path("/home/administrator/.hermes/xxx/yyy") → Path.home() / ".hermes" / "xxx" / "yyy"
    (r'Path\("/home/administrator/\.hermes/([^"]*)"\)',
     lambda m: f'Path.home() / ".hermes" / "'
              + m.group(1).replace("/", '" / "')
              + '"'),
    # 2. /home/administrator/.hermes 裸字符串
    (r'"/home/administrator/\.hermes"', 'str(Path.home() / ".hermes")'),
    # 3. /home/administrator 其他路径
    (r'Path\("/home/administrator/([^"]+)"\)',
     lambda m: f'Path.home() / "{m.group(1)}"'),
]

for py_file in ROOT.rglob("*.py"):
    if ".pyc" in str(py_file) or "venv" in str(py_file) or "backup" in str(py_file):
        continue
    try:
        content = py_file.read_text(encoding="utf-8")
        original = content
        for pattern, replacement in PATTERNS:
            content = re.sub(pattern, replacement, content)
        if content != original:
            py_file.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"Error {py_file}: {e}")
```

## 关键要点

1. **备份在前** — 先 `tar -cf backup.tar scripts/ agents_company/` 再替换
2. **正则要小心** — 嵌套引号和f-string中的变量引用可能会撞到
3. **Shebang行也要改** — `#!/home/administrator/...` → `#!/usr/bin/env python3`
4. **shell脚本单独处理** — `.sh` 文件用 `$HOME/.hermes` 而非 Python Path.home()
5. **验证语法** — 修改后必须随机抽样验证 `python3 -m py_compile`  
6. **验证无残留** — `grep -rn '"/home/administrator' scripts/ | grep -v backup | grep -v .pyc` 应为0

## 本项目的具体操作
- 自动脚本修改了352个.py文件
- 手动修复了36个.sh脚本和边缘情况
- 备份在 `/tmp/hermes_backup/scripts_backup.tar`（468MB）
