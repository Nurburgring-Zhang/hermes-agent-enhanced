# 规则评分 → 真正AI评分升级工作流

## 为什么要升级

`hermes_ai_scoring.py` 的 `--batch` 模式只处理 `ai_scored_at IS NULL` 的真正未评分条目。
但数据库中大量条目已有**规则评分**（`ai_score_reasoning LIKE '%keyword%'` 或 `'%规则%'` 或 `'%规则引擎评分%'`），
它们有内容（>100字符）但没有经过真正的AI内容理解评分。

区别：
| | 规则评分 | 真正AI评分 |
|---|---|---|
| 评分方式 | 本地关键词匹配 | DeepSeek API 六维理解 |
| 质量 | 关键词依赖，可能误判 | AI理解每条内容实际价值 |
| 区分字段 | `ai_score_reasoning` 含"规则评分"/"keyword" | `ai_score_reasoning` 含 `scarcity_reason` 等各维度推理 |
| 改造意义 | 分数可能偏差大 | 更精准，影响推送排序 |

## 检测有多少规则评分条目可升级

```sql
SELECT COUNT(*) FROM cleaned_intelligence
WHERE (ai_score_reasoning LIKE '%keyword%' 
       OR ai_score_reasoning LIKE '%规则%' 
       OR ai_score_reasoning LIKE '%规则引擎评分%'
       OR ai_score_reasoning LIKE '%规则评分%')
AND LENGTH(COALESCE(content,'')) > 100;
-- → 返回可升级条数（有内容才能AI理解评分）
```

## 已有脚本

`scripts/ai_score_upgrade_batch.py` — 直接调用 `hermes_ai_scoring.score_items_via_openrouter()` 升级200条。

```bash
cd ~/.hermes && python3 scripts/ai_score_upgrade_batch.py
```

**工作流**：
1. 加载 `.env` 中的 `DEEPSEEK_API_KEY`
2. 从 `active_memory.db` 加载 `keyword_weights`（偏好权重）
3. 查询符合升级条件的200条（按 `ai_score_total DESC, published_at DESC` 排序）
4. 每2条一批评分（DeepSeek Chat API, temperature=0.3）
5. AI评分写入 `ai_score_total` 等六维字段 + `ai_score_reasoning`（含各维度推理）

## 性能基准（2026-05-29实测）

### 首次基准（200条完整跑完）

| 指标 | 值 |
|---|---|
| 一次性处理 | 200条 |
| 批处理模式 | 每批2条调DeepSeek API |
| 总API调用 | 100批 |
| 总耗时 | ~14分钟（~8秒/批） |
| 升级后平均分 | 71.8 |
| 优秀(≥80) | 45条 (22.5%) |
| 良好(60-79) | 137条 (68.5%) |
| 中等(30-59) | 16条 (8.0%) |

均分71.8显著高于规则评分（规则评分通常在40-55之间），说明AI理解评分更准确地识别了内容的真实价值。

### 二次验证（2026-05-29 05:32 cron运行）

| 指标 | 值 |
|---|---|
| 待升级条数 | 194 |
| 实际完成 | 140（600s cron timeout前） |
| 超时前已处理 | 72.2% |
| 失败原因 | 97次API调用 × ~8s = ~776s > 600s timeout |
| **关键发现** | **脚本在超时前已增量保存所有已完成批次的评分，140条0丢失** |
| 本轮最高分 | 75.0（阿里云Qwen Cloud） |
| 本轮最低分 | 5.0 |
| 本轮60-79分 | 39条 |

**重要结论**：在600s超时环境下，每次最多处理~140-160条。剩余的规则评分条目在下次运行时自动被选中处理。

**实战建议**：
- 如果规则评分积压 >200条，分多次运行（每次自动处理~140-160条）
- 不需担心超时：`score_items_via_openrouter()` 每5批（10条）增量保存一次，**超时只损失当前未保存的批次**
- 19200条规则评分积压需要约120-140次cron调度才能全部升级为真正AI评分

## 与 `--batch` 模式的区别

| | `--batch 200` | `ai_score_upgrade_batch.py` |
|---|---|---|
| 查询条件 | `ai_scored_at IS NULL` | `ai_score_reasoning LIKE '%规则%'` |
| 适用 | 新入库未评分的干净数据 | 旧规则评分数据升级 |
| API | `score_items_via_openrouter()` | 同上，直接调用 |

两者共享相同的评分函数 `score_items_via_openrouter()`，区别仅在于数据选择条件。

## 检查升级结果

```sql
-- 查询最近AI评分升级的条目
SELECT id, title, ai_score_total, 
       SUBSTR(ai_score_reasoning, 1, 80) as reason
FROM cleaned_intelligence
WHERE ai_scored_at > datetime('now', '-30 minutes')
  AND ai_score_reasoning LIKE '%scarcity_reason%'
LIMIT 10;
```

## 注意

- 无内容（≤100字符）的规则评分条目无法升级——没有足够内容让AI理解，保留规则评分合理
- 升级操作是**覆盖式写入**，旧规则评分被新AI评分替换
- 大库（>200条可升级）如需全量升级，需要分多次运行脚本
- **坑：** DeepSeek API返回的JSON不含 `id` 字段，但 `score_items_via_openrouter()` 会在 `parse_ai_response()` 中按 `items` 列表顺序自动填充id。如果直接调用 `parse_ai_response()` 而不传入 `items` 参数，返回的JSON数组会缺少 `id`，导致 `save_scores_to_db()` 无法写入。（2026-05-29修复后已自动处理）
