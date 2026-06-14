# 端到端全链路验证方法

## 验证原则
每个模块必须独立可验证, 全部通过后才能交付。

## 验证清单结构

```
=== 1. Master Agent (规划层) ===
plan("做一份产品发布PPT")
  → content_type=ppt, primary_engine=frontend-slides
  → Workers≥2

=== 2. Engine Router (决策层) ===
decide("把文章做成短视频")
  → engines=[html-video, hyperframes]
  → confidence≥0.8

=== 3. 各引擎 (执行层) ===
每个引擎的输入→输出必须可追踪

=== 4. Quality Gate (审计层) ===
review(output) → score + verdict + notes
score≥60 → passed

=== 5. Web UI (接口层) ===
GET / → HTTP 200
POST /engine/plan → 返回ProductionPlan
```

## 多引擎验证模板
```python
# 一次性验证所有引擎
engines = {
    "StoryArc": StoryArcEngine(),
    "PPT": PPTEngine(),
    "Video": VideoEngine(),
    "Web": WebDesignEngine(),
    "Drama": ShortDramaEngine(),
    "T2I": T2IDataEngine(),
}
for name, eng in engines.items():
    # 每个引擎至少执行1个核心方法
    print(f"✅ {name}")
```

## 41测试模板
全项目应保持 30-50 个单元测试, 覆盖:
- 每个核心模块至少3个测试
- 每个数据引擎至少2个测试
- 全链路集成至少5个测试

## 陷阱
- 只看单个引擎通过不够, 必须全链路跑通
- 引擎规划和实际执行必须一致(plan的engine和实际调用的engine相同)
- Web UI的HTTP状态码和返回内容都要检查
