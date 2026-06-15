# pyproject.toml 部署故障修复模式
# 2026-06-15 实战

## 故障1: License Classifier 被 setuptools>=77 拒绝

**错误信息**:
```
setuptools.errors.InvalidConfigError: License classifiers have been superseded 
by license expressions (see PEP 639). Please remove:
License :: OSI Approved :: MIT License
```

**修复**: 从 `classifiers` 列表中移除 `"License :: OSI Approved :: MIT License"`，只保留 `license = "MIT"` 和 `license-files = ["LICENSE"]`。

## 故障2: cd scripts && 在 subprocess.run(cmd.split()) 中不工作

**根因**: `cmd.split()` 不展开shell内建命令。`cd` 是shell内建，不是可执行文件。

**修复**: 用 `cwd=str(HERMES / "scripts")` 替代 `cd scripts &&`。

## 故障3: glob通配符在 subprocess 中不展开

**根因**: `cmd.split()` 不展开shell glob。`test_*.py` 保持字面量，pytest找不到。

**修复**: 在Python中用 `glob()` 动态列出文件，然后传list给 subprocess:
```python
from glob import glob
test_files = [Path(f).name for f in glob(str(SCRIPTS / "test_*.py"))]
test_cmd = ["python3", "-m", "pytest"] + test_files
```

## 故障4: pip install PEP 668 外部管理环境

WSL Ubuntu 24.04 的 Python 受 PEP 668 保护。需要 `--break-system-packages` 标志:
```bash
pip install --break-system-packages -e .
```

## 故障5: setuptools.build_meta vs _legacy:_Backend

旧版 pyproject.toml 用了不存在的 `setuptools.backends._legacy:_Backend`。
修复为 `setuptools.build_meta`。
