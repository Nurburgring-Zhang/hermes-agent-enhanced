# 多项目融合: 独立服务+nginx架构 (2026-06-16 实战)

## 场景
将IMDF、智影、nanobot-factory三个项目融合为统一平台。

## 错误方案 (已验证失败)
**FastAPI sub-app mount模式：**
```python
from api.canvas_web import app as imdf_app
app.mount("/imdf", imdf_app)
```
**失败原因：**
- nanobot-factory的server.py有10700行+GPU/Agent集群/Electron IPC/Cluster Scheduler等复杂生命周期
- IMDF导入时污染sys.path(把imdf/推到sys.path[0])
- IMDF的core模块被缓存到sys.modules，后续 `from core.xxx` 都解析到错误的目录
- server.py有自关闭机制(可能与Electron IPC断开相关)

## 正确方案
**独立服务 + 可选nginx统一入口：**

```
nginx (可选)
  ├── /          → nanobot-factory (8899)
  ├── /imdf/*    → IMDF (8765)
  └── /zhiying/* → 智影 (8765, 内嵌于IMDF)
```

**启动脚本：**
```batch
start "IMDF" cmd /c "python api\canvas_web.py --port 8765"
start "Nanobot" cmd /c "python server.py --port 8899"
```

## 子应用挂载sys.path污染—完整修复
```python
# 导入前保存IMDF路径
_imdf_root = str(Path(__file__).parent / "imdf")
sys.path.insert(0, _imdf_root)
from api.canvas_web import app as imdf_app

# 导入后三步清理:
# 1. 移除IMDF路径
if _imdf_root in sys.path: sys.path.remove(_imdf_root)
# 2. 清除IMDF的core模块缓存
if 'core' in sys.modules:
    _core_file = getattr(sys.modules['core'], '__file__', '')
    if 'imdf' in str(_core_file):
        del sys.modules['core']
        for k in list(sys.modules.keys()):
            if k.startswith('core.'): del sys.modules[k]
# 3. 重新插入backend路径
sys.path.insert(0, str(_backend_dir))
```

## 更简洁的正确方案
**不要在父服务中导入子服务**。让每个服务独立运行在自己的端口。
