---
name: task-decomposer
description: 自动将复杂任务分解为可执行的子任务树，按优先级排序，标记依赖关系。
---

# Task Decomposer

## 何时使用
当收到超过3步的复杂任务时。或用户说"继续开发"、"全部实现"等。

## 使用方法
加载此skill后，分析当前任务目标，输出一个JSON格式的任务分解树。

## 任务分解树格式

```json
{
  "goal": "原始任务目标",
  "phases": [
    {
      "phase": 1,
      "name": "阶段名称",
      "priority": "P0/P1/P2",
      "parallel": true,
      "tasks": [
        {
          "id": "task-1",
          "name": "任务名称",
          "goal": "子任务目标",
          "depends_on": [],
          "estimated_steps": "3-5",
          "verification": "验证方式（curl/pytest/browser）"
        }
      ]
    }
  ]
}
```

## 分解原则
1. 每个子任务必须独立可验证
2. 并行任务之间不能有数据依赖
3. 每个phase内部可并行，phase之间串行
4. P0优先执行，P1次之，P2最后
5. 每个子任务标注验证方式

## 输出
输出分解后的任务树 + 推荐执行顺序 + 预计总步数。
