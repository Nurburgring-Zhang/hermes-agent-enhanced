---
name: imdf-infrastructure
description: "IMDF (Infinite Multimodal Data Foundry) v2.0 — 商用级多模态数据生产平台。26引擎/44算子(含真实实现)/90API/47种节点/+双AI互审(已注入SOUL.md)/智影数据工场迁移(需求管理/评测闭环/众包/交付/算法审核)/ComfyTV增强。Pure Python, FastAPI, ~85MB含前端模板。Web UI运行中。"
domain: devops
triggers:
  - "imdf"
  - "无限画布"
  - "多模态数据生产"
  - "数据工场"
  - "商用数据平台"
  - "前端画布"
  - "节点编辑器"
  - "penguin-canvas"
  - "智影"
  - "comfytv"
  - "vendor migration"
  - "数据算子"
  - "评测闭环"
  - "众包"
version: 3.0.0
---


# IMDF 项目工程规范 v2.0

## 项目位置
/mnt/d/Hermes/infinite-multimodal-data-foundry/

## 启动方式
cd /mnt/d/Hermes/infinite-multimodal-data-foundry && python3 api/canvas_web.py --port 8765
浏览器: http://localhost:8765

## 项目规模 v3.0 (2026-06-12)
- 44个Python引擎模块, ~132条API路由(v1+v1扩展+P0新功能)
- HTML_TEMPLATE前端(含数据浏览器/运营看板/管道监控面板)
- 16个新增功能模块:
  - P0: argon2密码加固/健康检查/结构化日志/FTS5搜索/标注一致性评分/质量断言框架/审计日志/任务队列/API版本控制+限流
  - Sprint1: 优雅关闭/缩略图预览/数据库迁移
  - Sprint2: 数据导入(CSV/JSON/Excel)/增量交付(版本差分+tar.gz)
  - Sprint3: AI预标注(DeepSeek API+BBox叠加)/管道监控
  - Sprint4: 前端数据浏览器(AG Grid分页/搜索/预览)/运营看板(Metric卡片+Canvas折线图)
  - Sprint5: 节点化工作流引擎(三层节点+DAG/拓扑排序/并行执行/6个预置模板)
- 三Agent互审全程开启: 每个Sprint前做架构/产品/工程交叉分析

## 引擎体系 (44个)
### 新增引擎 (18个, P0-Sprint5)
- auth_routes.py — argon2密码加固
- search_engine.py — FTS5全文搜索
- agreement_engine.py — 标注一致性评分(Cohen Kappa/IoU/Fleiss)
- assertion_engine.py — 质量断言框架(Column/Table/Row)
- task_queue.py — APScheduler任务队列
- preview_engine.py — 缩略图预览(PIL+ffmpeg+pdf2image)
- db_migration.py — 数据库迁移(版本化SQL+事务回滚)
- ingestion_engine.py — 数据导入(CSV/JSON/Excel+自动建表)
- delivery_inc.py — 增量交付(MD5差分+tar.gz patch)
- monitor_routes.py — 管道监控(队列深度/成功率/历史趋势)
- prelabel_router.py — AI预标注(3种task_type+BBox叠加)
- data_browser_routes.py — 数据浏览器(分页/搜索/预览)
- ops_dashboard_routes.py — 运营看板(概览+趋势图)
- nodes/registry.py — 节点注册表(48节点/三层分类)
- nodes/engine.py — DAG执行引擎(Kahn拓扑排序/循环检测/并行执行)
- nodes/templates.py — 工作流模板系统(6个预置模板+JSON Schema)


### 核心引擎 (6个)
- canvas_core.py — 无限画布核心(CanvasState+SceneGraph+History)
- operators_lib.py — 44个算子(采集7/清洗13/标注8/评分5/筛选5/导出6)
- dataset_manager.py — 数据集版本管理+6种格式导出(COCO/WebDataset/JSONL/Parquet/LLaVA/InternVL)
- eval_engine.py — 评测闭环+BadCase分析+反馈迭代
- multi_tenant.py — 多租户RBAC(admin/annotator/reviewer/viewer)
- requirement_engine.py — 需求全生命周期+任务自动分配

### 生产引擎 (7个)
- video_engine.py — 5合一视频引擎
- drama_engine.py — 7阶段短剧流水线
- ppt_engine.py — PPT引擎(10模板+9字体+17页型)
- web_engine.py — 网页引擎(21风格)
- story_arc_engine.py — 25故事总纲+情绪引擎
- comfyui_engine.py — ComfyUI工作流执行器
- video_composer.py — ffmpeg视频合成/帧提取/音频合成

### 数据引擎 (3个)
- data_t2i.py — 文生图训练数据生产
- data_edit.py — 图片编辑训练数据
- data_video.py — 视频/影视/绘本训练数据

### 商用级引擎 (8个)
- crowd_platform.py — 众包团队管理+技能分配+质量跟踪+薪酬计算
- data_delivery.py — 数据交付审核+多人审批链+版本对比
- algorithm_review.py — 算法在线审核+5级审批流(submit→pre_review→technical→final→deploy)
- stats_dashboard.py — 统计看板(日/周/月报+7维度指标)
- oss_triple_bucket.py — 阿里云OSS三桶(object/vector/table)+智能文件夹动态规则
- scene_exporter.py — 3D场景→glTF/OBJ文件导出
- zhiying_dev_engine.py — 智影7步SDLC开发引擎
- nanobot_adapter.py — NanoBot Factory API适配器

### API模块 (11个)
- canvas_web.py — Web UI画布(含31KB HTML_TEMPLATE)
- canvas_3d.py — 3D场景API(31端点)
- cloud_storage.py — COS/OSS签名上传
- media_manager.py — 媒体管理
- resource_library.py — 资源库
- system_config.py — 系统配置
- board_manager.py — 画布管理
- external_providers.py — 外部Provider
- image_processor.py — 图像处理
- figma_bridge.py — Figma联动
- theme_manager.py — 主题管理

## 迁移来源
- Penguin Canvas v2.1.4: 47种节点类型+后端模块
- 智影数据工场平台: 44算子/数据集管理/评测闭环/多租户/需求管理
- garden-skills(ConardLi 7K★): 231模板文件
- frontend-slides(20.5K★): 34套PPT模板
- html-video(2.4K★): 视频渲染引擎
- hyperframes(HeyGen 9.6K★): HTML→视频管线
- crawl4ai(67K★): 核心爬虫模块
- ComfyTV: 子图/下游传播/工作流导入风格(comfyui_engine增强)

## 前端UI v2.0
- 4选项卡侧边栏(节点/项目/数据/团队)
- 右侧属性面板(点击节点时显示参数配置)
- 底部状态栏(API/项目/用户状态)
- 画布缩放控件
- 工作流导入按钮(JSON上传)
- ComfyUI本地+Remote模式支持
- 双击节点编辑+拖拽连线+右键菜单+键盘快捷键(Ctrl+Z/Y/S/Del)

## 双AI互审机制
- 预审(pre_review): 高风险工具拦截+危险模式检测
- 验证(post_review): 连续3次失败检测
- 前端层: DANGEROUS_FRONTEND_OPS/DANGEROUS_PATTERNS
- 不可跳过: 每次工具调用前必须执行pre_review()

## 模型路由链(SOUL.md固化)
- 普通: deepseek-v4-flash
- 标准: deepseek-v4-pro
- 困难: deepseek-v4-pro
- 超难: 建议Claude 4.8/4.7/Fable 5/GPT 5.5/Gemini 3.5 Pro/Flash
- force_compressor插件: pre_context_load+post_tool_call双hook注入, 每轮对话强制压缩
- model_router插件: post_tool_call hook, 连续3次失败自动切换模型

## 关键陷阱(2026-06-10 实战)
1. HTML_TEMPLATE替换时只替换HTML字符串,不碰Python逻辑
2. DatasetFile是dataclass不是dict,_save_index需要default=_serialize
3. 众包引擎src/share_path不存在时os.path.exists报错,用参数控制
4. 算法审核的run_pre_review只推进一步,需要判断状态再决定是否继续
5. 每次开发新功能前走ZhiyingDev流程(7步SDLC+双审)
6. 所有路径用platform_config计算,勿硬编码
7. **审核不是阅读是运行** — routes_extended.py 16个端点返回静态JSON,读了3次都没发现
8. **算子注册≠算子实现** — operators_lib.py 44个算子run()默认return data,不做任何处理
9. **前端case要有真实API** — case'comfyui'之前只有addLog没有fetch调用
10. **重复case导致dead code** — case'image'在execNode中出现2次,第1个永远不会执行
11. **正则\\\\\\n陷阱** — `r'(?<=[。！？\\\\\\n])'` 是字面反斜杠+n不是换行
12. **相对导入在非包上下文中崩溃** — `from ..api.nanobot_adapter import` 在引擎模块中不能用
13. **空列表直接索引** — mp4_files[0]前必须检查len > 0
14. **contains比较大小写** — Rule.matches中self.value也要.lower()
15. **created_by参数被接收但未赋值** — requirement_engine.create_requirement缺了一行
16. **HTTP端点返回静态JSON** — routes_extended.py几乎所有POST端点只返回{**data}，没有真实引擎调用
17. **NANOBOT_HOST不带http://协议头** — httpx需要完整URL，缺协议头导致连接失败
18. **hmac_sha1_base64双重return** — 第1个return让第2个base64编码永远不会执行，OSS签名全废
19. **sync调用async在FastAPI中崩溃** — resource_library.py的_resolve_source用run_until_complete，在异步路由中抛'event loop already running'
20. **Dockerfile缺Pillow/python-multipart** — 图片处理和文件上传依赖缺失

## 关键陷阱(2026-06-12 补充)
21. 半假文件模式 — 同一个路由文件中部分端点调真实引擎，部分直接返回静态数据。审计时必须逐端点检查return语句是否为引擎层调用，不能只检查文件开头是否有import
22. 私有类名下划线 — MockObjectStore实际类名是_MockObjectStore。FastAPI启动时import报错500。修复: from module import _ActualName as PublicName
23. 同步函数误用async调度 — init_db()是同步函数但被asyncio.create_task(init_db())调用。报错An asyncio.Future, a coroutine or an awaitable is required。修复: 同步函数直接调用
24. 服务启动数据库报错不阻塞API — canvas_web.py顶层用旧代码asyncio.new_event_loop().run_until_complete(init_db())，在uvicorn已有事件循环时抛异常但catch后只打warning日志，服务正常但DB表没建。修复: 用同步调用
25. routes_extended.py修复模式 — 假实现修复模板: 导入引擎->实例化->调用方法->返回结果。CRUD_ESCALATE_AFFECTIONS必须在4处import中也检查对应引擎的list()->list_keys()API兼容性
26. APIRouter必须在if __name__块之前定义 — uvicorn.run()会fork进程，if __name__ == __main__块之后的路由注册不会被子进程加载
27. Pydantic List vs Dict类型错误 — 前端传list[]但后端模型定义nodes: Dict导致422验证错误。用List[Dict[str, Any]] + Field(default_factory=list)
28. FastAPI中间件执行顺序 — 多个@router.middleware(http)按定义顺序从外到内执行
29. except Exception隐式吞掉路由注册错误 — try: app.include_router(...); except: pass 导致路由404。不去掉try的话用精确异常类型
30. DAG执行engine的async def与await — DAGEngine.execute()是async def，路由中必须用await调用。漏掉导致coroutine object is not iterable
31. Pydantic模型修改后需重启 — Hot-reload下旧worker不加载新模型，必须kill旧进程重启
32. APScheduler SQLiteJobStore不能跨多个uvicorn worker共享

## 全链路真实产出状态(2026-06-11)

| 管线 | 状态 | 产出 |
|------|------|------|
| LLM对话 | ✅ DeepSeek API | 真实API调用,返回回复 |
| PPT生成 | ✅ HTML文件 | 真实产出(3KB+) |
| 视频生成 | ✅ ffmpeg合成 | 真实MP4(16KB/5秒) |
| 图片生成 | ✅ AI+Pillow | 真实PNG(24KB) |
| 短剧生成 | ❌ 模板字符串 | 无真实视频镜头(需要外部引擎) |
| ComfyUI | ❌ 需要本地实例 | 8188端口不通(环境限制) |

## vendor/第三方代码审核边界
vendor/crawl4ai/下80个Python文件(50,207行)是开源项目完整迁移。审核策略：
1. **检查非编写逻辑** — dead代码/同名覆盖/未使用的废弃函数  
2. **不检查内部正确性** — 由源项目测试保障
3. **只修严重影响本项目的bug** — 如base64清空、dead代码
4. **不改第三方框架的内部逻辑**

## 全项目深度审核最终统计(2026-06-12 Sprint3-5完成后)
- 54个核心Python文件 + 6个新增引擎 + 3个路由 + nodes/包(3文件) = 66+个Python文件
- ~20000+行代码 (含vendor/crawl4ai 50K行第三方)
- 发现修复: 42个bug (19高/14中/9低)
- 0语法错误, 0安全漏洞
- API端点: ~132条, 全部24项 Sprint1-5全链路验证通过
- 三Agent互审: 每个Sprint前做架构/产品/工程交叉分析

## 跨平台启动（2026-06-10 最终版）
- config/platform_config.py: find_project_root() 自动检测项目根目录
- config/global_config.py: DATA_ROOT = get_data_root()
- run.py/start.bat/start.sh: 三个平台启动器
- 无硬编码路径: grep -rn '/mnt\|D:\|C:\|/home/' 应为0
