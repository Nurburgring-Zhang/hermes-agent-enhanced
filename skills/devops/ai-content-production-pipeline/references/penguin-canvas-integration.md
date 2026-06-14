# T8-penguin-canvas v2.1.4 集成笔记

下载位置: /mnt/d/Hermes/imdf_vendor/penguin-canvas/
源仓库: https://github.com/T8mars/T8-penguin-canvas
技术栈: React 19 + TypeScript + Vite + Electron + Three.js + @xyflow/react

## 16个功能点的IMDF复刻位置

| 功能 | 源文件位置 | IMDF复刻 | 备注 |
|------|-----------|---------|------|
| 3D全景/导演台 | src/components/nodes/Panorama3DNode.tsx(6062行) | engines/data/data_3d.py | Three.js全景+MediaPipe姿势 |
| 姿势库/动作 | src/components/nodes/PoseMasterNode.tsx(3894行) | engines/data/data_3d.py | 20+预设姿势,18关节系统 |
| Figma联动 | tools/figma-bridge/ + backend/src/routes/figma.js | api/canvas_web.py → /api/figma/* | HTTP轮询队列模式 |
| 云存储COS/OSS | backend/src/cloudUploads/uploader.js(792行) | api/cloud_storage.py | 纯crypto签名,无SDK |
| 提示词模板 | src/components/PromptTemplateLibraryModal.tsx | api/canvas_web.py | 8图像+8视频分类 |
| ComfyUI remote | src/components/nodes/ComfyUIStoreNode.tsx | api/canvas_web.py | 支持remote+docker |
| 即梦CLI | backend/src/providers/jimengCli.js(784行) | api/canvas_web.py | 模型映射+WSL检测 |
| 上传20M | Electron原生配置 | api/canvas_web.py | max_size参数 |

## 复刻原则
- 不直接Copy源项目代码(许可证不同)
- 理解接口和逻辑后用Python重新实现
- 前端交互通过FastAPI REST + WebSocket模拟
- 业务逻辑(签名/编码/模板)完整复刻

## 关键发现
- Penguin Canvas的3D全景模块是最大的(13K行前端)
- 云存储签名完全用原生crypto实现(不依赖SDK)
- 即梦CLI跨Windows/WSL有完善的检测逻辑
- 提示词模板有丰富的分类质量提示体系