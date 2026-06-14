# auto_workflow 插件模式 — 消息驱动workflow

## 架构

```
用户消息 → Hermes主Agent → post_llm_call hook
  → plugins/auto_workflow/ → 写入 auto_workflow_queue (SQLite)
    → daemon每5分钟 → 读取队列 → deep_research(msg) → 保存workflow → G0注册
```

## 注入方式
- Hermes 插件系统 post_llm_call hook
- 无需任何外部配置——主Agent启动时自动加载
- 代码位置：`~/.hermes/plugins/auto_workflow/`
- 插件注册：`register(ctx)` → `ctx.register_hook("post_llm_call", auto_workflow_hook)`

## 调用链（已追到底）
1. Hermes 主Agent启动 → 扫描 plugins/
2. auto_workflow/plugin.yaml 存在 → 加载 __init__.py
3. register() → 注册 post_llm_call hook
4. 每次用户消息处理后 → hook自动调用 → 写入队列
5. daemon每5分钟 → 消费队列 → 构建workflow → G0注册

## 队列表定义
```sql
CREATE TABLE IF NOT EXISTS auto_workflow_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_message TEXT,
    assistant_summary TEXT,
    model TEXT,
    platform TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    processed_at TEXT,
    workflow_id TEXT,
    error TEXT
);
```

## 插件配置
文件：`~/.hermes/plugins/auto_workflow/plugin.yaml`
```yaml
name: auto-workflow
version: 1.0.0
hooks:
  - post_llm_call
```

## 已知限制
- 当前仅使用 deep_research 模板，未来可根据消息类型选择不同模板
- daemon中未调用 runtime.run()——workflow构建完成但未实际执行
- 需要 delegate_task 环境才能真正执行 workflow（主Agent或子Agent内）
