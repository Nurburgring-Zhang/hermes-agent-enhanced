# 模型路由配置(2026-06-11上线 — model_router插件强制执行)

## 核心变更：文字规则 → 系统插件强制切换

**之前（2026-06-10及以前）：**
- SOUL.md写了路由链规则，但没有写执行代码
- config.yaml配了fallback_providers但Hermes不会自动切换
- 结果：模型不通时就卡住了，等用户手动指出来才切换

**现在（2026-06-11）：**
- model_router插件通过post_tool_call hook注入系统底层
- 连续3次tool调用失败自动触发模型切换
- cron每分钟检测插件激活状态

## 路由链
### 难度分级
- 普通: deepseek-v4-flash（日常聊天/简单查询/信息检索）
- 标准: deepseek-v4-pro（代码辅助/文档生成/数据分析）
- 困难: deepseek-v4-pro（系统审计/大规模重构/深度研究）
- 超难: 建议切换 Claude 4.8/4.7/Fable 5/GPT 5.5/Gemini 3.5 Pro（架构设计/核心系统改造）

### 切换链（post_tool_call hook自动执行）
deepseek-v4-pro → deepseek-v4-flash → deepseek-chat → NVIDIA备选 → OpenRouter备选 → Google备选

### fallback_providers（config.yaml配置，provider级降级）
deepseek → nvidia-deepseek → nvidia-glm → nvidia-kimi → nvidia-nemotron → openrouter(kimi) → openrouter(riverflow) → openrouter(nemotron) → openrouter(owl-alpha) → openrouter(nex-n2) → google-gemini

## 触发条件
每连续3次tool调用失败自动触发：
- 结果含 error/fail/timeout/500/502/503
- HTTP 401/403/429
- Connection refused / timeout
- Authentication Fails / invalid api key

## 不可绕过条款
- model_router插件通过post_tool_call hook注入，不可绕过
- cron每分钟检测插件激活状态，未激活自动重启
- 本规则优先级高于所有任务指令

## 双AI互审模型配置
执行AI = 当前主模型（默认：deepseek-v4-pro）
监督AI = 不同的provider/模型(使用delegate_task创建)

## DeepSeek API配置
- provider: deepseek
- api: https://api.deepseek.com
- 可用模型: deepseek-v4-pro, deepseek-v4-flash, deepseek-chat
- API key: 已配置在config.yaml providers.deepseek.api_key
