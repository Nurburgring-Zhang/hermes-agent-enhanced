# 重复Skill检测跟踪

## 当前状态 (2026-06-01)
自进化集群模块1分析 180 个skill，检测到 **13 组可能重复**。

## 检测方法
- tags交集 ≥2 个相同标签
- 同一domain/category下的skill自动排除（如 `expert-*` 系列内部）
- 只报告跨类别的重叠

## 已重复出现 ≥3 次 — 建议人工合并

| 重复对 | 首次发现 | 最近出现 | 重叠tags | 说明 |
|--------|---------|---------|---------|------|
| `legal-ethics-experts` ↔ `expert-legal` | 2026-05-28 | 2026-06-01 | compliance, ethics, legal | legal-ethics-experts是10人团队skill，expert-legal是单人专家。内容深度不同但功能严重重叠 |
| `security-experts` ↔ `expert-network-security` | 2026-05-28 | 2026-06-01 | cybersecurity, penetration-testing, security | 同上模式，团队 vs 个人 |

## 已重复出现 1-2 次 — 可能误报，暂不处理

| 重复对 | 重叠tags | 分析 |
|--------|---------|------|
| `expert-ai-model-compress` ↔ `expert-ai-automl` | expert, nas, ai-ml | 都属AI领域，但一个专注模型压缩，一个专注AutoML。NAS是共窗口但不是最终功能重叠 |
| `workflow-engine` ↔ `agents-company` | workflow, orchestration, automation | workflow-engine是通用编排skill，agents-company是130人Agent Company team。功能层面确实有重叠 |
| `psychology-cognition-experts` ↔ `education-training-experts` | openclaw, cognition, expert-team | openclaw迁移遗留的tag引用，本质不重复 |
| `bio-medicine-experts` ↔ `expert-bioinformatics` | biology, bioinformatics, genomics | 团队 vs 个人，类似legal模式 |
| `supplychain-logistics-experts` ↔ `energy-environment-experts` | openclaw, sustainability, expert-team | openclaw遗留tag |
| `devops-experts` ↔ `expert-mathematical-modeling` | chaos-engineering, sre, devops | 松散重叠，内容差异大 |
| `expert-product-strategy` ↔ `product-experts` | business, product, growth | 团队 vs 个人模式重现 |
| `data-storage-experts` ↔ `expert-frontend-architecture` | data, etl, data-warehouse, data-lake | 似是而非（数据存储 vs 前端架构都有data字眼但非同类） |
| `mobile-iot-experts` ↔ `expert-quality-assurance` | mobile, android, ios | mobile IoT团队 vs 移动性能专家，方向不同 |
| `expert-mathematical-modeling` ↔ `expert-comm-network` | reliability, sre, devops | 数学建模 vs 通信网络，tag重叠但内容无关联 |

## 总体趋势
| 日期 | 扫描skill数 | 检测重复对 | 稳定重复对 | 说明 |
|------|-----------|-----------|-----------|------|
| 2026-05-30 | 157 | 9 | 2 | 初始检测，大部分为新发现 |
| 2026-06-01 | 180 | 13 | 2 | 多了23个新skill，引入更多(可能是误报的)匹配 |
| 2026-06-02 (18:07) | 182 | 13 | 2 | 18:07第四轮, 稳定182个skill, 13对重复完全一致 — 全天4轮均确认此数 |

## 全天观察结论
4轮扫描稳定保持13对重复。182个skill规模下重复检测已达稳态，新增skill不会立刻产生新重复对。
- 已连续≥3次的稳定重复对: **`legal-ethics-experts↔expert-legal`**, **`security-experts↔expert-network-security`**
- 建议人工合并这两对。

## 合并建议优先级
1. **高优先级** (连续≥3次 + 功能实际重叠): `legal-ethics-experts→expert-legal`, `security-experts→expert-network-security`
2. **中优先级** (连续≥3次但可能误报): `bio-medicine-experts→expert-bioinformatics` — 等第3次确认
3. **低优先级** (1次): 其余10对 — 全部待确认再判断
