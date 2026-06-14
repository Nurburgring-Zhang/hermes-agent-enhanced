# 审核陷阱v2 — 2026-06-11 新增

## 陷阱1: API端点签名验证缺失（高严重性）

**发现**：17个POST端点缺少 `Body()` 绑定。FastAPI 不会自动解析 JSON body。

**检查命令**：
```bash
for f in api/*.py; do
  posts=$(grep -c '@router.post\|@router.put' "$f" 2>/dev/null || echo 0)
  models=$(grep -c 'Body(' "$f" 2>/dev/null || echo 0)
  [ "$posts" -gt 0 ] && [ "$models" -lt "$posts" ] && echo "❌ $f"
done
```

## 陷阱2: 模型路由是规则不是执行代码

**发现**：SOUL.md 写了路由链规则但没有任何代码路径实际触发切换。
模型不通时系统不会自动切换——卡死直到用户指出。

**修复**：必须通过插件 hook 写入系统底层：
- `plugins/model_router/__init__.py` — post_tool_call hook 检测失败
- 连续3次失败自动按链切换
- cron 每分钟检测插件激活状态
- 规则写进 SOUL.md 不等于被执行

## 陷阱3: 审核不运行测试

**发现**：所有"审核"只读了代码——没有一次实际运行过测试。
读代码只能发现语法问题，无法发现运行时错误。

**修复**：
1. `import` 验证（不是只 `py_compile`）
2. 函数真实调用测试（`from x import y; print(y())`）
3. HTTP 端点 curl 测试
4. 前端浏览器交互验证
