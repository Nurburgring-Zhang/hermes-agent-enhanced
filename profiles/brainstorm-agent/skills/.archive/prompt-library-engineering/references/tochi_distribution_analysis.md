# to_chi Full Data Distribution Analysis (2026-05-24)

Based on analysis of all 518,013 entries in to_chi (javrate + xhs).

## Methodology
- Regex-based counting of keyword patterns across all 260 files
- Each entry counted only once per category (first match wins)
- Results guide sampling weights for prompt composition

## Age/Gender Distribution
| Category | Count | Proportion |
|----------|-------|------------|
| 年轻亚裔女性 | 159,040 | 30.7% |
| 年轻女性(无种族) | 13,375 | 2.6% |
| 女孩/少女 | 9,694 | 1.9% |
| 儿童 | 5,519 | 1.1% |
| 年轻男性(亚裔) | 4,933 | 1.0% |
| 年轻男性(无种族) | 4,115 | 0.8% |
| 婴儿 | 2,709 | 0.5% |
| 男孩 | 1,790 | 0.3% |
| 老年女性 | 193 | <0.1% |
| 中年男性 | 96 | <0.1% |
| 老年男性 | 80 | <0.1% |
| 中年女性 | 52 | <0.1% |
| **Unmarked** | ~316,514 | ~61.1% |

## Hair Color Distribution
| Color | Count | Proportion |
|-------|-------|------------|
| 黑色 | 104,950 | 20.3% |
| 棕色 | 31,546 | 6.1% |
| 白色/银发 | 31,279 | 6.0% |
| 金色 | 10,840 | 2.1% |
| 红色 | 7,072 | 1.4% |

## Skin Tone Distribution
| Tone | Count | Proportion |
|------|-------|------------|
| 白皙 | 17,988 | 3.5% |
| 苍白 | 3,010 | 0.6% |
| 小麦/古铜 | 315 | 0.1% |

## Scene Distribution (Top 20)
| Scene | Count | Proportion |
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

## Indoor vs Outdoor
| Type | Count | Proportion |
|------|-------|------------|
| 室内 (indoor) | 131,792 | 25.4% |
| 户外 (outdoor) | 90,701 | 17.5% |
| 摄影棚 (studio) | 14,809 | 2.9% |

## Special Categories
| Type | Count | Proportion |
|------|-------|------------|
| 内衣 (lingerie) | 40,966 | 7.9% |
| 裸体 (nude) | 34,228 | 6.6% |
| 泳衣 (swimsuit) | 12,173 | 2.3% |

## Pose Distribution
| Pose | Count | Proportion |
|------|-------|------------|
| 站立 | 142,384 | 27.5% |
| 坐着 | 81,038 | 15.6% |
| 躺着 | 22,131 | 4.3% |
| 趴着 | 13,536 | 2.6% |
| 倚靠 | 9,900 | 1.9% |
| 盘腿 | 7,706 | 1.5% |
| 跪着 | 6,835 | 1.3% |
| 蹲着 | 1,410 | 0.3% |

## Application to Prompt Generation
Use these proportions to guide sampling weights in the composition engine:

```python
SAMPLING_WEIGHTS = {
    'age_sex': {
        '年轻亚裔女性': 0.50,
        '年轻女性': 0.12,
        '女孩/少女': 0.08,
        '年轻男性': 0.08,
        '儿童': 0.05,
        '婴儿': 0.03,
        '其他': 0.14,
    },
    'scene': {
        '卧室': 0.25,
        '摄影棚': 0.15,
        '阳台/天台': 0.12,
        '花园/公园': 0.10,
        '街道/城市': 0.08,
        '户外自然': 0.08,
        '其他': 0.22,
    },
    'pose': {
        '站立': 0.40,
        '坐着': 0.25,
        '躺着': 0.08,
        '趴着': 0.05,
        '倚靠': 0.04,
        '其他': 0.18,
    },
    'special': {
        'regular': 0.83,
        'lingerie': 0.08,
        'nude': 0.07,
        'swimsuit': 0.02,
    }
}
```
