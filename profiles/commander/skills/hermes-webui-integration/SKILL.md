---
name: hermes-webui-integration
description: "集成第三方项目到Hermes Agent — webui/desktop/gbrain等，非Docker迁移"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, integration, webui, desktop, gbrain, non-docker]
    related_skills: [comfyui-node-development, github-repo-management]
---

# Hermes第三方项目集成

将第三方项目（尤其是 Claude Code / Hermes WebUI / Hermes Desktop / GBrain）集成到本地 Hermes Agent 环境，不依赖 Docker，全部迁移到原生环境。

## 通用原则

### 非Docker迁移

- 不允许使用 Docker 容器
- 所有代码迁移到原生 Python/Node.js 环境
- 通过 `scripts/` 下的启动脚本和 cron 保活实现

### 集成三步法

1. **分析** — 项目语言（Python/TS/JS）、依赖、入口文件、路径依赖
2. **复制** — cp -r 到 ~/.hermes/ 下的子目录（如 webui/）
3. **适配** — 配置环境变量指向本地路径，写启动脚本，加 cron 保活

### 典型路径适配

hermes-webui 通过 HERMES_HOME 环境变量定位配置，不需要改代码：
```bash
HERMES_HOME=$HOME/.hermes HERMES_WEBUI_PORT=8899 python3 server.py
```

## Hermes WebUI 集成

### 安装

```bash
cp -r /path/to/hermes-webui ~/.hermes/webui
cd ~/.hermes/webui
pip install pyyaml cryptography  # 仅两个依赖
```

### 启动

```bash
HERMES_HOME=$HOME/.hermes HERMES_WEBUI_PORT=8899 python3 server.py
```

自动发现 agent dir、config.yaml、workspace。自动监听 127.0.0.1:8899。

### 保活cron

```bash
# 每5分钟检查一次，崩溃自动重启
*/5 * * * * cd ~/.hermes && python3 scripts/webui_launcher.py >> logs/webui_launcher.log 2>&1
```

### 启动脚本 (scripts/webui_launcher.py)

```python
#!/usr/bin/env python3
import os, sys, subprocess, signal

HERMES_HOME = os.path.expanduser("~/.hermes")
WEBUI_DIR = os.path.join(HERMES_HOME, "webui")
PORT = "8899"
PID_FILE = os.path.join(HERMES_HOME, "webui.pid")

def is_running():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            pass
    return False

def start():
    if is_running():
        return
    env = os.environ.copy()
    env["HERMES_HOME"] = HERMES_HOME
    env["HERMES_WEBUI_PORT"] = PORT
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=WEBUI_DIR, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

def stop():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            os.remove(PID_FILE)
        except OSError:
            os.remove(PID_FILE)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop()
    else:
        start()
```

## GBrain 集成

### 安装

```bash
cd /path/to/gbrain
npm install --legacy-peer-deps  # 解决依赖冲突（package.json有大量peer dep冲突）
```

GBrain 是 TypeScript 项目（2364文件，50MB），依赖 `bun` 运行时。如果 bun 不在 WSL PATH 中（通常在 Windows npm 路径下），需要考虑只在 WSL 下安装 bun。

### Python桥接策略

对于重型 Node.js 项目（如 gbrain），不直接启动服务，而是创建一个 Python 桥接脚本：

1. **分析核心接口** — 从 `src/core/` 目录找到关键类（BrainRegistry, SearchEngine 等）
2. **创建 `scripts/gbrain_bridge.py`** — 暴露 Hermes 可调用的函数：
   - `search(query, limit)` → 返回搜索结果
   - `index_document(path, content)` → 索引文档
   - `list_sources()` → 列出数据源
3. **注册到 engine_core** — 在武器库扫描中标记为可用
4. **不用完整启动 Node.js 服务** — 除非用户明确需要实时检索能力

### 坑

- `npm install` 会报大量 peer dep 冲突，必须加 `--legacy-peer-deps`
- gbrain 的 `src/core/` 下可能有数百个 TS 文件，只提取核心检索类，不要试图全部 Python 重写
- MongoDB/PGLite 依赖可能需要在 WSL 额外安装

## Hermes Desktop 集成

Electron 桌面应用不能在 WSL 直接跑 GUI。提取纯逻辑模块：

### 可提取的模块（src/main/目录）

| 模块 | 文件 | 提取价值 | 
|------|------|---------|
| 会话管理 | `sessions.ts` | SQLite会话查询逻辑，可复用为Python session API |
| 技能管理 | `skills.ts` | 技能扫描/注册逻辑 |
| 提供商配置 | `providers.ts`, `provider-registry.ts` | 模型路由/提供商管理 |
| 安全 | `security.ts` | 安全策略检查 |
| SSH隧道 | `ssh-tunnel.ts`, `ssh-remote.ts` | 远程连接管理 |

### 提取方法

不直接翻译 TypeScript → Python（工作量太大）。策略：
1. 读懂 TS 源码的核心逻辑（主要是 SQLite 查询）
2. 用 Python 重写关键函数，直接操作 Hermes 的 SQLite 数据库
3. 注册到 `agent_enhancement_manager.py` 的 POST 插件中

### 坑

- hermes-desktop 使用了 `better-sqlite3` Node.js 绑定，不能直接在 Python 用
- Python 侧直接用 `sqlite3` 标准库操作同一个 DB 文件
- 会话查询模式需要从 TS 的 `Database.prepare().all()` 改为 Python 的 `cursor.execute().fetchall()`

## 故障排查

- WebUI 启动无输出？检查 HERMES_HOME 是否指向正确路径
- 8899端口被占用？改 PORT 变量
- Node.js 项目跑不起来？检查 npm install 是否成功
- 所有 crontab 路径用绝对路径，不要用 ~/

## Support Files

- `scripts/webui_launcher.py` — WebUI 自动启动/保活脚本（可直接复制到 ~/.hermes/scripts/ 使用）
- `references/gbrain-integration-notes.md` — GBrain 项目分析和集成策略详细笔记
- `references/2026-06-02-integration-session.md` — 本次三个项目集成的完整实战记录
