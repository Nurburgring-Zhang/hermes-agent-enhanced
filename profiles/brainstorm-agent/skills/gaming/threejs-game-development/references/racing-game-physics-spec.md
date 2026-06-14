# Racing Game Physics Specification

## Unit System (REQUIRED)
- 1 game unit = 1 meter
- Speed: m/s (display: km/h = m/s × 3.6)
- Acceleration: m/s²
- Positions: absolute meters from track origin

## Default Physics Values (Medium Difficulty)

| Parameter | Value | Real-world equivalent |
|-----------|-------|-----------------------|
| MAX_SPEED | 70 m/s | 252 km/h |
| ACCEL | 25 m/s² | 0-100km/h ~4s |
| BRAKE_FORCE | 35 m/s² | Sport brakes |
| STEER_SPEED | 2.5 rad/s | Responsive |
| FRICTION | 4 m/s² | Rolling + drivetrain loss |

## Track Lengths (Real Circuits)

| Circuit | Real Length | Game Length | ~Lap Time (70 m/s avg 60%) |
|---------|-------------|-------------|-----------------------------|
| Silverstone | 5891m | ~5200m | ~74s |
| Spa | 7004m | ~6500m | ~93s |
| Monza | 5793m | ~5200m | ~74s |
| Nürburgring | 20832m | ~18500m | ~264s (4m24s) |
| Monaco | 3337m | ~3200m | ~46s |
| Le Mans | 13629m | ~13000m | ~186s (3m6s) |
| Suzuka | 5807m | ~5000m | ~71s |

## Difficulty Levels (Real Units)

| Level | ACCEL | STEER | BRAKE | MAX_SPEED | Grip | AutoSteer | TCS |
|-------|-------|-------|-------|-----------|------|-----------|-----|
| 0 娱乐 | 30 | 3.0 | 40 | 75 (270km/h) | 2.0 | ✅ | ✅ |
| 1 轻松 | 28 | 2.8 | 38 | 72 (259km/h) | 1.5 | ✅ | ✅ |
| 2 中等 | 25 | 2.5 | 35 | 70 (252km/h) | 1.0 | ❌ | ❌ |
| 3 困难 | 22 | 2.2 | 30 | 67 (241km/h) | 0.7 | ❌ | ❌ |
| 4 大师 | 18 | 1.8 | 25 | 62 (223km/h) | 0.5 | ❌ | ❌ |

## NPC AI Speed

| Difficulty | Base Speed (m/s) | Base Speed (km/h) | Variance |
|------------|------------------|-------------------|----------|
| 0 娱乐 | 35 | 126 | ±5 |
| 1 轻松 | 42 | 151 | ±7 |
| 2 中等 | 50 | 180 | ±9 |
| 3 困难 | 60 | 216 | ±12 |
| 4 大师 | 68 | 245 | ±15 |

## Track Control Point Construction

**DO NOT use GPS coordinate conversion.** Hand-craft points based on known circuit layout:

```
Circuit shape → straight sections + corner radii → absolute (x,z) coordinates
```

Key conventions:
- Start/finish line at or near origin
- Counter-clockwise layout
- Elevation via y-coordinate (Spa: Eau Rouge climb ~80m, Nürburgring: ±80m variation)
- Close the loop by repeating first point as last
- ~13-26 control points per circuit (more for complex ones like Nürburgring)
