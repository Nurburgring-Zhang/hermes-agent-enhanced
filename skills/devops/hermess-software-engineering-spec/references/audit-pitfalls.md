# System Audit Methodology — 2026-06-11

## 关键教训: 审核不运行 = 没审核

2026-06-10/11 IMDF深度审核发现39个bug，其中没有一个是在之前任何"审核"中被发现的。
之前的"审核"只是读了代码说"看起来没问题"。

**根本原因**: 读代码只能检查语法，不能检查运行时行为。

## 核心禁令: POST端点必须走完整引擎调用

routes_extended.py 16个POST端点全部只返回 `{**data}` 不调用引擎。
检测方法: 看一眼return语句是否包含 from engines.xxx import 和 engine.xxx()

## 自豁免陷阱

执行AI会在干活时跳过审核 — 解决方法是: 取消执行AI的判断权。
没有"这个操作可以不审"的例外。每个工具调用前必须执行 pre_review()。

## 大规模能力穿透式审计流程

当需要检查系统"所有能力"的真实运行状态（而非表面已启用）时：

### Step 1: 并行扫描
用 delegate_task 分发多个子任务并行扫描不同维度，不要串行 grep。

### Step 2: 按层穿透

```
┌─ Process layer     ── systemctl status / ps aux / docker ps
├─ Cron layer         ── crontab -l + hermes cron list（双重检查）
├─ Log layer          ── tail -50 <log> 检查最近活动和错误
├─ DB layer           ── sqlite3 直接查记录行数、最新时间戳
├─ Import/load layer   ── python3 -c "import module" 验证可导入
└─ Functional layer   ── 实际触发脚本并观察真实产出
```

不要只看前两层就宣布通过。

### Step 3: 分级修复

| 层级 | 典型问题 | 修复方式 |
|------|---------|---------|
| systemd 服务崩溃 | 路径错误(.venv vs venv), PYTHONPATH 未设置 | 改ExecStart + WorkingDirectory |
| cron 缺失 | 迁移时丢失 | crontab -l 双重检查 |
| 脚本import错误 | venv和系统Python版本不一致 | 用 venv 的 python |
| 接口不兼容 | dataclass字段不一致 | 两端同时改 |
| 数据管道断裂 | 中间处理脚本报错 | 逐段检查 |

## 三层验证(审计后必须做)
改完后的验证顺序:
1. Process: systemctl status / ps aux
2. Log: tail -50 检查最近活动、错误
3. Functional: 实际调用并看到真实产出

## Skills合并评估框架

### 合并条件
两个skill可以合并当且仅当以下条件同时满足:
- 它们描述的是同一个系统/流程的不同侧面
- 或者一个是旧版(auto-generated)已被新版替代
- 或者它们在调用链中是流水线步骤,Agent需要全部加载才能完成一件事

### 不合并的条件
- 技术路线不同(如录屏vs原生渲染) — 合了会污染context
- 一个是底层基础设施,另一个是上层应用
- 功能独立且触发条件不同

### 合并执行
1. 先备份到 /mnt/d/Hermes/备份/skills_merge_*
2. 先创建伞skill(absorbed_into指向的目标)
3. 再逐项删除旧skill 并指定 absorbed_into=伞skill名
4. 验证skills list中旧skill消失,新skill可加载

## 大规模调研方法论

### 调研范围界定
每次调研前先确定:
- 调研目标(什么需求背景)
- 调研覆盖(哪些维度:开源项目/商业API/学术论文/实战文章)
- 与现有系统的关系(已有vs缺失vs可强化)

### 调研记录格式
每篇文章/项目记录:
- 核心价值(一句话)
- 关键参数和技术细节
- 与"我们的项目"的直接关系
- 可复用的设计模式
- 许可证(能否商用)

### 从调研到架构转化
调研产出后:
1. 对比分析: 找出各方案的最优点
2. 融合设计: 把多个方案的最优点组合成融合方案
3. 对标超越: 列出对标项目,逐项说明超越点
4. 架构文档: 输出完整设计说明书

## 跨项目源码分析模式

### 分析顺序
1. README — 项目定位和功能总览
2. CLI文档 — 可调用的命令和参数
3. API文档 — 编程接口
4. Core模块 — 核心实现
5. Test目录 — 使用示例

### CLI调用集成
```python
import subprocess, tempfile, json

# 调用外部CLI的一般模式
def call_external_cli(cmd_args: list, timeout: int = 120) -> dict:
    try:
        r = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return json.loads(r.stdout) if r.stdout else {"status": "ok"}
        return {"status": "error", "stderr": r.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except json.JSONDecodeError:
        return {"status": "ok_text", "output": r.stdout[:500]}
```

### Fallback模式
每个外部CLI调用必须有fallback:
```python
try:
    result = call_render_with_html_video(...)
except (FileNotFoundError, subprocess.CalledProcessError):
    result = fallback_html_screenshot(...)
```
