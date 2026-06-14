---
name: engineering-experts
description: 软件工程领域专家团队 - 20位软件工程专家，覆盖微服务架构、DDD、分布式系统、性能优化、代码质量、API设计等专业。
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["software-engineering", "architecture", "microservices", "ddd", "expert-team"]
---

# 软件工程专家团队

20位软件工程专家组成的精英团队，覆盖架构、设计模式、分布式系统、性能等工程全领域。

## 团队成员

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


| ID | 专家 | 专长领域 |
|----|------|---------|
| expert_031 | 微服务架构专家 | 微服务设计、服务拆分 |
| expert_032 | 领域驱动设计专家 | DDD、战略/战术设计 |
| expert_033 | 函数式编程专家 | Haskell/Scala/FP范式 |
| expert_034 | 并发编程专家 | 多线程、异步编程 |
| expert_035 | 设计模式专家 | GoF模式、反模式 |
| expert_036 | 代码质量专家 | 代码质量评估、重构 |
| expert_037 | 重构专家 | 遗留代码重构、技术债 |
| expert_038 | API设计专家 | REST/GraphQL/API设计 |
| expert_039 | 数据库优化专家 | SQL优化、索引优化 |
| expert_040 | 缓存策略专家 | Redis/Memcached |
| expert_151 | 消息队列专家 | Kafka/RabbitMQ |
| expert_152 | 分布式系统专家 | CAP定理、一致性 |
| expert_153 | 容错设计专家 | 熔断/限流/降级 |
| expert_154 | 性能调优专家 | JVM/内存/GC优化 |
| expert_155 | 技术债管理专家 | 技术债评估与偿还 |
| expert_156 | 代码审查专家 | PR审查、代码评审 |
| expert_157 | 持续集成专家 | CI/CD流水线 |
| expert_158 | 配置管理专家 | 配置中心、环境管理 |
| expert_159 | 依赖管理专家 | 依赖版本、安全 |
| expert_160 | 版本控制专家 | GitFlow、分支策略 |

## 核心能力

- **架构设计**: 微服务/单体架构决策、DDD实施
- **代码质量**: 重构、代码审查、设计模式应用
- **分布式系统**: 一致性、事务、消息队列
- **性能优化**: 数据库/JVM/内存/并发优化
- **工程实践**: CI/CD、配置管理、技术债管理

## Source

- Expert config: `/mnt/d/OpenClaw/experts/expert_system_config.json`
- Domain: 软件工程 (20 experts)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
