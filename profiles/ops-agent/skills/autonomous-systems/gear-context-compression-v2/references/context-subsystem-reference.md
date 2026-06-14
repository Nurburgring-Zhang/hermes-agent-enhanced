# 上下文子系统参考（2026-05-27 构建）

## 架构概览

```
对话启动 → session_init_check (自检)
              │
              ▼
    context_index_system (构建索引摘要 2120tokens + 14章节文件)
              │
              ▼
    context_auto_assoc (按任务类型预加载3章 1762tokens)
              │
              ▼
    surgical_context_slicer (按任务切分 947tokens)
              │
              ▼
    context_packer (通用压缩 2927tokens, 86.3%)
              │
              ▼
    cross_session_cache (跨轮次延续)
              │
              ▼
    对话中 → feedback_push (每子阶段推送进度)
              │
    无对话时 → status_reporter (每40分推送状态)
              │
    每1分钟 → context_selfcheck (14项自检)
```

## 脚本清单

| 脚本 | cron频率 | 输出文件 | 职责 |
|------|----------|----------|------|
| context_packer.py | 每1分 | context_pack.json | SOUL.md压缩 21312→2927t (86.3%) |
| surgical_context_slicer.py | 每1分 | surgical_context.json | 按任务类型(fix/push/develop)精准切分 |
| context_auto_assoc.py | 每1分 | context_auto_assoc.json | 分析任务意图→预加载3章摘要 |
| cross_session_cache.py | 每1分 | cross_session_cache.json | 跨轮次缓存+进度自动更新 |
| context_index_system.py | 每1分 | context_index.json + context_sections/ | 索引摘要(2120t)+14章节文件 |
| context_selfcheck.py | 每1分 | context_selfcheck.json | 14项全面自检 |
| status_reporter.py | 每40分+每2h | (推送微信) | 无对话时推送系统状态 |
| feedback_push.py | 按需调用 | (推送微信) | 长任务子阶段完成推进度 |
| session_init_check.py | 对话启动 | session_init.log | 启动自检+异常告警 |

## 索引-复原机制

**第一次对话：**
1. context_index_system 构建：索引摘要(2120t) + 14个章节文件
2. context_auto_assoc 按任务类型预加载3章(1762t)
3. 传给AI总共 ~3150t (原始SOUL.md 21312t的85%压缩率)
4. AI如需规则全文 → 从 ~/.hermes/reports/context_sections/<ID>.md 拉取

**后续轮次：**
1. cross_session_cache 保持上一轮进度
2. 只传增量变化（新完成项、新的下一步）
3. 索引路径全部自动映射到真实文件名（已修复硬编码bug）

## 常见陷阱

1. **文件名匹配** — context_sections/ 下文件名有完整后缀(如`八_七条永久执行规则_格林主人最高指令_20260523_固化_`)，不能硬编码缩写。用 glob + stem scan 3层回退
2. **context_index_system 默认命令** — 必须设为 `auto` 而非 `build`（只建章节不建索引）
3. **cronjob系统 vs crontab** — 有的任务在 cronjob 系统里不在 crontab -l 里，自检要同时查两个
4. **预加载章节为0** — 检查 context_sections 目录是否存在、文件名是否被TASK_SECTION_MAP的短名匹配到
5. **索引可追溯8/10** — 两个路径可能硬编码了不存在的文件名，修成动态glob即可
6. **状态推送重复** — status_reporter 有 30分钟去重逻辑（检查 push_records 最近推送时间）

## 测试清单

每次修改后运行：
```bash
cd ~/.hermes && python3 scripts/context_selfcheck.py
# 期望：14/14 全部通过，全部可追溯
```

单项测试：
```bash
# 验证预加载
python3 scripts/context_auto_assoc.py | grep "preloaded="

# 验证压缩率
python3 scripts/context_packer.py | grep "compression"

# 验证索引可追溯
python3 scripts/context_index_system.py
python3 -c "import json,re; idx=json.load(open('reports/context_index.json')); paths=re.findall(r'→ (context_sections/[^\\s]+)', idx['index_text']); print(sum(1 for p in paths if Path.home().joinpath('.hermes/reports/',p).exists()), '/', len(paths))"
```
