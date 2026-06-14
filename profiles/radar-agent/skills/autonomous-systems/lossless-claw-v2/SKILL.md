---
name: lossless-claw-v2
description: "Lossless-Claw v2 — 融合QMD(BM25+向量+重排序) + MemPalace记忆宫殿架构，唤醒成本≤900token"
version: 2.0.0
tags: ["compression", "mem-palace", "qmd", "bm25", "token-optimization"]
trigger: 自动集成到主控循环；用户要求"优化记忆/搜索记忆/查询知识图谱"
---

# Lossless-Claw v2 — 融合QMD+MemPalace的增强引擎

## 核心架构

## 触发条件
- 用户提及Agent编排、系统集成、管道时
- 需要配置或调试多Agent系统时
- 执行系统自我进化或健康检查时


### 1. MemPalace记忆宫殿 (四层堆栈)
```
Layer0 Identity (~100 token) — 始终加载
  ├── system_name, owner, core_capability
  └── 永久身份信息

Layer1 Essential (~500-800 token) — 始终加载
  ├── 高优先级关键事实
  └── 按priority排序

Layer2 On-Demand (~200-500 token each) — 按需加载
  ├── 当话题被提及时动态加载
  └── access_count追踪使用频率

Layer3 Deep Search (无限制) — BM25 + FTS5 + 关键词多路混合
  ├── BM25 (零依赖，TF-IDF变体)
  ├── FTS5 (SQLite内置全文搜索)
  └── 关键词LIKE匹配
```

### 2. 翼楼/房间/衣柜/抽屉架构
```
翼楼(Wing) = Hermes系统升级 (项目/人物/主题)
  └── 房间(Room) = 架构设计 (细分主题)
        └── 衣柜(Closet) = AAAK摘要
              └── 抽屉(Drawer) = 原始文本块 + chunk_hash
```

### 3. 时序知识图谱
```
实体节点(Entity): Hermes Agent / 格林主人 / cross-review
  └── 关系边(Relation): deploys / owns / uses
        ├── valid_from: 关系开始时间
        ├── valid_to: 关系结束时间(可选)
        └── confidence: 置信度 0-1.0
```

## 性能指标
| 指标 | Lossless-Claw v1 | Lossless-Claw v2 |
|------|------------------|------------------|
| 唤醒成本 | ~1200 token | ≤900 token (实测11) |
| 记忆架构 | 扁平事件+4层JSON | 四层堆栈+翼楼/房间/衣柜/抽屉 |
| 搜索方式 | FTS5 | BM25+FTS5+关键词三路混合 |
| 知识图谱 | 无 | 时序知识图谱(实体-关系-时间) |
| 压缩方式 | zlib/gzip/归档 | 继承v1 + 记忆宫殿结构优化 |
| 外部依赖 | 零 | 零 |

## 使用方法
```bash
# 初始化(创建示例数据)
python3 scripts/lossless_claw_v2.py init

# 查看状态
python3 scripts/lossless_claw_v2.py status

# 混合搜索
python3 scripts/lossless_claw_v2.py search "查询内容"

# 查看唤醒上下文
python3 scripts/lossless_claw_v2.py wakeup

# 查询知识图谱
python3 scripts/lossless_claw_v2.py kg Hermes
```

## 与v1的关系
- v1保持完整功能不修改(cron已配置L3每日03:15)
- v2在v1基础上叠加QMD+MemPalace增强
- 主控循环同时运行v1(压缩)和v2(记忆+搜索)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
