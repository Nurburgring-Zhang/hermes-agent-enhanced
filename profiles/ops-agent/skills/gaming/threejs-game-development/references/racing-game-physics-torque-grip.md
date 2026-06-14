# Racing Game Physics: Torque Curve + Grip-Break Drift Model

> Implementation notes from PlushRacingGame session (2026-05-29)

## Torque Curve Acceleration

Replace constant acceleration with a three-zone torque model:

```
speedRatio = playerSpeed / MAX_SPEED

Zone 1 (0-50%): full torque multiplier = 1.0
Zone 2 (50-80%): linear decay  multiplier = 1.0 - (ratio - 0.5) * 0.8
Zone 3 (80%+):   fast decay    multiplier = 1.0 - (ratio - 0.8) * 3.0
                  min effective = 0.15
```

This gives realistic feel: strong launch, gradual power fade at high speed, and a top-speed wall.

## Grip-Break Drift Model

Compute lateral acceleration as `|steerInput| * playerSpeed * STEER_SPEED`.
Compare against `gripLimit = tireGrip * 4` (tireGrip ranges 0.5-2.0 by difficulty).

```
if lateralAccel > gripLimit AND speed > 3 m/s:
    isDrifting = true
    targetSlip = sign(steerInput) * min(0.15, (lateralAccel - gripLimit) / gripLimit * 0.1)
    slipAngle lerps toward targetSlip at rate 2x delta
    slip velocity components added to movement:
        slipX = cos(playerAngle) * slipAngle * speed * delta
        slipZ = -sin(playerAngle) * slipAngle * speed * delta
    speed *= (1 - delta * 0.3)   // drift speed loss
else:
    isDrifting = false
    slipAngle decays *= 0.9
```

## ABS Braking Integration

```
if diffAbs enabled:
    // ABS limits brake force to prevent lockup
    brakeEffort = min(1.0, BRAKE_FORCE * delta * brake)
else:
    // No ABS: stronger at high speed but linear (simulates lockup risk)
    brakeEffort = BRAKE_FORCE * delta * brake * (1 + speedRatio * 0.5)
```

## Traction Control (TCS)

When TCS is active AND steering + throttle + speed > 60%:
- Reduce effectiveSteer by 15% (×0.85)
- This prevents full-throttle corner exit spin

## Difficulty-Dependent Steering Feel

```
if difficulty >= 3 (Hard/Master):
    // High-speed steering stays responsive (more challenging)
    speedFactor = max(0.5, 1 - speedRatio * 0.5)
else:
    // Normal mode: high-speed steering is softer
    speedFactor = max(0.35, 1 - speedRatio * 0.7)
```

## AI Free Driving (Track Pathfinding)

AI cars use independent physics state `{speed, angle, x, z}` not curve binding.

**Algorithm:**
1. Find nearest point on track curve (sample ~500 points)
2. Compute look-ahead target at `closestT + 0.015..0.025` (based on ai skill)
3. Steer toward target point using angular difference with clamped rate
4. Apply curvature-based braking: `curvature = 1 - |tangent·heading|`, brake proportional
5. Apply same track-boundary pushback as player

**Key parameters:**
- steerRate = `(1.0 + difficulty * 0.3) * 2.0` (rad/s)
- cornerBrake = `min(0.4, curvature * 2 * (1 - aiSkill * 0.5))`
- AI skill by difficulty: `0.3 + difficulty * 0.12`
