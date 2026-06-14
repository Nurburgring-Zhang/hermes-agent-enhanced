---
name: production-system-engineering-spec
description: 生产体系工程规范 — 需求挖掘/Agent Company/Expert System全链路定义。基于软件工程方法定义的分层架构(4层)、质量门禁、阶段验收标准、资源约束、回滚策略和审计规则。
---

# 生产体系工程规范 v2.0

## 何时使用
- 运行 omni_loop / production_chain 之前检查前置条件
- 审计管线产出的质量
- 排查管线执行中的问题
- 理解三层生产体系(L0-L4)的边界和契约
- 执行 Dynamic Workflows 前检查全能力链路是否就绪

## v2.0 新增（2026-06-09）
- 引用 Dynamic Workflows 的执行前强制三查（preflight）
- 引用 SDLCEnforcer 的软件开发流程强制
- 引用 Agent Company Matcher 自动员工分配
- 引用 evolution_durable 的复盘→进化循环

## 全能力执行前置条件（Dynamic Workflows 集成）
在运行任何生产任务之前，以下系统必须就绪：
1. **preflight.py** — 执行前强制三查（history/skill/search/assessment）
2. **active_engine.py** — SDLCEnforcer + WorkflowAutoActivator
3. **company_matcher.py** — 117员工自动匹配
4. **gear_integration.py** — G0/G1/G6对接
5. **evolution_durable.py** — 复盘→进化循环

详见 skills-orchestration-engine skill

## 分层架构
| 层 | 名称 | 核心职责 | 触发 |
|----|------|---------|------|
| L0 | 情报采集 | 42平台持续采集 | cron 3h/6h |
| L1 | 需求挖掘 | 情报→需求模式/趋势/机会 | cron 6:00 |
| L2 | 生产执行 | Agent Company生产组装 | cron 8:00 |
| L3 | 专家系统 | 按需调领域专家 | 按需 |
| L4 | 质量审计 | 各层产出完整性验证 | cron 30min/22:00 |

## 质量门禁

### L1出口标准（omni_loop Step 4 完成后）
- [ ] 需求有至少2条独立情报源支撑
- [ ] 目标用户定义清晰
- [ ] 核心痛点可复现
- [ ] 验证标准可量化
- [ ] 风险点已识别

### L2各阶段标准（production_chain 6阶段）
| 阶段 | 执行者 | 验收标准 |
|------|--------|---------|
| 1采集 | emp_004+005 | 5+信息源, 含趋势, <300行 |
| 2分析 | emp_014+001+002 | P0/P1/P2明确, 3+竞品 |
| 3设计 | emp_011+019+020 | 2+方案, 含风险/工作量 |
| 4生产 | emp_029~058 | 子任务独立验收, 九维清单 |
| 5验收 | emp_102~109 | 端到端通过, 缺陷已记录 |
| 6交付 | emp_123+059~078 | 产品包+摘要+已知问题 |

## 约束
- 子Agent≤8并行（受max_concurrent_children=3限制→阶段内串行）
- 全管线≤60分钟，超时标记degraded
- 中间产物≤50MB/周期，保留最新2周期
- 阶段超时保留已有产出不阻塞全链路
- 连续2次阶段失败标记blocker通知人工

## 回滚
- 单阶段: 从products.sqlite读上一阶段数据重试(≤2次)
- 全管线: 标记rolled_back，重建管线记录

## 模块化路由惰性导入模式（FastAPI循环依赖解决）

当从 server.py 拆分路由到独立 `routes/*.py` 模块时，如果路由函数依赖 server.py 中的全局变量（state, models等），会导致循环导入。

**症状：** `AttributeError: partially initialized module 'routes.X' has no attribute 'router'`

**修复方案：** 在路由模块中使用惰性导入函数，不在模块级加载 server.py：

```python
# routes/my_module.py
from fastapi import APIRouter, HTTPException

router = APIRouter()

def _get_state():
    \"\"\"Lazy import — 调用时再加载 server，此时server已完成初始化\"\"\"
    from server import state   # 函数内导入，避免模块级循环引用
    return state

@router.get("/api/agents")
async def list_agents():
    state = _get_state()
    return list(state.agents.values())
```

**关键点：**
1. 路由函数本身在 server.py 注册 `register_all_routers(app)` 时才被收集
2. 路由函数被调用时 server.py 已完成初始化，函数内导入安全
3. Pydantic model 也用惰性导入：`def _get_models(): from server import AgentRequest; return AgentRequest`
4. `Dict[str, Any]` 做请求体参数避免模块级导入 Pydantic models
5. routes/__init__.py 用 `from . import module; app.include_router(module.router)` 形式注册

## AI内容生产管线(IMDF扩展 2026-06-09)
无限画布系统用于AI内容生产时适用本规范:

| 层 | 对应IMDF模块 | 质量门禁 |
|----|-------------|---------|
| L0意图理解 | ContentAnalyzer | 内容类型识别准确率≥80% |
| L1规划 | MasterAgent + EngineRouter | 引擎选择有fallback |
| L2执行 | 5大引擎(图片/视频/短剧/PPT/网页) | Worker完成率≥80% |
| L3辅助 | Expert System | 可选,按需调用 |
| L4质量 | QualityGate + Reviewer | 评分≥60,清单项通过率≥70% |

详见 `/mnt/d/Hermes/infinite-multimodal-data-foundry/`

## 多模态训练数据生产管线规范（2026-06-10 新增）

当任务涉及 MLLM 训练数据的批量生产平台时，参考以下架构分层：

### 数据生产管线 7层

| 层 | 模块 | 功能 | 输出格式 |
|----|------|------|---------|
| L0 多租户 | multi_tenant | 用户/角色/项目/配额隔离 | 数据项目隔离 |
| L1 需求层 | requirement_manager | 自然语言需求→拆解任务 | 需求文档+子任务 |
| L2 任务层 | task_manager | 分配/执行/审核/仲裁 | 任务状态流转 |
| L3 算子层 | workflow_engine + operators_lib | DAG编排+44算子 | 流水线执行 |
| L4 Agent层 | agents/data_agents | 10种AI Agent自动化 | Agent执行结果 |
| L5 数据层 | data_manager + batch_engine | 版本控制/批量/格式导出 | 5种MLLM格式 |
| L6 质量层 | eval_manager + stats_manager | 评测闭环/BadCase/统计 | 评测报告+排行 |
| L7 治理层 | governance | 血缘追踪/审计日志/备份 | 合规审计 |

### 44算子6类清单（快速索引）
```
采集(7):   local_file/oss/web_crawler/database/rss/api/screenshot
清洗(13):  resolution/duration/aspect_ratio/blur/nsfw/dedup_md5/dedup_phash/
           language/sensitive/noise/snr/toxicity
标注(8):   classification/detection/caption/tagging/aesthetic/scene_detect/
           keyframe/speech_recognition
评分(5):   aesthetic/technical_quality/alignment/diversity/perplexity
筛选(5):   threshold/top_k/random/stratified/diversity
导出(6):   jsonl/parquet/csv/llava/coco/local
```

### 10种Agent自动化类型
需求解析 → 采集 → 清洗 → 预标注 → 质量评估 → 数据筛选 → 工作流编排 → 模型评测 → BadCase分析 → 反馈闭环

### API设计 v2 规范
- 前缀: `/api/v2`
- 资源命名: 复数名词 `/requirements`, `/tasks`, `/workflows`, `/operators`, `/assets`
- 惰性导入: routes/*.py 在函数内 from server import state 避免循环引用
- 错误格式: FastAPI HTTPException(status_code=4xx, detail="msg")

### 格式导出规范
| 格式 | 适用训练 | 输出文件 |
|------|---------|---------|
| LLaVA JSON | LLaVA 1.5/1.6 SFT | [{id, image, conversations}] |
| InternVL meta | InternVL 2.0 | JSON meta_path文件 |
| MMC4 JSON | 图文交错预训练 | {images, texts, urls} |
| COCO JSON | 检测/分割训练 | {images, annotations, categories} |
| JSONL | 通用/流式 | 每行一个JSON对象 |

### 全链路验证模板
```bash
cd backend && python3 << 'PYEOF'
# 验证所有模块导入
modules = ["core.requirement_manager", "core.task_manager", 
           "core.workflow_engine", "core.operators_lib",
           "core.eval_manager", "core.stats_manager", 
           "core.governance", "core.asset_manager",
           "core.multi_tenant", "core.batch_engine",
           "core.data_manager", "agents.data_agents",
           "routes.v2_zhiying"]
for m in modules:
    try:
        __import__(m)
        print(f"✅ {m}")
    except Exception as e:
        print(f"❌ {m}: {str(e)[:50]}")
PYEOF
```
**前端HTML_TEMPLATE必须包含真实交互，禁止纯静态展示。**

违反此规则=严重违规。在任何报告中声称"前端完成"之前必须确认:

```bash
# 自动检查(imdf项目根目录)
python3 audit.py    # 检查HTML中的交互功能

# 手动检查
curl http://localhost:PORT/ | grep -c 'addEventListener'    # >0
curl http://localhost:PORT/ | grep -c 'draggable'            # >0
curl http://localhost:PORT/ | grep -c 'fetch('               # >0
curl http://localhost:PORT/ | grep -c 'FileReader'           # >0
```

前端最低交互清单(缺一不可):
1. 拖拽添加节点 ← draggable + drop事件
2. 节点移动 ← mousedown + mousemove + 位置追踪
3. 连线系统 ← 输出口→输入口 + SVG贝塞尔曲线
4. 文件上传 ← FileReader + 拖放区域
5. 后端调用 ← fetch()到真实API端点
6. 执行按钮 ← 调用真实引擎
7. 历史 undo/redo
8. 工作流保存/加载

**任何声称"完成"但前端是静态展示的报告,视为虚假交付。**
- 需求质量 = 情报源数×0.2 + 平均评分×0.3 + 主题清晰度×0.3 + 验证标准完整性×0.2
- 生产质量 = 阶段通过率×0.3 + 子Agent成功率×0.3 + 验收满足率×0.2 + 按时完成率×0.2
- 综合 = 需求×0.4 + 生产×0.4 + 专家准确率×0.2
- ≥85 A级, 70-84 B级, 50-69 C级, <50 D级

## 交付完整性陷阱（2026-06-09 方法论版）
**千万不要在只做了逻辑重写时就说"迁移完成"。** 用户关心的不是代码行数,是功能能不能用、文件全不全。

### 迁移完成的标准(不仅仅是"代码复刻了")
```
□ 所有源文件物理拷贝(不只是逻辑重写)
□ 文件改名+重组织完成(完全不同)
□ 项目大小从"1M"变成"82M"级别(不是只搬逻辑)
□ 删除vendor后项目仍可独立运行
□ Web UI启动+200 OK
□ 核心API全部可用(不是只有路由注册)
□ 所有模板/资源/样式可查
```

### "完成"报告的四层验证标准
| 层 | 检查项 | 验收条件 |
|----|--------|---------|
| L0代码 | 逻辑复刻 | 模块可导入,测试通过 |
| L1文件 | 物理迁移 | 文件数接近源项目,大小合理 |
| L2资源 | 模板/样式/配置 | 模板可查,样式可用 |
| L3运行 | 实际跑通 | Web UI 200,API返回数据 |
| L4独立 | 删vendor验证 | 删掉外部目录后仍能跑 |

如果只做到L0就说"完成了",用户会发火。**至少做到L3才能报告完成。**

production_chain 和 multi_agent_engine 是跨文件调用的经典场景，极易出现接口漂移。

### 已知风险：dataclass字段不一致
IsolationTask 是 @dataclass 字段固定。调用方传了 dataclass 没定义的参数导致 TypeError。
教训：两个文件必须同时修改。改完一端立即验证另一端能否构造实例。

### 修复模式
```python
@dataclass
class IsolationTask:
    sop: dict = None          # 加字段
    tools: list = None

# 验证构造
task = IsolationTask(task_id='t', agent_id='a', agent_name='n',
                     sop={'steps':['a','b']}, tools=['file'])
```

### 质量门禁实现模式
旧代码6个阶段跑完后直接 status=delivered，不管成败。

正确模式：在 run_full_chain 中收集每个阶段的真实结果，≥4阶段通过才标记delivered。

```python
success_phases = sum(1 for _, fn in phases if fn())
if success_phases >= 4:     update_status(pid, 'delivered')
elif success_phases >= 2:   update_status(pid, 'partial')
else:                       update_status(pid, 'failed')
```
