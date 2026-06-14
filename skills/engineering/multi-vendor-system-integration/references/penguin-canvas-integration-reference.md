# Penguin Canvas v2.1.4 完整集成参考

## 项目规模
- 源: 421文件, 155K行代码, 187MB (React19 + TS + Electron + Three.js)
- 目标: 36 Python模块, 90 API路由, 679文件, 82MB (Python 3 + FastAPI)

## 技术栈转换
| 源 | 目标 |
|----|------|
| React 19 + TSX | Python FastAPI REST + WebSocket |
| @xyflow/react 画布 | InfiniteCanvas (纯Python) |
| Three.js 3D | Scene3DManager + REST API |
| Zustand 状态 | dataclass + JSON持久化 |
| Express 后端 | FastAPI + uvicorn |
| CSS变量主题(11套) | 拷贝改名到 frontend/src/styles/ |
| 97个React节点组件 | 拷贝改名到 frontend/src/nodes/ |

## 16个功能点迁移状态
15/16 已复刻, 1个Electron独享架构预留。

## 参考IMDF路径
- 3D引擎: engines/data/data_3d.py (30KB)
- 云存储: api/cloud_storage.py (18KB)
- 文件上传: api/media_manager.py
- 资源库: api/resource_library.py
- 系统设置: api/system_config.py
- 图片处理: api/image_processor.py
- Figma联动: api/figma_bridge.py
- 主题管理: api/theme_manager.py
- Provider注册: engines/provider_registry.py
- Web UI: api/canvas_web.py (90路由)
