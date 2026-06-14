---
name: self-correction
description: 自我修正循环（Reflexion模式）。输出后立即自评，发现问题自动修正，记录失败模式供未来使用。
---

# Self-Correction（Reflexion模式）

## 何时使用
每次工具调用返回错误后。每次任务执行中发现输出不符合预期时。

## 修正循环

### 第一步：自评
- 输出是否符合预期？
- 是否有错误/异常/警告？
- 是否偏离了原始目标？
- 是否有更好的方式？

### 第二步：诊断
- 搜索fact_store/memory中是否有类似的失败模式
- 如果是已知模式，应用已知的修复策略
- 如果是新模式，记录到memory

### 第三步：修复
- 修正输出
- 重新验证

### 第四步：记录
- 将失败模式记录到memory
- 标记: what went wrong, why, how fixed
- 用于future sessions中避免相同错误

## 失败模式记录格式
```
[FAILURE PATTERN]
Symptom: xxx
Root cause: xxx
Fix applied: xxx
Prevention: xxx
```

## 已知失败模式库
参见 `references/common-failure-patterns.md` — 包含6种经过实战验证的故障模式及修复方案。
每次遇到新故障时，先查询此库。如果匹配，直接应用已知修复。如果不匹配，修复后添加新模式。
