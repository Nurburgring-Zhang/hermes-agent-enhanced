# Racing Game v2 Enhancements

## Vehicle Tier System (5-Level Classification)

Reference implementation: `src/vehicles/VehicleTierSystem.ts`

```
Tier 1: Hot Hatch / Entry Sports   — 180-250 km/h,  full assists
Tier 2: Sports Car                 — 250-300 km/h,  partial assists  
Tier 3: Supercar / Hypercar        — 300-350 km/h,  minimal assists
Tier 4: GT3/Formula/Rally          — 280-370 km/h,  race assists
Tier 5: Prototype / Le Mans Hyper  — 330-400 km/h,  sim assists
```

Each tier defines: speedRange, accelRange, priceRange, aiSkillRange, assistLevel.

Mapping function: `getVehicleTier(type: string)` converts VehicleType to VehicleTier.

## Paint System

Reference: `src/vehicles/PaintSystem.ts`

- 9 categories: SOLID, METALLIC, MATTE, PEARL, CHROME, CUSTOM, LIVERY, CAMOUFLAGE, GRADIENT, NEON
- Each scheme: primaryColor, secondaryColor(? optional), accentColor, wheelColor, caliperColor, emissiveColor
- PaintSchemeRegistry class with 20+ default schemes
- Livery patterns: racing_stripe, gulf_racing, martini_stripe, castrol_edge, monster_claw
- Per-registry-key scheme sets (e.g. 'sports_car_default', 'race_car_default', 'hot_hatch_default')

## Vehicle Database Registration

VehicleDatabase uses `require('./configs/vehicles_XXX_YYY')` to register all exported vehicle configs.

Key types:
- `VehicleConfig`: complete vehicle config with attributes, appearance, sound, AI, stats
- `VehicleAppearance`: body/color/wheel/spoiler/neon details plus decals/decals/decals
- `VehicleAttributes`: maxSpeed, acceleration, braking, handling, enginePower, weight, tireGrip, etc.

## Lap Detection System

Instead of incrementing lapCount when `playerProgress > 1` (inaccurate), use **finish line zone detection**:

```typescript
const finishZone = 0.05; // 5% of track near start/finish
const prevProgress = this.playerProgress;
this.playerProgress += this.playerSpeed * delta / 500;
if (this.playerProgress > 1) this.playerProgress -= 1;
if (this.playerProgress < 0) this.playerProgress += 1;

// Detect forward crossing of finish line
const crossedForward = prevProgress < finishZone && this.playerProgress >= finishZone && this.playerSpeed > 0;
if (crossedForward && this.raceStartTime > 0) {
    const lapTime = (Date.now() - this.lapStartTime) / 1000;
    this.lapCount++;
    this.lapTimings.push(lapTime);
    this.lapStartTime = Date.now();
}
```

## Collision System

```typescript
// Compute car's offset from track centerline
const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), trackTangent).normalize();
const carOffset = right.dot(new THREE.Vector3(
    carPosition.x - trackCenter.x, 0, carPosition.z - trackCenter.z
));

const trackHalfWidth = 7; // half of total track width
if (Math.abs(carOffset) > trackHalfWidth - 0.5) {
    // Impact! Reduce speed, push back
    playerSpeed *= 0.95;
    collisionCooldown = 0.5;
    const pushDir = -Math.sign(carOffset);
    const pushAmount = (Math.abs(carOffset) - (trackHalfWidth - 0.5)) * 0.5;
    playerProgress += pushDir * pushAmount * 0.01;
    
    // Collision sound via AudioContext noise burst
    const noise = audioCtx.createBufferSource();
    const buf = audioCtx.createBuffer(1, 1000, 44100);
    // Fill with random samples
    const data = buf.getChannelData(0);
    for (let i = 0; i < 1000; i++) data[i] = (Math.random() * 2 - 1) * 0.15;
    noise.buffer = buf;
    const noiseGain = audioCtx.createGain();
    noiseGain.gain.value = 0.15;
    noise.connect(noiseGain).connect(audioCtx.destination);
    noise.start();
    noise.stop(audioCtx.currentTime + 0.1);
}
```

## AI Corner Braking

```typescript
// Sample tangent at two close points
const currentT = trackCurve.getTangent(aiProgress);
const aheadT = trackCurve.getTangent(aiProgress + 0.02);

// Curvature = 1 when tangents point in opposite directions
const dot = currentT.x * aheadT.x + currentT.z * aheadT.z;
const curvature = Math.max(0, 1 - Math.abs(dot));

// Reduce AI speed in corners
const cornerFactor = 1 - curvature * 0.5;
const aiSpeed = baseSpeed * cornerFactor + oscillation;
```

## Drift Physics

When steering hard at high speed, apply downforce-like speed reduction:
```typescript
const driftFactor = 1 - Math.abs(steer) * 0.15 * Math.abs(playerSpeed) / MAX_SPEED;
if (Math.abs(steer) > 0.5 && Math.abs(playerSpeed) > 20) {
    playerSpeed *= driftFactor;
}
```

## Mini-Map (Canvas 2D)

1. Sample 100 points from CatmullRomCurve3
2. Compute bbox of track points
3. Scale to 150x150 canvas with margin
4. Draw track as semi-transparent blue path
5. Draw player as cyan dot with glow
6. Draw AI as colored dots (red/green/magenta)
7. Draw start/finish as green dot

## Air Drag Model

```typescript
const drag = playerSpeed * playerSpeed * 0.0005 * Math.sign(playerSpeed);
playerSpeed -= drag * delta;
```
This creates a natural top-speed limit without hard-capping.
