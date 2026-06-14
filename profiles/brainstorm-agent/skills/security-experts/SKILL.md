---
name: security-experts
description: 安全与隐私专家团队 - 15位安全专家，覆盖网络安全、应用安全、密码学、渗透测试、零信任、云安全、威胁情报等专业。
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["security", "privacy", "cybersecurity", "penetration-testing", "zero-trust", "expert-team"]
---

# 安全与隐私专家团队

15位网络安全与隐私保护专家组成的精英团队，覆盖防御、渗透、合规全领域。

## 团队成员

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


| ID | 专家 | 专长领域 |
|----|------|---------|
| expert_196 | 网络安全专家 | 防火墙/IDS/IPS |
| expert_197 | 应用安全专家 | OWASP/代码审计 |
| expert_198 | 密码学专家 | 加密算法/密钥管理 |
| expert_199 | 渗透测试专家 | 渗透测试/红队 |
| expert_200 | 安全合规专家 | GDPR/ISO27001/SOC2 |
| expert_201 | 零信任架构专家 | Zero Trust架构 |
| expert_202 | 云安全专家 | CSPM/CWPP |
| expert_203 | IoT安全专家 | 物联网安全/固件安全 |
| expert_204 | 供应链安全专家 | SBOM/软件供应链 |
| expert_205 | 数据隐私专家 | 数据隐私/脱敏 |
| expert_206 | 身份认证专家 | IAM/SSO/MFA |
| expert_207 | 威胁情报专家 | CTI/威胁狩猎 |
| expert_208 | 漏洞研究专家 | CVE/漏洞分析 |
| expert_209 | 安全审计专家 | 审计/合规检查 |
| expert_210 | 灾难恢复专家 | DR/BCP/应急响应 |

## 核心能力

- **网络安全**: 防火墙/IDS/IPS/网络分段
- **应用安全**: 代码审计/DAST/SAST
- **渗透测试**: 红队演练/漏洞评估
- **合规**: GDPR/ISO27001/SOC2
- **云安全**: CSPM/CWPP/配置审计

## Source

- Expert config: `/mnt/d/OpenClaw/experts/expert_system_config.json`
- Domain: 安全与隐私 (15 experts)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
