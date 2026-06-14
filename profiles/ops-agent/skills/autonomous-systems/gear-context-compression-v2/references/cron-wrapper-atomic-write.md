# Cron Wrapper + 原子写入 + 文件锁参考

## Cron Wrapper 架构

```
cron (crontab) 
  → cron_wrapper.py context_packer.py  # 获取flock锁
    → context_packer.py                 # 执行真实脚本
    → 写日志到 cron_wrapper.log         # 记录rc/耗时/错误
  → 释放锁
```

所有被 `cron_wrapper.py` 包装的cron条目：

```cron
* * * * * cd /home/administrator/.hermes && python3 scripts/cron_wrapper.py context_packer.py >> logs/context_packer.log 2>&1
* * * * * cd /home/administrator/.hermes && python3 scripts/cron_wrapper.py surgical_context_slicer.py >> logs/surgical_slicer.log 2>&1
* * * * * cd /home/administrator/.hermes && python3 scripts/cron_wrapper.py context_auto_assoc.py >> logs/auto_assoc.log 2>&1
* * * * * cd /home/administrator/.hermes && python3 scripts/cron_wrapper.py cross_session_cache.py >> logs/cross_cache.log 2>&1
```

## 文件锁实现

```python
# cron_wrapper.py 核心逻辑
import fcntl, sys
from pathlib import Path

LOCK_DIR = Path("/tmp/hermes_locks")
LOCK_DIR.mkdir(parents=True, exist_ok=True)
lock_path = LOCK_DIR / f"{script_name}.lock"

lock_fd = open(lock_path, "w")
try:
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print(f"[cron_wrapper] 已有实例在运行，跳过")
    sys.exit(0)
# ... 执行脚本 ...
finally:
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
    lock_fd.close()
```

## 原子写入实现

```python
# hermes_common.py
def atomic_write(path, data, mode="json"):
    import hashlib
    path.parent.mkdir(parents=True, exist_ok=True)
    
    content = json.dumps(data, ensure_ascii=False, indent=2) if mode == "json" else data
    
    tmp = path.with_suffix(".tmp." + hashlib.md5(str(path).encode()).hexdigest()[:8])
    try:
        if mode == "bytes":
            tmp.write_bytes(content)
        else:
            tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)  # POSIX保证同文件系统rename原子性
    except Exception:
        try: tmp.unlink()
        except: pass
        raise
```

## 已知坑

1. **cron_wrapper.py 必须用硬编码路径** — `Path.home()` 在cron环境可能返回 `/` 而不是 `/home/administrator`。使用 `HERMES = Path("/home/administrator/.hermes")`。

2. **flock在NFS上不可靠** — 当前系统WSL本地ext4，无此问题。如果迁移到共享文件系统，需改用 `lockf` 或 `sqlite` 互斥。

3. **原子写入不防止TOCTOU** — `tmp.replace(path)` 是原子的，但两个进程同时写不同tmp文件然后先后replace，后写的会覆盖先写的。这种情况在cron_wrapper的flock保护下不会发生。

4. **lock目录清理** — `/tmp/hermes_locks/` 在系统重启后自动清空。不需要手动清理。
