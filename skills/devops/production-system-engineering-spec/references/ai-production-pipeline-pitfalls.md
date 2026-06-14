# AI内容生产管线审计坑 — 2026-06-09

## Agent Company 生产管线

### IsolationTask接口兼容性
IsolationTask 是 @dataclass，字段固定。调用方(production_chain_v2.py)传了sop和tools参数但dataclass没定义。
根因: 两个文件分属不同目录(agents_company/ vs scripts/)，各改了各的没同步。

**预防**: @dataclass增加字段后必须验证:
```python
python3 -c "from multi_agent_engine import IsolationTask; \
    t = IsolationTask(task_id='t', agent_id='a', agent_name='n', \
    sop={'steps':['x']}, tools=['file']); print('OK')"
```

### 质量门禁缺失
旧代码所有阶段跑完后直接 status=delivered，即使全部失败。
正确模式: 收集每个阶段的真实结果，≥4/6通过才delivered。

**预防**: run_full_chain 的结尾不能写死 delivered，必须根据成功阶段数动态判定。

### 35天空窗期
production_chain 从2026-05-04到2026-06-08停了35天。
根因: production_chain没有cron自动触发，依赖手动启动。
修复: 加cron每天8:00执行。

**预防**: 任何管线类脚本创建后立即配置cron触发器。

## 无限画布生产引擎

### 引擎选择器参数化
每个引擎有适用条件，EngineRouter需要:
- 内容类型匹配关键词
- 质量/成本/速度综合评分
- 至少两个候选(主引擎+fallback)

### 外部CLI的可用性检查
调用外部CLI前必须先检查:
```bash
which html-video 2>/dev/null || echo "NOT INSTALLED"
which npx 2>/dev/null || echo "NOT INSTALLED"
```
不可用时走fallback逻辑(不抛异常)。

### 故事弧引擎的beats兼容性
beats可以是dict或dataclass，代码必须同时支持两种类型访问:
```python
def _get(b, key, default=0.0):
    return b.get(key, default) if isinstance(b, dict) else getattr(b, key, default)
```

### 连续镜头约束
短剧/视频多镜头生成时，连续3个以上相同景别需要强制切换。
实现方式: 在shot分配循环中跟踪prev_shot_type，检测到重复时调_alternate_shot_type。
