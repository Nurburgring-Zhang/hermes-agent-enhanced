---
name: pre-task-checklist
description: 任务执行前的强制checklist。每个新任务开始时必须执行此skill。
---

# Pre-Task Checklist

## 何时使用
每次开始一个新任务时。特别是用户说"继续开发"、"修复"、"完善"等。

## 步骤

### Step 1: 目标确认
- 用户真正想要的是什么？（读最后3条消息确认）
- 输出物应该是什么形式？（代码/文档/分析/验证）
- 验收标准是什么？（什么算"完成"）

### Step 2: 历史检索
- session_search: 搜索这个任务是否之前处理过
- memory: 检查是否有相关教训
- fact_store: 搜索相关的事实知识

### Step 3: 能力检查
- 相关skill是否已加载（skill_view）
- 工具集是否就绪（需要terminal? file? web? browser?）
- 项目目录/文件是否可访问

### Step 4: 风险识别
- 是否需要改前备份？多文件批量修改前必须先cp到备份目录
- 是否有不可逆操作？（delete/rm/drop/覆盖写文件）
- 文件分配检查：要修改的文件是否被其他并行的子Agent也修改了？（每个文件只能分配给一个子Agent）
- 是否需要三AI互审？
- port绑定检查：如果启动服务，确认旧进程已被杀干净（fuser -k + ss -tlnp双验证）

### Step 5: 计划输出
- 写出1-3句话的任务计划
- 用todo列出执行步骤
- 每个步骤标记预计验证方式

## 验证
完成5步后，输出"✅ Pre-task checklist complete" + 简要计划

## 参考文件
- `references/nanobot-deployment-notes.md` — FastAPI+Vue3项目生产部署检查清单，包含端口清理仪式、.env配置、workers共享状态注意事项
