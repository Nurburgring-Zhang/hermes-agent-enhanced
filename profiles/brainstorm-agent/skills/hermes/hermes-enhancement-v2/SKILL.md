---
name: hermes-enhancement-v2
description: Hermes系统增强v2固化 — 构建/部署/发布AI Agent增强能力包的方法论
category: hermes
---

# Hermes Enhancement v2 — 增强能力包构建与发布技能

**版本**: 2.2  \n**部署日期**: 2026-06-01  \n**状态**: ✅ 已固化 | 自动运行中

---

## 技能概述

本技能记录两件事：
1. **Hermes v2增强的全部模块** — 确保所有增强能力处于"主动自动运行"状态
2. **增强能力包的构建与发布方法论** — 如何将一套Agent增强能力打包为可发布的独立项目

---

## Part A: 增强能力全景 (已部署+自动运行)

### A1. 三层认知架构

| 模块 | 文件 | 运行方式 | 功能 |
|------|------|----------|------|
| MonitorEngine | `agent/monitor.py` | cron + gear_enforcer | 监控状态/错误率/停滞 → 输出CONTINUE/CHECKPOINT/REFLECT/ABORT |
| ReflectorEngine | `agent/reflector.py` | gear_enforcer触发 | 三轮反思: 执行→策略→元认知，匹配错误模式库 |
| ModelRouter | `agent/model_router.py` | cron */5 * * * * | 按复杂度选通用/强力(不硬编码具体模型名) |
| ProgressTracker | `tools/progress_tool.py` | cron */30 * * * * | 每步推进度、里程碑、ETA |

### A2. 上下文压缩6脚本 (cron每1分钟)

`context_packer` / `surgical_context_slicer` / `context_auto_assoc` / `context_index_system` / `cross_session_cache` / `context_reconstructor`

验证: index 20/20可追溯，全链路8/8通过。

### A3. 段式无限对话

`segment_manager.py` — 50轮/段，每25轮段内压缩，三明治交接协议+轨迹JSONL归档
`consistency_guard.py` — 每5轮自检文件/cron/齿轮/上下文
`auto_healer.py` — 已知模式自动修复，连续3次失败推微信

### A4. P1-P3 质量+进化 (8个)

TR门禁 / DoD清单 / Reflexion(→memory_semantic) / GEPA(每天4:00) / 经验引擎(→skill_proposals) / AutoClean(dry-run) / 检查点 / 分层规划

### A5. 齿轮G0-G8 (9个)

全部在cron中，G1已注入MonitorEngine+ReflectorEngine+SegmentManager+ConsistencyGuard+AutoHealer

### A6. 生产引擎 (7) + 自进化(4) + evolution_v3(7) + 主动反馈(4) + Hy-Memory(9)

全部独立模块，存在且运行。

---

## Part B: 增强能力包的构建与发布方法论 (本轮提炼)

### B1. 哪些能力适合打包为增强层？

判断标准：
- **独立于Agent运行** — 不需要修改Agent内部代码，全部是独立脚本+cron
- **零API依赖** — 全部用Python标准库，不需要第三方API
- **文件系统持久化** — 不依赖Agent记忆，全部写文件/SQLite
- **OS级保险** — 通过crontab物理调度，Agent挂了也照常跑

符合以上4条的，适合打包；不符合的应该作为Agent内部能力。

### B2. 备份策略

**永远做两份备份：**
- 增量版：只包含本轮新增的增强文件 (轻量，快速定位)
- **完整版：包含所有历史增强** (从头恢复用这个，格林主人在此对话中明确要求)

**完整版的构建步骤：**
1. 审计所有历史增强能力清单（从skill/memory/文件修改历史收集）
2. 逐文件确认存在 → 复制到备份目录
3. 脱敏处理：绝对路径替换为Path.home()、API KEY替换为sk-xxxxxxxx、内网IP替换为占位符
4. 验证脱敏：grep检查无残留sk-/home/内网IP
5. 创建deploy.py + README.md

### B3. 脱敏清单

| 敏感项 | 替换为 | 示例 |
|--------|--------|------|
| `/home/administrator/.hermes` | `Path.home() / ".hermes"` | 替换所有硬编码路径 |
| `sk-` 开头的32+位KEY | `sk-xxxxxxxx...` | 替换config和注释中的KEY |
| 内网IP `172.31.32.1` | `{WSL_HOST_IP}` | 替换WSL网关IP |

### B4. GitHub发布准备

**目录结构**：
```
hermes-full-enhancement-pack/
├── README.md          # 完整文档(技术/用途/思考/未来)
├── deploy.py          # 一键部署(自动检测路径+复制+cron+测试)
├── agent/             # 认知层模块
├── tools/             # 工具模块
├── scripts/           # 核心脚本(50个)
├── production_loop/   # 生产引擎
├── auto_engine/       # 自进化
├── evolution_v3/      # V3强化
└── skills/            # 固化技能
```

**deploy.py必须做5件事**：
1. 自动检测`~/.hermes/`（支持`--path`覆盖）
2. 复制所有文件到正确位置
3. 添加cron条目（`--cron-only`只加cron）
4. 运行`test_all_enhancements.py`验证
5. 输出部署报告

**README.md必须包含**：
- 技术架构图 + 关键设计决策
- 用途场景（解决什么痛点）
- 设计思考（为什么这样设计）
- 未来规划
- 量化效果
- 文件清单
- cron配置

### B7. 脚本合并方法论（本轮新增）

**多个独立脚本合并为统一模块的规范流程：**

1. **分析阶段**：逐文件读取完整代码，提取每个脚本的：
   - 所有类定义 + 方法签名
   - 所有公开函数 + 参数列表
   - CLI入口（`if __name__` 块）
   - 配置常量
   - 外部依赖（import）

2. **合并原则**：
   - **不删不改接口**：每个旧脚本的公开函数、类、CLI入口全部保留
   - **旧脚本改为转发器**：顶部加 `from unified_module import *`，保留原有 CLI 逻辑
   - **统一路径**：硬编码的绝对路径全部替换为 `Path.home() / ".hermes"`
   - **统一配置**：重复的常量合并为一个定义

3. **转发器实现**：
   ```python
   # 旧脚本.py → 转发器，功能已迁移到 compression_engine
   from compression_engine import LosslessClawCompressor
   import sys, json
   if __name__ == "__main__":
       c = LosslessClawCompressor()
       # 保持原有CLI子命令不变
   ```

4. **验证清单**（每批合并后必须全部通过）：
   - 新模块语法检查
   - 每个子模块可独立实例化调用
   - 旧脚本转发器语法检查
   - 旧脚本转发器CLI调用正常（命令行执行）
   - 旧脚本import正常（`from old_script import X`）
   - cron 路径不变

5. **安全备份**：合并前每个旧脚本备份到 `/mnt/d/Hermes/备份/`

6. **格林主人特别要求**：
   - 合并必须无损，能力不能少只能多
   - 质量要有提升（统一错误处理/统一日志/统一路径）
   - 不允许简单删文件 — 必须保留转发器保证兼容
   - 每批合并后验证通过再继续下一批

### B5. 模型命名规则

不要指定具体模型名（如v4-flash/v4-pro/deepseek-chat）。用层级描述：
- `model_tier="value"` — 通用省钱模型（简单任务）
- `model_tier="performance"` — 强力高质量模型（复杂任务）
- `model_tier=""` — 自动判断

**代码开发任务用最强模型，不用专用代码模型。**

### B6. 优化优先级判定

基于此对话经验，可优化项分为三级：
- 🔴 P0: 欠的债（模型路由接入对话层）— 最有价值的未落地功能
- 🟡 P1-2: 有但不完美（GEPA无cron/Reflexion不写memory/自进化不提频）
- 🟢 P3: 锦上添花（多通道通知/趋势分析/增量更新）

---

## 验证命令

```bash
crontab -l                                      # cron完整性
python3 scripts/consistency_guard.py             # 一致性自检
python3 scripts/segment_manager.py stats         # 段状态
python3 scripts/test_all_enhancements.py         # 全链路测试
python3 scripts/self_recovery.py --check         # 自恢复检查
```

---

*本技能记录 2026-06-01 全系统增强的全部产出 + 增强能力包构建方法论*
