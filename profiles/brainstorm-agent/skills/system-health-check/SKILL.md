---
name: full-link-audit-and-fix
description: 极端严苛的全链路系统审计与修复 — 对自称"全自动AI驱动"的系统逐环节审计，发现并修复虚假实现/降级实现/硬编码模板冒充AI
category: governance
tags: [audit, system-test, quality-assurance, full-link]
---

# 全链路审计与修复方法论

对系统做极端严苛的逐环节审计，发现每个环节的真实运行状态，修复虚假实现。

## 适用场景

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


- 系统自称"全自动AI驱动"但实际执行效果存疑
- 需要验证从采集→清洗→AI评分→推送→需求挖掘→产品生成→测试→交付的完整链路
- 怀疑存在规则替代AI、硬编码模板冒充AI生成的虚假实现
- 审计要求"极端严苛"、"逐行审查"、"不依赖记忆"
- 格林主人要求：禁止降级实现、禁止仅作示例、禁止占位符、禁止只写核心代码

## 审计方法论(7步)

### 第1步：不依赖记忆——系统实际状态扫描

**禁止**直接凭记忆或旧报告下结论。必须做：

1. **查文件系统** — `ls -la ~/.hermes/scripts/`, `ls -la ~/.hermes/agents_company/`
2. **查数据库** — `sqlite3 ~/.hermes/intelligence.db` 看实际记录数、表结构、字段值
3. **查日志** — `cat/logs/*.log | tail -30` 看最近运行记录
4. **查crontab** — `crontab -l` 看实际调度
5. **查.env** — 看API key是否真存在、真可用

### 第2步：逐环节分类审计

| 环节 | 审计重点 | 常见陷阱 |
|------|---------|---------|
| 采集 | 是否有真数据入库？最近采集时间？静默源？ | 采集器存在但已死亡多天 |
| 清洗 | 过滤规则是否合理？去重逻辑是否正常？ | 重复数据漏网/白名单过宽 |
| AI评分 | **是否真的调用了AI API？** 看日志中"⚠️ 未配置API密钥" | **最常见虚假实现**：规则关键词匹配冒充AI |
| 推送 | 推送记录？PushPlus真实调用？ | 基于假评分排序 |
| 需求挖掘 | 是AI理解还是标签统计聚合？ | 统计聚合冒充AI需求生成 |
| 产品生成 | **是否真的调用了AI API？** 看product_spec是否硬编码 | **最常见虚假实现**：固定模板冒充AI生成 |
| 测试迭代 | 验收标准？多工况测试？ | 整个环节缺失 |
| 交付 | 交付物是否真实？ | 整个环节缺失 |

### 第3步：AI评分API key连接验证

这是最常见断裂点。验证流程：

```bash
# 1. 检查.env文件
cat ~/.hermes/.env | grep API_KEY

# 2. 检查环境变量（cron子进程不继承.env）
python3 -c 'import os; print(os.environ.get("OPENROUTER_API_KEY",""))'

# 3. 脚本必须手动加载.env（关键修复）
_env_path = HERMES / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if _line and "=" in _line and not _line.startswith("#"):
            k, v = _line.split("=", 1)
            if v.strip() and v.strip() != "***" and k not in os.environ:
                os.environ[k] = v

# 4. 真正调用API验证
response = call_openrouter("deepseek/deepseek-chat", "短暂测试")
# 确认返回非空、非402/400
```

**API key优先级**：DEEPSEEK_API_KEY → OPENROUTER_API_KEY → ANTHROPIC_API_KEY → OPENAI_API_KEY

### 第4步：产品生成真实性验证

查看production_auto.py中的输出是否是真正的AI响应：

```python
# ❌ 假AI模式（硬编码）：
product_spec['product_spec']['features'] = ['AI驱动的情报深度分析', ...]  # 永远一样
product_spec['product_spec']['tech_stack'] = ['Python', 'Hermes Agent']  # 永远一样

# ✅ 真AI模式：
ai_response = call_ai_api(prompt, system_msg, timeout=120)  # 真正调用LLM
product_spec = json.loads(ai_response)  # 解析AI返回
```

### 第5步：修复断裂点

| 断裂类型 | 修复方案 |
|---------|---------|
| 无API key | 1. 从.env加载 2. 写.env自动加载代码到脚本中 3. 多路key搜索 |
| AI评分是规则替代 | 添加.env加载 → 调用OpenRouter/DeepSeek → 解析JSON评分 → 写入DB |
| 产品是硬编码 | 重写为call_ai_api → 精简prompt控制token消耗 → 解析JSON → 写入产出 |
| 无测试交付 | 新建三层验收模块(语法+语义+一致性) + 交付物生成 + 交付数据库 |
| 无cron集成 | 添加cron条目：每小时/每天/每4小时 |

### 第6步：资源限制下分层策略

当AI API有余额限制(如OpenRouter仅支持~1500 output tokens)：

1. **按内容长度降序取** — 优先评内容最丰富的条目（最有价值）
2. **每批2条** — 短prompt避免402
3. **max_tokens=600** — 控制输出成本
4. **设置cron每4小时** — 持续渐进回填
5. **添加--high-value模式** — 每次只评6条最重要的

### 第7步：极端严苛测试

编写全链路测试脚本，包含：

- AI评分功能测试（真正调用API）
- 产品生成功能测试（真正AI方案）
- 交付验收功能测试（三层验收）
- 多工况测试（API不可用/空数据/极端分数等）
- 端到端集成测试（cron存在性/数据流完整性）
- 性能边界测试（超时控制/重试机制/环境变量脱敏）

目标：95%+通过率

## 代码示例

### .env自动加载片段

```python
_env_path = HERMES / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _k, _v = _k.strip(), _v.strip()
            if _v and _v != "***" and _k not in os.environ:
                os.environ[_k] = _v
```

### 多路API key搜索

```python
key = os.environ.get("DEEPSEEK_API_KEY", "")
if key: return (key, "https://api.deepseek.com/v1/chat/completions", "deepseek-chat")
key = os.environ.get("OPENROUTER_API_KEY", "")
if key: return (key, "https://openrouter.ai/api/v1/chat/completions", "deepseek/deepseek-chat")
```

### 三层验收结构

```python
def verify_syntax(product): ...  # JSON结构完整性
def verify_semantic(product): ...  # AI评估方案质量
def verify_consistency(product): ...  # 方案与源情报匹配度
```

### 全链路测试模板

```python
TOTAL_TESTS = 0; PASSED_TESTS = 0; FAILED_TESTS = []
def test(name, condition, detail=""):
    ...
# 6个section × 51个用例
```

## 关键陷阱

- **402 Payment Required** — OpenRouter余额不足时出现，降低max_tokens和batch_size
- **子进程.env不可见** — cron/子进程不继承Hermes加载的.env，必须脚本内手动加载
- **"规则评分"冒充"AI评分"** — 日志中搜索"⚠️ 未配置API密钥"、"增强规则评分替代"
- **硬编码产品方案** — 检查production_auto.py中product_spec是否包含固定列表的features/tech_stack
- **一致性验收误报** — 中文关键词重叠低，需要放宽阈值或考虑语义相似度

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
