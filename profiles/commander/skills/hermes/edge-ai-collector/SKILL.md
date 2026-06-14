---
name: edge-ai-collector
description: 采集 edge-ai-vision.com 的Edge AI内容并加入Hermes情报管道
usage: cd ~/.hermes && python3 scripts/collect_edge_ai.py [--push]
trigger: 每小时自动采集，内容可进入v12推送
---

# Edge AI Daily 采集器

## 数据源

## 触发条件
- 用户提及Hermes系统状态、配置、诊断时
- 需要检查或修复Hermes自身功能时
- 执行系统升级、能力激活、模块检查时

- RSS Feed: `https://www.edge-ai-vision.com/feed/`
- 内容类型: Edge AI芯片/Physical AI/工业视觉/AI算法优化

## 内容方向分析结果
| 方向 | 占比 | 关键词 |
|------|------|--------|
| Edge AI芯片/NPU/FPGA | 56% | Processors, NPU, FPGA, SoC |
| AI算法/模型优化 | 30% | Algorithms, Quantization |
| Physical AI/机器人 | 22% | Robotics, Physical AI |
| 工业视觉 | 16% | Industrial Vision |
| 智能感知 | 16% | Sensors, Camera, 3D |

## 采集器脚本路径
~/.hermes/scripts/collect_edge_ai.py

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
