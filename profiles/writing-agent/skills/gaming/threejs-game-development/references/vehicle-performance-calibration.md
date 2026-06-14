# Vehicle Performance Calibration Methodology (100-point scale, v3.0)

## Rules (from user mandate)

1. **100-point scale** for all 6 dimensions (not 1-10)
2. **Tier medians**: T1=10, T2=30, T3=50, T4=70, T5=90
3. **Intra-tier spread**: average score within ±5 of median (max spread ≤10 across all vehicles in tier)
4. **Single-dimension spread**: per-dimension scores within ±7.5 of tier median (max spread ≤15)
5. **Intra-vehicle spread**: all 6 dimensions within ±8 of the vehicle's own average
6. **Upgrade cap**: 3 levels of upgrades, max climb = 2 tiers (T1→T3 maximum)
7. **Vehicle personality**: dimensions should vary meaningfully — every vehicle has a character, not cookie-cutter scores

## Calibration Algorithm

```typescript
// Step 1: Raw score from physical attributes
raw = {
    speed:        map(attrs.maxSpeed, 150, 450, 0, 100),
    acceleration: map(100 - attrs.acceleration * 20, 0, 100, 0, 100), // lower seconds = higher score
    handling:     map(attrs.handling*10 + attrs.grip*5 + attrs.steering*5, 0, 200, 0, 100),
    braking:      map(120 - attrs.braking, 0, 100, 0, 100),
    downforce:    map(attrs.downforce * 30 + 10, 0, 150, 0, 100),  // +10 baseline to avoid floor
    durability:   map(attrs.stability*10 + max(0, (weight-800)*0.03), 0, 120, 0, 100),
}

// Step 2: Scale to tier median
const scale = rawAvg > 0 ? median / rawAvg : 1.0;
scaled = { ...raw } × scale

// Step 3: Clamp average to ±5 of median
if (avg < median - 5) shift all up; if (avg > median + 5) shift all down

// Step 4: Clamp intra-vehicle spread (each dim within avg±8)
for each dim: clamp(scaled[dim], max(0, avg-8), min(100, avg+8))

// Step 5: Clamp single-dimension spread (each dim within median±7.5)
for each dim: clamp(scaled[dim], max(0, median-7.5), min(100, median+7.5))

// Step 6: Personality injection (power-to-weight ratio drives profile shape)
const personality = clamp((power/weight - 0.15) * 50, -1, 1);
scaled.speed   += personality * 4 * 0.5;   // high PWR → faster
scaled.accel   += personality * 4 * 0.3;
scaled.handling-= personality * 4 * 0.2;   // compensate: handling-focused cars are heavier
scaled.durability-= personality * 4 * 0.3; // speed costs durability
```

## Upgrade Model

- 3 upgrade levels per vehicle
- Each level boosts all dimensions by ~8 points average
- Cap: cannot exceed next tier's median × 1.05
- T1 max = 50 (T3 median), T2 max = 50, T3 max = 70, T4 max = 90, T5 max = 100

```typescript
const boostMap = { 1: 0.3, 2: 0.6, 3: 1.0 }; // fraction of total 24pt boost
const targetAvg = Math.min(baseAvg + boost × 24, tierMaxUpgradeMedian + 5);
const ratio = targetAvg / baseAvg;
upgradedProfile = { ...baseProfile } × ratio (capped at 100 per dim)
```

## Physics Mapping (100-point score → game parameters)

Score mapped to game physics using a baseline + delta model:

| Parameter | Baseline (score=50) | Per-point delta |
|-----------|-------------------|-----------------|
| MAX_SPEED | 80 | +1.0/point |
| ACCEL | 20 | +0.15 × speedScore |
| STEER_SPEED | 3.0 | +0.03 × handlingScore |
| BRAKE_FORCE | 25 | +0.15 × brakingScore |

Upgrade multiplier adds a 1.0→1.32× boost to ACCEL, STEER, BRAKE (but only 0.5× effect on MAX_SPEED for balance).

## Verification Checklist

For every calibration batch, verify:
- [ ] Intra-tier average spread ≤ 10 (all vehicles in same tier)
- [ ] Single-dimension spread ≤ 15 (e.g. all T1 speeds between 5-20)
- [ ] Every vehicle's 6 dimensions within its own avg ± 8
- [ ] Tier medians: T1≈10, T2≈30, T3≈50, T4≈70, T5≈90
- [ ] Inter-tier gap > 0 (no overlap: T1 max < T2 min)
- [ ] Upgrade cap respected (TypeScript constants match spec)
- [ ] Personality injection produces visibly different profiles (not all same shape)

## Pitfalls

- **downforce floor too low**: Raw downforce score from real data is often 2-5/100 for T1-T2 cars because they have tiny aero. Add a +10 baseline offset so it doesn't drag the average down unfairly.
- **durability metric**: Heavy cars aren't "more durable" in a racing sense. Use a weight-based formula but cap the benefit: `durability = stability×10 + max(0, (weight-800)×0.03)`. Too much weight weighting flattens handling differences.
- **scale warping**: Raw data from a T5 car might have topSpeed=400 while T1 has topSpeed=230 — a factor of ~1.7x. But the median scores are 10 vs 90 (9x). The scaling step handles this but can produce weird profiles if raw scores are clustered. Test with the tier's actual attribute ranges.
- **personality overwrites constraints**: Personality injection runs AFTER the spread clamps. If a car is already at the intra-vehicle spread boundary (+8), personality can push it past. Always re-clamp after personality.
- **F1 cars break everything**: Formula cars have handling/braking scores that are naturally way above their tier average. They may need special handling (accept slight violations of ±8 intra-spread — 1 point wiggle is OK for extreme vehicles).
