---
name: ai-content-production-pipeline
description: AI内容生产管线构建方法论 — 从需求定义/全局调研/架构设计到TDD实现/引擎对接/Web UI的全流程。基于Infinite Multimodal Data Foundry项目(63项目调研, 41测试, 5引擎)的实战经验。
---

# AI内容生产管线构建方法论

## 何时使用
- 需要构建大规模的AI内容生产系统(图片/视频/短剧/PPT/网页)
- 需要将多个开源方案融合为一个统一的Agent驱动系统
- 需要设定质量门禁和验收标准

## 完整开发流程

### Phase 1: 需求定义
- 明确需求边界(什么类型的生产内容)
- 明确约束条件(质量/成本/速度优先级)
- 输出: 需求文档

### Phase 2: 全局调研
- 开源项目(GitHub Stars, 架构, 关键参数, 许可证)
- 商业API(Endpoint, 定价, 限制)
- 学术论文(核心方法, 关键结果)
- 实战文章(工作流, Pitfalls)
- 每项记录: 核心价值, 技术细节, 与我们项目的关系, 可复用设计

### Phase 3: 架构设计
- 融合方案(取各项目最优点组合)
- 对标超越(列出对标项目逐项说明超越点)
- 核心模块: 画布状态/场景图/历史/引擎路由/Agent调度/质量审计
- 见: `无限画布系统_v3_世界顶级架构设计.md`

### Phase 4: TDD实现
1. 核心模块(canvas_core.py) — 画布状态+场景图+历史管理器
2. 引擎层(engine_router + 各引擎) — 统一调度+具体实现
3. Agent层(master_agent) — 任务规划+质量门禁+错误恢复
4. API层(nanobot_adapter) — 外部能力集成
5. 测试 — 每次提交至少19/19通过

### Phase 5: 真实引擎对接
- 下载目标项目源码到本地vendor目录
- 分析CLI接口(README → 命令列表 → 参数 → 输出格式)
- 用subprocess.run封装真实调用
- 每调用有try/except和fallback

### Phase 6: Hermes Skill封装
- 生成skill.yaml
- 包含: 前置检查/引擎参数/决策链/使用示例

### Phase 7: Web UI
- FastAPI + 原生HTML/CSS/JS(无框架)
- WebSocket实时推送
- 暴露: 画布状态/引擎规划/渲染执行/元素CRUD

## 关键设计决策

### 引擎选择器
```python
# 根据内容类型/质量/成本自动选择
decision = engine_router.decide(user_input, prefer_quality=True, prefer_cost="free")
```

### 每引擎多引擎fallback链
```python
primary_engine = "html-video"
fallback_engine = "garden-video"  # 主引擎失败时自动切换
second_fallback = "html-screenshot"  # 能兜底的终极方案
```

### 质量门禁三层
1. 代码层: 函数级约束(景别交替/情绪曲线/时长分布)
2. Agent层: 独立Reviewer逐项检查Checklist
3. 数据层: Worker完成率≥80%

## 参考项目
- IMDF: /mnt/d/Hermes/infinite-multimodal-data-foundry/ (41/41 tests)
- Vendor源码: /mnt/d/Hermes/imdf_vendor/
- 架构文档: /home/administrator/无限画布系统_v3_世界顶级架构设计.md

## 训练数据生产方向(5大引擎)
| 方向 | 生产内容 | 输出格式 |
|------|---------|---------|
| T2I数据 | 预训练图文对/微调/ControlNet条件对 | WebDataset/COCO/Parquet |
| 图片编辑数据 | Outpaint/Inpaint/超分数据对 | 输入输出+蒙版+JSON |
| 视频数据 | 帧提取/视频Caption/视频编辑对 | ffmpeg管线+JSON |
| 影视/短剧数据 | 多镜头叙事对/角色一致性对 | JSON结构化 |
| 绘本数据 | 页面布局/风格一致性/适龄参数 | JSON |

## 第三方项目复刻工作流
当需要将某个开源项目的功能复制到本系统时:

1. 下载源码: git clone --depth 1 到 imdf_vendor/
2. 分析项目结构: package.json/features.json → 技术栈+功能清单
3. 按功能分类找到对应源文件,分析后端API/前端组件
4. 提取功能接口: 每个功能点的CLI/API参数 → Python封装
5. 创建复刻模块: 用纯Python+Web API复刻核心逻辑
   - 前端交互用FastAPI REST+WebSocket
   - 后端业务逻辑完全复刻(签名/编码/模板)
6. 逐步替换: 从高优先级到低优先级渐进集成

本session的Penguin Canvas集成实践可作为参考。
