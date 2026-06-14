---
description: "微调、RLHF/DPO/GRPO 训练、分布式训练框架和优化工具"
category: mlops/training
---

# Training (训练)

此子分类包含模型训练和微调相关的技能。

## 子技能

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### axolotl
Axolotl 微调框架，简化 LLM 的微调流程。

### grpo-rl-training
GRPO（Group Relative Policy Optimization）强化学习训练实现。

### peft
PEFT（Parameter-Efficient Fine-Tuning）参数高效微调技术，包括 LoRA、Adapter 等。

### pytorch-fsdp
PyTorch FSDP（Fully Sharded Data Parallelism）分布式训练实现。

### trl-fine-tuning
Hugging Face TRL（Transformer Reinforcement Learning）微调库。

### unsloth
Unsloth 高效微调工具，大幅加速 LLM 训练并减少内存占用。

## 回滚方案
### 模型回退
1. 切换到上一个已知稳定的模型版本
2. 重新加载模型权重
3. 验证推理结果与预期一致

### 配置还原
1. 恢复配置文件到上一版本
2. 重启服务使配置生效
3. 确认服务健康检查通过
