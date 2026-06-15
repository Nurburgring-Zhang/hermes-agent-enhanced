# 部署验证E2E协议

> 来源: 2026-06-15 Hermes Agent Enhanced 部署验证实战
> 12/13 PASS (92.3%) — 三阶段验证框架

## 三阶段部署验证

### Phase 1: 部署路径验证

```bash
# 1. 安装脚本路径
bash -n install.sh                    # 语法检查
grep -n "SCRIPT_DIR" install.sh       # 所有$引用路径

# 2. Cron任务脚本存在性
cat config/crontab_backup.txt | while read line; do
  script=$(echo "$line" | grep -oP 'scripts/\S+\.py')
  test -f "$script" && echo "✅ $script" || echo "❌ MISSING: $script"
done

# 3. Systemd服务路径
for s in services/*.service; do
  grep -E "ExecStart|WorkingDirectory" "$s"
  # 手动验证每个路径存在
done

# 4. 依赖完整性
pip install --dry-run . 2>&1 | tail -5
```

### Phase 2: 子系统E2E运行时验证

按顺序启动每个子系统并验证真实输出：

```python
# 1. 规则引擎 — 确认规则激活
from scripts.rule_enforcer import SdlcEnforcer
r14 = SdlcEnforcer()
assert r14 is not None

# 2. 弹性模式 — 状态转移
from scripts.resilience_patterns import CircuitBreaker
cb = CircuitBreaker(name='test')
for _ in range(5): cb.record_failure()
assert cb.state.name == 'OPEN'

# 3. Loop引擎 — 完整生命周期
from scripts.loop_engine import LoopEngine
engine = LoopEngine()
result = engine.register_loop({...})
# 验证: 创建→执行→检查点→恢复

# 4. API网关 — HTTP响应
from scripts.api_gateway import app
# curl http://localhost:8000/health → 200

# 5. 安全链 — 拦截/放行
from scripts.security_sandbox import SecuritySandbox
s = SecuritySandbox()
r, msg = s.check('write_file', '/etc/passwd')
assert r == False and 'BLOCKED' in msg
```

### Phase 3: 故障注入

```python
# 1. 熔断器强制断开
cb = CircuitBreaker(name='fault_test')
for _ in range(5): cb.record_failure()
assert cb.state.name == 'OPEN'

# 2. 文件保护
# 尝试写入/etc/passwd → 应返回BLOCKED

# 3. 检查点恢复
# 创建→写入→模拟崩溃→恢复→验证状态一致
```

### 压力测试协议

```bash
# 3轮稳定性测试
for i in 1 2 3; do
  echo "=== Round $i ==="
  time python3 -m pytest scripts/ -q --tb=no
done

# 内存泄漏检测（100次创建/销毁）
python3 -c "
import tracemalloc; tracemalloc.start()
# ... 100x create/destroy ...
snapshot = tracemalloc.take_snapshot()
print(f'Memory: stable' if <threshold else 'LEAK DETECTED')
"
```

## 常见失败模式

| 失败 | 根因 | 修复 |
|------|------|------|
| pip install超时 | WSL+PEP 668+30+依赖 | --break-system-packages |
| cd in subprocess | cmd.split()不展开shell | 用cwd=参数 |
| test_*.py glob失败 | subprocess不展开glob | 用Python glob显式列出 |
| AttributeError on None | 状态未初始化 | 添加None guard |
| subagent timeout 600s | 依赖解析/网络请求 | 缩小scope, 拆分agent |
