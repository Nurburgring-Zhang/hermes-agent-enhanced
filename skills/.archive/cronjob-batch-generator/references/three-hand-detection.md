# 三手问题检测与修复指南 (Three-Hand Detection & Fix)

## Problem Statement

When generating text-to-image prompts from multiple template libraries, the combination of:
- A static hand pose ("一只手自然垂落，另一只手轻触XXX的边缘")
- An active activity ("她正在用锅铲翻动食材")

...results in a person described as having 3 hands, which produces deformed images.

## Detection Patterns

### Pattern 1: Static + Active Contradiction
A prompt has BOTH:
- `自然垂落` (passive/static hand)
- `正在` followed by an action verb like 锅铲/翻动/切/炒/煮/煲/写/画/翻书/打字/泡/洗/弹/拿/端

**Fix**: Remove the passive hand description, keep the active one.

### Pattern 2: Triple "一只手" Description
A prompt has 3 distinct hand descriptions:
- `一只手自然垂落，另一只手轻触XXX`
- PLUS `她正在做YYY`

**Fix**: Delete the "一只手自然垂落，另一只手轻触" clause.

### Pattern 3: Accessory Worn on Wrong Body Part
A prompt says `颈间佩戴着一条精致的袜子/手套/眼镜/发簪/腰带/胸针`

**Root cause**: 12_配饰鞋帽库.txt contains items where the accessory tag doesn't match the content.

**Fix**: Fix the library entries before generation, or post-hoc string replacement.

## Python Detection Script

```python
import re

def has_three_hands(prompt):
    """Check if a prompt describes 3 hands for 1 person"""
    has_passive = '自然垂落' in prompt
    has_active = '正在' in prompt and any(w in prompt for w in [
        '锅铲', '翻动', '切', '炒', '煮', '煲', '写', '画', 
        '翻书', '打字', '泡', '洗', '弹', '拿', '端',
        '举着', '握着', '撑着'
    ])
    return has_passive and has_active

def count_hand_phrases(prompt):
    """Count unique hand phrases"""
    one_hand = len(re.findall(r'一只手', prompt))
    other_hand = len(re.findall(r'另一只手', prompt))
    both_hands = len(re.findall(r'双手', prompt))
    left_right = len(re.findall(r'[左右]手', prompt)) - (one_hand + other_hand)
    return one_hand + other_hand + both_hands + left_right

def fix_three_hands(prompt):
    """Remove the passive hand description while keeping active one"""
    # Pattern: "，一只手自然垂落，另一只手XXX。"
    prompt = re.sub(r'，?一只手自然垂落，另一只手[^。]*[。，]', '，', prompt)
    prompt = re.sub(r'[。，]?\s*一只手自然垂落\s*[。，]', '，', prompt)
    prompt = re.sub(r'，?\s*另一只手轻触[^。]*边缘[。，]', '，', prompt)
    # Cleanup multiple commas
    prompt = re.sub(r'，+', '，', prompt)
    prompt = re.sub(r'[，。]\s*[。]', '。', prompt)
    return prompt
```

## Post-Generation Batch Scan

```bash
python3 -c "
import re
with open('batch_file.txt', 'r') as f:
    content = f.read()
prompts = content.split('\n\n')
for i, p in enumerate(prompts):
    if '自然垂落' in p and '正在' in p:
        has_active = any(w in p for w in ['锅铲','翻动','切','炒','煮'])
        if has_active:
            print(f'三手: prompt[{i+1}]')
print('Done')
"
```

## Verification After Fix

After running the fix, verify:
```bash
# Check zero three-hand prompts remain
python3 -c "
import re
with open('batch.txt') as f: content = f.read()
ps = [p.strip() for p in content.split('\n\n') if p.strip()]
bad = sum(1 for p in ps if '自然垂落' in p and any(w in p for w in ['锅铲','正在煮','正在切','正在炒']))
print(f'残余三手: {bad}')
"
```
