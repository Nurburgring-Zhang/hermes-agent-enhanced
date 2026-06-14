---
name: awesome-codex-skill-bridge
description: |
  50+生产级Codex技能迁移桥接方案。映射awesome-codex-skills 
  (github.com/ComposioHQ/awesome-codex-skills) 的全部技能到Hermes技能体系。
  包含渐进式加载设计、Composio->Hermes工具转换、skill-creator元技能适配、
  connect模式、meeting-notes-and-actions移植、以及技能市场分类索引方案。
  
  触发条件: 任何提到 "awesome-codex-skills"、"Codex技能迁移"、
  "技能桥接"、"Composio技能移植"、"技能市场分类" 或需要将
  Codex/Composio技能模式引入Hermes的场景。
category: software-development
tags: [bridge, architecture, codex, composio, skill-migration, reference-architecture]
---

# Awesome Codex Skill Bridge

## 概述

**awesome-codex-skills** (github.com/ComposioHQ/awesome-codex-skills) 是
一个拥有 **880+ SKILL.md** 文件的生产级技能仓库，涵盖：
- 50+ 人工设计的高质量技能 (Development, Productivity, Communication, Data, Meta)
- 800+ Composio自动化技能 (连接1000+应用的模板化集成)

本bridge skill 提供**完整的迁移方案**，将所有分类映射到Hermes自有技能体系，
而非照搬实现。Hermes开发者应按需选择迁移路径。

---

## 1. 架构对比: Codex Skills vs Hermes Skills

| 维度 | Codex Skills | Hermes Skills |
|------|-------------|---------------|
| **触发机制** | YAML `description` 字段 (Codex读取所有元数据) | YAML frontmatter `description` (Hermes在system prompt中扫描) |
| **加载模型** | 三级渐进: 元数据->Body->Resources | 两级: SKILL.md正文 (全部加载) |
| **工具调用** | Composio CLI (`composio execute`) | Hermes `delegate_task` / native MCP / `terminal` |
| **目录结构** | `skill-name/SKILL.md + scripts/ + references/ + assets/` | `skill-name/SKILL.md` (+ 可选resources via skill_manage) |
| **资源目录** | `scripts/`(可执行), `references/`(文档), `assets/`(模板) | 通过`skill_view(name, file_path)`加载linked files |
| **元技能** | `skill-creator` (自描述) | 无直接对应，通过本bridge映射 |
| **安装** | `skill-installer` + `CODEX_HOME/skills/` | `skill_manage(action='create')` |
| **分享** | `skill-share` (Composio + Slack) | 无原生机制 |

### Hermes特有增强

- **`delegate_task`** 可替代Composio CLI的复杂多步工作流
- **MCP原生客户端** (native-mcp skill) 可替代Composio的app连接
- **`terminal`** 可直接替代 `composio execute` 的简单shell调用
- **`patch`** 工具提供比Codex codemod更安全的文件编辑

---

## 2. 渐进式加载设计

### Codex三级加载

```
Level 1: YAML frontmatter (name + description only)
         -> always in context, ~100 tokens per skill
Level 2: SKILL.md body (markdown instructions)
         -> loaded only when skill triggers
Level 3: Bundled resources (scripts/, references/, assets/)
         -> loaded on demand by agent decision
```

### Hermes适配方案

Hermes目前没有Codex那样的自动匹配机制，但可以模拟：

**方案A: 元数据索引 (推荐)**
- 创建一个 `awesome-codex-skill-bridge/references/skill-index.json`
- 列出所有awesome-codex-skills的name/description/category
- Hermes读取索引后决定加载哪个具体迁移方案
- 每个方案作为单独reference文件按需加载

**方案B: 分类子技能**
- 将50+技能按类别拆分为5个子skill

**方案C: 单文件+触发器关键词**
- 本skill即为单一切入点
- 在description中列出所有触发关键词
- 正文按分类分节，Hermes通过搜索定位所需部分

**推荐: 方案A + 方案C 混合**

---

## 3. 技能分类映射表

### 3.1 Development & Code Tools

| Codex技能 | 分类 | Hermes映射 | 优先级 | 备注 |
|-----------|------|-----------|-------|------|
| `codebase-migrate` | Dev | `subagent-driven-development` + `systematic-python-source-patching` | HIGH | Codex版依赖Composio, Hermes用 `delegate_task` |
| `pr-review-ci-fix` | Dev | `requesting-code-review` + `github-code-review` | HIGH | |
| `gh-fix-ci` | Dev | `requesting-code-review` + `github` | HIGH | gh CLI已有 |
| `gh-address-comments` | Dev | `github-code-review` + `requesting-code-review` | MEDIUM | |
| `issue-triage` | Dev | `github-issues` | MEDIUM | |
| `deploy-pipeline` | Dev | `devops` + 手动脚本 | LOW | 场景差异大 |
| `create-plan` | Dev | `writing-plans` + `plan` | DONE | Hermes已有更优版本 |

### 3.2 Productivity & Collaboration

| Codex技能 | Hermes映射 | 优先级 | 备注 |
|-----------|-----------|-------|------|
| `connect` | 见第7节 | HIGH | 核心技能, 需MCP桥接 |
| `meeting-notes-and-actions` | 见第8节 | HIGH | 独立移植 |
| `notion-research-documentation` | `note-taking`/`obsidian` | MEDIUM | Notion->Obsidian |
| `notion-knowledge-capture` | `note-taking`/`obsidian` | MEDIUM | |
| `notion-meeting-intelligence` | `note-taking` | MEDIUM | |
| `linear` | `linear` productivity skill | DONE | |
| `internal-comms` | 直接推理 | LOW | |

### 3.3 Communication & Writing

| Codex技能 | Hermes映射 | 优先级 | 备注 |
|-----------|-----------|-------|------|
| `email-draft-polish` | `email` skill | MEDIUM | himalaya CLI可用 |
| `changelog-generator` | 手动脚本 | MEDIUM | 纯git命令 |
| `content-research-writer` | 直接推理 | LOW | 模板化写作 |
| `support-ticket-triage` | `hermes-intelligence-system-v4` | LOW | |

### 3.4 Data & Analysis

| Codex技能 | Hermes映射 | 优先级 | 备注 |
|-----------|-----------|-------|------|
| `spreadsheet-formula-helper` | 直接推理 | LOW | 无工具依赖 |
| `datadog-logs` | `devops` + API | LOW | 需API key |
| `langsmith-fetch` | 手动实现 | LOW | |
| `sentry-triage` | `github-issues` workflow | LOW | |

### 3.5 Meta & Utilities

| Codex技能 | Hermes映射 | 优先级 | 备注 |
|-----------|-----------|-------|------|
| `skill-creator` | 见第6节 | HIGH | 核心元技能 |
| `skill-installer` | `skill_manage(action='create')` | HIGH | 原生支持 |
| `skill-share` | 无对应 | LOW | 需Slack |
| `connect-apps` | 见第7节 | HIGH | connect别名 |

---

## 4. 关键技能迁移方案

### 4.1 codebase-migrate -> Hermes版

Codex版依赖: Composio CLI

**Hermes版**:
1. 使用 `search_files` / `terminal(rg)` 扫描代码库
2. 使用 `patch` 工具进行定向替换
3. 使用 `terminal(git)` 进行版本控制
4. 使用 `github-pr-workflow` skill处理PR生命周期

转换模板:
```
Codex方式                             Hermes方式
composio search "create issue"       -> delegate_task(task="创建issue", agent="github")
composio execute GITHUB_CREATE_PR    -> github-pr-workflow skill
composio run --file workflow.ts      -> delegate_task + subagent-driven-development
```

### 4.2 gh-fix-ci / pr-review-ci-fix -> Hermes版

直接复用已有Hermes skill:
- `github` skill (gh CLI)
- `requesting-code-review` skill
- `systematic-debugging` skill

### 4.3 datadog-logs / sentry-triage

Composio CLI调用替换为直接curl调用对应REST API (需配置环境变量)

---

## 5. Composio CLI -> Hermes Native Tools 转换表

| Composio CLI命令 | Hermes等效操作 | 优先级 |
|-----------------|---------------|-------|
| `composio execute GITHUB_*` | `github` skill 或 gh CLI | HIGH |
| `composio execute GMAIL_*` | `email` skill 或 himalaya CLI | HIGH |
| `composio execute SLACK_*` | MCP桥接 (mcporter) | MEDIUM |
| `composio execute NOTION_*` | `notion` productivity skill | MEDIUM |
| `composio execute LINEAR_*` | `linear` productivity skill | DONE |
| `composio execute DATADOG_*` | curl Datadog API | LOW |
| `composio execute SENTRY_*` | curl Sentry API | LOW |
| `composio link <app>` | native-mcp skill + OAuth | HIGH |
| `composio search <query>` | web_search 或 native-mcp | MEDIUM |
| `composio run --file <file>` | delegate_task + 子代理 | HIGH |
| `composio proxy <url>` | terminal(curl ...) | MEDIUM |

### MCP桥接替代方案

Hermes的 `native-mcp` skill + `mcporter` skill 构成替代基础:
1. `mcporter list` -> 替代 `composio search`
2. `mcporter call <server> <tool>` -> 替代 `composio execute`
3. native-mcp OAuth -> 替代 `composio link`

---

## 6. skill-creator元技能移植

Codex的 `skill-creator` 核心设计移植到Hermes:

### 核心原则
1. **Concise is Key** - 上下文窗口是公共资源
2. **设置合适自由度** - 高:纯文本 / 中:参数化 / 低:精确脚本
3. **渐进式披露** - 元数据->正文->资源三级加载

### Hermes Skill创建流程
```bash
# 1. 创建
skill_manage action=create name=<skill-name> content="..."

# 2. 添加文件
skill_manage action=write_file name=<skill-name> \
  file_path=scripts/xxx.py file_content="..."

# 3. 迭代修改
skill_manage action=patch name=<skill-name> old="..." new="..."
skill_manage action=edit name=<skill-name> content="..."

# 4. 读取验证
skill_view name=<skill-name>
```

### 命名规范
- 小写字母、数字、连字符
- 最多64字符
- 动词引导: `collect-wechat-enhanced`
- 工具命名空间: `github-code-review`

---

## 7. connect技能Hermes版

Codex的 `connect` 允许连接1000+应用。Hermes等效方案:

### 已有连接能力
- email (himalaya CLI)
- github (gh CLI)
- note-taking (obsidian)
- google-workspace
- notion, linear
- native-mcp (通用API)
- mcporter (MCP桥接)
- devices (蓝牙/MQTT/HTTP)
- smart-home (Hue)

### 连接决策树
```
请求外部操作
  -> 有native工具?   -> 使用对应skill
  -> 有MCP服务器?    -> mcporter call
  -> 有REST API?     -> terminal(curl)
  -> 无法直接操作    -> 生成文本/创建脚本
```

---

## 8. meeting-notes-and-actions移植

### 触发条件
用户提供会议转录/笔记/聊天记录，要求结构化纪要。

### 工作流
1. 输入收集: 源文本、标题、日期、参会人、输出偏好
2. 内容处理: 标准化文本、保留直接引语
3. 信息提取: Summary / Decisions / Open Questions / Risks / Action Items
4. 输出格式:
```markdown
# 会议纪要: {title}
**日期**: {date} | **参会**: {attendees}
## 摘要
{2-3句概述}
## 决策
- [x] {决策1}
## 未解决问题
- [?] {问题1}
## 风险/阻塞
- [!] {风险1}
## 待办事项
- [ ] {任务1} @张三 (截止: 2026-05-10)
```
5. 可选: 时间线 / Slack简报

### Hermes集成
- 结果保存到Obsidian: `note-taking` skill
- 待办推送: `pushplus-wechat` skill
- 决策归档: `hermes-archiver` skill

---

## 9. 技能市场分类与索引方案

### 三维分类法

```
维度1: 功能领域
- DEVELOPMENT / PRODUCTIVITY / COMMUNICATION
- DATA_ANALYSIS / OPERATIONS / INTELLIGENCE
- META / AUTOMATION

维度2: 工具依赖
- NATIVE / CLI / MCP / API / BRIDGE

维度3: 复杂度
- S (<50行) / M (50-200) / L (200-500) / XL (>500)
```

### 索引方案 (JSON)
```json
{
  "skills": [
    {
      "name": "github-pr-workflow",
      "category": "DEVELOPMENT",
      "tooling": "CLI",
      "complexity": "M",
      "tags": ["github", "pr", "review"]
    },
    {
      "name": "hermes-intelligence-system-v4",
      "category": "INTELLIGENCE",
      "tooling": "NATIVE",
      "complexity": "XL",
      "tags": ["collection", "pipeline"]
    }
  ]
}
```

### 当前Hermes技能分布 (~100 skills)
- INTELLIGENCE: ~25 | DEVELOPMENT: ~15 | PRODUCTIVITY: ~10
- CREATIVE: ~10 | OPERATIONS: ~8 | MLOPS: ~8
- EXPERT_SYSTEM: ~7 | AUTOMATION: ~6 | META: ~5 | RESEARCH: ~5

---

## 10. 迁移优先级

```
高价值+高难度: codebase-migrate, skill-creator, connect (Phase 1)
高价值+低难度: meeting-notes, gh-fix-ci, email-draft, changelog (Phase 2)
低价值+低难度: spreadsheet-helper, content-writer (Phase 3)
低价值+高难度: datadog, sentry, 800+ composio-automations (Phase 4)
```

### 决策树
```
值得迁移?
  -> Hermes已有等效?    YES=不迁移,映射即可
  -> 依赖Composio?      YES=需MCP桥接
  -> 纯指令无依赖?      YES=低优先级,直接推理
  -> 高频重复任务?      YES=高优先级,创建skill
  -> 比直接推理更好?    YES=迁移, NO=不迁移
```

---

## 11. 800+自动化技能批量处理

composio-skills/ 目录有800+统一模板技能:

```markdown
---
name: <appname>-automation
description: Automate <AppName> tasks via Rube MCP (Composio).
---
```

### 批量转换策略

1. **元迁移**: 创建脚本从awesome-codex-skills repo读取所有composio-skills
2. **按需加载**: 创建索引文件, Hermes需要时搜索
3. **MCP替代**: 安装composio MCP server后所有技能自动可用:
   ```bash
   mcporter call composio <TOOL_NAME> '{"args": ...}'
   ```

---

## 附录

### A. Hermes Skill分类 (按awesome-codex映射)

DEVELOPMENT: subagent-driven-development, test-driven-development, systematic-debugging, systematic-python-source-patching, requesting-code-review, github-code-review, github-pr-workflow, github-issues, writing-plans, plan, plugin-system-architecture

PRODUCTIVITY: note-taking/obsidian, email/himalaya, google-workspace, linear, notion, productivity, powerpoint, nano-pdf, ocr-and-documents

COMMUNICATION: xitter/xurl

DATA: data-science, jupyter-live-kernel

META: (此bridge填补空白)

### B. 参考资源
- github.com/ComposioHQ/awesome-codex-skills
- docs.composio.dev/docs/cli
- Hermes skill格式: `skill_view(software-development)`, `skill_view(autonomous-ai-agents)`
## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
