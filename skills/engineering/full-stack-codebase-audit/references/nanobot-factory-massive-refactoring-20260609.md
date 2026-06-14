# NanoBot Factory 大规模重构日志 — 2026-06-09

## 约6小时的端到端重构

从"项目架构混乱/无包结构/server.py 9181行/无限画布基础版"到"标准包+模块化路由+10Agent画布引擎"。

## 关键经验

### 项目清理
- 批量删除: 37个垃圾文件(fix_*13个, test_*22个, 备份目录2个)
- 确认cron中无引用待删除文件
- 留意隐藏目录 .nanobot_*_backups

### pyproject.toml
- [tool.setuptools.packages.find] where=["backend"] include=["nanobot_factory*", "routes*"]
- console_scripts: nanobot-server = "nanobot_factory.server:main"
- 注意：pip install -e . 会在import时执行server.py(尝试连ollama等)->超时
- 解决: 通过 nanobot_factory/server.py 做路径拼接延迟导入

### server.py模块化
- 原始大小: 9181行
- 拆分策略: 按功能拆,先新增不删旧
- 用 APIRouter() 替代 @app.* 装饰器
- routes/__init__.py 做 import 中心
- 在 server.py 末尾加 try/except 包装的 register_all_routers(app)
- 新旧路由共存时旧路由优先匹配(FastAPI按注册顺序) -> 新路由实际不会被调用
- 安全迁移: 所有新路由和老路由同时存在, 测试通过后再考虑删除旧路由

### 无限画布升级
- 从507行基础CanvasState升级为861行Agent驱动
- 10个Agent: ImageGen/Edit/Outpaint/Video/Drama/PictureBook/Composition/Stylist/Reviewer/Storyboard
- Goal Hive: decompose_request->get_execution_plan(串行分层+并行同级)
- Engine Router: action->role映射表
- Reviewer: 每层执行后自动审核

### 多子代理并行修改冲突
- 多个delegate_task同时修同一server.py会冲突
- 解决方案: 排他性修改串行化, 大文件一次只给一个子代理

### 测试体系
- 从0到282测试, 增量构建
- 每新建一个模块立即测试可导入
- 每批修改完后全量回归
