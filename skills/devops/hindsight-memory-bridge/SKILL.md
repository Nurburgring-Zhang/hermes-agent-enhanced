---
name: hindsight-memory-bridge
description: Hindsight知识图谱记忆系统桥接。基于15K★开源项目Hindsight的生物拟态记忆架构(实体+关系+时间序列)，补齐Hy-Memory缺失的PostgreSQL+pgvector向量嵌入+知识图谱层。实现跨session语义召回、实体关联推理、自动知识图谱构建。
---

# Hindsight Memory Bridge — 知识图谱记忆层

## 作用
Hy-Memory P0-P3 是基于SQLite的结构化记忆系统。Hindsight在它之上增加：
- PostgreSQL + pgvector 向量嵌入（语义检索）
- 实体关系图谱（节点+边+时间序列）
- 跨session因果推理
- 94.1% LongMemEval得分

## 架构
```
Hy-Memory P0-P3 (现有, SQLite)
   + Hindsight Bridge (新增, PostgreSQL+pgvector)
   = 完整4层记忆: P0操作级 + P1压缩级 + P2事实级 + P3画像级
                                   + Hindsight知识图谱级
```

## 核心能力
1. **语义召回**: 用向量嵌入找"语义相似"的记忆，不依赖关键词匹配
2. **实体链接**: 人物/项目/技术实体自动识别并关联
3. **时间推理**: 按时间线检索事件演变的因果链
4. **跨session**: 即使换了对话会话，知识图谱持续累积

## 集成方式
Hindsight通过两种方式与Hermes集成：
1. Hermes L4记忆后端（hermes memory setup中选择hindsight）
2. 独立API层（PostgreSQL+pgvector，通过hindsight-api守护进程）

## 部署状态
- Hindsight插件: Hermes已安装（plugin: hindsight, status: available）
- 需要: PostgreSQL数据库 + pgvector扩展
- 当前: 未激活（Hy-Memory P0-P3作为主记忆系统运行中）

## 启动方式
```bash
# 1. 启动PostgreSQL+pgvector
# 2. 配置Hermes使用Hindsight后端
hermes memory setup  # 选择hindsight
```
