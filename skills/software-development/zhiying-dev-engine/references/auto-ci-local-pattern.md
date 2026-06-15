# auto_ci.py 动态测试发现模式 (2026-06-15)

## 演进历史

v1: 硬编码40个测试文件名 — 每次新增测试都要手动更新auto_ci
v2: 用通配符 `"python3 -m pytest test_*.py"` — glob在subprocess中不展开 
v3: 用Python `glob()` 动态发现 + list-based subprocess — 当前方案

## 当前实现

```python
from glob import glob

def _get_test_files():
    files = sorted(glob(str(SCRIPTS / "test_*.py")))
    return [Path(f).name for f in files if "playwright" not in Path(f).name]

# 排除慢测试
test_files = [f for f in _get_test_files() if f not in (
    "test_hy_memory.py", "test_context.py", "test_gear_system.py",
    "test_unified_collector.py", "test_scoring.py", "test_push.py",
    "test_gongbu_impl.py", "test_cleaning_pipeline.py",
)]
test_cmd = ["python3", "-m", "pytest"] + test_files + ["-q", "--tb=short", "-x"]
```

## 关键点
- `run_step()` 接受list（不split）或string（用split()）
- 永远不要用 `shell=True` —— 用cwd + list传参
- `_get_test_files()` 过滤掉 playwright 测试（需要浏览器）
- 慢测试单独排除，保持CI在120秒以内
