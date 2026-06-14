# Racing Game Physics Engine Architecture

Sim-level three.js racing physics implementation — based on real-world car data (BMW M3 E46 as reference prototype).

## Physics Parameter Declaration

All physics constants declared as `private readonly` class properties. Reference prototype: M3 E46 (343hp, 365Nm, 1495kg, 52/48 weight split).

### Engine Parameters
```typescript
ENGINE_POWER_HP = 343
ENGINE_MAX_TORQUE_NM = 365
ENGINE_MAX_RPM = 8000
ENGINE_IDLE_RPM = 800
ENGINE_TORQUE_PEAK_RPM = 4900
ENGINE_TORQUE_AT_IDLE = 0.65    // 65% of peak at idle
ENGINE_TORQUE_AT_MAX = 0.55     // 55% at redline
```

### Transmission
```typescript
GEAR_RATIOS = [4.23, 2.53, 1.67, 1.23, 1.00, 0.83]  // M3 E46 Getrag 420G
FINAL_DRIVE = 4.10
WHEEL_RADIUS = 0.33              // ~255/40R18
DRIVETRAIN_EFFICIENCY = 0.85     // 15% drivetrain loss
```

### Vehicle Mass & Geometry
```typescript
VEHICLE_MASS = 1495              // kg
WEIGHT_FRONT = 0.52
WEIGHT_REAR = 0.48
CG_HEIGHT = 0.50                 // meters
WHEELBASE = 2.73                 // meters
```

### Tire Grip (UHP Summer Performance)
```typescript
TIRE_PEAK_LONGITUDINAL_MU = 1.05
TIRE_PEAK_LATERAL_MU = 1.00
TIRE_SLIDING_MU = 0.80
TIRE_LOAD_SENSITIVITY = 0.08     // 8% mu reduction per load doubling
```

### Brakes
```typescript
BRAKE_MAX_DECEL = 11.3           // m/s² (~1.15g, 100-0km/h in 34m)
BRAKE_BALANCE_FRONT = 0.65
```

### Aerodynamics
```typescript
CD = 0.32                        // drag coefficient
FRONTAL_AREA = 2.12              // m²
AIR_DENSITY = 1.225              // kg/m³
CL_FRONT = -0.02                 // slight front downforce
CL_REAR = 0.05                   // slight rear lift (typical street car)
```

### Suspension
```typescript
SUSPENSION_SPRING_FRONT = 55000  // N/m (55 N/mm)
SUSPENSION_SPRING_REAR = 50000
SUSPENSION_DAMP_BUMP_FRONT = 1800    // N-s/m
SUSPENSION_DAMP_REBOUND_FRONT = 3000
SUSPENSION_DAMP_BUMP_REAR = 1500
SUSPENSION_DAMP_REBOUND_REAR = 2600
SUSPENSION_TRAVEL = 0.15         // meters
ANTI_ROLL_STIFFNESS = 20000      // N-m/rad
```

### Steering
```typescript
STEER_RATIO = 16
STEER_MAX_ANGLE = 0.52           // rad (~30°)
CASTER_ANGLE = 0.12              // rad (~7°)
```

## Physics Engine Update Flow (per frame)

Each frame in `updatePlayer(delta)`, the engine executes in this order:

### Step 1: Engine Torque Curve (5-zone S54 model)

```typescript
engineRpmNorm = (rpm - 800) / (8000 - 800)  // 0.0 to 1.0

Zone 1 (0.00-0.05): Idle → 65% → 100% torque buildup
Zone 2 (0.05-0.35): Low-mid → 100-108% rapid climb
Zone 3 (0.35-0.70): Torque plateau → 108% peak @ ~4900rpm
Zone 4 (0.70-0.90): High-RPM → 108% → 83% gradual drop
Zone 5 (0.90-1.00): Redline → 83% → 50% sharp drop

engineTorqueNm = 365 × torqueCurveValue
```

### Step 2: Drivetrain

```typescript
ratio = GEAR_RATIOS[gear-1] × FINAL_DRIVE

// Auto shift logic
if (rpm > 7500 && gear < 6) shift up
if (rpm < 1500 && speed > 2m/s && gear > 1) shift down

// RPM dynamic simulation
// Throttle: converge targetRpm with engine inertia
// Off-throttle: RPM drops at 2500 RPM/s
// Clutch (shifting): drops at 3000 RPM/s

wheelTorqueNm = engineTorqueNm × ratio × DRIVETRAIN_EFFICIENCY × powerMultiplier × accelMultiplier
driveForceN = wheelTorqueNm / WHEEL_RADIUS
```

### Step 3: Load Transfer

```typescript
// Weight transfer during acceleration
weightTransferLong = (driveForce × CG_HEIGHT) / WHEELBASE

frontStaticWeight = VEHICLE_MASS × 9.81 × WEIGHT_FRONT
rearStaticWeight = VEHICLE_MASS × 9.81 × WEIGHT_REAR

frontLoad = frontStaticWeight - weightTransferLong  // lifts
rearLoad = rearStaticWeight + weightTransferLong     // squats
```

### Step 4: Tire Longitudinal Grip (Pacejka simplified)

```typescript
// Load-dependent mu reduction (Pacejka load sensitivity)
muLong = TIRE_PEAK_LONGITUDINAL_MU × gripMultiplier × 
         (1 - TIRE_LOAD_SENSITIVITY × ln(loadPerWheel / Fz0))

// RWD: only rear wheels drive, front gets 5% residual
maxDriveForceRear = muLongRear × rearLoad
maxDriveForceFront = muLongFront × frontLoad × 0.05
maxDriveForceTotal = maxDriveForceRear + maxDriveForceFront

// Slip control
slipRatio = (wheelSpeed - carSpeed) / carSpeed
if (slipRatio > 0.15) → reduce drive force (TCS)

// TCS active → limit to 92% of max
driveForceApplied = min(driveForceN, maxDriveForceTotal) × (TCS ? 0.92 : 1.0)
acceleration = driveForceApplied / VEHICLE_MASS
```

### Step 5: Braking

```typescript
brakeDeceleration = BRAKE_MAX_DECEL × brakeMultiplier × difficultyMultiplier
brakeForce = min(VEHICLE_MASS × brakeDeceleration, muLong × load × 0.8)

if (ABS enabled) → decelerate at 90% of brakeForce (threshold braking)
if (no ABS) → decelerate faster but risk lockup
```

### Step 6: Aerodynamic Drag + Downforce

```typescript
dragForce = 0.5 × AIR_DENSITY × CD × FRONTAL_AREA × v²
dragDecel = dragForce / VEHICLE_MASS
playerSpeed -= dragDecel × dt

downforceFront = 0.5 × AIR_DENSITY × CL_FRONT × FRONTAL_AREA × v²
downforceRear = 0.5 × AIR_DENSITY × CL_REAR × FRONTAL_AREA × v²
// Downforce adds to tire grip at high speed
```

### Step 7: Tire Lateral Force (Magic Formula)

```typescript
// Slip angles
vehicleSlipAngle = atan2(lateralVelocity, longitudinalSpeed)
frontSlipAngle = vehicleSlipAngle + steerAngle × 0.8
rearSlipAngle = vehicleSlipAngle × 0.95

// Magic formula parameters
B = 8    // stiffness
C = 1.3  // shape
D = TIRE_PEAK_LATERAL_MU  // peak
E = 0.3  // curvature

// Magic formula:
// Fy = D × Fz × sin(C × atan(B × α - E × (B × α - atan(B × α))))

// Where α = slip angle in degrees
// This produces the classic peak → decline shape
```

### Step 8: Yaw Dynamics

```typescript
// Moment balance
a = WHEELBASE × WEIGHT_REAR   // front axle to CG
b = WHEELBASE × WEIGHT_FRONT  // rear axle to CG
yawMoment = (Fy_front × a) - (Fy_rear × b)

yawInertia = VEHICLE_MASS × a × b  // simplified
yawDamping = 20000                 // N-m-s/rad

yawRate += (yawMoment - yawDamping × yawRate) / yawInertia × dt
yawRate = clamp(-4, 4)  // limit to 4 rad/s

playerAngle += yawRate × dt
```

### Step 9: Body Roll & Pitch

```typescript
// Roll moment = lateral force × CG height
rollMoment = lateralAccel × VEHICLE_MASS × CG_HEIGHT
rollStiffness = springAvg × (0.5 × WHEELBASE)² + antiRollBar
targetBodyRoll = rollMoment / rollStiffness
bodyRoll = lerp(clamp(-0.3, 0.3))

// Pitch moment = longitudinal force × CG height
pitchStiffness = similar formula
targetBodyPitch = pitchMoment / pitchStiffness
bodyPitch = lerp(clamp(-0.15, 0.15))
```

### Step 10: Position Update

```typescript
// Local velocity vector
localVx = playerSpeed         // forward
localVy = lateralVelocity      // sideslip

// World transform (Z- = forward direction)
worldDx = sin(playerAngle) × localVx - cos(playerAngle) × localVy
worldDz = -cos(playerAngle) × localVx - sin(playerAngle) × localVy

// Apply to position
carX += worldDx × dt
carZ += worldDz × dt

// Render
playerCar.position.set(carX, carY, carZ)
playerCar.rotation.y = playerAngle
playerCar.rotation.z = bodyRoll      // visual roll
playerCar.rotation.x = bodyPitch     // visual pitch
```

## Dynamic Multipliers (Vehicle Differentiation)

Instead of overwriting static physics constants, use multiplier system:

```typescript
_accelMultiplier = 1.0    // power-to-weight ratio vs M3 baseline
_handlingMultiplier = 1.0 // steering sensitivity
_brakeMultiplier = 1.0    // braking force
_weightFactor = 1.0       // mass penalty

// Difficulty multipliers (non-overwriting)
_gripMultiplier = 1.0     // tire grip (1.3 easy → 0.65 expert)
_powerMultiplier = 1.0    // engine output (1.2 easy → 0.8 expert)
_brakeHelperMultiplier = 1.0 // brake assist
```

These apply to `wheelTorqueNm`, `muLong`, `muLat`, and `brakeDeceleration` **within** the physics engine — they never overwrite the static constants themselves.

## Tire Grip Reference (mu)

| Tire Type | Longitudinal mu | Lateral mu |
|-----------|----------------|------------|
| All-season street | 0.80-0.90 | 0.70-0.85 |
| UHP summer | 0.95-1.10 | 0.90-1.05 |
| R-compound semi-slick | 1.10-1.20 | 1.05-1.20 |
| Racing slick (warm) | 1.30-1.60 | 1.30-1.70 |

## Aerodynamics Reference

| Vehicle | Cd | Frontal Area (m²) |
|---------|----|------------------|
| Family sedan | 0.28-0.32 | 2.10-2.30 |
| Sports coupe | 0.29-0.34 | 1.90-2.10 |
| GT race car | 0.35-0.42 | 1.80-2.00 |
| F1 car | 0.70-1.10 | 1.40-1.50 |

Downforce coefficient CL: street = -0.05 to +0.10, race car = -1.00 to -2.00, F1 = -2.50 to -3.00

## Suspension Reference

| Class | Spring Front (N/mm) | Spring Rear (N/mm) |
|-------|--------------------|--------------------|
| Street comfort | 25-45 | 20-35 |
| Sport street | 35-55 | 30-50 |
| Performance | 50-80 | 45-75 |
| Track club | 80-140 | 70-120 |
| GT race | 140-250 | 120-200 |

| Class | Bump Front (N-s/m) | Rebound Front | Bump:Rebound |
|-------|--------------------|--------------|-------------|
| Street | 800-1500 | 1500-2500 | 1:2 |
| Sport | 1200-2000 | 2000-3500 | 1:1.7 |
| Track | 1800-3500 | 3000-6000 | 1:1.5 |
| Race | 2500-5000 | 4000-8000 | 1:1.2 |
