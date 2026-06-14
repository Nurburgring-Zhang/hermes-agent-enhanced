## 死声明模式（2026-06-12 实战新增）

### 定义

**死声明**: 代码/配置文件/文档中声明了一个能力存在，但该能力在运行时从未被调用或对应的文件不存在。

比"降级实现"更隐蔽——降级实现至少写了代码（虽然假装工作），死声明连代码都没有。

### 检测方法

1. **文件存在性检查**: 对SOUL.md/AGENTS.md中的每个路径声明执行 `test -f`
   ```
   SOUL.md: "由 force_compressor 插件实现"
   → test -f scripts/force_compressor.py (不存在→死声明)
   ```

2. **运行时路径追踪**: 确认每个文件至少有一条import/调用/钩子路径
   ```
   rule_enforcer.py 定义了13条规则
   → grep -rn "from rule_enforcer import\|import rule_enforcer"
   → 如果为空：死文件，运行时不会执行
   ```

3. **插件注册表 + 执行计划双确认**:
   ```
   agent_enhancement_manager.py PLUGIN_REGISTRY: 有 ("rule_enforcer", ...)
   + safe_hook_pre_conversation: 有 _try_load("rule_enforcer", ...) 吗？
   → 注册表有但 _try_load 无：插件被注册了但不会触发
   ```

4. **cron + 声明双核对**:
   ```
   SOUL.md: "cron每1分钟检测插件状态"
   → crontab -l | grep -c "每分钟\|* * * *"
   → 无对应条目→死声明
   ```

### 实战案例

| 声明 | 代码 | 运行时 | 发现 |
|------|------|--------|------|
| rule_enforcer (27KB，13条规则) | ✅ 完整 | ❌ 无import路径 | 死文件 |
| force_compressor (主动压缩插件) | ❌ 不存在 | ❌ | 连文件都没有 |
| model_router cron监控 | ✅ 存在 | ⚠️ 只跑stats | 只输出配置不做路由 |
| Dual Review Engine | ✅ 完整 | ❌ 无调用者 | 定义完整但无人调用 |

### 在审核清单中的应用

在 `17项排查清单` 中增加第18项：

18. **死声明检查**: 对项目的每份承诺能力/声明文件，验证：
    - [ ] 声明的文件存在 (`test -f`)
    - [ ] 文件有至少一条运行时入口 (import/cron/hook/子进程)
    - [ ] 入口路径能在真实环境中触发 (不仅仅是测试用例)
    - [ ] 插件注册表 + 执行计划双确认
