# Three.js Game Break Heuristics — Field Notes

## Debugging Protocol: The "Useless UI" Pattern

User says "UI shows but nothing works." 
→ The `requestAnimationFrame` callback is throwing on frame 1.
→ Work backward from the RAF entry point.

### Step-by-step

1. Open browser DevTools Console BEFORE clicking anything.
2. Filter for `ReferenceError`. Ignore Three.js material warnings.
3. If you see `ReferenceError: XYZ is not defined` in a RAF function:
   - THAT line is the root cause. Fix it first.
   - Common culprits: `{caret}` artifacts, undefined variable references in patch leftovers.
4. If NO errors but game is frozen:
   - Add a frame counter log at loop entry.
   - If counter stops after frame 1, the loop body threw and `requestAnimationFrame` was never called again.
5. If loop runs but visuals don't change:
   - The render call may be silently failing (composer vs renderer fallback missing).
   - Try skipping composer entirely: use `this.renderer.render(this.scene, this.camera)` directly.

### Known One-Line Killers

```
let steerInput = steerRaw;{caret}
```
→ Causes `ReferenceError: caret is not defined`. `grep -rn "caret" src/` after patching.

## The Track-Bound vs Free Driving Trap

### Symptom
Player can steer visually but position follows the racing line anyway. "转向不管用，顺着赛道跑"

### Root Cause
Position is computed from `trackCurve.getPoint(playerProgress)` instead of independent x/z coordinates.

### Fix
```typescript
// WRONG — track-bound:
this.playerProgress += this.playerSpeed * delta / 500;
const pos = this.trackCurve.getPoint(this.playerProgress);
this.playerCar.position.copy(pos);

// RIGHT — free 3D driving:
this.carX += Math.sin(this.playerAngle) * this.playerSpeed * delta;
this.carZ += Math.cos(this.playerAngle) * this.playerSpeed * delta;
this.playerCar.position.set(this.carX, this.carY, this.carZ);
this.playerCar.rotation.y = this.playerAngle;

// Then find nearest track point for lap detection only:
let closestDist = Infinity;
let closestProg = 0;
for (let t = 0; t <= 1; t += 1/samples) {
  const d = carPos.distanceTo(this.trackCurve.getPoint(t));
  if (d < closestDist) { closestDist = d; closestProg = t; }
}
this.playerProgress = closestProg;
```

### Collision Push Direction Bug
```typescript
// DEADLY — pushDir is (0,0,0):
const searchPos = new THREE.Vector3(this.carX, 0, this.carZ);  // SAME as car
...
new THREE.Vector3(this.carX - searchPos.x, ...)  // = 0!

// FIX — use nearest track point:
const nearestPt = this.trackCurve.getPoint(closestProgress);
const dx = this.carX - nearestPt.x;
const dz = this.carZ - nearestPt.z;
```

### AI Speed vs Player Speed Mismatch

AI uses progress (0-1), player uses real meters. These are DIFFERENT coordinate systems.

```typescript
// WRONG — AI speed is dimensionless:
this.aiProgress[i] += aiSpeed * delta / 500;  // 500 is arbitrary

// RIGHT — convert to real units:
const trackLen = circuitList[currentCircuitIndex].gameLength;  // meters
this.aiProgress[i] += (aiSpeed_mps / trackLen) * delta;  // progress per second
```

## Track Mesh Construction

### Y-Coordinate Must Follow Terrain
```typescript
// WRONG — flat road with offset:
const left = p.clone().add(right.clone().multiplyScalar(-trackWidth / 2));
left.y += 0.1;  // <-- Bad: ignores control point elevation

// RIGHT — road follows terrain:
const left = p.clone().add(right.clone().multiplyScalar(-trackWidth / 2));
// left.y is already p.y — keep it
```

### Texture Orientation
```typescript
// Track runs along U axis (wrapS), width is V axis (wrapT):
trackTexture.wrapS = THREE.RepeatWrapping;     // along track
trackTexture.wrapT = THREE.ClampToEdgeWrapping; // across track (1x stretch)
trackTexture.repeat.set(30, 1);  // 30 repeats along length, 1x across width

// Canvas layout for track texture (1024x128):
// - 1024 pixels wide = along track direction
// - 128 pixels tall = across track width
// - Yellow lines at top+bottom edges = track boundaries
// - White dashed line center = lane marking
```

## Track Scale Decision

**Set scale ONCE and derive everything from it.**

Wrong approach:
```
s = 50 → too short → s = 300 → too big → s = 120 → physics broken again
```

Right approach:
```
Pick target lap time → compute required circumference → set scale → derive speed/accel from real physics
```

Example:
- Target: 60-90s lap
- Circuit: Silverstone real = 5891m → game ~5000m
- Speed: 70 m/s × 0.7 (corner efficiency) × 71s = ~3500m traveled ≈ right
- Set ALL physics from real-world car data, not arbitrary numbers

## Memory Update Criteria

When the user expresses frustration about a class of problem (>2 occurrences), add it to the appropriate skill's pitfalls section. Frustration is a FIRST-CLASS skill signal.

Signal patterns that warrant skill updates:
- "为什么还不是X" (Why is it still not X?) → previous fix was incomplete
- "你他妈" + specific technical complaint → root cause was missed, add check
- Repetition of same complaint across multiple sessions → systemic blind spot
