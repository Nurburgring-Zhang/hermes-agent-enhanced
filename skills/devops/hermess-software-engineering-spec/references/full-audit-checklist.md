# 完整审计检查清单

## 执行顺序（先做这张清单，再做Step 6的其他工作）

### Phase 1: 语法检查（5分钟）
```bash
# 检查所有文件语法
find . -name "*.py" -not -path "*__pycache__*" -exec python3 -c "import py_compile; py_compile.compile('{}', doraise=True)" \;
# 期望: 全部通过, 0错误
```

### Phase 2: 导入检查（10分钟）
```bash
# 对每个关键模块执行真实导入
python3 -c "from api.auth_routes import AuthService; print('auth OK')"
python3 -c "from api.routes_extended import *; print('routes OK')"
python3 -c "from engines.* import *; print('engines OK')"  # 每个引擎单独测
# 期望: 所有import成功, 无模块级崩溃
```

### Phase 3: 跨文件一致性检查（10分钟）
```bash
# 检查导入名 vs 导出名
grep "from api.routes_extended import" api/canvas_web.py | tr ',' '\n' | while read name; do
  name=$(echo $name | xargs)
  grep -q "router = APIRouter\|$name = " api/routes_extended.py 2>/dev/null && echo "OK: $name" || echo "MISSING: $name"
done

# 检查POST端点Body()绑定
post_count=$(grep -c "@router.post\|@app.post" api/routes_extended.py)
body_count=$(grep -c "Body" api/routes_extended.py)
echo "POST端点: $post_count, Body绑定: $body_count"
test "$post_count" -eq "$body_count" && echo "OK" || echo "FAIL: 缺少Body()绑定"
```

### Phase 4: 启动检查（15分钟）
```bash
# 尝试启动（至少确保不立即崩溃）
timeout 5 python3 api/canvas_web.py --port 18765 2>&1 | head -5
# 期望: 打印"Starting at http://..."而不是Traceback
```

### Phase 5: HTTP端点测试（30分钟）
```bash
# 启动后curl每个路由
for path in / /auth/register /api/crowd/stats /api/requirements/create /api/stats/daily; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8765$path")
  echo "$code $path"
done
# 期望: 所有端点返回200/400/401(预期错误), 没有500
```

### Phase 6: 业务逻辑测试（20分钟）
```bash
# POST请求实际发送JSON body验证响应
curl -s -X POST http://127.0.0.1:8765/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"test123","role":"admin"}' | grep -q "username" && echo "注册OK"
# 其他POST类似
```

## 常见失败模式

1. **POST端点422/500**: 检查 `data: Dict[str, Any] = Body(...)` 而不是 `data: dict`
2. **启动后500**: 检查模块级import（`from X import Y` 在文件顶部，崩溃时整个服务挂）
3. **路由404**: 检查 `include_router` 中的变量名是否匹配实际的 `APIRouter` 变量名
4. **asyncio崩溃**: 不要在模块初始化用 `asyncio.create_task`（没有事件循环），用 `new_event_loop().run_until_complete()`
5. **bcrypt/passlib崩溃**: 用 `try: import passlib` 包裹或用纯 `hashlib` 替代
