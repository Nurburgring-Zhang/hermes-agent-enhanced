# 模型路由策略

## 命名约定（格林主人偏好）

代码/文档中使用**抽象梯队名称**，不用具体模型名：

| 文档中 | 含义 |
|:-------|:-----|
| `model_tier="value"` | 通用省钱模型 |
| `model_tier="performance"` | 强力高质量模型 |

严禁在文档/Skill中使用具体模型名。具体模型通过config.yaml配置。

## 梯队定义

| 梯队 | 适用任务 |
|:------|:-------------|
| value | 检索/查询/单步操作/状态检查 |
| balanced | 修复/推送/普通分析/开发 |
| performance | 复杂推理/长链/架构设计/高精度 |

## 关键规则：代码任务用最强模型

格林主人2026-06-01纠正：代码开发任务应该使用最强可用模型，不是切换到代码专用模型。

错误做法：
```python
# ❌ 不要切换到代码专用模型
if "code" in task_type:
    model = "deepseek-coder"
```

正确做法：
```python
# ✅ 代码任务走performance梯队
if "code" in task_type or "develop" in task_type:
    pass  # 保持最强可用模型
```

## 复杂度判定维度

1. 关键词密度(35%): 分布式/共识/加密/安全/架构等高复杂关键词占比
2. 逻辑深度(30%): if/else/for/while/递归/并行/条件句
3. 代码比例(20%): 代码块数量
4. 长度因子(15%): 字符数/500标准化

## 配置路径

- 模型定义: config.yaml → custom_providers
- 路由引擎: agent/model_router.py
- 调用: llm_bridge.llm_call(model_tier="value"|"performance")
