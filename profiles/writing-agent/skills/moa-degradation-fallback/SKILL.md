---
name: moa-degradation-fallback
description: MoA(多智能体编排)工具使用OpenRouter模型失败时的降级处理配置知识。记录失败模式和回退策略
category: operations
tags: [operations, moa, degradation, fallback, openrouter]
---

# moa-degradation-fallback

## 问题描述

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

MoA工具连续调用OpenRouter模型失败。检查.env中`OPENROUTER_API_KEY`状态和信用额度。

## 降级策略

### 1. 检查MoA状态
MoA工具位于：`/home/administrator/.hermes/hermes-agent/tools/`
检查 .env 中的 `OPENROUTER_API_KEY` 是否有效：
```bash
curl -s https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | python3 -m json.tool
```

### 2. 降级配置
当OpenRouter不可用时，系统自动降级：
1. **跳过MoA调用** — 工具直接返回fallback结果而非崩溃
2. **使用辅助LLM** — 通过`auxiliary_client`使用其他可用模型
3. **记录失败次数** — 若24h内失败>5次，暂停MoA尝试，等待下次演化报告

### 3. recovery检查
检查cron健康度和自愈状态：
```bash
grep -i "moa\|openrouter\|api_key" /home/administrator/.hermes/logs/agent.log | tail -20
```

### 4. 当前状态 (2026-05-08)
- MoA工具参考模型调用失败次数: 5次/24h
- OpenRouter API Key: 存在于.env中（掩码状态）
- 处理: 已配置降级跳过MoA调用，系统不依赖于MoA运行

### 5. 已知OpenRouter模型失败模式 (2026-05-08更新)
从 errors.log 分析发现以下模型不可用模式：
| 模型 | 错误码 | 原因 |
|---|---|---|
| openai/gpt-5.4-pro | 403 | 区域限制 (not available in your region) |
| google/gemini-3-pro-preview | 404 | 端点不存在 (no endpoints found) |
| anthropic/claude-opus-4.6 | 403 | 区域限制 (not available in your region) |
| deepseek/deepseek-v3.2 | 402 | 信用不足 (needs more credits) |
| 图片分析模型 | 403 | 区域限制 |

**建议**: 移除以上不可用模型引用，或替换为可用模型如 deepseek-chat、deepseek-reasoner。

## 长期方案
当OpenRouter恢复后，清理fallback配置并重新激活MoA。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
