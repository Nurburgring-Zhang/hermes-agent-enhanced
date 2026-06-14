# OpenClaw Smart Router for Hermes

智能路由系统 - 自动为AI任务选择最优模型

## 模块清单

✅ **13个核心模块** 全部实现：

1. **types.py** - 完整的数据类型定义（数据类、枚举）
2. **models.py** - 模型注册表（13个预配置模型）
3. **logger.py** - 支持颜色、多级别的日志系统
4. **cache.py** - 带LRU和过期清理的缓存系统
5. **config_loader.py** - 配置加载器 + 热重载支持
6. **ai_analyzer.py** - AI指令分析器（含规则回退）
7. **model_selector.py** - 智能模型选择器（能力匹配、成本优化）
8. **satisfaction_evaluator.py** - 满意度评估和升级决策
9. **routing_engine.py** - 核心路由引擎
10. **openclaw_adapter.py** - OpenClaw集成适配器
11. **__init__.py** - 主入口，提供SmartRouter类
12. **config.example.yaml** - 配置示例
13. **test_router.py** - 完整测试套件

 additionally:
 - **INTEGRATION.md** - 详细集成指南
 - **demo.py** - 演示脚本

## 核心功能

### ✅ 指令分析
- 意图识别：13种任务意图
- 复杂度评估：4个级别
- 能力需求提取
- AI分析 + 规则回退双保险

### ✅ 模型选择
- 免费优先策略
- 能力匹配过滤
- 成本优化
- 智能评分排序
- 失败重试机制

### ✅ 满意度驱动
- 用户反馈收集
- 连续不满意检测
- 自动升级建议
- 性能趋势分析

### ✅ 配置管理
- YAML配置文件
- 热重载支持（文件监视）
- 环境变量覆盖
- 动态配置更新

### ✅ 日志与监控
- 多级别日志（debug/info/warn/error）
- 彩色终端输出
- 文件日志支持
- 详细统计信息

### ✅ 缓存系统
- LRU缓存策略
- TTL过期清理
- 容量限制
- 命中率统计

## 快速使用

```python
from openclaw_smart_router import SmartRouter

# 创建路由器
router = SmartRouter()

# 路由指令
decision = router.route("用Python写快速排序")
print(f"选中: {decision.recommended_model.name}")

# 报告结果
router.report_execution(
    ExecutionResult(success=True, execution_time=2.5)
)

# 提交反馈
router.submit_feedback(rating=4, comments="很好")
```

详细使用请参阅 `INTEGRATION.md`。

## 测试

运行测试套件：

```bash
cd ~/.hermes/skills/openclaw-smart-router
python3 test_router.py
```

测试包括：
- 15个功能测试用例
- 6个集成测试
- 20次性能测试迭代

**目标：准确率 >= 90%**

## 配置示例

```yaml
# ~/.hermes/skills/openclaw-smart-router/config.yaml
default_free_model: claude-3-haiku
auto_upgrade_enabled: true
upgrade_threshold: 3
models:
  - claude-3-haiku
  - gpt-4o-mini
  - gemini-1.5-flash
  - gpt-4o
  - claude-3-opus
log_level: info
```

## 架构亮点

1. **异步友好** - 全面 async/await 支持
2. **线程安全** - 关键操作加锁保护
3. **可扩展** - 插件化设计，易于添加新模型
4. **生产就绪** - 完整的错误处理、日志、统计
5. **零外部依赖** - 仅标准库（除可选的watchdog用于热重载）

## 与Hermes集成

参考 `INTEGRATION.md` 文件，包含：
- 集成架构图
- 消息处理流程集成
- 配置详细说明
- 高级功能使用
- 故障排除指南

## 文件说明

```
~/.hermes/skills/openclaw-smart-router/
├── __init__.py              # 主入口，SmartRouter类
├── types.py                 # 类型定义
├── models.py                # 模型注册表
├── ai_analyzer.py           # AI分析器
├── model_selector.py        # 模型选择器
├── satisfaction_evaluator.py # 满意度评估器
├── routing_engine.py        # 路由引擎
├── openclaw_adapter.py      # OpenClaw适配器
├── config_loader.py         # 配置加载器
├── logger.py                # 日志系统
├── cache.py                 # 缓存系统
├── config.example.yaml      # 配置示例
├── test_router.py           # 测试套件
├── demo.py                  # 演示
├── INTEGRATION.md           # 集成文档
└── README.md                # 本文件
```

## 验证检查清单

✅ 所有 TypeScript 源码已转换为 Python
✅ 完整功能实现（无简化）
✅ 配置文件系统
✅ 热重载支持
✅ 日志系统
✅ 缓存机制
✅ 错误处理
✅ 性能统计
✅ 反馈收集
✅ 测试用例
✅ 集成文档

## 版本

版本: 1.0.0
兼容: Hermes CLI
Python: 3.9+

---

**OpenClaw Smart Router** - 让AI模型选择更智能
