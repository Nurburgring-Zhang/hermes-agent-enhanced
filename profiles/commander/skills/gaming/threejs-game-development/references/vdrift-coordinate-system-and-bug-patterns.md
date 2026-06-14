# VDrift Coordinate System & This Session's Bug Patterns

## CRITICAL: VDrift Coordinate System — The #1 Source of All Car Orientation Bugs

This session spent 100+ edits fighting car-facing-backwards, wheels-in-air, car-flying-away bugs. The ROOT CAUSE was always the same: wrong coordinate transform.

**VDrift origin coordinate system (VALIDATED against 13 car models by vertex analysis):**
```
x = left/right (negative = left)
y = FORWARD/BACKWARD (y- = FRONT of car, y+ = REAR — THIS IS COUNTERINTUITIVE)
z = UP/DOWN (z+ = up, z- = down)
```

**The most common wrong assumption** (which caused ALL the bugs): assuming y+ is the car front. It's NOT. VDrift uses y- as the front direction.

**Proof from vertex analysis (model ATT.json, Audi TT):**
- y+端(y>1.9): z范围[-0.25, -0.13] — all below z=0, flat = trunk/rear
- y-端(y<-1.9): z范围[-0.26, 0.10] — has z>0 vertices = engine hood bulge = FRONT
- High-z vertices concentrate at y- end: 968顶点 vs 522 at y+ end

## CORRECT Z-up→Y-up Conversion

```typescript
// Option A: Vertex transform (BEST — keeps coordinates clean for all children)
// Formula: newPos = (x, z, -y)
// Front: original y- → new z = -(-1.97) = 1.97 → car faces Z+
verts[i] = rawVerts[i];         // x unchanged
verts[i+1] = rawVerts[i+2];     // y ← original z (up)
verts[i+2] = -rawVerts[i+1];    // z ← -original y (forward, negated)
// Same for normals:
normals[i+1] = rawNorms[i+2];
normals[i+2] = -rawNorms[i+1];

// Option B: Group rotation (use when vertex transform is impractical)
const bodyGroup = new THREE.Group();
bodyGroup.rotation.x = -Math.PI / 2;   // Z-up → Y-up
bodyGroup.rotation.y = Math.PI;        // Flip front from Z- to Z+
group.add(bodyGroup);
// NOTE: Children added to bodyGroup will have their positions rotated AGAIN.
// Add tires to the PARENT group with world-space coordinates.
```

## Wheel Position (Vertex Transform Space)

```
Body Y range after transform: -0.52 (bottom) to 0.66 (top)
Tire center Y = body_bottom + tire_radius = -0.52 + 0.30 = -0.22
carY (vehicle group offset) = 0.52

Tire world Y = carY + (-0.22) = 0.30
Tire contact world Y = 0.30 - 0.30 = 0.0 ✅ (on ground)

Front tires: original (±0.72, y=-1.97, z=0.06) → (±0.72, 0.06, 1.97)
Rear tires: original (±0.70, y=1.89, z=0.05) → (±0.70, 0.05, -1.89)
```

## LatheGeometry Tire Alignment

```typescript
// LatheGeometry rotates 2D profile around Y-axis.
// Tire should be in YZ plane, rolling axis = X (left/right).
// Correct: rotation.z = PI/2 flips Y→X
tire.rotation.z = Math.PI / 2;  // ✅

// All wheel sub-components must share this axis:
// CylinderGeometry:  rotation.z = PI/2 → axis X ✅
// TorusGeometry:     rotation.z = PI/2 → ring in YZ ✅
// Brake disc:        rotation.z = PI/2 → face YZ ✅
```

## Camera Behind Car

```typescript
// Car faces Z+ → Z- is behind
const behind = new THREE.Vector3(
    -Math.sin(angle) * dist,
    height,
    -Math.cos(angle) * dist   // Z- = behind
);

// Car faces Z- → Z+ is behind  
const behind = new THREE.Vector3(
    -Math.sin(angle) * dist,
    height,
    Math.cos(angle) * dist    // Z+ = behind
);
```

## Movement Direction

```typescript
// Car faces Z+ (Option A):
worldDz = cosA * speed;     // +cos = Z+ = forward ✅

// Car faces Z- (bodyGroup rotation ONLY, no vertex transform):
worldDz = -cosA * speed;    // -cos = Z- = forward ✅
```

## Visual Debug: Add Markers

```typescript
const sphereGeo = new THREE.SphereGeometry(0.2, 8, 8);
const frontMarker = new THREE.Mesh(sphereGeo, new THREE.MeshBasicMaterial({color: 0x0066ff}));
frontMarker.position.set(0, 1, 3);  // Z+3 = front marker
carGroup.add(frontMarker);
```

## Race Starts Immediately Bugs

**Three fixes needed together:**
1. Start delay: `const raceStartDelay = elapsed < 3;` in `crossedForward` check
2. Don't reset `_lapComplete` during lap 0: `if (progress < 0.01 && lapCount > 0)`
3. Don't finish if lapCount would exceed: `if (crossedForward && lapCount < TOTAL_LAPS)`

## AI Spin Bug

AI target angle must match movement direction:
```typescript
// If AI moves: ai.z += -cos(angle) * speed (Z- direction)
// Then target must also use Z-:
const targetAngle = Math.atan2(dx, -dz);  // not dz!

// If AI uses progressive model (track follower):
this.aiCars[i].rotation.y = Math.atan2(tangent.x, tangent.z);  // Z+
// OR
this.aiCars[i].rotation.y = Math.atan2(tangent.x, -tangent.z);  // Z-
// Must match player direction!
```

## GPS Circuits — Control Point Density

Real GPS tracks need more control points:
```typescript
// Interpolate 4x points between GPS waypoints
for (let i = 0; i < rawPoints.length; i++) {
    const curr = rawPoints[i];
    const next = rawPoints[(i + 1) % rawPoints.length];
    for (let j = 0; j < 4; j++) {
        const t = j / 4;
        points.push(new THREE.Vector3().lerpVectors(curr, next, t));
    }
}
```

## Slow Start Acceleration

At standstill, force RPM to climb:
```typescript
const minRpmTarget = this.ENGINE_IDLE_RPM + 1000;  // minimum 1800rpm
const rpmTarget = Math.max(minRpmTarget, ...);
```

## Difficulty as Pure Multipliers

```typescript
this._gripMultiplier = [1.3, 1.15, 1.0, 0.85, 0.65][d];
this._powerMultiplier = [1.2, 1.1, 1.0, 0.9, 0.8][d];
// Stacks: mu *= this._gripMultiplier * this._accelMultiplier;
```

## Car Disappears On Move

Fix: set car Y at creation time, not just in updatePlayer:
```typescript
startPos.y = 0.52;
this.playerCar.position.copy(startPos);
this.carY = 0.52;
```
