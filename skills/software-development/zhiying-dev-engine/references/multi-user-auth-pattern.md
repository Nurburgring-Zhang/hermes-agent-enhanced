# 多用户统一认证+预设账号体系

## 场景

部署数据生产平台后需要预置多角色账号，供：
- 管理员（全部权限）
- 生产团队（主O/质检/生产人员）
- 众包团队（负责人/管理/质检/生产人员）
- 需求方（只能提需求/查看进度/审核交付）

## 账号体系（11类预设）

| 用户名 | 密码 | 角色 | 所属团队 |
|--------|------|------|---------|
| admin | Admin@2026! | admin | system |
| prod_lead | Prod@2026! | team_lead | production |
| qc_lead | QC@20261! | reviewer | production |
| prod_user1 | Prod1@2026! | annotator | production |
| prod_user2 | Prod2@2026! | annotator | production |
| prod_user3 | Prod3@2026! | annotator | production |
| crowd_lead | Crowd@2026! | team_lead | crowdsource |
| crowd_mgr | CrowdM@2026! | reviewer | crowdsource |
| crowd_qc | CrowdQ@2026! | reviewer | crowdsource |
| crowd_user1 | Crowd1@2026! | annotator | crowdsource |
| client1 | Client@2026! | viewer | client |

## 实现

### 统一认证模块 (backend/auth/unified_auth.py)
- JWT (PyJWT) + argon2密码哈希
- SQLite持久化 + WAL模式
- 角色：admin / team_lead / reviewer / annotator / viewer
- 兼容现有 auth_routes.py 接口

### 初始化脚本 (backend/scripts/init_accounts.py)
```bash
python scripts/init_accounts.py --reset  # 删除重建所有账号
python scripts/init_accounts.py --dry-run  # 预览不执行
```

### 认证路由 (backend/routes/auth_routes.py)
- POST /api/auth/login → JWT登录
- POST /api/auth/register → 注册
- POST /api/auth/refresh → token刷新
- GET /api/auth/me → 当前用户信息
- GET/PUT/DELETE /api/auth/users/* → 管理员用户管理

## 权限矩阵

| 操作 | admin | team_lead | reviewer | annotator | viewer |
|------|-------|-----------|----------|-----------|--------|
| 管理用户 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 创建任务 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 审核数据 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 标注数据 | ✅ | ✅ | ✅ | ✅ | ❌ |
| 查看进度 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 提需求 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 查看统计 | ✅ | ✅ | ✅ | ✅ | ✅ |
