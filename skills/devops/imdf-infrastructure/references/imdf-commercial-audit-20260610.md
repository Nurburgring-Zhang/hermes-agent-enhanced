# IMDF商用级补齐 — 2026-06-10 实战审计与修复

## 审核发现的Bug清单

### P0: 17个POST端点Body()绑定缺失
位置: api/routes_extended.py
症状: 所有POST端点返回500 Internal Server Error
根因: `def xxx(data: dict):` 未加`Body()`绑定, FastAPI无法解析JSON body
修复: `def xxx(data: Dict[str, Any] = Body(...)):`
涉及端点: create_worker, create_team, assign_task, create_delivery, submit_delivery, submit_review, approve_delivery, submit_algorithm, pre_review_algorithm, approve_algorithm, deploy_algorithm, create_requirement, assign_requirement, verify_requirement, close_requirement, oss_upload, oss_sync

### P0: 路由变量名不匹配
位置: api/canvas_web.py
症状: `from api.routes_extended import require_router` — 但实际变量名是`req_router`
修复: `from api.routes_extended import req_router`

### P0: bcrypt/passlib版本不兼容
位置: api/auth_routes.py
症状: 注册/登录返回500
根因: passlib 1.7.4 + bcrypt 4.2 不兼容
修复: 替换为纯hashlib实现 (salt:hex格式)

### P1: 数据库初始化无事件循环
位置: api/canvas_web.py
症状: "数据库初始化失败: no running event loop"
根因: `asyncio.create_task(init_db())` 在模块加载时没有事件循环
修复: `new_event_loop + run_until_complete`

### P2: 前端面板使用alert()占位
位置: api/canvas_web.py HTML_TEMPLATE
症状: 点击侧边栏按钮弹出alert提示而不是调用真实API
修复: 替换为真实的fetch调用

## 为什么审核没发现
1. 读了代码但没有运行
2. 只看了语法正确性
3. bcrypt import在模块级崩溃但单文件测试没触发

## 验证标准
```bash
curl -s http://localhost:8765/auth/register -X POST \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"test","role":"viewer"}'
# 期望: {"username":"test","role":"viewer","created_at":"..."}
```
