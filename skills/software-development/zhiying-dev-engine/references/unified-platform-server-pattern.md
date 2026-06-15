# 统一平台server_unified.py架构模式 (2026-06-17实战)

## 问题
nanobot-factory的server.py（10,700行）有复杂lifespan（GPU监控/Agent集群/Electron IPC），独立运行时自关闭。尝试在server.py中挂载IMDF作为子app失败——sys.path污染+sys.modules缓存导致后续import全部指向错误目录。

## 正确架构：server_unified.py

不修改server.py。创建轻量级统一入口：

```python
# server_unified.py — 统一数据生产平台主入口
# 位置: D:\Hermes\生产平台\nanobot-factory\server_unified.py

IMDF_DIR = os.path.join(BASE_DIR, 'backend', 'imdf')
sys.path.insert(0, IMDF_DIR)

from api.canvas_web import app as imdf_app
app.mount("/", imdf_app)  # IMDF+智影作为主应用(352路由)

# nanobot-factory保持独立服务(server_nanobot.py:8898)
```

## 架构图
```
server_unified.py (8899)      server_nanobot.py (8898)
├── / → IMDF+智影(352路由)    ├── /aigc → 图片/视频生成
├── /nb → Vue前端(需build)    ├── /comfyui → ComfyUI工作流
└── /api/* → 全功能API        ├── /digital-human → 数字人
                              └── /batch → 批量生产
```

## 关键教训
1. **不要修改server.py** — 10,700行的lifespan太复杂，任何修改都可能触发自关闭
2. **不要挂载子app到server.py** — sys.path/sys.modules污染无法完全清理
3. **独立服务+共享数据目录** — 两个服务共享 `data/` 目录，通过文件系统通信
4. **IMDF作为主应用** — IMDF+智影功能更完整（352路由 vs nanobot的~50路由），适合作为根应用

## 同步协议
当IMDF有新功能时，从 `/mnt/d/Hermes/infinite-multimodal-data-foundry/` 同步到统一平台：
```bash
SRC=/mnt/d/Hermes/infinite-multimodal-data-foundry
DST=/mnt/d/Hermes/生产平台/nanobot-factory/backend/imdf
# 同步新增引擎
cp $SRC/engines/new_engine.py $DST/engines/
# 同步canvas_web.py(含所有路由注册)
cp $SRC/api/canvas_web.py $DST/api/canvas_web.py
# 同步前端
cp $SRC/frontend/index.html $DST/../frontend/imdf/index.html
cp $SRC/frontend/js/app.js $DST/../frontend/imdf/js/app.js
```
