---
name: comms-networks-experts
description: 通信与网络专家团队 - 15位网络专家，覆盖5G、WiFi、SDN、网络协议、光网络、卫星通信、量子通信、网络安全等专业。
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["networking", "5g", "wifi", "sdn", "network-protocols", "optical", "expert-team"]
---

# 通信与网络专家团队

15位通信与网络专家组成的精英团队，覆盖5G、WiFi、SDN、网络协议、光通信全领域。

## 团队成员

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


| ID | 专家 | 专长领域 |
|----|------|---------|
| expert_136 | 5G技术专家 | 5G NR/网络切片/边缘计算 |
| expert_137 | WiFi优化专家 | WiFi6/mesh/无线优化 |
| expert_138 | 网络协议专家 | TCP/IP/路由协议 |
| expert_139 | SDN专家 | 软件定义网络/OpenFlow |
| expert_140 | 网络功能虚拟化专家 | NFV/虚拟化网络功能 |
| expert_141 | 光网络专家 | 光纤通信/WDM |
| expert_142 | 卫星通信专家 | 卫星网络/星链 |
| expert_143 | 量子通信专家 | 量子密钥/QKD |
| expert_144 | 网络编码专家 | 网络编码/分布式存储 |
| expert_145 | 网络仿真专家 | NS-3/网络仿真 |
| expert_146 | 网络测量专家 | 网络测量/性能评估 |
| expert_147 | 流量工程专家 | 流量优化/TE |
| expert_148 | 网络安全审计专家 | 网络审计/安全评估 |
| expert_149 | 无线传感网络专家 | WSN/传感器网络 |
| expert_150 | 网络切片专家 | 网络切片/5G网络 |

## 核心能力

- **5G/移动网络**: 5G NR/网络切片/MEC
- **企业网络**: WiFi/有线网络优化
- **SDN/NFV**: 软件定义网络/虚拟化
- **光/卫星通信**: 光网络/卫星通信
- **网络安全**: 网络审计/安全评估

## Source

- Expert config: `/mnt/d/OpenClaw/experts/expert_system_config.json`
- Domain: 通信与网络 (15 experts)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
