# IMDF 全链路功能测试方法

## 测试原则

1. **不是测"API返回200"，是测"这个流程真的能产出可用的数据"**
2. **先做引擎层调用测试，再做HTTP层全链路测试**
3. **每次重启服务后必须检查扩展路由是否全部注册成功**

## 测试步骤

### Phase 1: 基础设施
```bash
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/
# 期望: 200
```

### Phase 2: 认证
```bash
# 注册
curl -s -X POST http://127.0.0.1:8765/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"Test123!","role":"admin"}'

# 登录（获取token）
curl -s -X POST http://127.0.0.1:8765/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"Test123!"}'
```

### Phase 3: 扩展路由验证
确认所有27条扩展路由都在openapi.json中：
```bash
curl -s http://127.0.0.1:8765/openapi.json | \
  python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d.get('paths',{})))"
```
如果扩展路由缺失，原因是 canvas_web.py 中 `include_router` 在 try/except 内，
导入异常时被静默捕获。检查 `from api.routes_extended import ...` 的变量名是否匹配。

### 常用变量名陷阱
```
routes_extended.py 中定义的 router 变量名 → canvas_web.py 中 import 的名字

crowd_router ✅ (common)
delivery_router ✅ 
review_router ✅
stats_router ✅
req_router ✅ (可能拼成 require_router ❌)
oss_router ✅

Mock类名：
  _MockObjectStore → 导入时需要 as MockObjectStore (因类是私有的 _ 开头)
  list_keys() → 不是 list() (方法名是 list_keys)
```

### Phase 4: 完整流程测试

| 顺序 | 端点 | 测试内容 |
|------|------|----------|
| 1 | POST /auth/register | 注册用户 |
| 2 | POST /auth/login | 登录获取token |
| 3 | POST /api/requirements/create | 创建需求 |
| 4 | GET /api/requirements/ | 需求列表 |
| 5 | POST /api/crowd/workers | 创建工人 |
| 6 | POST /api/crowd/teams | 创建团队 |
| 7 | GET /api/crowd/stats | 团队统计 |
| 8 | POST /engine/plan | 引擎规划 |
| 9 | POST /api/ppt/generate | PPT产出 |
| 10 | POST /api/chat | AI对话 |
| 11 | POST /api/video/generate | 视频产出 |
| 12 | POST /api/delivery/create | 创建交付 |
| 13 | GET /api/delivery/ | 交付列表 |
| 14 | POST /api/review/submit | 审核提交 |
| 15 | GET /api/review/ | 审核状态 |
| 16-18 | GET /api/stats/{daily,weekly,monthly} | 统计看板 |
| 19-23 | POST/GET /api/oss/* | OSS存储 |
