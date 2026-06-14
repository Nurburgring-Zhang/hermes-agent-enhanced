# ComfyUI完整集成模式（2026-06-15实战）

## 核心理念
"集成ComfyUI" = 将ComfyUI完整代码克隆到项目目录下作为子模块，**不是**Docker容器，**不是**远程API调用

## 目录结构
```
nanobot-factory/
├── backend/           # FastAPI后端
├── web/               # Vue3前端
├── comfyui/           # ← ComfyUI完整克隆
│   ├── main.py
│   ├── execution.py
│   ├── nodes.py
│   └── ... (673个文件)
└── start.sh           # 同时启动两套系统
```

## 集成步骤
1. `git clone https://github.com/comfyanonymous/ComfyUI.git comfyui`
2. ComfyUI Provider已存在 `backend/production_workbench.py` 中（ComfyUIProvider类）
3. 配置 `.env` 添加 `COMFYUI_URL=http://127.0.0.1:8188`
4. 启动：`cd comfyui && python main.py --listen 0.0.0.0 --port 8188`

## Provider代码验证
ComfyUIProvider.generate() 使用 aiohttp.ClientSession 真实POST到:
- `{base_url}/prompt` — 队列生成任务
- `{base_url}/history/{request_id}` — 查询结果
- `{base_url}/interrupt` — 中断生成

## 系统统一启动（start.sh）
```bash
cd comfyui && python main.py --listen 0.0.0.0 --port 8188 &
sleep 10
cd backend && python server.py
```

## 注意
- 首次启动ComfyUI会编译CUDA kernel，约1-2分钟
- 模型目录：`comfyui/models/checkpoints/`
- Nanobot的ComfyUIProvider自动发现本地ComfyUI
