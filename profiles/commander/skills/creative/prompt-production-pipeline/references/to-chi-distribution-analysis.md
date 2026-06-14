# TO-CHI Data Distribution Analysis

## Source
- Total entries: 518,013
- Source: D:\ComfyUI\提示词\to_chi
- Files: 260 (javrate 68 + xhs 192)
- javrate: ~135,098 lines, all人物写真
- xhs: ~384,912 lines, mixed content (人物 + 室内 + 产品 + 食物)

## Excluded Data
- 室内设计 (interior design photos)
- 美甲 (nail art)
- 食物 (food photography)
- 纯产品展示 (product-only shots)

## Age/Sex Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| 年轻亚裔女性 | 159,040 | 30.7% |
| 年轻女性(无种族) | 13,375 | 2.6% |
| 女孩/少女 | 9,694 | 1.9% |
| 儿童 | 5,519 | 1.1% |
| 年轻男性 | 4,933 | 1.0% |
| 年轻男性(无种族) | 4,115 | 0.8% |
| 婴儿 | 2,709 | 0.5% |
| 男孩 | 1,790 | 0.3% |
| 老年女性 | 193 | 0.0% |
| 中年男子 | 96 | 0.0% |
| 老年男子 | 80 | 0.0% |
| 中年女性 | 52 | 0.0% |
| **无明确标记** | ~316,000 | ~61% |

## Hair Color Distribution

| Color | Count | Percentage |
|-------|-------|------------|
| 黑色/深色 | 104,950 | 20.3% |
| 棕色 | 31,546 | 6.1% |
| 白色/银发 | 31,279 | 6.0% |
| 金色 | 10,840 | 2.1% |
| 红色 | 7,072 | 1.4% |

## Skin Color Distribution

| Type | Count | Percentage |
|------|-------|------------|
| 白皙 | 17,988 | 3.5% |
| 苍白 | 3,010 | 0.6% |
| 小麦/古铜 | 315 | 0.1% |

## Scene Distribution (Top 20)

| Scene | Count | Percentage |
|-------|-------|------------|
| 卧室 | 44,638 | 8.6% |
| 摄影棚/工作室 | 38,691 | 7.5% |
| 阳台/天台 | 34,132 | 6.6% |
| 花园/公园 | 24,744 | 4.8% |
| 街道/城市 | 20,621 | 4.0% |
| 户外自然 | 14,223 | 2.7% |
| 森林 | 13,411 | 2.6% |
| 餐饮空间 | 12,394 | 2.4% |
| 浴室 | 10,073 | 1.9% |
| 客厅 | 9,683 | 1.9% |
| 厨房 | 8,457 | 1.6% |
| 海滩 | 6,757 | 1.3% |
| 舞台/剧院 | 3,711 | 0.7% |
| 车内 | 2,712 | 0.5% |
| 文化空间 | 2,360 | 0.5% |
| 泳池 | 2,218 | 0.4% |
| 办公室 | 1,832 | 0.4% |
| 教堂/寺庙 | 1,607 | 0.3% |
| 更衣室/化妆间 | 303 | 0.1% |

## Environment Type

| Type | Count | Percentage |
|------|-------|------------|
| 室内 (indoor) | 131,792 | 25.4% |
| 户外 (outdoor) | 90,701 | 17.5% |
| 摄影棚 (studio) | 14,809 | 2.9% |

## Pose Distribution

| Pose | Count | Percentage |
|------|-------|------------|
| 站立 | 142,384 | 27.5% |
| 坐着 | 81,038 | 15.6% |
| 躺着 | 22,131 | 4.3% |
| 趴着 | 13,536 | 2.6% |
| 倚靠 | 9,900 | 1.9% |
| 盘腿 | 7,706 | 1.5% |
| 跪着 | 6,835 | 1.3% |
| 蹲着 | 1,410 | 0.3% |

## Special Attributes

| Attribute | Count | Percentage |
|-----------|-------|------------|
| 内衣 (lingerie) | 40,966 | 7.9% |
| 裸体 (nude) | 34,228 | 6.6% |
| 泳衣 (swimsuit) | 12,173 | 2.3% |

## Key Insights for Prompt Composition

1. **年轻亚裔女性 dominates at 30.7%** — sampling must reflect this
2. **61% of data has NO explicit age/sex** — these can be used for background/filler
3. **Bedroom is the #1 scene** (8.6%) — interior scenes outnumber outdoor 25.4% vs 17.5%
4. **Standing is the default pose** (27.5%) — sitting is 15.6%, all others <5%
5. **内衣/裸体合计 14.5%** — significant erotic content segment
6. **黑色头发 dominates** (20.3%) — brown and silver at ~6% each
