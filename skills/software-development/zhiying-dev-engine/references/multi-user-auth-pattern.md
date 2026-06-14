# 多用户系统完整实施模式

## 触发条件
用户要求"公开给所有人使用，每个账号独立管理自己的API Key，管理员管理权限和分配"

## 实施清单（5项缺一不可）

### 1. DB持久化用户存储
替换内存`users_db = {}` 为SQLite users表：
- 启动时 `_load_users()` 加载所有用户到内存
- 注册时 `_save_user(username, password_hash, role)` 同步写入SQLite
- `CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash, role, enabled, max_datasets, max_storage_mb, max_api_calls_per_day, created_at)`
- 迁移：新列用 ALTER TABLE 添加，try/except 容错

### 2. 用户自助API Key管理
每个用户只能管理自己的Key：
- `POST /api/v1/api-keys/create` → 只给当前登录用户生成Key（`imdf_sk-{32hex}`）
- `GET /api/v1/api-keys` → 只返回当前用户的Key
- `DELETE /api/v1/api-keys/{id}` → 吊销自己的Key，越权返回403
- API Key表加 `owner` 列关联username

### 3. 管理员用户管理路由
`api/admin_routes.py` — 7个端点：
- `GET /api/admin/users` — 管理员查看所有用户列表（含配额信息）
- `PUT /api/admin/users/{username}/role` — 修改角色，自我降级保护
- `PUT /api/admin/users/{username}/disable` — 启用/禁用用户，自我禁用保护
- `DELETE /api/admin/users/{username}` — 删除用户+吊销其API Key
- `GET /api/admin/stats` — 用户统计（按角色/状态）
- `GET/PUT /api/admin/users/{username}/quota` — 查看/设置配额

### 4. 权限矩阵中间件
`engines/permission_matrix.py`:
```python
PERMISSIONS = {
    "admin": ["*"],
    "reviewer": ["review","view","stats","export"],
    "annotator": ["annotate","view","upload"],
    "viewer": ["view"],
}
def check_permission(role, action) -> bool
def require_admin(current_user) -> None  # 非admin抛403
```

### 5. 前端配套
- `/login.html` — 独立登录/注册页（Dark Theme）
- JWT自动注入 — `api.js`中所有请求自动带 `Authorization: Bearer {token}`
- 401自动刷新 — `refreshAccessToken()` → 失败则 `redirectToLogin()`
- 管理员面板 — settings页面内的Admin Tab（仅admin角色可见）
- 用户设置 — API Key生成/吊销/复制，密码修改，配额使用

## 致命陷阱
- `_save_user()` 中变量名必须与register函数内一致（`password_hash` 不是 `hashed`），否则所有注册全部500
- users表必须与 `_load_users()` 的SELECT列顺序一致
- `create_admin.py` 写入SQLite → `auth_routes.py` 在启动时 `_load_users()` 加载，两者必须互通
