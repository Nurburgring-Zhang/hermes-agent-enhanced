# 证据驱动Skill进化模式总结

来自 hermes-curator-evolver (pingchesu) + SkillClaw (AMAP-ML) 源码分析, 2026-05-30

## hermes-curator-evolver 核心模式

### 1. 证据收集无侵入模式
```python
# 通过Hermes Plugin Hook无侵入收集
# 3个钩子: on_post_tool_call / on_post_llm_call / on_session_end
# 所有异常 try/except 吞掉，永不中断主Session
```

### 2. 语义分类规则引擎（零LLM成本）
```python
# candidates.py 的 classify_record() 规则链:
# 1. line-numbered dump → IGNORE
# 2. near cap → SKILL_UPDATE (容量预警)
# 3. safety preference → MEMORY
# 4. tool failure → REPLAY_BENCHMARK
# 5. workflow pattern → SKILL_UPDATE 或 SKILL_NEW
# 6. ephemeral → IGNORE
# 7. low confidence → IGNORE

# 中文Workflow检测
_ZH_WORKFLOW_PATTERN = re.compile(
    r"(流程|步驟|SOP).{0,80}(先|再|最後).{0,160}(先|再|最後)", re.DOTALL
)
```

### 3. 4种确定性变体策略
```python
_VARIANT_SPECS = (
    ("default-verify-first",  evidence_limit=5,  style="verify-first"),
    ("compact-evidence-first", evidence_limit=3,  style="evidence-first"), 
    ("wide-errors-first",     evidence_limit=8,  style="errors-first"),
    ("spillover-minimal-inline", evidence_limit=2, style="verify-first", force_spillover=True),
)
```

### 4. 受保护写入的9层门禁
```python
# guarded_apply.py:
# 1. SHA256校验当前文件
# 2. 备份到 backup_dir / <ts> /
# 3. 内置结构检查 (size cap + managed block boundedness)
# 4. 可选 Pre-verify (自定义验证命令)
# 5. 写入文件
# 6. 可选主 Verify (自定义验证命令，超时300s)
# 7. 注册支持文件到manifest
# 8. 来源溯源 (只写入 local-agent-created)
# 9. 恢复演练 (回放manifest到临时目录验证)

# 分阶段校验引擎:
# 廉价阶段: 文件大小检查 + managed block完整性
# 昂贵阶段: 自定义验证命令 (测试套件、编译检查等)
```

### 5. Pin检测 + 核心Skill保护
```python
_DEFAULT_CORE_AUTO_APPLY_PROTECTED_PATTERNS = (
    "hermes-agent", "hermes-*", "gsd-*", "github-*", 
    "mcp-*", "native-mcp", "claude-code", "codex",
    "subagent-*", "systematic-debugging", "test-driven-development",
)
# Pin: frontmatter中 pin: true 的skill受到保护
```

## SkillClaw 核心模式

### 1. Session评判4维度
```python
# session_judge.py:
dimensions = {
    "completeness": 0.3,  # 任务完成度
    "difficulty":   0.2,  # 任务难度
    "efficiency":   0.3,  # 步骤效率
    "reusability":  0.2,  # 可复用性
}
```

### 2. Collective Evolution
多用户共享Skill库，通过共享存储（OSS/S3/Local）实现Client-Server解耦。

### 3. Multi-Agent适配器模式
```python
_ADAPTERS = {
    "hermes": _configure_hermes,
    "codex": _configure_codex,
    "claude-code": _configure_claude_code,
    # 每个Agent一个函数，通过字典集中分发
}
```

## Hermes现有实现对比

| 特性 | curator-evolver | SkillClaw | Hermes现有 |
|------|----------------|-----------|-----------|
| 证据收集 | Plugin Hook | API代理拦截 | 复盘引擎(state.db) |
| 语义分类 | 规则引擎(零LLM) | LLM Pipeline | 规则引擎(零LLM) |
| 变体生成 | 4种确定性 | LLM决策(4种) | 4种确定性 |
| 评分 | 确定性公式 | LLM评估 | 确定性公式 |
| 写入 | 9层门禁 | 直接写入 | 4层(SHA+备份+验证+回滚) |
| 来源追溯 | provenance gates | Nacos注册 | 无 |
| 恢复演练 | restore_drill | 无 | 无 |
| 集体进化 | 单机 | 多用户共享 | 单机 |
