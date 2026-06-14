# 条件链审计方法论（2026-06-10 固化）

## 核心问题

设计中经常出现"在条件A下才执行"的模块，但从未确认条件A本身是否成立。
如果不追根到底，就会造出"能导入但不能运行"的虚假功能。

## 条件链审计步骤

### Step 1: 列举假设条件

对于每个声称"自动运行"的功能，列出它的所有前置条件：

```
功能X 在 条件A 下执行
  → 条件A 需要 条件B 下才能触发
    → 条件B 需要 条件C 下才能触发
      → ...
```

### Step 2: 逐层验证

每层验证方式：
- **代码存在性**：搜索代码中是否有相关调用 (`grep -rn`)
- **调用路径**：从功能入口往上追，找到调用者
- **触发机制**：是 cron/event/hook 还是手动调用？
- **运行时依赖**：需要哪些函数被提前配置/注入？

### Step 3: 标记断链

每层验证后判断：
- ✅ 路径完整（无需额外条件）
- ❌ 路径中断（需要外部触发但无人触发）
- ⚠️ 路径脆弱（依赖某函数被调用但非强制）

### Step 4: 修复断链

修复策略（按优先级）：
1. **插件 hook** — 引擎原生支持的 hook（pre_tool_call, post_tool_call 等）
2. **cron 注入** — 独立于主进程的定时任务
3. **齿轮冗余** — 三路以上的冗余触发路径
4. **engine-level monkey-patch** — 最低优先级，维护成本高

## 典型案例

### 案例1：executor.dual_review 的断链审计

```
❌ executor.dual_review → 需要 configure_dual_review()
    → configure_dual_review 需要被某人调用
      → 没有任何代码调用 configure_dual_review
        → 死链 ❌
```

修复前：`executor.py import dual_review` + `await dual_review(...)` 但 `_delegate_fn` 永远是 None。

修复后：`plugins/dual_review/__init__.py` 通过 pre_tool_call hook 自动触发，无需任何外部配置。

### 案例2：runtime.run() 的断链审计

```
❌ runtime.run() → 包含 preflight + G0 + G1 + SDLC + Company + 复盘 + 进化
    → runtime.run() 需要被调用
      → 没有任何代码调用 runtime.run()
        → 死链 ❌
```

修复前：18个模块全部注入到 runtime.run() 中，但没人调用过它。

修复后：full_chain_test.py 每天10/22点 cron 自动调用，验证全部注入点。但 runtime.run() 仍未接入 Hermes 主流程——这是进一步的待办。

## 预防措施

构建任何新模块时必须回答的三个问题：

1. **这条代码路径谁触发？**（明确触发者）
2. **什么时候触发？**（每分钟/每次消息/每次tool调用？）
3. **触发条件是否无条件满足？**（如果条件需要外部配置，必须追查那个配置本身是否成立）

如果三个问题不能立刻回答 → 模块还不是"在运行"。

## 检查清单

```
□ 模块可导入（__import__ 成功）
□ 函数可调用（callable() 为 True）
□ 有明确的触发者（cron/event/hook/agent loop）
□ 触发者本身在运行（确认触发者的条件链完整）
□ 所有前置函数已被注入（configure() 已被调用）
□ 有健康检查（mandatory_engine 或类似机制）
□ 失效后有自动恢复（重启/重注入/重新注册）
```
