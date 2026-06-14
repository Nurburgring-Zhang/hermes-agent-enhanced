# BERTopic Analysis of to_chi Dataset (2026-05-24)

## Overview
Applied BERTopic with `paraphrase-multilingual-MiniLM-L12-v2` embedding model to 20,000 samples from to_chi (javrate + xhs). Discovered 17 latent themes.

## Theme Distribution

| Topic ID | Count | Keywords (Top 5) | Interpretation |
|----------|-------|-------------------|----------------|
| -1 (noise) | 4,208 | - | Mixed/ambiguous |
| 0 | 10,234 | 浅景深, 写实风格, 高分辨率摄影, 暖色调 | Standard indoor portrait |
| 1 | 1,574 | 特写视角, 微距镜头, 柔和自然光 | Close-up/detail |
| 2 | 1,311 | 户外人像摄影, 户外场景, foliage | Outdoor portrait |
| 3 | 966 | 高分辨率摄影, 写实风格, 高对比度 | High-quality portrait |
| 4 | 301 | 特写视角, 双眼紧闭 | Face close-up |
| 5 | 223 | 夏日氛围, 明亮自然光 | Summer outdoor |
| 6 | 197 | 教室环境, 对焦清晰 | Classroom/study |
| 7 | 176 | 夏日氛围, 晴朗天空 | Sunny outdoor |
| 8 | 155 | 照片, 双眼紧闭 | Close-up detail |
| 9 | 123 | foliage, 自然光 | Outdoor nature |
| 10 | 114 | 临床环境, 护士制服 | Medical/uniform |
| 11 | 106 | 家庭室内场景 | Family indoor |
| 12 | 99 | 户外海滩场景, 晴朗天空 | Beach |
| 13 | 83 | foliage, 宁静氛围 | Nature calm |
| 14 | 68 | 浅景深, 汽车内饰 | Car interior |
| 15 | 62 | 职业着装, 办公环境 | Office |

## Key Insight
BERTopic clusters primarily by **photography parameters** (景深, 风格, 光源) rather than content semantics (年龄, 服装, 道具). The embedding model gives high weight to frequent technical terms like "浅景深" and "写实风格" which appear in most entries.

This is both a limitation and a feature:
- **Limitation:** Cannot discover finer-grained content dimensions (age, clothing type, pose)
- **Feature:** Automatically identifies shooting style clusters that would take hours to define manually

## Application
Use BERTopic topics as a **pre-clustering step** before regex extraction, not a replacement. The 17 topics provide a coarse taxonomy that helps:
1. Understand the data landscape
2. Guide which extraction rules to apply to which cluster
3. Validate that hand-crafted dimension categories match actual data distribution
