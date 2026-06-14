# Penguin Canvas v2.1.4 → IMDF 迁移方法论

## 源项目信息
- 仓库: T8mars/T8-penguin-canvas
- 版本: v2.1.4 (2026-06)
- 规模: 421文件, 155K行
- 技术栈: React 19 + TypeScript + Vite + Electron + @xyflow/react + Three.js + Zustand
- 后端: Node.js Express, 41路由文件, 15个Provider

## 迁移策略

### 技术栈转换
```
React组件 (97节点)  → 纯Python FastAPI + WebSocket
前端Three.js 3D     → Python Scene3DManager + REST API
Zustand状态管理     → Python dataclass + JSON持久化
Node.js Express     → Python FastAPI
CSS变量主题(11套)    → Python模板系统
```

### 功能点识别方法
1. 读 features.json (4834行) 获取完整功能清单
2. 对照README/release-notes的16个v2.1.4功能点
3. 在src/中定位每个功能点的组件文件:
   - 3D全景 → Panorama3DNode.tsx(6062行) + PoseMasterNode.tsx(3894行) + panorama3d.ts(3217行)
   - 云存储 → backend/src/cloudUploads/uploader.js(792行)
   - 提示词模板 → promptTemplateLibrary.ts(1252行)
   - 即梦CLI → providers/jimengCli.js(784行)
4. 分析后端API路由确定接口签名

### 后端接口提取模板
```python
# 源项目  backend/src/routes/figma.js (179行)
# POST /import → 队列写入
# GET  /claim  → 队列消费
# →
# canvas_web.py:
# @app.post("/api/figma/import")
# @app.get("/api/figma/claim")

# 源项目 backend/src/cloudUploads/uploader.js (792行)
# 腾讯云COS V5签名 + 阿里云OSS Auth签名
# 纯crypto实现,无SDK依赖
# →
# api/cloud_storage.py: sign_cos_request() + sign_oss_authorization()
```

### 关键发现
- 云存储签名完全可以用原生crypto实现,不需要SDK
- 即梦CLI跨Windows/WSL检测逻辑可以直接复用
- 提示词模板库1252行,核心是JSON数据结构而非UI
- Figma桥接用HTTP轮询模式,简单可靠
- 16功能中15个可纯后端复刻,仅"拖出文件夹"需要Electron
