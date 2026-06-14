# VDrift Full TypeScript Port — Session Methodology (2026-05-31)

This captures the process used to port VDrift cardynamics (cardynamics.h/.cpp, 1977 lines) into
TypeScript, along with the `buildCarConfig()` factory and PlushRacingGame integration.

## Port Strategy

### Step 1: Map the dependency graph before writing any code

VDrift physics has a strict dependency tree. Read headers in THIS order:

```
DriveShaft         ← driveshaft.h (base: angle, ang_velocity, inertia, inv_inertia)
Spline             ← spline.h (Catmull-Rom interpolation for torque curves)
CarEngine          ← carengine.h + .cpp (depends on DriveShaft + Spline)
CarTransmission    ← cartransmission.h (gear ratios, shift logic)
CarClutch          ← carclutch.h (friction torque from pressure*area*friction*radius)
CarDifferential    ← cardifferential.h (final drive, LSD params)
CarBrake           ← carbrake.h (bias, handbrake)
CarWheel           ← carwheel.h (depends on DriveShaft)
CarSuspension      ← carsuspension.h + .cpp (spring + damping + anti-roll)
CarTire            ← cartire1.h + cartirebase.h (Pacejka MF: Fx/Fy/Mz)
Driveline          ← driveline.h (MotorJoint + ClutchJoint + solve2/solve4)
CarDynamics        ← cardynamics.h + .cpp (integrates everything above)
CarConfigs         ← buildCarConfig() factory (13 real cars)
```

### Step 2: Read each C++ header completely, then write the TS equivalent

For each subsystem:
1. Read the `.h` file (interfaces + member variables)
2. Read the `.cpp` file (implementation — only for Engine, Suspension, Tire, Dynamics)
3. Write TS with the EXACT same formula chain — no mathematical simplification
4. Pay special attention to Pacejka coefficients (longitudinal[11], lateral[15], aligning[18])

### Step 3: C++ to TS translation rules

| C++ | TypeScript |
|-----|-----------|
| `btScalar` | `number` |
| `btVector3(x, y, z)` | `{x, y, z}` literal or class |
| `&obj.field` (reference) | `obj.field` (TS auto-reference) |
| `obj->method()` | `obj.method()` |
| `Sh = a[10] * gamma + a[11] * dfz` | SAME — direct transliteration |
| `M_PI` | `Math.PI` |
| `btSqrt(x)` | `Math.sqrt(x)` |
| `copysign(x, y)` | `Math.sign(y) * x` |
| `Clamp(x, lo, hi)` | `Math.max(lo, Math.min(hi, x))` |
| `Min(x, y)` / `Max(x, y)` | `Math.min(x, y)` / `Math.max(x, y)` |
| `template<Stream>` | omit (debug only) |
| `template<Serializer>` | omit (save/load only) |
| `for (const auto & node : cfg)` | iterate manually |
| `assert()` | `console.assert()` or omit |

### Step 4: CarConfigs — the 13-car factory pattern

Each car has:
- `hp` → maxPower (W) = hp * 746
- `torque` (Nm) as peakTq → 8-point torque curve
```typescript
// Construct the torque curve from real car specs
// Peak at peakRpm, then droop towards redline
return [
    {rpm: 350, torque: peakTq * 0.55},      // stall
    {rpm: peakRpm * 0.4, torque: peakTq * 0.75},
    {rpm: peakRpm * 0.6, torque: peakTq * 0.88},
    {rpm: peakRpm * 0.8, torque: peakTq * 0.97},
    {rpm: peakRpm, torque: peakTq},            // peak
    {rpm: peakRpm + (redline-peakRpm)*0.5, torque: peakTq * 0.92},
    {rpm: redline, torque: peakTq * 0.82},
    {rpm: rpmLimit, torque: peakTq * 0.60},
];
```

Wheel positions: `trackFront/2` and `trackRear/2` for x, `wheelbase * weightDist` for z.
Four identical wheel configs but per-vehicle camber/toe/spring rates.

### Step 5: Integration into PlushRacingGame

```typescript
// In constructor/init:
this.vdriftPhysicsFull = new CarDynamics();
this.vdriftPhysicsFull.Load(buildCarConfig(modelId));

// In updatePlayer():
this.vdriftPhysicsFull.SetThrottle(throttle);
this.vdriftPhysicsFull.SetBrake(brake);
this.vdriftPhysicsFull.SetSteering(steer);
this.vdriftPhysicsFull.Update(dt);

// Read back:
this.playerSpeed = this.vdriftPhysicsFull.getSpeed();
this.playerAngle = Math.atan2(v.velocity.x, v.velocity.z);  // NOT yawRate integrate
this.carX = this.vdriftPhysicsFull.position.x;
this.carZ = this.vdriftPhysicsFull.position.z;
```

## Pitfalls Captured During This Session

1. **`&this.xxx` in TypeScript is INVALID.** This is C++ reference syntax. Replace `d.shaft[0] = &this.engine.shaft` with `d.shaft[0] = this.engine.shaft`. TS object assignments are reference semantics automatically.

2. **`if (this.drive & DriveEnum.FWD)` is correct.** VDrift uses bitwise flags for combined drive types (e.g. FWD|RWD = AWD). The `&` here is intentional bitwise AND, not address-of.

3. **Double `* dt` in drag formula.** When translating air drag:
   ```typescript
   // WRONG
   this.velocity.x -= this.velocity.x * dragDecel * dt / |v| * dt;  
   // RIGHT  
   this.velocity.x -= this.velocity.x * dragDecel * dt / |v|;
   ```

4. **Don't pre-allocate Driveline.motor.** Use `d.motor = []; d.motor.push(new MotorJoint())`. The first is engine, then one per wheel.

5. **Pacejka `sigma` in percent.** VDrift PacejkaFx takes `sigma * 100` (percent). Lateral `alpha` is in degrees. This is crucial for the magic formula B/C/D/E shape.

6. **CarDynamics.position vs CarDynamics.velocity.** The position is set externally by the game engine; CarDynamics integrates velocity internally. Reset both on track reset.

## File Manifest (Phase 1 complete)

```
src/physics/VDriftPhysicsFull/
├── index.ts              — re-export all classes
├── DriveShaft.ts         — base: angle, ang_velocity, inertia
├── Spline.ts             — Catmull-Rom interpolation
├── CarEngine.ts          — Heywood friction + torque spline + NOS
├── CarTransmission.ts    — gear ratios, shift, clutch speed
├── CarClutch.ts          — friction torque from pressure/area/radius
├── CarBrake.ts           — bias + handbrake
├── CarDifferential.ts    — final drive + LSD params
├── CarWheel.ts           — radius, width, mass
├── CarTire.ts            — Pacejka MF: Fx/Fy/Mz
├── CarSuspension.ts      — spring, damping, anti-roll
├── Driveline.ts          — MotorJoint + ClutchJoint + solve2/solve4
├── CarDynamics.ts        — main update loop, integrates everything
└── CarConfigs.ts         — buildCarConfig() for 13 cars
```
