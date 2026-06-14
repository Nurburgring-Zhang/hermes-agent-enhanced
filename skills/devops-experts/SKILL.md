---
name: devops-experts
description: DevOps与SRE领域专家团队 - 15位专家，覆盖SRE实践、混沌工程、GitOps、CI/CD、可观测性、SLO管理等。
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["devops", "sre", "chaos-engineering", "gitops", "observability", "expert-team"]
---

# DevOps与SRE专家团队

15位DevOps与SRE专家组成的精英团队，覆盖自动化、可靠性、可观测性全领域。

## 团队成员

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


| ID | 专家 | 专长领域 |
|----|------|---------|
| expert_121 | SRE实践专家 | SRE方法论、错误预算 |
| expert_122 | 混沌工程专家 | 故障注入、Chaos Monkey |
| expert_123 | GitOps专家 | GitOps流水线、ArgoCD |
| expert_124 | CI/CD架构专家 | 流水线设计、Jenkins/GitHub Actions |
| expert_125 | 制品管理专家 | Artifactory/Nexus |
| expert_126 | 环境管理专家 | 多环境管理、容器环境 |
| expert_127 | 发布工程专家 | 蓝绿部署/金丝雀/灰度 |
| expert_128 | 基础设施自动化专家 | Terraform/Ansible/Pulumi |
| expert_129 | 可观测性架构专家 | OpenTelemetry/Datadog |
| expert_130 | SLO管理专家 | SLO/SLI/SLA设计 |
| expert_131 | 错误预算专家 | 错误预算管理、风险评估 |
| expert_132 | 故障复盘专家 | 复盘方法论、改进措施 |
| expert_133 | 容量工程专家 | 容量规划、自动伸缩 |
| expert_134 | 变更管理专家 | 变更流程、风险控制 |
| expert_135 | 安全DevOps专家 | DevSecOps、安全扫描 |

## 核心能力

- **SRE实践**: SLO/SLI/SLA、错误预算、Toil消除
- **混沌工程**: 故障注入、韧性验证
- **GitOps**: IaC、声明式基础设施
- **CI/CD**: 流水线设计与优化
- **可观测性**: 指标/日志/追踪统一

## Source

- Expert config: `/mnt/d/OpenClaw/experts/expert_system_config.json`
- Domain: DevOps与SRE (15 experts)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
