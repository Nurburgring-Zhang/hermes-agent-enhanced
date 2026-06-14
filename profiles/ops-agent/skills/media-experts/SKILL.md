---
name: media-experts
description: 内容与创意领域专家团队 - 10位内容创作专家，覆盖技术写作、视频制作、数据可视化、交互叙事、游戏叙事、品牌文案等专业。
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ["content", "creative", "video", "data-visualization", "storytelling", "expert-team"]
---

# 内容与创意专家团队

10位内容创作与创意专家组成的精英团队，覆盖写作、视频、可视化、叙事等全领域。

## 团队成员

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


| ID | 专家 | 专长领域 |
|----|------|---------|
| expert_271 | 技术写作专家 | 技术文档、API文档 |
| expert_272 | 科普创作专家 | 科普内容、Science Communication |
| expert_273 | 视频制作专家 | 视频剪辑、后期制作 |
| expert_274 | 数据可视化专家 | D3.js/Tableau/可视化设计 |
| expert_275 | 交互叙事专家 | 交互式内容、互动叙事 |
| expert_276 | 游戏叙事专家 | 游戏剧情、世界观构建 |
| expert_277 | 信息设计专家 | 信息图、数据讲故事 |
| expert_278 | 品牌文案专家 | 品牌内容、营销文案 |
| expert_279 | 社交媒体内容专家 | 社交内容、病毒传播 |
| expert_280 | 播客制作专家 | 音频制作、内容策划 |

## 核心能力

- **内容创作**: 技术写作、创意写作、科普创作
- **视频制作**: 脚本、拍摄、剪辑全流程
- **数据可视化**: 图表设计、交互可视化
- **叙事设计**: 故事结构、交互叙事
- **品牌传播**: 品牌调性、内容策略

## Source

- Expert config: `/mnt/d/OpenClaw/experts/expert_system_config.json`
- Domain: 内容与创意 (10 experts)

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
