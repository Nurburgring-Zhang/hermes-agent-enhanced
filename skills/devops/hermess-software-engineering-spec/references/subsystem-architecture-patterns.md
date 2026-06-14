# 子系统构建模式 — Dynamic Workflows 实战经验

## 多层子系统模式

Dynamic Workflows 系统（~/.hermes/workflows/）遵循以下架构模式：

```
types.py          → 数据契约（所有模块共享的核心类型）
storage.py        → 持久化层（SQLite CRUD + checkpoint）
executor.py       → 执行层（任务调度封装 + delegate_task适配）
scheduler.py      → 调度层（调度算法 + 状态管理）
runtime.py        → 运行时层（状态机 + 生命周期 + 集成注入）
dsl.py            → 用户接口层（Python DSL + 模板）
adversarial.py    → 扩展模块（特定领域能力）
preflight.py      → 扩展：执行前检查
gear_integration.py → 扩展：齿轮系统对接
retrospect_integration.py → 扩展：复盘
bridge.py         → 桥接：对接现有系统
__init__.py       → 统一导出
```

这是推荐的子系统构建模式：
1. 先定义契约（types.py）
2. 再实现持久化（storage.py）
3. 再实现核心执行（executor + scheduler）
4. 再实现运行时管理（runtime）
5. 再用 DSL 包装成易用接口
6. 扩展模块用独立文件但不违反依赖方向（只依赖types/executor/runtime）

## 底层注入点

在 runtime.py 中有三个注入点用于集成强制能力：

1. **执行前注入**（第165行附近）：每个phase执行前调用的preflight检查
2. **启动时注入**（第146行附近）：workflow启动时的G0注册
3. **完成时注入**（finally块）：workflow完成/失败的复盘+G6验证

新增强制能力的步骤：
1. 在 workflows/ 下创建新模块
2. 在 runtime.py 中 import
3. 在对应注入点调用

## 与齿轮系统集成模式

所有需要持久监控的子系统应实现 GearIntegration 的3个对接点：
- G0: 启动时注册任务
- G1: 运行时写入进度
- G6: 完成后验证质量

调用方式：`from workflows.gear_integration import gear; gear.register_to_gear_vault(...)`
