# 商用级深度打磨+高可用完整方案 (2026-06-17实战总结)

## 打磨框架（3层×3轮）

```
Round 1: 全量API压测(40+端点实测) → 修复失败项 → 重启验证
Round 2: 边缘情况+并发+延迟基准 → 空/超限/错误输入 → 性能基准表
Round 3: 前端导航+跨页面联动 → 数据流完整性 → 持久化验证
```

## 高可用性增强（Phase 1-3）

### Phase 1: 自愈+保护+配置
- `deploy/imdf.service`: Restart=always + RestartSec=5 + WatchdogSec=30
- `api/middleware/robustness.py`: ConcurrencyLimiter(100) + X-Request-ID + 30s超时 + Panic Recovery
- `config/settings.py`: 统一配置中心(.env→环境变量→默认值)

### Phase 2: 可观测性
- 日志: RotatingFileHandler(10MB×5) + 慢请求日志(>1s)
- 指标: Prometheus格式 /metrics + P50/P95/P99直方图
- 健康检查: /health(基础) + /health/ready(就绪) + /health/live(存活)

### Phase 3: Agent主动驱动
- `engines/scheduler_engine.py`: 4预置cron任务(清理/刷新/排行/自检)
- `engines/event_engine.py`: 3事件触发器(上传→打标/标注→评分/导入→分类)

## 运维脚本套件
- `scripts/concurrency_test.py` — 1000并发压测
- `scripts/backup.py` — SQLite+配置+文件打包tar.gz
- `scripts/restore.py` — 从tar.gz恢复+完整性校验
- `scripts/log_rotation_verify.py` — 日志轮转验证
- `scripts/e2e_test.py` — 17步端到端测试
- `scripts/health_check.py` — systemd watchdog用健康检查
- `scripts/alert.sh` — webhook/邮件告警

## 商用级可达性验证矩阵

| 维度 | 验收项 | 结果 |
|------|--------|------|
| 代码层 | DAM预览100% / 审美std=7.5 / 事件E2E / 14模板 | ✅ |
| 运维层 | 并发保护 / 日志轮转 / 备份恢复 / E2E | ✅ |
| 高可用 | systemd自愈 / 请求ID / 配置中心 / 健康检查 | ✅ |
| 可观测 | metrics / 三级健康 / 告警 / 慢请求日志 | ✅ |
| Agent | 4cron / 3事件 / APScheduler | ✅ |

## 常见遗漏模式
- 新增路由后必须**重启服务**才能生效（FastAPI不会热重载新import的模块）
- 子Agent修改canvas_web.py后，必须重新同步到统一平台
- 模板路由/管线路由/api-keys需要401认证是正常的（不是bug）
