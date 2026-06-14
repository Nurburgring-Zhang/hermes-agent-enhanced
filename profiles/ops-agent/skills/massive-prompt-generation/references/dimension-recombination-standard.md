# Dimension Recombination Standard — For Prompt Generation

## Source Data

V7 dimension libraries at `D:\\Hermes\\1000000提示词\\高质量模板\\维度库_api_v7\\`

| Dimension | Size | Avg len | Natural frequency |
|-----------|------|---------|-------------------|
| A01_年龄性别 | 57,282 | 7.8字 | 97% (person data) |
| A02_发型 | 52,576 | 7.9字 | 97% |
| A03_肤色 | 23,908 | 5.0字 | 7% |
| A04_表情眼神 | 36,192 | 7.6字 | 80% |
| A05_姿势 | 128,596 | 13.3字 | 100% |
| B01_场景环境 | 449,266 | 18.6字 | 100% |
| B02_活动行为 | 103,407 | 12.1字 | 99.8% |
| C01_美学风格 | 275,477 | 5.2字 | 96.8% |
| C02_光照条件 | 135,061 | 6.9字 | 100% |
| C03_色彩调性 | 133,684 | 8.7字 | 100% |
| C04_构图镜头 | 215,114 | 6.1字 | 99.6% |
| D01_服装款式 | 88,673 | 16.3字 | 80.6% |
| D02_配饰鞋帽 | 55,051 | 12.7字 | 35.4% |
| D03_材质质感 | 106,597 | 7.4字 | 40.0% |
| D04_动态效果 | 11,420 | 9.3字 | 73.6% |
| D05_天气时间 | 32,218 | 5.1字 | 54.4% |
| D06_氛围情感 | 107,369 | 5.0字 | 73.8% |

## 12 Mandatory Dimensions (every prompt)

```
[OPEN]    A01_年龄性别 + A02_发型           → 人物出场
[SCENE]   A05_姿势 + B01_场景环境            → 人物与空间
[DRESS]   D01_服装款式                       → 穿着
[ACTION]  B02_活动行为 + A04_表情眼神         → 动作表情
[LIGHT]   C02_光照条件 + C03_色彩调性         → 光影色彩
[FRAME]   C04_构图镜头                       → 画面框架
[CLOSE]   C01_美学风格 + D06_氛围情感         → 风格收尾
```

## 3 Optional Dimensions

Randomly add 0-2 of:
- D02_配饰鞋帽 (adds jewelry/shoes detail)
- D03_材质质感 (adds fabric/texture detail)
- D05_天气时间 (adds weather/time context)

## B02/A05 Redundancy Rule

Any pose fragment in A05 (站/坐/跪/躺) MUST also be placed in B02.

## Order Template

1. A01_年龄性别 → A02_发型
2. A05_姿势 → B01_场景环境
3. D01_服装款式
4. [D02_配饰鞋帽] [D03_材质质感] (optional)
5. B02_活动行为 → A04_表情眼神
6. [D05_天气时间] (optional)
7. C02_光照条件 → C03_色彩调性
8. C04_构图镜头
9. C01_美学风格 → D06_氛围情感

## Combination Rules

1. 12 mandatory dimensions, each at least 1 fragment
2. 0-2 optional dimensions, randomly chosen
3. Total fragments per prompt: 15-25
4. No two consecutive fragments from the same dimension
5. Scene-lighting consistency: indoor→soft light, outdoor→natural light
6. Weather-clothing consistency: summer→light, winter→thick

## Prohibitions

- 比喻词（仿佛/犹如/就像/宛如/如同）
- 数字化描述（距离/厚度/角度等具体数字）
- 科技元素（量子/夸克/粒子/齿轮/全息/数据）
- 三手多手（一个人只能有两只手）
- 裸体时D01跳过，D02配饰保留
- 标题/序号/分段 — 必须是一段完整的文字，500-800字
