# IMDF项目结构 — P0完成

项目位置: `/mnt/d/Hermes/infinite-multimodal-data-foundry/`

```
├── core/canvas_core.py          # 507行 — CanvasState/SceneGraph/HistoryManager
│   ├── CanvasElement(7种类型)
│   ├── Shot(镜头: 时长/运镜/口播/字幕/转场)
│   ├── Scene(场景: 镜头列表+状态快照+角色位置)
│   ├── CanvasState(元素管理+场景管理+快照)
│   ├── HistoryManager(undo/redo/每5步检查点/版本分支)
│   └── InfiniteCanvas(顶层管理器)
│
├── engines/
│   ├── engine_router.py         # — 5引擎统一调度
│   │   ├── 10种内容类型识别
│   │   ├── 9个引擎能力矩阵+评分
│   │   ├── 12+12套模板清单
│   │   └── 自动fallback链
│   ├── ppt_engine.py            # — PPT生成引擎
│   │   ├── 10套模板(颜色/字体/背景完整设计)
│   │   ├── 9对字体配对(Claude Design)
│   │   ├── 17种标准页型(PPT Director)
│   │   └── 完整HTML输出(键盘导航+进度点)
│   └── story_arc_engine.py      # — 故事弧引擎
│       ├── 25个故事感总纲(情绪曲线+节拍)
│       ├── 情绪映射(50+中文情绪词→数值)
│       ├── 景别交替检测(代码级强制)
│       ├── 镜头连续性追踪+自动修正
│       ├── 独立Reviewer优化
│       └── 大师级影视语言(CinematographyDirector)
│
├── agent/master_agent.py        # — 主控Agent
│   ├── ContentAnalyzer(8种内容类型识别+风格提取)
│   ├── QualityGate(每内容类型验收清单+Reviewer评分)
│   ├── ErrorRecovery(失败记录+CheckList+降级策略)
│   └── MasterAgent(plan→execute→review→deliver)
│
├── api/nanobot_adapter.py       # — NanoBot API适配
│   ├── check_health/list_models
│   ├── generate_image/video
│   ├── upscale_image/execute_comfyui
│   └── batch_generate
│
├── tests/test_core.py           # 19个测试(19/19通过)
│   ├── TestCanvasCore(5)
│   ├── TestMasterAgent(5)
│   ├── TestEngineRouter(3)
│   ├── TestStoryArcEngine(3)
│   └── TestPPTEngine(3)
│
├── pyproject.toml               # Python包配置
└── README.md                    # 项目文档
```

## 关键设计决策

1. CanvasState用深拷贝快照(undo/redo不共享引用)
2. HistoryManager每5步自动检查点+命名版本分支
3. StoryArcEngine兼容dict和dataclass的beat访问
4. EngineRouter可扩展(新引擎只需注册到ENGINE_CAPABILITIES)
5. MasterAgent用ContentAnalyzer自动识别内容类型
6. QualityGate按内容类型生成验收清单
7. ErrorRecovery记录失败模式+降级策略
8. NanobotAdapter通过HTTP API调用(不耦合代码)
