---
name: software-development
description: "软件开发 — 涵盖代码开发、调试、测试、代码审查、计划编写、子代理开发、插件架构、系统补丁等全流程的软件工程技能"
category: software-development
---

# Software Development (软件开发)

此分类包含软件开发的完整工作流技能，从计划制定、代码实现、测试驱动开发到调试和代码审查，覆盖现代软件工程的各个关键环节。

### 格林主人代码偏好（强制遵守）

格林主人对代码交付有极端严格的偏好，多次因违反被纠正：

- **直接改核心代码。** 需要注入能力时改 `run_agent.py`、`agent/conversation_loop.py`、`model_tools.py` 等核心文件，不要写包装器/中间层/外部桥接脚本。
- **建立4层冗余注入架构。** 单一路径的注入会在升级git reset后丢失。必须同时在model_tools.py(进程启动)、conversation_loop.py(对话前)、run_agent.py(对话后)、hermes_cli/__init__.py(CLI启动) 四个位置注入。详见 `references/4-path-injection-architecture.md`。
- **修改前备份。** `cp 源文件 /mnt/d/Hermes/备份/文件名.bak.$(date +%Y%m%d_%H%M%S)`
- **改完验证语法。** `python3 -c "import py_compile; py_compile.compile('xxx.py', doraise=True); print('✅')"`
- **必须真实实现。** 禁止降级/模拟/示例/占位符。如果某个功能不能真实实现，直接说不能，不要糊弄。
- **上传到GitHub前脱敏。** 检查代码中的硬编码路径（格林主人、administrator、`/mnt/d/`等），替换为通用占位符。
- **不要用Docker。** 所有代码在原生环境运行。
- **不要批量生成配置。** 每个员工/专家配置必须逐个手工深度定制。
- **references/comfyui-node-refactoring.md** — ComfyUI节点重构模式：if/elif/else转独立if块、多端口输出组装、system prompt+总纲双维护、AST return审计、静默失败模式
- **references/comfyui-user-preference-conciseness.md** — 格林主人对AI模板的极端简洁偏好：禁止数值参数、禁止微观细节、视觉化语言优先（2026-05-27 三次修正后固化）
- **references/comfyui-dom-widget-upload.md** — 用 addDOMWidget + 隐藏STRING widget 实现多图上传+缩略图预览，替代9个IMAGE输入端口
- **references/comfyui-output-port-consolidation.md** — 多模式输出端口合并为单一"模式输出"端口+元数据JSON端口
- **references/large-file-chunking.md** — 大文件分块构造模式，规避 write_file 覆盖陷阱，多轮测试框架，行号前缀修复
- **references/ast-return-audit.md** — AST 精确验证 return 语句返回值个数方法（避免字符串逗号误判），ComfyUI 节点多端口审计
- **references/write-file-truncation-trap.md** — write_file 接收短内容时静默截断大型文件的陷阱，事故恢复路径，历史案例
- **references/structural-codebase-repair.md** — 大型AI生成TS/JS代码库（10K-100K+ LOC）的分层修复策略：结构断裂→模块断裂→类型断裂→逻辑断裂，含webpack/tsconfig/huge-HTML清理修复模式

此分类包含以下 11 个子技能：

## 子技能

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### agents-company-real-output
修复 Agents Company 工作流，使其生成真正可运行的软件项目而非模拟数据，通过调用 RealProjectGenerator 方法生成实际产出。

### multi-expert-routing-system
实现多专家代理系统，支持自动路由、隔离工作空间/内存以及专家间协作，从概念到集成的完整实现。

### plan
Hermes 的计划模式 — 检查上下文，将 Markdown 计划写入工作区的 `.hermes/plans/` 目录，仅规划不执行。

### plugin-system-architecture
设计并实现生产级插件系统，包含生命周期管理、依赖解析、事件总线、热重载和插件间通信。

### requesting-code-review
提交流程前的验证管线 — 静态安全扫描、基线感知质量门禁、独立审查子代理和自动修复循环。

### subagent-driven-development
按实现计划派发独立子代理任务，每个任务经过规范合规性和代码质量两阶段审查后合并。

### systematic-debugging
遇到任何 Bug、测试失败或意外行为时使用。四阶段根因调查流程 — 不先理解问题就不修复。

### systematic-python-source-patching
安全修改 Python 源文件，整体替换函数/方法块而不破坏缩进或引入语法错误。

### test-driven-development
实现任何功能或 Bug 修复前使用。强制执行 RED-GREEN-REFACTOR 循环，测试先行。

### worldmonitor-external-event-monitoring
完整的外部事件监控系统，支持多种事件源、处理管线、持久化和 HTTP 管理接口。

### writing-plans
有规范或需求文档的多步骤任务使用。创建包含精确文件路径和完整代码示例的综合实现计划。

## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
