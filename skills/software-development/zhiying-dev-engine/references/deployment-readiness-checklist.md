# IMDF商用级部署就绪模式 (2026-06-16实战固化)

## 部署就绪检查清单

当项目达到"商用级"时，必须包含以下部署配置（不是"后续再补"）：

### 必须交付的部署文件
1. **systemd服务** — `deploy/imdf.service`
   - Type=simple, Restart=always, RestartSec=5
   - ProtectSystem=strict, NoNewPrivileges=yes
   - 明确指定ReadWritePaths（只允许写数据和日志目录）

2. **nginx配置** — `deploy/nginx-imdf.conf`
   - HTTP→HTTPS重定向
   - SSL证书配置（Let's Encrypt路径）
   - 安全头: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
   - 静态文件由nginx直接serve（/css/, /js/），减轻后端压力
   - 大文件上传限制(client_max_body_size 500M)
   - WebSocket升级支持

3. **CORS中间件** — 在FastAPI app创建后立即添加
   - allow_origins=["*"] 仅开发环境
   - 生产部署时改为具体域名

4. **环境变量模板** — `.env.example`
   - 所有必需的环境变量列表
   - SECRET_KEY/API_KEY等敏感字段用占位符
   - 每个变量的用途注释

5. **部署指南** — `deploy/DEPLOY.md`
   - 3步快速部署（pip install → systemd → nginx）
   - 安全清单（修改JWT密钥/配置HTTPS/限制CORS）
   - 验证命令

### 部署后验证
- `systemctl status imdf` → Active: active (running)
- `curl https://domain/api/health` → {"status":"ok"}
- `curl -I -H "Origin: https://domain" https://domain/` → access-control-allow-origin
- 核心API端点全部可访问
