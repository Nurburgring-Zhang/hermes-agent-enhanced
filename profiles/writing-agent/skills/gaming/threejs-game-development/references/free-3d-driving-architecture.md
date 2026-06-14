# Free 3D Driving Architecture — Three.js Racing Games

## Architecture Decision: Track-Progressive vs Free 3D

This reference documents the migration from track-progressive ("rail") driving to true free-3D driving in a Three.js racing game.

## Conceptual Difference

### Track-Progressive (OLD/BROKEN pattern)
- Car position = `trackCurve.getPoint(playerProgress)` — ALWAYS on the curve centerline
- Car angle = `atan2(trackTangent.x, trackTangent.z)` — ALWAYS tangent to the curve
- "Steering" only changes a small lateral offset (±slipAngle * factor)
- The car CANNOT leave the track or drive independently
- This is essentially a rail-shooter with a car skin

### Free 3D (NEW/CORRECT pattern)  
- Car has independent X/Z coordinates: `carX += sin(playerAngle) * speed * delta`
- Car angle changes via actual steering input: `playerAngle += steerInput * STEER_SPEED * delta`
- The track curve is ONLY used for: lap detection (find nearest point), boundary collision (distance from nearest point), AI (still follows progress)
- The car CAN leave the track, spin out, drive in reverse, etc.

## Migration Steps

### Step 1: Add independent position variables
```typescript
private carX = 0;
private carZ = 0;
private carY = 0.5;
```

### Step 2: Replace position update in physics loop
```typescript
// OLD — glues car to track:
this.playerProgress += this.playerSpeed * delta / trackLength;
const pos = this.trackCurve.getPoint(this.playerProgress);
this.playerCar.position.copy(pos);

// NEW — free driving:
const moveX = Math.sin(this.playerAngle) * this.playerSpeed * delta;
const moveZ = Math.cos(this.playerAngle) * this.playerSpeed * delta;
this.carX += moveX;
this.carZ += moveZ;
this.playerCar.position.set(this.carX, this.carY, this.carZ);
```

### Step 3: Replace angle update
```typescript
// OLD — forced to track tangent:
const targetAngle = Math.atan2(trackTangent.x, trackTangent.z);
this.playerCar.rotation.y = targetAngle;  // always faces track direction

// NEW — player controls heading:
if (Math.abs(this.playerSpeed) > 0.5) {
    const speedFactor = Math.max(0.3, 1 - speedNorm * 0.5);
    this.playerAngle += steerInput * this.STEER_SPEED * delta * speedFactor;
}
this.playerCar.rotation.y = this.playerAngle;
```

### Step 4: Replace lap detection
```typescript
// OLD — derived from playerProgress:
const prevProgress = this.playerProgress;
this.playerProgress += speed * delta / 500;
// check crossing of 0→1 boundary

// NEW — project onto track curve each frame:
let closestProgress = 0;
let closestDist = Infinity;
const searchPos = new THREE.Vector3(this.carX, 0, this.carZ);
for (let t = 0; t <= 1; t += 0.02) {
    const pt = this.trackCurve.getPoint(t);
    const d = searchPos.distanceTo(pt);
    if (d < closestDist) { closestDist = d; closestProgress = t; }
}
const prevProgress = this.playerProgress;
this.playerProgress = closestProgress;
// now check crossing of 0→1 boundary normally
```

### Step 5: Replace boundary collision
```typescript
// OLD — offset from track centerline:
const carOffset = right.dot(carPos - trackPos);
if (Math.abs(carOffset) > trackRight) { /* push back */ }

// NEW — distance from nearest point:
if (closestDist > trackRight) {
    // car left the track — push toward nearest point on curve
    this.carX += pushDir.x * (closestDist - trackRight + 0.5) * -0.3;
    this.carZ += pushDir.z * (closestDist - trackRight + 0.5) * -0.3;
    this.playerSpeed *= 0.5;
}
```

### Step 6: AI stays on progress model
AI vehicles do NOT need free driving — they remain on the track-progressive model:
```typescript
this.aiProgress[i] += aiSpeed * delta / 500;
const aiPos = this.trackCurve.getPoint(this.aiProgress[i]);
this.aiCars[i].position.copy(aiPos);
```

## Pitfalls

### DO NOT mix models
If car position comes from `trackCurve.getPoint()` but playerAngle changes independently, the car will SLIDE SIDEWAYS while being dragged forward. Either fully commit to free 3D or fully commit to progress-based.

### Lap detection with brute-force nearest point
The 50-sample loop runs every frame. For cars far from the track (crashed), the nearest point may be geometrically ambiguous. This is acceptable for arcade physics but not for simulation.

### Speed units
When switching to free 3D, speed is in "game units per second" (no conversion needed). HUD display: `kmh = Math.round(speed * 3)` for reasonable display values (120 speed → 360 km/h displayed).
