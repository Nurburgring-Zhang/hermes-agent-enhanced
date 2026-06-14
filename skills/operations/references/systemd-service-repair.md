# Hermes Systemd Service 修复手册

## 常见失败模式

### 模式1: PYTHONPATH 未设置
**症状**: `ImportError: cannot import name '__version__' from 'hermes_cli' (unknown location)`
**原理**: Hermes 使用 `pip install -e .` 安装，hermes_cli 包在 site-packages 里只有 `.pth` 文件，systemd 启动时找不到。
**修复**: 在 `[Service]` 段加 `WorkingDirectory=/home/administrator/.hermes/hermes-agent`

### 模式2: venv 路径错误
**症状**: `ExecStart=` 或 `Environment=VIRTUAL_ENV=` 指向不存在的 `.venv/`（多了一个点）
**常见typo**: `.venv` vs `venv`
**修复**: 两个路径都要检查并纠正

### 模式3: 端口冲突
**症状**: `OSError: [Errno 98] Address already in use`
**常见原因**: 手动启动的进程占用了 systemd 要用的端口
**修复**: 先杀旧进程，或给 systemd 版本设不同端口（环境变量优先）

### 模式4: 重复安装（user + system）
**症状**: `⚠ Both user and system gateway services are installed`
**修复**: 保留一个，`sudo hermes gateway uninstall --system` 删掉 system 级别的

## 通用修复流程

```bash
# 1. 查看错误日志
journalctl --user -u hermes-gateway.service --no-pager -n 20

# 2. 确认当前状态
systemctl --user status hermes-gateway.service

# 3. 修改 unit 文件
# 文件在 ~/.config/systemd/user/hermes-<name>.service
# 修改后重载
systemctl --user daemon-reload
systemctl --user restart hermes-<name>.service

# 4. 验证
systemctl --user status hermes-<name>.service
# 期望: Active: active (running)
```

## Hermes 各服务的 unit 关键配置

### gateway (hermes-gateway.service)
```
WorkingDirectory=/home/administrator/.hermes/hermes-agent
ExecStart=/home/administrator/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace
```

### eternal (hermes-eternal.service)
```
WorkingDirectory=/home/administrator/.hermes
ExecStart=/home/administrator/.hermes/hermes-agent/venv/bin/python3 /home/administrator/.hermes/scripts/eternal_loop.py
```
注意：必须用 venv 的 python3，不是系统的 `/usr/bin/python3`

### webui (hermes-webui.service)
```
WorkingDirectory=/home/administrator/.hermes/webui
ExecStart=/home/administrator/.hermes/hermes-agent/venv/bin/python /home/administrator/.hermes/webui/server.py
Environment=HERMES_WEBUI_PORT=8890
```
端口通过 `HERMES_WEBUI_PORT` 环境变量覆盖（config.py 默认 8787）
