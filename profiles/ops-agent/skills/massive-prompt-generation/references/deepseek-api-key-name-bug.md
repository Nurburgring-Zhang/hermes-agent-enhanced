# DeepSeek API Key-Name Behavior

## The Bug

If the system prompt only defines dimensions in natural language (e.g., "A01_年龄性别：年龄+性别"), the API invents its own key names:

```
WRONG output format (what you get without template):
{"主体":["年轻亚裔女性"], "发型":["深色头发"], "服装":["白色上衣"], ...}

RIGHT output format (what you want):
{"A01_年龄性别":["年轻亚裔女性"], "A02_发型":["深色头发"], "D01_服装款式":["白色上衣"], ...}
```

## The Fix

Put the **complete JSON template** at the **very top** of the system prompt, before any dimension definitions:

```
输出JSON数组，每个元素是{"条目N":{"A01_年龄性别":[],"A02_发型":[],"A03_肤色":[],"A04_表情眼神":[],"A05_姿势":[],"B01_场景环境":[],"B02_活动行为":[],"C01_美学风格":[],"C02_光照条件":[],"C03_色彩调性":[],"C04_构图镜头":[],"D01_服装款式":[],"D02_配饰鞋帽":[],"D03_材质质感":[],"D04_动态效果":[],"D05_天气时间":[],"D06_氛围情感":[]}}
```

Then add: "17个维度键名必须严格使用A01_A02_B01格式。"

## Test Result

With the template in prompt, 40-row batch tested clean — all 17 keys matched perfectly. Without it, every single API call used different Chinese key names.

## Other API Quirks

- DeepSeek `completion_tokens` hard limit seems to be ~16K. Above that, JSON gets truncated mid-array.
- Temperature 0.1 works best for extraction tasks — creative enough to handle varied input, deterministic enough for consistent output format.
- 2 concurrent calls work fine; 3+ may trigger rate limits (observed 429 errors on sustained 3-concurrent).
