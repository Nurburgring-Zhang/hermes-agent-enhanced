# 统一平台同步+深度打磨模式 (2026-06-15实战)

## 背景

IMDF独立项目在 `/mnt/d/Hermes/infinite-multimodal-data-foundry/` 完成了全部Batch1-4开发和深度打磨后，用户指出**目标错误**——应该打磨的是统一平台 `D:\Hermes\生产平台\nanobot-factory\`（集成了IMDF+智影的完整nanobot-factory）。

## 统一平台审计差异

审计发现统一平台的IMDF子系统有75个旧文件，缺了全部新增：
- 17个新引擎文件
- 11个新API路由
- 1个middleware包
- 1个config/settings.py
- 8个脚本
- 5个前端JS页面
- 更新的canvas_web.py（含所有路由注册）
- 更新的index.html + app.js

## 批量同步协议

```bash
SRC=/mnt/d/Hermes/infinite-multimodal-data-foundry
DST=/mnt/d/Hermes/生产平台/nanobot-factory/backend/imdf

# 1. 引擎+API批量复制（29个文件）
for f in engines/*.py api/*.py api/middleware/*.py config/*.py; do
  mkdir -p "$(dirname "$DST/$f")"
  cp "$SRC/$f" "$DST/$f"
done

# 2. 脚本同步
DST_SCRIPTS=/mnt/d/Hermes/生产平台/nanobot-factory/scripts
for f in scripts/*.py scripts/*.sh; do
  cp "$SRC/$f" "$DST_SCRIPTS/$(basename $f)"
done

# 3. 前端文件同步
cp "$SRC/frontend/index.html" "$DST/../frontend/imdf/index.html"
cp "$SRC/frontend/js/app.js" "$DST/../frontend/imdf/js/app.js"
for f in frontend/js/pages/{drama-studio,data-viewer,dam-viewer,picture-book,template-market}.js; do
  cp "$SRC/$f" "$DST/../frontend/imdf/$f"
done
```

## 统一平台启动

从统一平台目录启动IMDF的正确方式：

```python
# start_imdf.py — 放在 nanobot-factory 根目录
import sys, os
IMDF_DIR = os.path.join(os.path.dirname(__file__), 'backend', 'imdf')
sys.path.insert(0, IMDF_DIR)
sys.path.insert(0, os.path.dirname(IMDF_DIR))
from api.canvas_web import app
uvicorn.run(app, host='0.0.0.0', port=8765)
```

**关键**：必须同时把 `imdf/` 和 `backend/` 两个路径加入sys.path，因为IMDF内部用 `from core.canvas_core import ...`（在imdf/core/）和 `from api.xxx import ...`（在imdf/api/）。

## 导入验证结果

```
✅ IMDF可导入, 352路由
✅ 模型网关加载 (/api/models, /api/chat)
✅ 分类规则引擎加载 (12条预置规则)
✅ 音频能力路由加载
✅ 数据寻源路由加载
✅ DAM资产管理 (F1.8)
✅ 审美评分 (F1.11)
✅ 绘本成书 (F1.7)
✅ 模板市场 (F2.6)
✅ 数据管线 (F2.5)
✅ 调度器路由
⚠️ 非关键缺失: metrics_routes, external_routes, sharing_routes, personnel_routes
```

## WSL进程杀死问题

WSL环境会持续用SIGTERM(15)杀掉长时间运行的Python服务进程。这不是代码bug——在Windows裸机上运行时不会遇到此问题。

验证服务在WSL中正常运行的方法：
- 启动后5秒内测试（进程被杀前）
- 使用`python3 -c "import..."`验证导入而非启动服务
- Windows部署使用`start_imdf.py`或`完整部署.bat`
