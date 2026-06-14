# 2026-06-10 条件链审计结果

## 审计对象
Hermes Dynamic Workflows 系统全部 18 项增强功能

## 审计方法
逐功能追查调用链：声称在X条件下执行 → 检查X是否被触发 → 谁触发X → 追到底

## 审计结果

### ✅ 无条件自动运行（9项）

| 功能 | 调用链 | 验证证据 |
|------|--------|---------|
| mandatory_engine | G1齿轮(1min cron) + G7醒来(1min cron) + daemon(5min cron) 三路冗余 | `mandatory_engine.log` 每分钟有记录 |
| dual_review(插件) | Hermes主Agent启动→pre_tool_call hook→每个delegate_task前 | `gear_registry.dual_reviews` 有记录 |
| auto_workflow(插件) | Hermes主Agent启动→post_llm_call hook→每次消息后写入队列 | `auto_workflow_queue` 表有数据 |
| gear_integration | gear_enforcer(cron每分钟) | `gear_registry` 有10+注册任务 |
| retrospect | cron每15分钟 | `hermes_retrospect` crontab存在 |
| evolution | cron每30分钟+每天3点 | `retro_candidates` 表有数据 |
| full_chain_test | cron每天10/22点 | `full_chain_test.json` 有执行记录 |
| daemon | cron每5分钟 | `workflow_daemon.log` 最近5分钟有记录 |
| storage | SQLite数据库真实存在 | `workflow.db` 可读写 |

### ❌ 死链（9项）——全部卡在 runtime.run() 无调用方

| 功能 | 死链位置 | 卡死原因 |
|------|---------|---------|
| preflight | runtime.py phase循环 | 代码已注入，但runtime.run()从未被调用 |
| company_matcher | executor.py execute_task() | 同上 |
| SDLC | executor.py execute_task() | 同上 |
| adversarial | runtime.py 完成阶段 | 同上 |
| scheduler | 被runtime.run()调用 | 同上 |
| recover | 需runtime写checkpoint | 同上 |
| durable | 需runtime.run_durable() | 同上 |
| unified_engine | 未被执行 | 同上 |
| DSL | 库代码 | 需手动调用 |

### 🔧 修复方案：最终强制执行器

**位置**: `workflows/mandatory_executor.py`

**原理**: 在 daemon 中通过 subprocess 启动 `hermes chat -z` 子进程。子进程有完整 Hermes 主Agent 上下文（包括 delegate_task），从而 runtime.run() 可被真正调用。

**三路冗余**: daemon(5min) + 独立cron(5min) + gear_enforcer(1min 检查)

```mermaid
graph TD
    A[用户发消息] --> B[auto_workflow插件 post_llm_call hook]
    B --> C[写入 auto_workflow_queue SQLite]
    C --> D[daemon每5分钟扫描]
    D --> E[mandatory_executor.py]
    E --> F[启动hermes chat -z子进程]
    F --> G[子进程有delegate_task上下文]
    G --> H[runtime.run() 可被真正调用]
    H --> I[preflight/Company/SDLC/adversarial/scheduler/recover/durable 全部激活]
```

## 教训总结

1. **"能导入 ≠ 在运行"** — 必须验证调用链有终端，且终端确实被触发
2. **configure() 模式不可靠** — 暴露配置函数没人调用=死路，改用 plugin hook
3. **根因集中** — 9条死链是一个根因（runtime.run()无调用方），不是9个独立问题
