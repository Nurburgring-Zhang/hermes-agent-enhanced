# 2026-05-31 全能力深度盘点记录

## 诊断方法
- 使用 `write_file` 创建诊断脚本（避免沙箱转义问题）
- 一次检测一个子系统：先用快速快照（terminal+python3 -c）再用深度脚本
- 使用 `delegate_task` 并行3路执行修复：评分清理 + Ollama桥修复 + 索引/齿轮验证

## 关键发现

### 1. 数据库位置与实际路径不符
技能中写死的路径如 `/mnt/d/openclaw/experts/`、`memories/*.md` 不存在。实际路径：
- Experts目录：`~/.hermes/agents_company/experts/` (390个)
- Memory DB：`~/.hermes/active_memory.db` (35表，含memory_semantic/scene/profile等)
- Mem0：`~/.hermes/memory/mem0_data/mem0_store.db` (15,495条)

### 2. cleaned_intelligence评分覆盖度15,129条100%
但存在9条ai_score_total=0的数据来自热点平台（weibo/douyin/baidu）的Label/Score元数据条目，无实际内容。已归档+删除。

### 3. Ollama通过WSL桥成功
- LM Studio 8080端口被rogue HTTP server占用（一个中文游戏页面），清除后仍未启动API server
- Ollama在Windows上运行，从WSL通过`172.31.32.1:11434`可达
- 7个模型可用，选`qwen3-14b-creativewrite:latest`

### 4. L3画像生成的`_call_local_llm`只试localhost
L3脚本只试localhost:8080和localhost:11434，没有WSL host IP fallback。
llm_bridge.py已修复添加`_get_wsl_host_ip()`函数。

### 5. 推送记录
- 今日218条全部成功
- push_records总计4,263条
- push_records表没有`ai_score_total`列（旧诊断脚本用的列名错误）
- push_records列：id, cleaned_id, title, content, url, source, platform, push_level, push_channel, push_status, push_time, push_response, opened, created_at

### 6. 齿轮
- gear_registry.json中gears={}是空的（不是bug，齿轮注册在tasks对象中）
- 3个已注册链式任务（含签名凭证）
- wake_guide显示gear_health=healthy, gear_heartbeat=1.0min

### 7. 生产引擎
- 3个遗留测试任务（test_task_001, test_task_verify_001/002）来自5月25-26日
- 已全部清理
- engine_running=True

## 统计快照
| 指标 | 值 |
|------|-----|
| Scripts | 279个 |
| Skills (包含辅助目录) | 233个 |
| Skills (含SKILL.md) | ~198个 |
| Agents Employees | 130人（12部门） |
| Experts | 390人（30领域） |
| active_memory.db memory_semantic | 69条 |
| active_memory.db memory_scene | 16个 |
| active_memory.db memory_profile | 3条 |
| active_memory.db structmem_events | 8,377个 |
| active_memory.db memory_episodic | 78条 |
| mem0_meta | 15,495条 |
| intelligence.db raw_intelligence | 13,971条 |
| intelligence.db cleaned_intelligence | 15,065条 |
| intelligence.db push_records | 4,263条 |
| intelligence.db archive_cleaned | 1,723条 |
| Cron | 36行 |
| DBs总计 | 50+个 |

## 修复项清单
1. ✅ 9条零分数据归档+删除
2. ✅ Ollama桥修复（llm_bridge.py + config.yaml）
3. ✅ LM Studio 8080端口清理（rogue HTTP server）
4. ✅ 生产引擎3个测试任务清理
5. ✅ wake_guide更新（ai_scoring_pending=6→0, today=0→464）
6. ✅ context_index重建验证（20 sections）
7. ✅ 64条低分数据归档（score<20→archive_cleaned）
