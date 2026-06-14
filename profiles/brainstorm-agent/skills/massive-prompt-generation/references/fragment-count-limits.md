# CRITICAL: Fragment Count Limits (Discovered via User Frustration)

## The Rule

When composing prompts from dimension library fragments, **take exactly 1 fragment** from each of these dimensions:

| Dimension | Why? | What goes wrong with 2+ |
|-----------|------|------------------------|
| **D01_服装款式** | Clothing stacking | "连衣裙+胸罩+丝袜+内裤+高跟鞋" = 5 items, user: "这句话有问题吗？" |
| **A05_姿势** | Three hands | "右手...双手...左臂" = contradictory, user: "这他妈有几只手了？？？？" |
| **B02_活动行为** | Three hands + body | Same as A05 — both hands + single hand contradiction |
| **A04_表情眼神** | Head/eye contradiction | "头部向下倾斜...头部转向肩后" = impossible, user called this out |

## Only These Dimensions Can Take 2 Fragments

| Dimension | Max fragments | With filter |
|-----------|:------------:|-------------|
| B01_场景环境 | 2 | INDOOR/OUTDOOR consistency filter |
| ALL OTHERS | 1 | — |

## History of This Rule

This was learned through **4 rounds of user corrections** in a single session. Each correction was progressively more frustrated:

1. First correction: "她双臂交叉于胸前，双手自然垂放，正用手势示意，手指轻轻指向身旁" — user: "这他妈有几只手了？？？？"
2. Second correction: "置身于城市日落时分的户外环境中...左臂沿枕头伸展" — user: "这他妈到底在室外还是室内？？"
3. Third correction: "蓝白竖条纹连衣裙...内穿白色蕾丝胸罩...外罩透明粉色丝袜" — user pointed out 5-item stacking
4. Final correction: "头部微微向下倾斜，正闭着眼睛微笑，头部转向肩后" — impossible head position

**Lesson**: Always default to 1 fragment per dimension when composing prompts. Only B01_场景环境 can take 2, and only with strict scene-type filtering.
