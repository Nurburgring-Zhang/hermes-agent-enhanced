# GBrain 集成笔记（2026-06-02）

## 项目概况
- 仓库: garrytan/gbrain
- 语言: TypeScript
- 大小: 50MB, 2364文件
- 运行环境: Bun (不是 Node.js)
- 核心依赖: @ai-sdk/anthropic, @ai-sdk/openai, @electric-sql/pglite, express
- Star: 20405

## 安装过程
```bash
git clone --depth 1 https://github.com/garrytan/gbrain.git
cd gbrain
npm install --legacy-peer-deps  # 必须加 --legacy-peer-deps
```

## 架构（从 AGENTS.md / src/core 分析）

### CLI 入口
- `src/cli.ts` — 使用 bun 运行
- 构建: `bun build --compile --outfile bin/gbrain src/cli.ts`

### 核心引擎
- `src/core/brain-registry.ts` — BrainRegistry 类
- `src/core/brain-resolver.ts` — 检索解析
- `src/core/pglite-engine.ts` — PGLiteEngine (本地轻量引擎)
- `src/core/postgres-engine.ts` — PostgresEngine (生产引擎)
- `src/core/operations.ts` — 操作注册表

### MCP 服务
- `src/mcp/server.ts` — MCP 协议服务，暴露给 Agent 调用

## 集成到 Hermes 的策略

### 方案A：完整部署（推荐）
1. 安装 bun（curl -fsSL https://bun.sh/install | bash）
2. gbrain init 初始化知识库
3. 启动 MCP 服务
4. Hermes 通过 MCP 协议调用

### 方案B：Python 桥接（轻量）
创建 scripts/gbrain_bridge.py，暴露 search/index/list 三个函数。
本质上是用 Python 调用 gbrain 的 CLI 命令并解析输出。

## 当前状态
- 代码已 clone 到 /mnt/m/Hermes/integrations/gbrain/
- npm install 完成
- Python 桥接脚本骨架已创建但未实现
- bun 安装在 Windows 路径，WSL 不可用
