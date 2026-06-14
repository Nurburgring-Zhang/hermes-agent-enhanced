# Dimension Library Extraction Evolution (v1 → v4)

## Version Timeline

| Version | Approach | Result | Problem |
|---------|----------|--------|---------|
| **v1** | Keyword matching | ~16K entries, 2-5 chars avg | Too coarse, no context |
| **v2** | Keyword + boundary extract | ~57K, 8-11 chars | "搭配未穿裤子" dirty data |
| **v3-final** | Boundary-aware + cleansing | ~213K, 8-16 chars across 18 libs | Truncation: "留着棕色长" |
| **v4-semantic** | **Sentence-level extraction** | **~1.29M across 17 libs, 10-17 chars** | ✅ Best quality |

## The Breakthrough: Sentence-Level Extraction

The fundamental shift was from **character-level boundary detection** to **sentence-level semantic unit extraction**.

### Before (v3-final boundary extract):
```python
def boundary_extract(text, keyword, max_left=8, max_right=30):
    idx = text.find(keyword)
    left = idx  # count backward 8 chars
    right = idx + len(keyword)  # count forward 30 chars
    # ... PRONE TO CUTTING IN THE MIDDLE OF WORDS
```

### After (v4 semantic extract):
```python
def get_sentences(text):
    return [s for s in re.split(r'[。；！？]', text) if len(s) >= 4]

def extract_hair(sentences):
    for sent in sentences:
        for kw in hair_kws:
            if kw in sent:
                # Extract complete sentence fragment
                # Use comma as natural boundary
                segment = extract_between_commas(sent, kw)
                if validate_hair(segment):
                    results.append(segment)
```

## The Semantic Validation Layer

Each extraction function has a **dedicated validator** that checks whether the extracted text actually belongs to that dimension:

```
A02_发型 → validate_hair(): "发" must be in text
A03_肤色 → validate_skin(): "肤" or "白" or "麦" or "古" must be present
A04_表情 → validate_expression(): must contain expression keywords
```

This prevented the classic "双手提起黑色长袖" → matched "黑色长" as hair → extracted into hair library bug.

## Key Quality Metrics on v4

- **A01_年龄性别**: 18,683 entries, 0 truncation artifacts (vs 535 in v3)
- **A03_肤色**: 661 entries, 0 cross-dimension contamination (vs "马尾，肤色白皙" artifacts in v3)
- **Total**: 1,293,231 entries across 17 libraries
- **Avg entry length**: 10-17 chars (meaningful fragments, not keywords)
- **Dirty rate**: <0.1% (vs ~5% in v3)
