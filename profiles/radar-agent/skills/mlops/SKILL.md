---
description: "ML工程化 — 机器学习全生命周期工具，涵盖模型训练、微调、部署、推理优化和向量数据库等 MLOps 技能"
category: mlops
---

# MLOps (ML 工程化)

此分类包含机器学习工程化各个阶段的技能，从云 GPU 平台、模型训练、模型仓库到推理部署和向量检索。

此分类包含以下 1 个子技能和 7 个子分类：

## 子技能

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时


### huggingface-hub
Hugging Face Hub CLI（hf）— 搜索、下载和上传模型及数据集，管理仓库，使用 SQL 查询数据集，部署推理端点，管理 Spaces。

## 子分类

### cloud
GPU 云提供商和无服务器计算平台，用于 ML 工作负载。包含 modal 等工具。

### evaluation
模型评估基准、实验跟踪、数据整理、分词器和可解释性工具。包含 lm-evaluation-harness、weights-and-biases 等。

### inference
模型推理服务、量化（GGUF/GPTQ）、结构化输出、推理优化和模型手术工具。包含 gguf、guidance、llama-cpp、vllm 等。

### models
特定模型架构和工具 — 计算机视觉（CLIP、SAM、Stable Diffusion）、语音（Whisper）、音频生成（AudioCraft）和多模态模型。

### research
使用声明式编程构建和优化 AI 系统的 ML 研究框架。包含 dspy。

### training
微调、RLHF/DPO/GRPO 训练、分布式训练框架和优化工具。包含 axolotl、peft、unsloth、trl-fine-tuning 等。

### vector-databases
向量相似性搜索和嵌入数据库，用于 RAG、语义搜索和 AI 应用后端。

## 回滚方案
### 模型回退
1. 切换到上一个已知稳定的模型版本
2. 重新加载模型权重
3. 验证推理结果与预期一致

### 配置还原
1. 恢复配置文件到上一版本
2. 重启服务使配置生效
3. 确认服务健康检查通过
