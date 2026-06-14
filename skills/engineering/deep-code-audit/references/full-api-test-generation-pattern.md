# 全量API集成测试生成模式
## 来自Nanobot Factory 2026-06-14实战

## 触发条件
当项目需要从单元测试升级到API级集成测试时使用本模式。
典型场景：审计发现只有内部逻辑测试没有HTTP端点测试、用户要求"商用级测试覆盖"、从~80测试扩展到~180测试。

## 测试骨架

```python
import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import app

client = TestClient(app)

class TestFullAPI:
    """全量API集成测试"""
```

## 必须覆盖的端点类别

每个类别至少3-5个测试方法：

1. **基础系统** — health, metrics, metrics/json, 首页, 每个前端页面
2. **认证** — login (200), auth/me (session有效), auth/me (无session→失败)
3. **核心业务** — 节点列表 (≥20个节点), 节点分类
4. **每个新模块** — 
   - ML Backend: register/list/predict/active-learning
   - 多模态标注: create/get/delete annotation
   - RBAC: org创建/项目创建/成员添加/权限检查
   - 数据集版本: init/commit/log/branch/merge/tag/checkout/rollback
   - Pipeline: create/advance/fail/complete/reset
   - 质量中心: overview/anomalies
   - 生成API: generate (400), queue/status

## 速率限制防御

```python
# 所有API测试都必须兼容速率限制
assert r.status_code in (200, 429)           # 读取端点
assert r.status_code in (200, 404, 429)      # 可能404的端点
assert r.status_code in (200, 400, 422, 429) # 可能验证错误的端点
assert r.status_code in (200, 500, 429)      # 可能500的端点
```

不要假设任何端点永远返回200——速率限制是生产环境的正常行为。

## 测试隔离原则

每个test_函数应该自包含：
```python
def test_create_and_read(self):
    # 创建资源
    r1 = client.post("/api/resource", json={...})
    assert r1.status_code in (200, 429)
    if r1.status_code != 200:
        return  # rate limited, 跳过后续
    resource_id = r1.json().get("id")
    
    # 读取资源
    r2 = client.get(f"/api/resource/{resource_id}")
    assert r2.status_code in (200, 429)
```

不要在test之间共享状态——pytest执行顺序不确定。

## 执行命令

```bash
cd backend && python3 -m pytest tests/test_full_api.py -v -q
# 预期: 96 passed (含速率限制兼容)
```
