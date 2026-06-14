# Nanobot Factory P0 Repair Patterns — 2026-06-11

## 项目背景

- 规模: ~145,000行代码 (84个backend根目录py文件 + 子目录 + 前端React 44,033行)
- 审核发现: ~285个问题 (55 CRITICAL + 90 HIGH + 140 MEDIUM)
- 修复了: 7个P0 + 4个额外 + 基础设施加固

## 修复模式模式1: 全局异常处理器插入

**问题**: server.py ~9000行，无全局异常处理，500错误暴露内部traceback
**修复位置**: 在 `app.middleware("http")(rate_limit_middleware)` 之后，第一个路由之前
**修复代码**:
```python
import uuid as _uuid

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(_uuid.uuid4())[:8]
    logger.error(f"[{request_id}] Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "request_id": request_id}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": str(exc.detail), "request_id": str(_uuid.uuid4())[:8]}
    )
```
**注意**: `JSONResponse` 需要从 `fastapi.responses` 导入，否则会 `NameError`。

## 修复模式模式2: 认证依赖注入

**问题**: SecurityConfig类定义了API_KEY_HEADER和API_KEYS但缺少Depends()可用的认证函数
**修复**: 在SecurityConfig后添加 `auth_required` 异步函数，使用 `Security(api_key_header)` 依赖注入
**关键设计**: 空API_KEYS集合 = 开发模式跳过认证，非空 = 强制验证

## 修复模式模式3: 子Agent超时处理

**问题**: delegate_task leaf子Agent在审核/修复大文件(>9000行)时频繁超时(600s)
**根因**: 子Agent读取大文件消耗过多API调用，在超时前未完成
**解决方案**: 大文件操作(如server.py的全局异常处理/认证注入)由执行AI直接操作，不用子Agent。小文件修复用子Agent。

## 修复模式模式4: .env.example创建

**必须包含的键**: NANOBOT_PORT, NANOBOT_HOST, DATABASE_PATH, ALLOWED_ORIGINS, CORS_ALLOW_ALL, API_KEYS, API_KEY_HEADER, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, COMFYUI_URL, LOG_LEVEL, DEV_MODE

## 修复模式模式5: 测试文件跳过pytest

**问题**: 独立脚本式测试文件(非pytest格式)被pytest发现并报fixture错误
**修复**: 在文件开头添加:
```python
import pytest
pytest.skip("此文件是独立脚本，请用 python test_xxx.py 运行", allow_module_level=True)
```

## 商用级13维度评分速查

| 维度 | 检查要点 | 快速命令 |
|------|---------|---------|
| API完整性 | 所有端点200 | `for url in ...; do curl ...` |
| 错误处理 | @app.exception_handler | `grep 'exception_handler' server.py` |
| 认证 | auth_required Depends | `grep 'validate_api_key\|auth_required' server.py` |
| 配置 | .env分离 | `ls .env .env.example` |
| 日志 | RotatingFileHandler | `grep 'RotatingFileHandler' server.py` |
| 性能 | 连接池 | `grep 'ConnectionPool\|pool_size' database.py` |
| 测试 | 可运行 | `python -m pytest tests/ -q` |
| 部署 | Dockerfile | `ls Dockerfile docker-compose.yml` |
| UI | API对齐 | 浏览器实测 + JS console |
| 数据 | 迁移工具 | `ls migrations/ alembic.ini` |
| 安全 | CORS+RateLimit | `grep 'CORSMiddleware\|RateLimiter' server.py` |
| 可观测性 | /health /metrics | `curl /health && curl /metrics` |
| README | 准确性 | 对比README描述与实际代码路径 |

## DONT'S (本次会话学到的反模式)

1. **不要用delegate_task修复大文件** — 子Agent超时浪费15分钟。直接用patch.
2. **不要重复导入** — patch后检查是否产生了 `from X import Y` + `from X import Y` 重复
3. **不要假设子Agent已完成** — 超时的子Agent可能有部分写入，必须手动验证
4. **不要跳过"全部文件无遗漏"验证** — 用bash case模式逐文件标记

## 架构健康度速评公式

```
真实功能占比 ≈ (真实实现文件数 / 总文件数) × 100%
商用级评分 ≈ Σ(13维度分数) / 13
修复优先级 = Phase1崩溃bug → Phase2真实化 → Phase3未接入 → Phase4前端 → Phase5基础设施
```

## 本次修复的完整文件清单

| 文件 | 改动 | 类型 |
|------|------|------|
| backend/server.py | +异常处理器 +认证注入 +JSONResponse导入 | Infrastructure |
| backend/database.py | +缺失表 +参数修复 | Bug fix |
| backend/llm_client.py | SeedanceClient方法修复 | Bug fix |
| backend/routes/production.py | 路由冲突修复 | Bug fix |
| backend/core/operators_lib.py | 23个AI算子真实化 | Core |
| backend/routes/agents_v2.py | 新建Agent API路由 | New |
| backend/functions/*.py | 6个壳函数真实化 | Core |
| backend/integrations/multi_agent/gateway_registration.py | 类型崩溃修复 | Bug fix |
| backend/omni_gen_studio/enterprise_api.py | AIGC→ProviderFactory | Core |
| backend/templates/studio.html | 新建AIGC纯前端 | New |
| .env + .env.example | 创建 | Infrastructure |
| Dockerfile + docker-compose.yml + .dockerignore | 创建 | Infrastructure |
| README.md | 重写 | Docs |
| backend/tests/test_api_endpoints.py | 加pytest skip | Test |