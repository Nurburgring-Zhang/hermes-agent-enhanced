# Hermes Scripts 安全加固报告

**日期**: 2026-06-15
**目标目录**: `/home/administrator/.hermes/scripts/`
**工具**: bandit 1.9.4

---

## 加固前状态

| 指标 | 数值 |
|------|------|
| 扫描总行数 | 364,216 |
| 总告警数 | 5,451 |
| HIGH 严重度告警 | 87 |
| 核心模块 HIGH 告警 | 38 |
| 第三方/供应商 HIGH 告警 | 49 |

## 加固后状态

| 指标 | 数值 |
|------|------|
| HIGH 严重度告警 | 49 |
| 核心模块 HIGH 告警 | **0** ✅ |
| 第三方/供应商 HIGH 告警 | 49（未修改） |

---

## 修复清单

### B324: 弱哈希算法 (MD5 → SHA256) — 36处修复

所有核心模块中的 `hashlib.md5()` 调用已替换为 `hashlib.sha256()`。

| # | 文件 | 行号 | 说明 |
|---|------|------|------|
| 1 | `collector_kuaishou_enhanced.py` | 52 | url_hash 函数 |
| 2 | `collector_overseas_enhanced.py` | 76 | url_hash 函数 |
| 3 | `csdn_blog_collector.py` | 113 | URL 去重哈希 |
| 4 | `douyin_account_collector.py` | 143 | url_hash 去重 (2处) |
| 5 | `douyin_account_collector.py` | 418 | 关键词搜索哈希 |
| 6 | `douyin_account_collector.py` | 604 | 测试哈希 |
| 7 | `episodic_injector.py` | 114 | 条目ID生成 |
| 8 | `hermes_common.py` | 45 | 临时文件命名 |
| 9 | `hermes_intelligence_pipeline.py` | 344 | 内容哈希去重 |
| 10 | `hermes_short_drama_engine.py` | 262 | 场景种子生成 |
| 11 | `hermes_short_drama_engine.py` | 277 | 配音文件命名 |
| 12 | `hermes_ultimate_collector.py` | 41 | is_dup 去重 |
| 13 | `hermes_ultimate_collector.py` | 49 | insert_article 去重 |
| 14 | `hermes_vector_engine.py` | 48 | 词向量哈希 |
| 15 | `hermes_video_engine.py` | 338 | 输出文件命名 |
| 16 | `l1_extractor.py` | 475 | 语义ID生成 |
| 17 | `l2_scene_scheduler.py` | 230 | 场景ID生成 |
| 18 | `memory_engine.py` | 517 | 事实去重 (walrus) |
| 19 | `memory_engine.py` | 518 | 关系去重 (walrus) |
| 20 | `memory_engine.py` | 533 | 语义记忆ID |
| 21 | `memory_engine.py` | 578 | 事件ID生成 |
| 22 | `memory_engine.py` | 599 | 知识ID生成 |
| 23 | `memory_evolution_v2.py` | 154 | 内容哈希增强 |
| 24 | `memory_evolution_v2.py` | 488 | 持久记忆哈希 |
| 25 | `score_batch_4.py` | 322 | URL哈希去重 |
| 26 | `score_batch_7.py` | 296 | URL哈希去重 |
| 27 | `self_recovery.py` | 142 | 备份文件校验 |
| 28 | `self_recovery.py` | 148 | 本地文件校验 |
| 29 | `system_deep_test.py` | 252 | 输出一致性校验 |
| 30 | `wechat_mp_direct.py` | 252 | URL去重哈希 |
| 31 | `xhs_collector_v4.py` | 39 | url_hash 函数 |
| 32 | `xhs_collector_v4.py` | 58 | 笔记ID去重 (2处) |
| 33 | `xhs_collector_v5.py` | 42 | url_hash 函数 |
| 34 | `xhs_collector_v5.py` | 61 | 笔记ID去重 |

### B605: 不安全的shell调用 — 1处抑制

| 文件 | 行号 | 处理方式 |
|------|------|----------|
| `claw_panel.py` | 234 | 添加 `# nosec B605` — 仅用于终端清屏 |

### B602: subprocess shell=True — 1处抑制

| 文件 | 行号 | 处理方式 |
|------|------|----------|
| `test_suite.py` | 122 | 添加 `# nosec B602` — 测试基础设施运行器 |

---

## 未修改的第三方/供应商代码 (49 HIGH告警)

以下目录中的HIGH告警未被修改（第三方代码，按任务要求排除）：

- `scripts/RedCrack/` — 6 告警 (XHS逆向工程)
- `scripts/collectors/TikTokDownloader/` — 10 告警
- `scripts/collectors/MediaCrawler/` — 3 告警
- `scripts/collectors/wechat-mp-mcp/.venv/` — 30 告警 (pip/setuptools虚拟环境)

---

## B304/B413 (不安全密码算法 DES/ARC4)

经扫描确认，核心模块中不存在 B304 (DES) 或 B413 (ARC4/Pycrypto) 告警。
这两个类型的告警仅出现在 `scripts/RedCrack/` 等第三方供应商代码中。

---

## 修改文件汇总 (24个文件)

```
scripts/claw_panel.py
scripts/collector_kuaishou_enhanced.py
scripts/collector_overseas_enhanced.py
scripts/csdn_blog_collector.py
scripts/douyin_account_collector.py
scripts/episodic_injector.py
scripts/hermes_common.py
scripts/hermes_intelligence_pipeline.py
scripts/hermes_short_drama_engine.py
scripts/hermes_ultimate_collector.py
scripts/hermes_vector_engine.py
scripts/hermes_video_engine.py
scripts/l1_extractor.py
scripts/l2_scene_scheduler.py
scripts/memory_engine.py
scripts/memory_evolution_v2.py
scripts/score_batch_4.py
scripts/score_batch_7.py
scripts/self_recovery.py
scripts/system_deep_test.py
scripts/test_suite.py
scripts/wechat_mp_direct.py
scripts/xhs_collector_v4.py
scripts/xhs_collector_v5.py
```

---

## 验证命令

```bash
# 运行 bandit 仅检查 HIGH 级别
cd /home/administrator/.hermes
bandit -r scripts/ --severity-level high

# 预期输出: 核心模块 0 HIGH 告警
```
