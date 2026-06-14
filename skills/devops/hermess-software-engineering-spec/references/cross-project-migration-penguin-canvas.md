# 跨项目功能复刻实战记录: Penguin Canvas v2.1.4

## 项目总览
| 指标 | 源项目 | 目标(IMDF) |
|------|--------|-----------|
| 文件数 | 421 | 29 |
| 代码行 | ~155,000 | 7,940 |
| 技术栈 | React 19 + TS + Electron | Python 3 + FastAPI |
| 画布引擎 | @xyflow/react | InfiniteCanvas(纯Python) |
| 3D引擎 | Three.js | Scene3DManager + REST API |
| 测试 | 无 | 41/41 ✅ |
| 开发周期 | 约6个月 | 1次对话session |

## 前端组件等价映射(97个节点→6大引擎)
React节点(97种) → Python引擎(7种):
- Panorama3DNode, PoseMasterNode → Data3DEngine
- VideoNode, SeedanceNode → VideoEngine
- LLMNode → MasterAgent
- ImageNode, ImageEditModal → PPTEngine / DataEditEngine
- OutputNode → OutputManager
- ComfyUIStoreNode → NanobotAdapter

## 关键技术栈的Python等效实现
| 源技术 | 目标实现 | 关键代码 |
|--------|---------|---------|
| @xyflow/react | InfiniteCanvas | core/canvas_core.py |
| Zustand store | dataclass+JSON | 各引擎 __init__ |
| Three.js Scene | Scene3DManager | engines/data/data_3d.py |
| COS SDK | hmac_sha1+requests | api/cloud_storage.py |
| OSS SDK | hmac_sha1+xml解析 | api/cloud_storage.py |
| Figma轮询 | HTTP队列 | canvas_web.py figma路由 |
| 即梦CLI解析 | 正则+版本映射 | canvas_web.py 即梦路由 |

## 不迁移的部分及原因
| 功能 | 原因 |
|------|------|
| 11套CSS动画主题 | 纯前端展示层,Python后端无法等价 |
| Electron拖出文件夹 | 需要原生客户端支持 |
| 成就系统 | 与生产核心功能无关 |
| E2E测试 | 需要完整前端环境 |
