---
name: v8-final-push
description: v8_final_push.py - 最终推送（用delegate_task做真正AI六维评分）
category: auto-generated
tags: [auto-generated, v8-final-push]
---

# v8-final-push

由Hermes自进化引擎于 2026-05-03 05:00 自动生成。

## 源文件

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

该脚本存在于 skill 目录内：
`/home/administrator/.hermes/skills/v8-final-push/v8-final-push.py`

> ⚠️ 原引用路径 `~/hermes/scripts/v8_final_push.py` 已失效，该文件不在 scripts/ 下。

## 使用方法
加载此skill后可直接使用其功能。
运行方式：`python3 /home/administrator/.hermes/skills/v8-final-push/v8-final-push.py`

## 注意
此脚本依赖 delegate_task 做AI六维评分，
评分后需要手动运行 `scripts/apply_v8_scores.py`。
⚠️ 脚本内嵌了 PushPlus token（生产环境凭据），仅在授权范围内使用。

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
