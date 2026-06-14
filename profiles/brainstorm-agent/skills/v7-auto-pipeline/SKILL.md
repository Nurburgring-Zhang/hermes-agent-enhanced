---
name: v7-auto-pipeline
description: Hermes v7 全自动纯AI驱动情报生产管线 ====================================== 纯AI驱动，全程无人干预，自动完成： 1. 全平台采集 (1000+条)
category: auto-generated
tags: [auto-generated, v7-auto-pipeline]
---

# v7-auto-pipeline

由Hermes自进化引擎于 2026-05-04 05:00 自动生成。

## 源文件

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

该脚本已从 `scripts/` 移动到 skill 目录内：
`/home/administrator/.hermes/skills/v7-auto-pipeline/v7-auto-pipeline.py`

## 使用方法
加载此skill后可直接使用其功能。
运行方式：`python3 /home/administrator/.hermes/skills/v7-auto-pipeline/v7-auto-pipeline.py`

## 注意
⚠️ v7管线是独立运行脚本，非 cron 调度的主采集管线。
主采集管线由 `master_pipeline.py` 和 `guardian.py cycle` 管理。

## 自动生成说明
此skill是从系统中已有的脚本自动提取而来。

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史
