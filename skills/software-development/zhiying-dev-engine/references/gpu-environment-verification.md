# GPU环境验证与PyTorch部署检查清单

## 快速验证命令
```bash
# torch + CUDA
python3 -c "import torch; print(f'torch {torch.__version__} CUDA={torch.cuda.is_available()} GPU={torch.cuda.get_device_name(0)} VRAM={torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')"

# diffusers + transformers
python3 -c "import diffusers, transformers; print(f'diffusers {diffusers.__version__} transformers {transformers.__version__}')"
```

## 典型输出（RTX 4090）
```
torch 2.12.0+cu130 CUDA=True GPU=NVIDIA GeForce RTX 4090 VRAM=48.0GB
diffusers 0.38.0 transformers 5.3.0
```

## 虚拟环境创建（Linux）
```bash
# 方法1: venv（需要python3-venv）
sudo apt-get install -y python3.12-venv
cd /project/root
python3 -m venv .venv
source .venv/bin/activate

# 方法2: 用户级pip（WSL/开发环境，无sudo时）
pip3 install --user --break-system-packages \
  torch torchvision \
  diffusers \
  sentence-transformers \
  transformers \
  opencv-python-headless \
  openai-whisper \
  fastapi uvicorn aiohttp pydantic
```

## WSL环境特殊处理

**问题**: `python3 -m venv .venv` 时报错 `ensurepip is not available`
**原因**: WSL默认不安装python3-venv
**方案1**: `sudo apt-get install -y python3.12-venv`（需要sudo密码）
**方案2**: 直接用 `pip3 install --user --break-system-packages` 安装到用户目录

**问题**: `pip install` 提示 `externally-managed-environment`
**原因**: PEP 668 —— 系统Python包管理器不允许pip安装
**方案**: `--break-system-packages` 标志（仅限开发环境，不要在生产服务器使用）

## 服务器启动验证
```bash
# 启动后端
cd backend && python3 server.py &

# 验证服务器就绪
sleep 5
curl -s http://127.0.0.1:8001/health

# 验证AIGC生成链路
curl -s -X POST http://127.0.0.1:8001/api/v2/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test cat","model":"omni_gen_local","width":512,"height":512,"steps":20}'

# 预期: status=queued, task_id=xxx  （实际模型推理在后台异步执行）
```

## 常见问题
- 端口被占用: `fuser -k 8001/tcp` 或 `pkill -f "python3 server.py"`
- 多个进程残留: `ps aux | grep python | grep -v grep | awk '{print $2}' | xargs kill -9`
- CUDA内存不足: `torch.cuda.empty_cache()` 或重启进程
