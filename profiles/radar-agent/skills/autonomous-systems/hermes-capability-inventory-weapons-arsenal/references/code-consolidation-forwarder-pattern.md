# 代码合并方法论 — 前向转发器模式（2026-06-02 验证通过）

## 背景

Hermes scripts/ 目录下累积了大量功能重叠的脚本（35个记忆相关脚本、9个压缩引擎脚本、5个编排器脚本）。需要在**保证所有旧调用路径100%兼容**的前提下合并为统一模块。

## 前向转发器模式（Forwarder Pattern）

### 步骤

1. **分析重叠** — 逐文件读完整代码，提取类/函数/CLI入口/配置常量
2. **建立统一模块** — 新建 `xxx_engine.py`，包含所有原脚本的类和方法
3. **创建转发器** — 旧脚本改为：
   ```python
   #!/usr/bin/env python3
   """转发器 — 功能已迁移到 xxx_engine.UnifiedClass"""
   from xxx_engine import UnifiedClass
   import sys, json
   if __name__ == "__main__":
       # 保持原有CLI入口
       ...
   ```
4. **分批验证** — 每批合并后验证三件事：
   - 语法检查：`import py_compile; py_compile.compile('xxx.py', doraise=True)`
   - 新模块：`timeout 10 python3 xxx_engine.py status`
   - 旧脚本：`timeout 10 python3 old_script.py status`

### 本次成果（2026-06-02）

| 批次 | 旧脚本 | 新模块 | 大小 | 状态 |
|------|--------|--------|------|------|
| 压缩引擎 | 9→1 | compression_engine.py | 37KB, 7模块 | ✅ |
| 记忆引擎 | 7→1 | memory_engine.py | 58KB, 9模块 | ✅ |
| 编排器 | 5→1 | orchestrator.py | 12KB, 5模块 | ✅ |
| 工具集 | 3→1 | memory_tools.py | 5KB | ✅ |
| **总计** | **21→4** | | **112KB** | ✅ |

### 关键原则

- **永远不要删除旧脚本** — cron/import/CLI全部依赖旧路径
- **转发器保持轻量** — 只做 import + 转发，不加新逻辑
- **在一批完成后立即验证** — 不等全部写完
- **不信任LLM自觉遵守** — 本次用户纠正了“不要停下来汇报进度，继续下一个”
