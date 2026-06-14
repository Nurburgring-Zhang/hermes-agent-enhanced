# OpenClaw Smart Router - Hermes 集成指南

## 简介

OpenClaw Smart Router 是一个智能路由系统，能够根据用户指令自动选择最合适的 AI 模型。本指南说明如何将其集成到 Hermes 主系统中。

## 系统架构

```
┌─────────────────┐
│    Hermes CLI   │
└────────┬────────┘
         │ 消息处理
         ▼
┌─────────────────────────────┐
│   OpenClaw Smart Router     │
│   (智能路由系统)            │
├─────────────────────────────┤
│  1. AI Analyzer            │ ← 分析指令意图、复杂度
│  2. Model Selector         │ ← 选择最佳模型
│  3. Satisfaction Evaluator │ ← 评估满意度、升级决策
│  4. Routing Engine         │ ← 整合所有组件
└─────────────┬───────────────┘
              │ RoutingDecision
              ▼
┌─────────────────┐
│   AI 模型调用   │
└─────────────────┘
```

## 安装位置

系统文件已放置在：
```
~/.hermes/skills/openclaw-smart-router/
├── __init__.py           # 主入口
├── types.py              # 类型定义
├── models.py             # 模型注册表
├── ai_analyzer.py        # AI分析器
├── model_selector.py     # 模型选择器
├── satisfaction_evaluator.py
├── routing_engine.py
├── openclaw_adapter.py
├── config_loader.py
├── logger.py
├── cache.py
├── config.example.yaml   # 配置示例
└── test_router.py        # 测试套件
```

## 快速开始

### 1. 基本使用

```python
from openclaw_smart_router import SmartRouter, create_router

# 方法1: 使用快速路由
router = create_router()

# 方法2: 使用 SmartRouter 类（推荐）
router = SmartRouter()

# 路由指令
decision = router.route("用Python写一个快速排序算法")
print(f"选择模型: {decision.recommended_model.name}")

# 报告执行结果
router.report_execution(
    ExecutionResult(
        success=True,
        execution_time=2.5,
        tokens_used=1500
    )
)

# 提交反馈
router.submit_feedback(rating=4, comments="回答很好")
```

### 2. 配置自定义 AI 提供者

Hermes 系统需要提供 AI 调用接口给分析器：

```python
async def my_ai_provider(prompt: str) -> str:
    """自定义AI提供者 - 调用实际AI模型"""
    # 这里调用 Hermes 的 AI 接口
    response = await call_hermes_ai(prompt)
    return response

router = SmartRouter()
router.set_ai_provider(my_ai_provider)
```

### 3. 集成到消息处理流程

在 Hermes 的消息处理模块中集成智能路由：

```python
# hermes/message_handler.py (示例)

from openclaw_smart_router import SmartRouter

class HermesMessageHandler:
    def __init__(self):
        # 初始化智能路由器
        self.router = SmartRouter(
            config_path='~/.hermes/skills/openclaw-smart-router/config.yaml',
            ai_provider=self._call_ai_model  # 提供AI调用函数
        )

        # 可选：设置回调
        self.router.set_callbacks({
            'on_model_selected': self._on_model_selected,
            'on_upgrade_triggered': self._on_upgrade_triggered,
            'on_feedback_received': self._on_feedback_received
        })

    async def process_message(self, user_message: str, context: dict = None):
        """处理用户消息"""
        try:
            # 1. 智能路由 - 选择模型
            routing_context = RoutingContext(
                session_id=context.get('session_id', 'default'),
                conversation_history=context.get('history', []),
                preferences=UserPreferences(
                    preferred_tier=context.get('preferred_tier')
                )
            )

            decision = await self.router.route(user_message, routing_context)

            # 2. 使用决策的模型执行
            selected_model = decision.recommended_model
            self.logger.info(f"使用模型 {selected_model.name} 处理消息")

            response = await self._execute_with_model(
                model=selected_model,
                message=user_message
            )

            # 3. 报告执行结果
            self.router.report_execution(
                ExecutionResult(
                    success=True,
                    response=response,
                    execution_time=response.time,
                    tokens_used=response.tokens
                )
            )

            return {
                'response': response.text,
                'model_used': selected_model.id,
                'upgraded': decision.should_upgrade
            }

        except Exception as e:
            self.logger.error(f"消息处理失败: {e}")
            # 可以尝试使用后备模型
            return {'error': str(e)}

    def _on_model_selected(self, model):
        """模型选择回调"""
        self.logger.info(f"模型已选择: {model.name}")

    def _on_upgrade_triggered(self, reason):
        """升级触发回调"""
        self.logger.warning(f"模型升级触发: {reason}")

    def _on_feedback_received(self, feedback):
        """反馈接收回调"""
        self.logger.info(f"收到反馈: rating={feedback.rating}")

    async def _call_ai_model(self, prompt: str) -> str:
        """调用AI模型（用于分析器）"""
        # 这里实现实际的AI调用
        # 例如：response = await self.ai_client.chat(prompt)
        return "分析结果"  # 占位符

    async def _execute_with_model(self, model: ModelInfo, message: str):
        """使用指定模型执行"""
        # 这里调用实际的模型执行逻辑
        # 对应不同的模型提供商（OpenAI、Anthropic等）
        pass
```

## 配置说明

### 配置文件位置

默认搜索路径：
1. `./openclaw-router-config.yaml`
2. `~/.hermes/skills/openclaw-smart-router/config.yaml`
3. `/etc/openclaw-router/config.yaml`

### 配置示例

请参考 `config.example.yaml` 文件，主要配置项：

```yaml
# 默认模型
default_free_model: claude-3-haiku
default_standard_model: gpt-4o
default_premium_model: claude-3.5-sonnet-20241022

# 升级策略
auto_upgrade_enabled: true
upgrade_threshold: 3  # 评分低于3自动升级

# 可用模型列表
models:
  - claude-3-haiku
  - gpt-4o-mini
  - gemini-1.5-flash
  - gpt-4o
  - claude-3-opus
  # ...

# 日志
log_level: info
log_file: /var/log/openclaw/router.log
```

### 环境变量覆盖

支持通过环境变量覆盖配置：

- `OPENCLAW_LOG_LEVEL` - 日志级别
- `OPENCLAW_ENABLE_CACHE` - 是否启用缓存
- `OPENCLAW_AUTO_UPGRADE` - 是否自动升级
- `OPENCLAW_UPGRADE_THRESHOLD` - 升级阈值
- `OPENCLAW_CACHE_EXPIRATION` - 缓存过期时间（秒）

## 高级功能

### 1. 用户偏好定制

```python
prefs = UserPreferences(
    preferred_tier=ModelTier.FREE,  # 偏好免费模型
    max_cost=0.01,                  # 最大成本 $0.01/1M tokens
    preferred_language='中文',
    exclude_models=['gpt-4-turbo'],  # 排除特定模型
    always_premium=False
)

context = RoutingContext(
    user_id='user123',
    session_id='session456',
    preferences=prefs
)

decision = await router.route(message, context)
```

### 2. 性能统计和监控

```python
# 获取详细统计
stats = await router.get_statistics()
print(f"总任务数: {stats['total_tasks']}")
print(f"成功率: {stats['success_rate']}%")
print(f"平均满意度: {stats['average_satisfaction']}")

# 模型分布
for tier, count in stats['model_distribution'].items():
    print(f"  {tier}: {count}")

# 健康检查
health = await router.health_check()
print(f"健康状态: {health['healthy']}")
if not health['healthy']:
    print(f"问题: {health['issues']}")
```

### 3. 配置热重载

```python
from openclaw_smart_router import ConfigLoader

# 配置文件修改后自动重载
loader = ConfigLoader(
    config_path='config.yaml',
    auto_reload=True  # 启用文件监视
)

# 手动触发重载
loader.reload_config()

# 或者动态更新配置（不持久化）
loader.update_config({
    'auto_upgrade_enabled': False,
    'log_level': 'debug'
})
```

### 4. 缓存管理

```python
router = SmartRouter()

# 获取缓存统计
cache_stats = router.router.get_analyzer().get_cache_stats()
print(f"缓存大小: {cache_stats['size']}")
print(f"命中率: {cache_stats['hit_rate']}")

# 清空缓存
router.router.get_analyzer().clear_cache()
```

### 5. 强制模型切换

```python
# 切换到特定模型
success = await router.switch_model('gpt-4o')
if success:
    print("模型切换成功")
```

### 6. 会话历史管理

```python
# 获取会话历史
history = await router.get_history(session_id='session123')
for record in history:
    print(f"任务: {record.user_instruction[:50]}...")
    print(f"  选择: {record.routing_decision.recommended_model.name}")
    print(f"  成功: {record.execution_result.success if record.execution_result else 'N/A'}")
```

## 测试验证

运行测试套件验证系统功能：

```bash
cd ~/.hermes/skills/openclaw-smart-router
python test_router.py
```

测试覆盖：
- 功能测试：15个测试用例，覆盖各类型的指令路由
- 集成测试：6个集成场景
- 性能测试：20次迭代

预期结果：
- 功能准确率 >= 90%
- 所有集成测试通过
- 平均路由延迟 < 1秒

## 故障排除

### 问题1: "No AI provider configured"

**原因**: 未设置 AI 提供者

**解决**:
```python
router = SmartRouter()
router.set_ai_provider(your_ai_function)
```

### 问题2: 模型选择不准确

**可能原因**:
- 分析器置信度低
- 模型能力配置不匹配

**解决**:
1. 提供更好的分析提示词
2. 调整 `min_confidence_for_tier_escalation` 配置
3. 检查模型能力标记是否正确

### 问题3: 配置文件不生效

**检查**:
- 配置文件路径是否正确
- YAML 语法是否正确
- 权限是否正确

**解决方案**:
```python
loader = ConfigLoader('/path/to/config.yaml')
print(loader.get_config())
```

### 问题4: 热重载不工作

**原因**: watchdog 包未安装

**解决**:
```bash
pip install watchdog
```

或禁用热重载：
```python
loader = ConfigLoader(auto_reload=False)
```

## 性能优化建议

1. **启用缓存**: `enable_cache: true`（默认开启）
2. **减少分析复杂度**: 对于简单指令使用规则回退
3. **批量处理**: 对多个指令可以批量分析
4. **监控缓存命中率**: 保持缓存命中率 > 70%

## 与 Hermes 集成的建议

### 位置建议

在 Hermes 代码库中的集成位置：

```
hermes/
├── core/
│   ├── message_processor.py  # ← 在这里集成路由调用
│   └── ai_client.py          # ← AI模型调用
├── skills/
│   └── openclaw-smart-router/  # ← 本系统
└── config/
    └── router.yaml              # ← 全局配置
```

### 改动建议

在 `message_processor.py` 中添加：

```python
from skills.openclaw_smart_router import SmartRouter

class MessageProcessor:
    def __init__(self):
        self.router = SmartRouter(
            config_path='~/.hermes/config/router.yaml',
            ai_provider=self.ai_client.analyze_intent
        )

    async def process(self, message, user_context):
        # 获取路由决策
        decision = await self.router.route(message, user_context)

        # 根据决策选择AI模型
        model_id = decision.recommended_model.id
        response = await self.ai_client.chat(message, model=model_id)

        # 收集反馈（用户对回复的评价）
        self.collect_user_feedback(...)

        return response
```

## 总结

OpenClaw Smart Router 提供了：

- ✅ 完整的智能路由功能
- ✅ 高可扩展性（可通过AI提供者自定义）
- ✅ 配置热重载
- ✅ 完整的日志和监控
- ✅ 缓存机制
- ✅ 满意度驱动的自动升级
- ✅ 易于集成到 Hermes

如需进一步支持，请查阅源代码注释或联系开发团队。
