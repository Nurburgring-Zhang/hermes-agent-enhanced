# FastAPI子应用挂载 — sys.path/sys.modules污染修复

## 问题

将IMDF作为子应用挂载到nanobot-factory FastAPI时：
```python
sys.path.insert(0, str(Path(__file__).parent / "imdf"))
from api.canvas_web import app as imdf_app
app.mount("/imdf", imdf_app)
```

此后所有 `from core.dataset_version import ...` 都报 `ModuleNotFoundError`，
尽管 `backend/core/dataset_version.py` 确实存在。

## 根因链

1. IMDF的 `canvas_web.py` 在导入时执行 `sys.path.insert(0, str(_PROJECT_ROOT))`，
   把 `/backend/imdf/` 推到 `sys.path[0]` 位置
2. IMDF的 `import core.canvas_core` 导致 `core` 包被缓存到 `sys.modules['core']`
   （路径指向 `/backend/imdf/core/__init__.py`）
3. 后续 `from core.dataset_version import get_version_manager` 
   使用缓存的 `sys.modules['core']`（IMDF版本），其中没有 `dataset_version`

## 修复

```python
# 导入后清理sys.path污染 + 清除缓存的核心模块
if _imdf_root in sys.path:
    sys.path.remove(_imdf_root)
_bd = str(_backend_dir)
if _bd in sys.path:
    sys.path.remove(_bd)
sys.path.insert(0, _bd)

# 清理IMDF的core模块缓存
if 'core' in sys.modules:
    _core_file = getattr(sys.modules['core'], '__file__', '')
    if 'imdf' in str(_core_file):
        del sys.modules['core']
        _to_del = [k for k in sys.modules if k.startswith('core.')]
        for k in _to_del:
            del sys.modules[k]
```

## 验证

```python
import sys
from pathlib import Path
_backend_dir = Path('/mnt/d/Hermes/生产平台/nanobot-factory/backend')
_imdf_root = str(_backend_dir / "imdf")

sys.path.insert(0, str(_backend_dir))
sys.path.insert(0, _imdf_root)
from api.canvas_web import app as imdf_app  # IMDF sub-app

# 清理
sys.path.remove(_imdf_root)
_bd = str(_backend_dir)
if _bd in sys.path: sys.path.remove(_bd)
sys.path.insert(0, _bd)
del sys.modules['core']
for k in list(sys.modules.keys()):
    if k.startswith('core.'): del sys.modules[k]

# 现在应该成功
from core.dataset_version import get_version_manager  # ✅
