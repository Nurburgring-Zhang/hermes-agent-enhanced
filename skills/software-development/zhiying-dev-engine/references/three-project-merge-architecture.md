# 三项目融合架构模式 (2026-06-16 实战)

## 场景
将 IMDF(数据标注/工作流/画布) + 智影(44算子/需求/评测) + nanobot-factory(AIGC/Vue管理) 三个独立项目融合为统一数据生产平台。

## 核心教训: 不要用FastAPI sub-app mount

**失败的方案:**
```python
# ❌ 将IMDF作为子应用mount到nanobot-factory
sys.path.insert(0, str(Path(__file__).parent / "imdf"))
from api.canvas_web import app as imdf_app
app.mount("/imdf", imdf_app)
```

**失败原因:**
1. **sys.path污染** — IMDF的canvas_web.py在导入时调用`sys.path.insert(0, ...)`,把IMDF目录推到sys.path[0]。此后所有`from core.xxx import ...`都在IMDF的core/中查找(无相应文件)。
2. **sys.modules缓存污染** — `import core`被缓存在sys.modules中指向IMDF的core,后续nanobot-factory的`from core.dataset_version import ...`使用了错误的core模块导致ModuleNotFoundError。
3. **主机生命周期冲突** — nanobot-factory的server.py(10,700行)有GPU监控/Electron IPC/Agent集群调度/文件监听器/任务队列等复杂生命周期管理,子应用挂载会干扰这些组件的启动。

**修复三步骤(短期但不稳定):**
```python
# 1. 导入后移除IMDF路径
sys.path.remove(_imdf_root)
# 2. 清除模块缓存
del sys.modules['core']
for k in list(sys.modules.keys()):
    if k.startswith('core.'): del sys.modules[k]
# 3. 重新插入backend路径
sys.path.insert(0, str(_backend_dir))
```

**即使如此修复** — nanobot-factory在加载完所有组件(33个Agent/GPU监控/集群调度/任务队列)后仍会自行关闭(干净shutdown,非崩溃),可能与Electron主进程断开连接触发。

## 正确方案: 独立服务 + 反向代理

```
架构:
  IMDF+智影 (8765端口) -- 独立FastAPI进程
  nanobot-factory (8899端口) -- 独立FastAPI进程
  nginx (80/443) → 统一入口
    /          → 8899
    /imdf/*    → 8765
    /zhiying/* → 8765
```

**启动脚本:**
```bat
start "IMDF" cmd /c "cd D:\Hermes\infinite-multimodal-data-foundry && python api\canvas_web.py --port 8765"
start "Nanobot" cmd /c "cd D:\Hermes\生产平台\nanobot-factory\backend && python server.py --port 8899"
```

**优势:**
- 每个服务独立生命周期,不互相干扰
- 任何一个崩溃不影响另一个
- 可以独立扩容/重启/更新
- nginx处理静态文件缓存、SSL终止、负载均衡

## 预设多角色账号体系(11类)

| 用户名 | 密码 | 角色 | 团队 | 用途 |
|--------|------|------|------|------|
| admin | Admin@2026! | admin | system | 超级管理员 |
| prod_lead | Prod@2026! | team_lead | production | 生产主O |
| qc_lead | QC@20261! | reviewer | production | 质检主O |
| prod_user1/2/3 | Prod1/2/3@2026! | annotator | production | 生产人员 |
| crowd_lead | Crowd@2026! | team_lead | crowd | 众包负责人 |
| crowd_mgr | CrowdM@2026! | reviewer | crowd | 众包管理 |
| crowd_qc | CrowdQ@2026! | reviewer | crowd | 众包质检 |
| crowd_user1 | Crowd1@2026! | annotator | crowd | 众包人员 |
| client1 | Client@2026! | viewer | client | 需求方 |

**实现:**
```python
# backend/auth/unified_auth.py — JWT + argon2 + SQLite持久化
# backend/scripts/init_accounts.py --reset — 一键初始化
```

## 商用级验证清单(25项)
```
基础设施: Web 200 / Health / 认证 / 限流 / 审计日志 / 静态文件 (6项)
核心业务: 数据集CRUD / AI预标注 / DAG工作流 / 图片生成 / 视频生成 / 数据采集 / 备份 / OSS (8项)
前端页面: dashboard/datasets/annotate/workflow/tasks/team/delivery/review (8项)
高级功能: 图片标注工具 / 评测审核 / 44算子管线 / 智影入口 (4项)
```
