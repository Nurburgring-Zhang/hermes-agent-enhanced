# 5-Difficulty Physics Engine for Racing Games

When implementing progressive difficulty levels in a CatmullRomCurve3-based racing game's monolithic game class.

## Core Physics Parameters by Difficulty

| Param | Effect | 娱乐(0) | 轻松(1) | 中等(2) | 困难(3) | 大师(4) |
|-------|--------|---------|---------|---------|---------|---------|
| ACCEL | Acceleration rate | 22 | 21 | 20 | 18 | 16 |
| STEER_SPEED | Steering angular velocity | 4.5 | 3.8 | 3.0 | 2.2 | 1.8 |
| BRAKE_FORCE | Braking deceleration | 28 | 27 | 25 | 23 | 20 |
| MAX_SPEED | Top speed cap | 85 | 82 | 80 | 78 | 75 |
| FRICTION | Rolling friction | 6 | 7 | 8 | 9 | 12 |
| tireGrip | Lateral grip multiplier | 2.0 | 1.5 | 1.0 | 0.7 | 0.5 |

## Assist Systems

| Feature | 娱乐 | 轻松 | 中等 | 困难 | 大师 |
|---------|------|------|------|------|------|
| AutoSteer ratio | 90% | 50% | 0% | 0% | 0% |
| AutoBrake | Yes | No | No | No | No |
| Traction Control | Yes | Yes | Yes | No | No |
| ABS | Yes | Yes | No | No | No |

## Physics Model Details

### 1. Engine Torque Curve
```typescript
const speedNorm = Math.abs(playerSpeed) / MAX_SPEED;
const torqueCurve = 1 - speedNorm * 0.5; // drops 50% at top speed
let engineForce = ACCEL * delta * throttle * Math.max(0.2, torqueCurve);
```

### 2. Traction Control (TCS)
```typescript
if (diffTractionControl && throttle > 0 && speedNorm > 0.8) {
    engineForce *= (1 - speedNorm * 0.3);
}
```

### 3. ABS
```typescript
if (diffAbs && speedNorm > 0.3) {
    brakeForce *= 0.8; // 20% braking reduction but keeps control
}
```

### 4. AutoSteer
```typescript
// Sample curvature ahead — compute natural steering angle
const lookAhead = 0.03;
const curTangent = trackCurve.getTangent(playerProgress);
const aheadTangent = trackCurve.getTangent(playerProgress + lookAhead);
const cross = new THREE.Vector3().crossVectors(curTangent, aheadTangent);
const autoSteer = -cross.y * 3.0;
// Blend manual + auto
const autoRatio = difficulty === 0 ? 0.9 : 0.5;
steerInput = rawSteer * (1 - autoRatio) + autoSteer * autoRatio;
```

### 5. Slip Angle and Drift
```typescript
// Slip angle accumulates/de-accumulates based on steering and speed
slipAngle += (steerInput * speedNorm * delta * 2 - slipAngle) * delta * 3;
slipAngle = clamp(slipAngle, -0.2, 0.2);  // max ±11° — prevents car from orienting sideways

// Drift detection
isDrifting = Math.abs(slipAngle) > 0.12 && speed > 20;
if (isDrifting) playerSpeed *= (1 - delta * 0.3); // gentler drift drag

// Understeer at high speed with low grip
const understeer = Math.max(0, speedNorm - tireGrip * 0.8);
const lateralAccel = steerInput * STEER_SPEED * delta * speedFactor * (1 - understeer);
```

### 5b. Position Mapping — Lateral Offset
**Critical**: The lateralOffset multiplier must be small. A value of 2.0 combined with slipAngle ±0.5 causes the car to be physically displaced 1.0+ units sideways from the track centerline, making it look like it's sliding off the road.

```typescript
const lateralOffset = slipAngle * 0.5;  // max 0.1 units lateral offset
```

### 5c. Vehicle Rotation — Direct Set vs Accumulation
**Critical**: Do NOT accumulate rotation using lerp (`angle += (target - angle) * delta * k`). This creates a persistent offset between the visual car heading and the actual track direction, especially at high frame deltas. Instead, set rotation directly:

```typescript
// BAD — accumulates error:
playerAngle += ((targetAngle + driftAngle) - playerAngle) * delta * 4;
car.rotation.y = playerAngle;

// GOOD — sets directly, no drift error:
const targetAngle = Math.atan2(trackTangent.x, trackTangent.z);
const driftAngle = slipAngle * 0.15;  // visual-only, small
car.rotation.y = targetAngle + driftAngle;
```

### 5d. Roll Animation — Reduce Intensity
The body roll during steering should be subtle. A coefficient of -0.15 at speedNorm=1 produces 8+ degrees of visible lean. Reduce to -0.08:

```typescript
const rollAngle = steerInput * -0.08 * speedNorm;
car.rotation.z += (rollAngle - car.rotation.z) * delta * 5;
```
```typescript
// Look ahead for sharp curves and brake automatically
const curvature = 1 - Math.abs(curTangent.dot(aheadTangent));
if (curvature > 0.2 && speedNorm > 0.5) {
    playerSpeed -= curvature * 30 * delta;
}
```

### 7. Lateral Position (Track Centering + Drift Offset)
```typescript
const normal = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
const lateralOffset = slipAngle * 2; // drift pushes car sideways
car.position.set(
    trackPos.x + normal.x * lateralOffset,
    trackPos.y + 0.5 + bounceOffset,
    trackPos.z + normal.z * lateralOffset
);
```

### 8. AI Difficulty Synchronization

AI speed and cornering skill scale with difficulty:

| Difficulty | AI Base Speed | AI Variance | Corner Skill |
|------------|--------------|-------------|--------------|
| 0 (娱乐) | 30 | ±2 | 0.30 (bad) |
| 1 (轻松) | 38 | ±3 | 0.42 |
| 2 (中等) | 45 | ±5 | 0.54 |
| 3 (困难) | 55 | ±8 | 0.66 |
| 4 (大师) | 65 | ±12 | 0.78 (good) |

```typescript
const aiSkill = 0.3 + difficulty * 0.12;
const cornerFactor = 1 - curvature * aiSkill;
const consistency = 1 - difficulty * 0.05;
const noiseScale = (1 - consistency) * 8;
const aiSpeed = baseSpeed * cornerFactor + sin(time * 0.001 + i) * noiseScale;
```

## Progressive Feature Injection Pattern

When adding features to a monolithic game class:

1. **Add private properties** at class top
2. **Call init** in the main init/start method
3. **Add hotkey** in the keyboard handler
4. **Create HUD elements** in DOM dynamically (with duplicate-guard: `if (id exists) return`)
5. **Modify update loop** — the feature reads properties set by the init/cycle method
6. **Build-validate** after each step

This pattern applies to: difficulty system, paint system, upgrade system, and season/points.
