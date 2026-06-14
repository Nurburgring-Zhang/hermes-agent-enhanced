# Racing Game Physics — Real-World Engineering Model

## Reference Data Sources (from session 2026-05-30)

7 real sports car specs collected from manufacturer data, automotive databases, motorsport literature:

| Car | hp | Torque(Nm) | 0-100(km/h) | Weight(kg) | Drive | Gear Ratios (1-6) | FD |
|-----|----|-----------|-------------|-----------|-------|-------------------|---|
| Audi TT 8J | 200-211 | 280 | 6.4s | 1395 | FWD/AWD | 3.30/1.94/1.31/1.03/0.82/0.68 | 4.23 |
| Nissan 350Z | 287-306 | 363 | 5.5s | 1450 | RWD | 3.79/2.32/1.62/1.27/1.00/0.79 | 3.36 |
| Ferrari 360 | 400 | 373 | 4.5s | 1470 | RWD(MR) | 3.29/2.16/1.61/1.27/1.03/0.85 | 4.44 |
| BMW M3 E46 | 343 | 365 | 5.2s | 1495 | RWD | 4.23/2.53/1.67/1.23/1.00/0.83 | 3.62 |
| Corvette C6 | 400-436 | 569-575 | 4.1s | 1441 | RWD | 2.97/2.07/1.43/1.00/0.71/0.57 | 3.42 |
| Toyota Supra MKIV | 320(276JDM) | 440 | 5.0s | 1580 | RWD | 3.83/2.19/1.38/1.00/0.81/0.65 | 3.27 |
| McLaren F1 | 618 | 651 | 3.2s | 1140 | RWD(MR) | (6MT) | ~3.0 |

## Tire Grip Coefficients (mu)

| Tire Type | Peak Longitud. mu | Peak Lateral mu | Sliding mu |
|-----------|------------------|-----------------|------------|
| All-season street | 0.80-0.90 | 0.70-0.85 | ~0.70 |
| UHP summer street | 0.95-1.10 | 0.90-1.05 | ~0.80 |
| R-compound (semi-slick) | 1.10-1.20 | 1.05-1.20 | ~0.90 |
| Racing slick (warm) | 1.30-1.60 | 1.30-1.70 | ~1.00-1.10 |

Load sensitivity: mu decreases ~8-10% per 100% load increase.

## Aerodynamics

| Vehicle Type | Cd | Frontal Area (m²) | Cd*A (m²) |
|-------------|----|-------------------|-----------|
| Family sedan | 0.28-0.32 | 2.10-2.30 | 0.59-0.64 |
| Sports coupe | 0.29-0.34 | 1.90-2.10 | 0.55-0.61 |
| Supercar (street) | 0.31-0.36 | 1.80-2.00 | 0.56-0.62 |
| GT race car | 0.35-0.42 | 1.80-2.00 | 0.63-0.70 |
| F1 (open wheel) | 0.70-1.10 | 1.40-1.50 | 0.98-1.05 |

Downforce (CL): Street -0.05~+0.10 | Sport aero -0.20~-0.40 | Race wing -1.00~-2.00

## Suspension Parameters

### Spring Rates (N/mm)
| Setup | Front | Rear |
|-------|-------|------|
| Street comfort | 25-45 | 20-35 |
| Sport street | 35-55 | 30-50 |
| Performance street (M3, 350Z) | 50-80 | 45-75 |
| Track/club sport | 80-140 | 70-120 |
| GT race car | 140-250 | 120-200 |
| Formula | 250-500+ | 200-400+ |

### Damping Coefficients (N·s/m)
| Setup | Front bump | Front rebound | Rear bump | Rear rebound |
|-------|-----------|-------------|-----------|-------------|
| Street comfort | 800-1,500 | 1,500-2,500 | 700-1,300 | 1,300-2,200 |
| Sport street | 1,200-2,000 | 2,000-3,500 | 1,000-1,800 | 1,800-3,000 |
| Track/club | 1,800-3,500 | 3,000-6,000 | 1,500-3,000 | 2,500-5,500 |
| Race | 2,500-5,000 | 4,000-8,000 | 2,000-4,500 | 3,500-7,000 |

Bump:rebound ratio: ~1:2 street, ~1:1.5 track, ~1:1.2 race

---

## Physics Engine Architecture (Implemented 2026-05-30)

### Constant Declarations

```typescript
// ENGINE — BMW M3 E46 S54B32
ENGINE_POWER_HP = 343;
ENGINE_MAX_TORQUE_NM = 365;
ENGINE_MAX_RPM = 8000;
ENGINE_IDLE_RPM = 800;

// TRANSMISSION — Getrag 420G 6MT
GEAR_RATIOS = [4.23, 2.53, 1.67, 1.23, 1.00, 0.83];
FINAL_DRIVE = 4.10;
WHEEL_RADIUS = 0.33;        // 255/40R18
DRIVETRAIN_EFFICIENCY = 0.85;

// VEHICLE
VEHICLE_MASS = 1495;         // kg
WEIGHT_FRONT = 0.52;
WEIGHT_REAR = 0.48;
CG_HEIGHT = 0.50;            // m
WHEELBASE = 2.73;            // m

// TIRES (UHP summer)
TIRE_PEAK_LONGITUDINAL_MU = 1.05;
TIRE_PEAK_LATERAL_MU = 1.00;
TIRE_SLIDING_MU = 0.80;
TIRE_LOAD_SENSITIVITY = 0.08;

// BRAKES
BRAKE_MAX_DECEL = 11.3;     // m/s² (100-0km/h in 34m)

// AERO
CD = 0.32;
FRONTAL_AREA = 2.12;         // m²
CL_FRONT = -0.02;
CL_REAR = 0.05;

// SUSPENSION
SUSPENSION_SPRING_FRONT = 55000;   // N/m
SUSPENSION_SPRING_REAR = 50000;
SUSPENSION_DAMP_BUMP_FRONT = 1800; // N·s/m
SUSPENSION_DAMP_REBOUND_FRONT = 3000;
ANTI_ROLL_STIFFNESS = 20000;       // N·m/rad

// STEERING
STEER_RATIO = 16;
STEER_MAX_ANGLE = 0.52;     // rad (~30°)
```

### Physics Update Pipeline (per frame)

```
INPUT (throttle, brake, steer, delta)
    │
    ├── 1. ENGINE + TORQUE CURVE
    │     engineRpmNorm → 5-zone torque curve (idle→climb→plateau→fall→drop)
    │     engineTorque = MAX_TORQUE × torqueCurveValue
    │     ratio = GEAR_RATIOS[gear] × FINAL_DRIVE
    │     wheelTorque = engineTorque × ratio × DRIVETRAIN_EFF × _powerMultiplier × _accelMultiplier
    │     driveForce = wheelTorque / WHEEL_RADIUS
    │
    ├── 2. TIRE LONGITUDINAL GRIP
    │     weightTransfer = driveForce × CG_HEIGHT / WHEELBASE
    │     frontLoad/rearLoad = staticWeight ± weightTransfer
    │     mu_x = TIRE_MU × gripMultiplier × (1 - loadSensitivity × ln(Fz/Fz0))
    │     maxDriveForce = mu_x × rearLoad (RWD)
    │     slipRatio check → limit drive if spinning
    │
    ├── 3. BRAKING
    │     brakeDecel = BRAKE_MAX_DECEL × _brakeMultiplier × _brakeHelperMultiplier
    │     brakeForce = min(mass×decel, mu_x×load×0.8)
    │     ABS: 90% efficient → prevents lockup
    │     No-ABS: 120% efficiency → shorter but locked
    │
    ├── 4. DRAG + ROLLING RESISTANCE
    │     F_drag = 0.5 × ρ × Cd × A × v²
    │     downforce: 0.5 × ρ × CL × A × v² (affects tire load)
    │     rollingResistance = 0.015 × g × dt
    │
    ├── 5. STEERING + TIRE LATERAL (Magic Formula)
    │     steerAngle = input × nonlinearCurve × STEER_MAX_ANGLE
    │     B=8, C=1.3, D=TIRE_PEAK_LATERAL_MU, E=0.3
    │     Fy = D × load × sin(C × atan(B × slipAngle - E×(B×slipAngle - atan(B×slipAngle))))
    │
    ├── 6. YAW DYNAMICS
    │     yawMoment = a × Fy_front - b × Fy_rear
    │     yawRate += (yawMoment - yawDamping × yawRate) / yawInertia × dt
    │     playerAngle += yawRate × dt
    │
    ├── 7. BODY ROLL + PITCH
    │     rollMoment = lateralAccel × mass × CG_HEIGHT
    │     bodyRoll = rollMoment / rollStiffness (springs + ARB)
    │     pitchMoment = longAccel × mass × CG_HEIGHT
    │
    └── 8. POSITION UPDATE
          local: (velocity, lateralVelocity)
          world: (sinA×v - cosA×latVel, -cosA×v - sinA×latVel) × dt
```

### Difficulty System (Multipliers Only — Does NOT Override Physics)

| Level | Grip | Power | Brake | Features |
|-------|------|-------|-------|----------|
| 0 🎪 娱乐 | 1.30x | 1.20x | 1.30x | AutoSteer+AutoBrake+ABS+TCS |
| 1 😊 轻松 | 1.15x | 1.10x | 1.15x | TCS+ABS |
| 2 ⚖️ 中等 | 1.00x | 1.00x | 1.00x | TCS only |
| 3 🔥 困难 | 0.85x | 0.90x | 0.85x | No assists |
| 4 💀 大师 | 0.65x | 0.80x | 0.70x | No assists, real simulation |

### Vehicle Differentiation (per-car multipliers, set by `applyRealCarPhysics()`)

```typescript
_accelMultiplier = powerToWeight / basePowerToWeight
  // base = 343hp/1495kg
  // Formula: 618hp/1140kg → 618/1140 / 343/1495 = 0.542 / 0.229 = 2.36x
  // Corvette: 436hp/1441kg → 436/1441 / 343/1495 = 0.302 / 0.229 = 1.32x
  // Audi TT: 200hp/1395kg → 200/1395 / 343/1495 = 0.143 / 0.229 = 0.62x

_brakeMultiplier = 33 / brakingDistance
  // M3: 33/33 = 1.0, McLaren: 33/30 = 1.1, SUV: 33/40 = 0.825

_handlingMultiplier = handlingRating / 5  // handling 1-10
  // sports car 8/10 → 1.6x, family car 5/10 → 1.0x
```

### Key Implementation Details

**Torque Curve (5 zones):**
```
0-5%   idle area: linear 0.65→1.0
5-35%  low rev: curve 1.0→1.08 (peak at ~25% norm ≈ 2600rpm)
35-70% torque plateau: sin wave ~1.08 (peak at 65% norm ≈ 4900rpm)
70-90% high rev decay: 1.08→0.83
90-100% redline drop: 0.83→0.50
```

**Auto Shift Logic:**
```
Up-shift: rpm > 7500 → next gear, rpm *= 0.72
Down-shift: rpm < 1500 && speed > 2m/s → prev gear, rpm *= 1.35
Shift time: 0.25s
```

**Anti-Slip (traction control):**
```
slipRatio = (wheelSpeed - vehicleSpeed) / vehicleSpeed
if slipRatio > 0.15 → limit force to 70-30% of max grip
TCS on: additional 8% cut on driveForce
```

**Brake Model:**
```
No-ABS: brakeForce × 1.2 (can lock up)
ABS: brakeForce × 0.9 (pulse at limit)
brake force capped by tire grip: min(desiredForce, mu_x × load × 0.8)
```

**Roll/Pitch:**
```
rollStiffness = (springFront + springRear) × 0.5 × (0.5 × wheelbase)² + antiRollBar
bodyRoll = clamp(rollMoment / rollStiffness, -0.3, 0.3) ≈ ±17°
bodyPitch = clamp(pitchMoment / pitchStiffness, -0.15, 0.15) ≈ ±8.5°
```
