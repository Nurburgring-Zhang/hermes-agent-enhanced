# 性能基准数据（2026-06-16 采集于nanobot-factory项目）

## API响应时间（5次平均）
| 端点 | 平均响应 | 说明 |
|------|---------|------|
| `/` (首页) | 4ms | 静态文件 |
| `/health` | 3ms | 内存状态读取 |
| `/api/v2/nodes` | 1ms | 内存注册表查询 |
| `/api/v2/db/tables` | 10ms | SQLite查询 |
| `/api/v2/auth/login` | <1ms | 内存Session创建 |

## 前端构建
| 指标 | 值 |
|------|-----|
| 构建时间 | 19.56s - 20.9s |
| 总JS chunk | 29个 |
| Element Plus chunk | 740K |
| 页面chunk范围 | 6.4K - 36K |
| 总CSS | 317K (Element Plus) |
| 最大页面chunk | Workflow: 36K |

## 生产部署
| 指标 | 值 |
|------|-----|
| Workers | 4个 |
| 并发限制 | 200 |
| 请求限制 | 10,000/worker |
| keep-alive | 30s |
| 验证 | 10/10 requests 200 @ 5ms avg |
