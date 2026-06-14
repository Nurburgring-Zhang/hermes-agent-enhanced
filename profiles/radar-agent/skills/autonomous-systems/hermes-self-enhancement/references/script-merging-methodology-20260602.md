# Hermes脚本合并实战记录: 21→4 (2026-06-02)

## 背景

Hermes系统中存在大量功能重叠的独立脚本，主要分布在 `~/.hermes/scripts/` 和 `~/.hermes/hermes-agent/` 下。
经过审计发现21个脚本存在明显的功能重复，合并为4个统一模块。

## 合并详情

### 合并清单

| 新模块 | 旧脚本 | 合并方式 |
|--------|--------|----------|
| `compression_engine.py` (37KB) | lossless_claw.py, emergency_compressor.py, rtk_compressor.py, context_compressor.py, compress_soul.py, fidelity_validator.py, memory_compress.py, run_compression.py, archive_compressor.py | 9→1, 每个旧脚本的公开接口在新模块保留同名方法 |
| `memory_engine.py` (58KB) | hermes_memory_engine.py, hermes_memory_engine_v2.py, unified_memory_core.py, hierarchical_memory.py, active_memory.py, memory_highway.py, init_active_memory_db.py | 7→1, 超大文件分15批写入 |
| `orchestrator.py` (12KB) | unified_orchestrator.py, orchestral_orchestrator_v3.py, hy_memory_orchestrator.py, parallel_memory_orchestrator.py, integration.py | 5→1 |
| `memory_tools.py` (5KB) | memory_index.py, memory_stats.py, memory_search_test.py | 3→1 |

### 转发器

每个旧脚本被替换为4行转发器:
```python
#!/usr/bin/env python3
\"\"\"转发器 — 功能已迁移到 xxx.py\"\"\"
from xxx import *
if __name__ == "__main__":
    main()
```

### 被保留的独立模块

以下模块虽然功能类似但仍有独立价值，不合并:
- `forced_executor.py` — 独立武器系统
- `hermes_retrospect.py` — 复盘引擎(hermes_retrospect.py与memory反思引擎存在少量底层函数重叠，但复盘引擎有独立CLI，保留)
- `hermes_camel_guard.py` — 安全护栏(独立工具链)
- `task_enhancement_engine.py` — 综合任务引擎
- `tool_unloader.py` — 工具卸载器(与hy_memory_orchestrator有重叠但独立API)
- `mermaid_builder.py` — Mermaid构建器
- `auto_recall.py` — 自动召回(与RAG系统重叠但独立管道)
- `memory_evolution_v2.py` — 记忆进化(独立子系统)
- `agent_enhancement_manager.py` — 插件管理器(与新模块有关联但不被继承)
- `task_boundary.py` — 任务边界检测(独立逻辑)

### 额外保留的特殊脚本
- `hermes_super_guardian.py` — 高层监护
- `autonomous_agent_journal.py` — 日志
- `optimize_git_history.py` — git优化
- `realtime_push_notification.py` — 实时推送
- `migration_*` — 迁移工具保留

### 同步的额外修改
- `migration/check_scripts.py` — 更新模块计数校验和(旧: 22468脚本+16K帧, 新: 22468脚本→204个+24个转发器)
- `auto_engine/evolution_v3/self_check_engine.py` — 增加新模块存在性检查(+4)，移除旧脚本检查
- `SOUL.md` — 引用旧脚本的地方改为新模块路径
- `AGENTS.md` — 同上
- `context_sections/` — 同上

## 经验教训

1. **分批写入必须小心Python文件完整性** — 400KB的__init__.py需要10+批写入，每批必须写完整类定义
2. **转发器测试** — 每个旧脚本装转发器后必须测试 `python3 xxx.py` 能正常转发
3. **cron检查** — 旧cron路径会自动使用转发器，不需要改cron
4. **备份要全量做** — 不是只备份要改的文件，要备份整个目录(包含.git)
5. **大文件合并时用 `for loop + python3 -c "import ast; ast.parse..."` 每批验证语法** 比一次性写完再检查更安全
6. **21→4合并后，转发器可能被误删除** — 写入后立即检查每个转发器是否存在且可执行
