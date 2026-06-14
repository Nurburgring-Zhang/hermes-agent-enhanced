# 死声明检测方法论 (2026-06-12 实战)

## 定义

**死声明** = 代码/配置/文档声明了一个能力，但运行时没有任何路径到达这个声明。
比"假实现"更隐蔽——假实现至少写了代码（虽然假装执行），死声明连运行时执行都没有。

## 检测矩阵

对每个声明的能力，执行以下4级穿透检查：

| 级别 | 检查 | 方法 | 判定 |
|------|------|------|------|
| L1 | 文件存在 | `test -f <path>` | 通过=文件在磁盘上 |
| L2 | 被导入/引用 | `grep -rn 'import.*X\|from.*X import'` | 通过=至少1个其他文件引用它 |
| L3 | 被拦截链调用 | 追踪运行时执行路径：agent_enhancement_manager._try_load() / tool_executor.py / conversation_loop / run_agent / cron | 通过=有至少1条执行路径 |
| L4 | 真实产生可观测输出 | 验证日志文件/状态文件/实际修改 | 通过=能在日志中找到执行记录 |

## Hermes系统中的L4死声明检测（特定于本系统）

由于Hermes的增强能力通过4层注入体系运行，每层的检测方法不同：

### 进程启动层（model_tools.py）
```bash
# 检查是否在model_tools.py被引用
grep -n 'rule_enforcer\|force_compressor\|dual_review' ~/.hermes/hermes-agent/model_tools.py
```

### 对话前层（conversation_loop.py PRE hook）
```bash
grep -n 'pre_conversation_hook\|_try_load' ~/.hermes/hermes-agent/agent/conversation_loop.py
```

### 工具调用层（tool_executor.py）
```bash
grep -n 'pre_tool_intercept\|post_tool_intercept\|post_review' ~/.hermes/hermes-agent/agent/tool_executor.py
```

### 插件系统（agent_enhancement_manager.py）
```bash
# 注册表中是否有
grep "plugin_name" ~/.hermes/scripts/agent_enhancement_manager.py
# safe_hook_pre/post中是否有_try_load调用
grep "_try_load.*plugin_name" ~/.hermes/scripts/agent_enhancement_manager.py
```

### 响应层（rule_enforcer.py的post_response_intercept等）
```bash
# R9/R11等是否被集成了
grep "DualModelEnforcer\|IterationEnforcer\|RealImplementation" ~/.hermes/scripts/rule_enforcer.py
```

## 2026-06-12 发现的6个死声明

| 声明 | 文件 | L1存在 | L2引用 | L3执行路径 | L4可观测 | 判定 | 修复 |
|------|------|--------|--------|-----------|---------|------|------|
| rule_enforcer.py R1-R5 | scripts/rule_enforcer.py | ✅ | ❌ | ❌ | ❌ | 死声明 | 注入tool_executor+conversation_loop+run_agent |
| force_compressor | scripts/不存在 | ❌ | ❌ | ❌ | ❌ | 死声明 | 创建文件(10.9KB)+注册67插件 |
| dual_review_engine | scripts/dual_review_engine.py | ✅ | ❌ | ❌ | ❌ | 死声明 | 需注入tool_executor |
| R9 DualModelEnforcer | rule_enforcer.py内 | ✅ | ❌ | ❌ | ❌ | 死声明 | 集成到post_response_intercept |
| R11 IterationEnforcer | rule_enforcer.py内 | ✅ | ❌ | ❌ | ❌ | 死声明 | 集成到post_response_intercept |
| R8 AccountabilityEnforcer | rule_enforcer.py内 | ✅ | ✅(自引用) | ❌ | ❌ | 死声明 | record_unused添加自动触发 |

## 与假实现的区别

| 特征 | 假实现 | 死声明 |
|------|--------|--------|
| 代码存在 | ✅ 写了代码 | ✅ 写了代码或只写了声明 |
| 运行时可达 | ✅ 可达 | ❌ 不可达 |
| 做了什么 | 返回固定值/空值/占位符 | 什么都没做（代码不执行） |
| 检测难度 | 中（需要运行并检查输出） | 高（需要追踪执行路径） |
| L3检测足够 | ❌ 需要L4 | ✅ L3即可发现 |

## 预防措施

1. 每次添加新能力后，追踪完整的调用路径：`声明位置 → 代码文件 → import点 → 运行时执行链 → 输出`
2. 对每个集成的模块，执行`grep -rn 'module_function'`检查至少1处非自身的引用
3. 所有`_try_load`调用必须在`agent_enhancement_manager.py`的`safe_hook_pre_conversation`或`safe_hook_post_conversation`中
4. reg规则: 任何新模块的PR必须附带`运行时验证`——证明这个模块在完整系统上下文中可达
