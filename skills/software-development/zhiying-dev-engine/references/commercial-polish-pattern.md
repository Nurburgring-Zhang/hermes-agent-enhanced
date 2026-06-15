# 商用级多轮打磨模式 (Commercial Polish Pattern)

> 2026-06-15 实战提炼 — Hermes Agent Enhanced 10轮打磨方法论

## 10轮打磨框架

```
R1  代码质量    bare except→0, ruff F/E/W修复, import排序
R2  框架补齐    基于行业研究创建核心框架模块
R3  补全+修复   从本地包迁移缺失模块, F821未定义名称修复
R4  性能优化    重复import提升到顶部, 弃用API替换
R5  文档完善    Google-style docstrings, README架构图, CHANGELOG
R6  质量门禁    生成QUALITY_REPORT, 综合评分
R7  安全加固    os.system→subprocess, shell注入修复, 敏感信息扫描
R8  冗余清理    死代码扫描, 循环import检测, 路径验证
R9  测试提升    为低覆盖模块创建测试, 拓扑/仪表盘/启动
R10 集成修复    E2E测试通过, 最终质量报告更新
```

## 每轮必做检查

1. **回归验证**: 核心测试零退化
2. **安全扫描**: 无新增API密钥/敏感信息
3. **import验证**: 所有新模块可导入
4. **git提交**: 每轮独立commit, 清晰描述

## 质量指标演进

| 维度 | R1 | R6 | R10 |
|------|-----|-----|------|
| 代码质量 | 75 | 85 | 88 |
| 安全基线 | 80 | 95 | 97 |
| 测试覆盖 | 60 | 75 | 82 |
| 文档完整 | 70 | 90 | 92 |
| 部署就绪 | 70 | 80 | 85 |
| **综合** | **71** | **85** | **87** |

## 关键教训

1. **不要跳过安全扫描** — 本会话中发现25个nvapi密钥在git跟踪中, 差点推送
2. **write_file会覆盖整个文件** — 对已存在文件只用patch, 不用write_file
3. **子Agent输出必须核实** — 子Agent声称"已创建"≠文件真实存在
4. **pip install需要验证** — pyproject.toml中的license classifier会导致setuptools>=77失败
