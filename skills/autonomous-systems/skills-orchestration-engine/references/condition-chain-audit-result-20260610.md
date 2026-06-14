# 2026-06-10 条件链审计完整结果

## 审计对象
Hermes Dynamic Workflows 系统全部 18 项功能

## 审计方法
追踪每条声称的调用链从声明位置到终端。逐层追问：声称在X条件下执行 → X被谁触发？ → 触发条件是什么？ → 追到底。

## 最终结果

### ✅ 无条件自动运行（9项）

| 功能 | 调用链终端 | 证据 |
|------|-----------|------|
| mandatory_engine | G1齿轮(1min cron) + G7醒来(1min cron) + daemon(5min cron) 三路 | logs/mandatory_engine.log 每分钟有记录 |
| dual_review(插件) | Hermes 主Agent启动 → pre_tool_call hook | logs/dual_review/reviews.jsonl 有内容 |
| auto_workflow(插件) | Hermes 主Agent启动 → post_llm_call hook | workflow.db auto_workflow_queue 有数据 |
| gear_integration | gear_enforcer cron 每分钟 | gear_registry 10+注册任务 |
| retrospect | cron 每15分钟 | retro_candidates 表有数据 |
| evolution | cron 每30分钟+每天3点 | evolution_trigger.log 更新 |
| full_chain_test | cron 每天10/22点 | full_chain_test.log 更新 |
| daemon | cron 每5分钟 | workflow_daemon.log 更新 |
| storage | SQLite 数据库 | workflow.db 可读写 |

### ❌ 死链（9项）— 全部卡在 runtime.run() 无调用方

| 功能 | 注入位置 | 声称 | 实际 |
|------|---------|------|------|
| preflight | runtime.py phase循环 | 每个phase前自动 | runtime.run()从未被调用 |
| company_matcher | executor.py execute_task() | 每个task自动匹配 | 同上 |
| SDLC | executor.py execute_task() | 每个task注入SDLC流程 | 同上 |
| adversarial | runtime.py 完成阶段 | 完成后自动对抗验证 | 同上 |
| scheduler | 被runtime.run()调用 | 4种调度模式 | 同上 |
| recover | 需runtime.run()写checkpoint | 断点恢复 | 同上 |
| durable | 需runtime.run_durable() | 持久化执行 | 同上 |
| unified_engine | 独立入口 | 统一执行 | 从未被执行 |
| DSL | 库代码 | Python DSL | 需手动调用 |

### 根因分析

```
runtime.run() 无调用方
  → 原因1: 依赖外部主动触发（无人做这件事）
  → 原因2: executor.py 和 runtime.py 中的强制注入（preflight/company/SDLC）都是代码层正确
  → 原因3: 所有注入点都跑在 phase 循环内，但 phase 循环从未被启动
```

### 修复方案

**最终强制执行器** (mandatory_executor.py):
- 在 daemon(5min cycle) 中，从 auto_workflow_queue 读取 pending workflow
- 用 hermes chat -z 启动子Agent进程
- 子Agent有完整 Hermes 主Agent上下文（含 delegate_task）
- 子Agent在 conversation_loop 中走正常消息处理 → pre_tool_call hook 触发 → dual_review
- 三路冗余: daemon(5min) + 独立cron(5min) + gear_enforcer(1min 检查)

```
用户发消息 → auto_workflow插件(post_llm_call) → 写入SQLite队列
  → daemon每5分钟扫描pending任务
    → mandatory_executor 启动 chat -z 子进程
      → 子进程走 conversation_loop
        → pre_tool_call hook (dual_review)
        → 子Agent使用 delegate_task 执行任务
        → runtime.run() 可被真正调用
          → preflight/Company/SDLC/adversarial/scheduler/recover/durable 全部激活
```

## 关键教训

1. "能导入 ≠ 在运行" — 必须验证调用链有终端且终端被触发
2. configure() 模式不可靠 — 改用 plugin hook (无条件，主Agent启动自动加载)
3. 根因集中 — 9条死链同一个根因，不是一个修复9个独立问题
4. 检查逻辑必须改为"调用链完整性检查"，不是"是否可import"检查
