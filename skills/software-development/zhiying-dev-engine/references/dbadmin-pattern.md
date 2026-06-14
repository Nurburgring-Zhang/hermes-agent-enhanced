# 数据库管理后台实现模式（2026-06-15实战）

## 适用场景
在Vue3+FastAPI项目中添加Web数据库管理界面（对标phpMyAdmin）

## 架构
```
DBAdmin.vue（848行）
├── 左侧面板 — 表列表（el-table显示表名+行数）
├── 中央面板（el-tabs切换）
│   ├── 表结构 — el-table显示列名/类型/可空/默认值/主键
│   ├── 数据浏览 — el-table分页显示表数据，支持翻页
│   └── SQL查询 — el-input textarea + 执行按钮 + 结果el-table
└── 右侧面板 — 库信息（路径/大小/版本）+ 索引列表
```

## 后端API（6个端点）
```python
GET  /api/v2/db/tables                 # 表列表+行数
GET  /api/v2/db/tables/{name}          # 表结构(列/索引)
GET  /api/v2/db/tables/{name}/data     # 分页数据
POST /api/v2/db/query                  # SQL查询(只允许SELECT)
GET  /api/v2/db/info                   # 库信息
POST /api/v2/db/tables/{name}/index    # 创建索引
```

## SQL安全
- 只允许以SELECT开头的查询
- 使用参数化查询
- sqlite3.Row → dict 转换

## 路由注册
```
{ path: '/dbadmin', component: () => import('../pages/DBAdmin.vue') }
```
