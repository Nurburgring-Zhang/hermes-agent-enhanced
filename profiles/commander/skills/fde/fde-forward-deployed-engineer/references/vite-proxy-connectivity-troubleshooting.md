# Vite Proxy 前端-后端连通性故障排查

## 场景

React/Vite 前端 + FastAPI/Django/其他后端 分离部署时，前端页面渲染正常但显示"Offline"、数据不加载。

## 根因

Vite dev server 的 `server.proxy` 默认只代理 `server.proxy` 块中明确指定的路径前缀。如果后端路由不在这些前缀下（如 `/health`、`/metrics`、WebSocket 端点 `/ws`），前端直接请求这些路径会落到 Vite 自身的 HTML 路由上，返回 HTML 而非后端 JSON。

## 排查流程

### 1. 确认是否为代理问题

在前端浏览器 Console 执行：

```js
fetch('/health').then(r => r.text()).then(t => console.log(t.substring(0, 200)))
```

- 返回 `{"status":"healthy"...}` → 代理正常
- 返回 `<!DOCTYPE html>` → 代理缺失，请求被 Vite 自己处理了

### 2. 确认后端实际运行中

直接从终端访问后端：

```bash
curl http://localhost:8001/health
```

- 返回 JSON → 后端正常，问题在代理层
- 失败 → 后端没启动或端口不对

### 3. 审计后端所有非`/api`路由

```bash
grep -rn "@app\.\(get\|post\|ws\|put\|delete\)" backend/ server.py 2>/dev/null | grep -v "/api/" | head -20
```

常见非`/api`端点：
- `/health` — 健康检查
- `/metrics` — 指标
- `/ws` — WebSocket
- `/` — 根路径
- `/docs` — OpenAPI 文档

### 4. 修复代理配置

在 `vite.config.ts` 的 `server.proxy` 块中添加缺失规则：

```ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:PORT', changeOrigin: true },
    '/health': { target: 'http://localhost:PORT', changeOrigin: true },
    '/metrics': { target: 'http://localhost:PORT', changeOrigin: true },
    '/ws': { target: 'ws://localhost:PORT', ws: true },  // WebSocket 需要 ws: true
  }
}
```

### 5. 重启 Vite

HMR 不会重载 proxy 配置。必须杀掉 Vite 进程重启：

```bash
pkill -f vite  # 或 Ctrl+C 重启
npx vite --host 0.0.0.0
```

### 6. 验证修复

```bash
curl http://localhost:5173/health
# 应返回 {"status":"healthy","agents_count":...} 等 JSON
```

## 前端检查点（代码级）

如果前端依然显示 Offline，检查前端 API 服务层的 URL：

```ts
// api.ts — 确认 API_BASE_URL
const API_BASE_URL = '';  // 相对路径 → 走 Vite 代理
// 或
const API_BASE_URL = 'http://localhost:8001';  // 绝对路径 → 不走代理（有 CORS 问题）
```

如果用了绝对路径，需要后端配置 CORS 允许前端 origin。

## 快速自查表

- [ ] 后端健康检查: `curl http://localhost:8001/health` → JSON
- [ ] 前端代理: `curl http://localhost:5173/health` → JSON（非HTML）
- [ ] WebSocket: 浏览器 Console 显示 "WebSocket connected" 而非错误
- [ ] API 调用: 若前端用相对路径（`''`），Vite 代理必须覆盖所有后端路由
- [ ] 改完 proxy 后必须重启 Vite（kill + restart, HMR 不重载 proxy）
