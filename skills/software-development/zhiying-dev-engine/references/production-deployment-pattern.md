# Production Deployment with uvicorn Workers

模式来源：nanobot-factory 项目 2026-06-16 生产部署实战

## 标准部署命令

```bash
cd backend
uvicorn production_app:app --host 0.0.0.0 --port 8001 --workers 4 \
    --log-level info \
    --limit-concurrency 200 \
    --limit-max-requests 10000 \
    --timeout-keep-alive 30
```

## production_app.py 模板

```python
"""生产级ASGI入口"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import app  # 导入主app实例
```

## 关键注意事项

### 1. 内存状态不共享
uvicorn workers 是独立进程。`class._workers: Dict = {}` 这种类级内存存储：
- Worker A 添加的数据对 Worker B 不可见
- 必须用 SQLite/PostgreSQL/Redis 做共享状态

### 2. 端口清理
多进程下旧进程更难杀干净：
```bash
# 保险做法
fuser -k 8001/tcp
sleep 3
fuser 8001/tcp 2>/dev/null || echo "free"
# 再启动
```

### 3. 启动验证
```bash
# 检查进程
ps aux | grep uvicorn | grep -v grep
# 检查端口
ss -tlnp | grep 8001
# 检查API
curl http://127.0.0.1:8001/health
```

### 4. .env 生产配置
```bash
ALLOWED_ORIGINS=http://your-frontend-domain.com
DATABASE_PATH=/app/data/nanobot.db
LOG_LEVEL=INFO
DEV_MODE=false
```

## deploy.sh 完整模板

```bash
#!/bin/bash
HOST=${NANOBOT_HOST:-"0.0.0.0"}
PORT=${NANOBOT_PORT:-8001}
WORKERS=${NANOBOT_WORKERS:-4}
APP_MODULE="production_app:app"

cd "$(dirname "$0")/backend"

uvicorn "$APP_MODULE" \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info \
    --limit-concurrency 200 \
    --limit-max-requests 10000 \
    --timeout-keep-alive 30
```
