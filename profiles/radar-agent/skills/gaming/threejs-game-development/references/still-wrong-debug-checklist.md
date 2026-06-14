# Still Wrong? — Debug Checklist

When the user says "still wrong" after you've already attempted a fix, STOP editing the same code. The problem is in a DIFFERENT place. Run through this checklist before touching any code.

## Level 1: Quick Checks (2 minutes)

### 1A: Check field declarations
Look for `private cameraMode = 0` — if missing after a refactor, `this.cameraMode === 0` always evaluates to `false` (undefined !== 0), forcing the overhead drone camera branch every time.

**Missing field = silent undefined bug.** This is the #1 cause of drone-view fixes not working — edits to camera math do nothing when the real problem is a missing field declaration.

### 1B: Check for duplicate variable declarations
After any in-place engine/torque curve/transmission rewrite, grep for:
```
let torqueCurveValue
const engineTorqueNm
let driveForceApplied
const frontLoadWithAero
const rearLoadWithAero
```
Each must appear **exactly once**. Duplicates = build error. Zeros = different error. ANY remaining `frontLoadWithAero` after deletion = runtime crash (black canvas, no build error).

### 1C: Check for deleted constant references
After removing physics constants, grep for:
```
TIRE_PEAK_LONGITUDINAL_MU, TIRE_PEAK_LATERAL_MU, TIRE_LOAD_SENSITIVITY
AIR_DENSITY, CL_FRONT, CL_REAR
frontLoadWithAero, rearLoadWithAero
```
ANY remaining reference = runtime crash. Build succeeds silently, game logs "started", canvas is black.

## Level 2: Direction/Position Checks (5 minutes)

### 2A: Wheel position
Expected: wheels under wheel arches.
Check: Read vertex data to find wheel arch y-values, not body extreme y-values.

### 2B: Car forward direction — MARKER TEST
Add visible marker spheres before and behind the car:
```typescript
// In createPlayerCar(), before scene.add:
const markerGeo = new THREE.SphereGeometry(0.2, 8, 8);
const redMarker = new THREE.Mesh(markerGeo, new THREE.MeshBasicMaterial({color: 0xff0000}));
redMarker.position.set(0, 1, 3);
this.playerCar.add(redMarker);
const blueMarker = new THREE.Mesh(markerGeo, new THREE.MeshBasicMaterial({color: 0x0066ff}));
blueMarker.position.set(0, 1, -3);
this.playerCar.add(blueMarker);
```
Press W — car should move toward one marker. That direction is forward.

### 2C: Camera sign
If forward = Z+: `behind.z = -cosA * dist`
If forward = Z-: `behind.z = +cosA * dist`

### 2D: BodyGroup check
Check: does buildVDriftCar create a bodyGroup with rotation?
- If YES (group rotation): addWheelsToCar MUST receive the OUTER group, not bodyGroup
- If NO (vertex transform): bodyGroup has no rotation, all coordinates are world-space

### 2E: Forward direction
```
After (x,z,-y) transform where y- = front:
  Z+ is forward → worldDz = +cosA * speed, rotation.y = atan2(x, z)
  Z- is forward → worldDz = -cosA * speed, rotation.y = atan2(x, -z)
```

## Level 3: addWheelsToCar Crash Protocol (NEW)

### 3A: Check for the "group is not defined" ReferenceError
**Symptom**: Game starts, canvas is black, console shows:
```
Uncaught (in promise) ReferenceError: group is not defined
    addWheelsToCar http://localhost:8000/dist/bundle.js:2
    buildVDriftCar http://localhost:8000/dist/bundle.js:2
```

**Root Cause**: The function `addWheelsToCar(parentGroup: THREE.Group, accentColor: number)` was renamed from an old signature (previously `addWheelsToCar(group: THREE.Group, ...)` or `addWheelsToCar(bodyGroup: THREE.Group, ...)`), but the internal reference `const wheelParent = group;` was never updated to match the new parameter name.

**The Five Signatures That Cause This Crash** (any of these patterns are wrong if the internal reference doesn't match):
```
// Parameter named X, but body references Y → ReferenceError: Y is not defined
addWheelsToCar(parentGroup...) { const wheelParent = group; ... }     ← CRASH
addWheelsToCar(bodyGroup...) { const wheelParent = group; ... }       ← CRASH  
addWheelsToCar(group...) { const wheelParent = bodyGroup; ... }       ← CRASH
```
The parameter name and the first usage of it INSIDE the function MUST match exactly.

**Fix**: 
```typescript
private addWheelsToCar(parentGroup: THREE.Group, accentColor: number): void {
    const wheelParent = parentGroup;  // ← MUST match parameter name
    // ... use wheelParent everywhere ...
}
```

### 3B: Check the call site in buildVDriftCar
```typescript
// buildVDriftCar(group, ...):
// 'group' is the outer group — this is what we want for wheels
// bodyGroup is the rotated child — DON'T pass this
this.addWheelsToCar(group, accentColor);  // ← pass 'group', NOT 'bodyGroup'
```

**Why**: If you pass `bodyGroup` (which has rotation), the wheel positions get warped by the rotation matrix. A local y-coordinate of 0.06 becomes world z-coordinate of -0.06, and local z=1.53 becomes world y=1.53 (the roof!). The wheels end up on the roof of the car.

## Level 4: Wheel Position Mismatch

### 4A: Check wheel Y-coordinate
After applying the vertex transform (x, z, -y):
- Body minimum y = original minimum z (e.g., -0.52 for ATT)
- Tire center y = body_min_y + tire_radius (e.g., -0.52 + 0.30 = -0.22)
- Body maximum y = original maximum z (e.g., 0.66 for ATT)

If `positions` array uses y=0.06 (original z of wheel vertices ≈ ground level) instead of y=-0.22 (body bottom + tire radius), the wheels float at body midpoint in the air.

**Correct**: `y = min_z_of_model + wheel_radius`

### 4B: Check wheel Z-coordinate (which axle)
After (x, z, -y) transform where y- is front:
- Front wheels should be at z = -front_y ≈ -1.53 (NOT z = -1.97 which is bumper!)
- Rear wheels should be at z = -rear_y ≈ +1.49

Using body extremes (z=±1.97) puts wheels at bumpers, not under arches. Always find wheel arch positions from vertex data at the body's widest points near the ground.

## Level 5: Five-System Alignment (NEW — CRITICAL)

When forward direction is wrong (car moves backward on W), ALL of these must change together:

| Component | If forward = Z+ | If forward = Z- |
|-----------|-----------------|-----------------|
| `worldDz` in updatePlayer | `+cosA * speed` | `-cosA * speed` |
| `rotation.y` in createPlayerCar | `atan2(x, +z)` | `atan2(x, -z)` |
| `rotation.y` in createAICars | `atan2(x, +z)` | `atan2(x, -z)` |
| `behind.z` in updateCamera | `-cosA * dist` | `+cosA * dist` |
| `ai.z +=` in updateAI | `+cos(angle) * speed` | `-cos(angle) * speed` |
| `targetAngle` in updateAI | `atan2(dx, +dz)` | `atan2(dx, -dz)` |

**NEVER** change just one of these. A common mistake: fix worldDz and rotation.y but forget camera → car moves forward but camera is in front of car (drone view). Or fix worldDz but forget AI → player moves forward but AI drives backward.

## Quick Reference — Correct State (ATT model, vertex transform, verified y- = front)

| Parameter | Value |
|-----------|-------|
| bodyGroup rotation | NONE (vertex transform) |
| wheel y-position | -0.22 (body min y + tire_radius) |
| wheel positions | front: (±0.72, -0.22, -1.53), rear: (±0.70, -0.22, 1.49) |
| carY | 0.52 |
| body y-range after transform | -0.52 ~ 0.66 |
| engine | M3 E46 S54B32: 365Nm@4900rpm, 8000rpm redline |
| gears | [4.23, 2.53, 1.67, 1.23, 1.00, 0.83] + FD 3.62 |
| tires | 255/40R18, radius=0.33m |
| tire_peak_mu | 1.05 |
| brake_max_decel | 11.0 m/s² (1.12g) |
