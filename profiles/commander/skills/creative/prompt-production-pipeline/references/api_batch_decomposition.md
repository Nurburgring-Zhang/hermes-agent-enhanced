# API Batch Decomposition for 17-Dimension Extraction

## The Key Insight (2026-05-25)

**Problem discovered:** The AI was outputting Chinese dimension names ("主体""发型""服装""动作/姿态") instead of the required standard format ("A01_年龄性别""A02_发型""B02_活动行为").

**Root cause:** The system prompt described the dimension DEFINITIONS but didn't explicitly specify the KEY NAMES to use in the JSON.

## The Fix: Exact JSON Key Template

In the system prompt, put the COMPLETE JSON structure at the VERY TOP:

```
输出JSON数组，每个元素是{"条目N":{"A01_年龄性别":[],"A02_发型":[],"A03_肤色":[],"A04_表情眼神":[],"A05_姿势":[],"B01_场景环境":[],"B02_活动行为":[],"C01_美学风格":[],"C02_光照条件":[],"C03_色彩调性":[],"C04_构图镜头":[],"D01_服装款式":[],"D02_配饰鞋帽":[],"D03_材质质感":[],"D04_动态效果":[],"D05_天气时间":[],"D06_氛围情感":[]}}

17个维度键名必须严格使用A01_A02_B01格式。每个维度值为数组，无内容则放空[]。
```

A single line of `"A01_年龄性别":[]` etc. tells the model the exact key format. Without this, it invents its own names.

## B02_活动行为 Extraction Fix

The model needs to understand that **micro-actions count**:
- "整理头发", "望向窗外", "左手轻握布料", "向左看", "低头", "仰头"
- Standing/sitting/lying down counts when it describes HUMAN action
- "建筑坐落在山坡上" — not a human action, skip
- "她站在窗前" — put "站" in BOTH A05 AND B02

## D02_配饰鞋帽 Extraction Fix

The model needs to distinguish **product photography** from **person wearing**:
- "她穿着黑色高跟鞋" → extract to D02
- "戴着金色项链" → extract to D02
- "产品摄影展示一双运动鞋" → DO NOT extract (product, not person)
- "包包展示" → DO NOT extract

The system prompt must explicitly spell out this distinction with clear examples.

## Batch Size: 50 Items/Round

50 items produces ~10K output tokens which fits in the 16K max_tokens window without truncation. 100 items overflows and gets cut.

## Cost Analysis

- 50 items: ~10K input + ~13K output = ~$0.006/round
- 520K items (full to_chi): ~$62 total
- vs delegate_task: ~$0.02/round (because of 42K fixed overhead), ~$208 total

## Concurrent Architecture

2 concurrent API calls is safe for DeepSeek (no rate limiting observed at this level).
Write to dimension library files with `a` (append) mode.
Use `threading.Lock` if writing from multiple threads.

## Resume Architecture

State file saves per-file + (start_line, end_line) ranges already processed.
On restart: load state, skip already-processed ranges, continue.
Auto-pause at 10 hours, save state, exit cleanly.

## Output Format

Each dimension library is a flat .txt file with one entry per line.
Files are appended to, never overwritten.
No deduplication is performed (can be done as post-processing).
