---
name: web-game-debugging
description: >-
  Systematic debugging and QA methodology for Three.js/WebGL browser games.
  Covers: end-to-end render verification, physics state inspection, 
  webpack class-scope pitfalls, UI stub detection, scale/layout mismatch diagnosis,
  and the 5-layer game-break detection protocol.
category: engineering
tags:
  - three-js
  - webgl
  - game
  - debugging
  - qa
  - webpack
---

# Web Game Debugging

Systematic methodology for diagnosing broken Three.js/WebGL browser games in production-like runs.

## Core Principle: The 5-Layer Game-Break Detection Protocol

## 触发条件
- 用户提及调试、修复、分析代码问题时
- 需要系统性排查复杂Bug时
- 执行架构分析或代码审核时


When a game shows UI but nothing happens visually, DO NOT patch individual features. Run the 5-layer check in order:

### Layer 1: Console Errors — Real vs Noise
- Open browser DevTools Console **before** clicking anything.
- Distinguish Three.js internal warnings (`THREE.Material: parameter 'emissive' has value of undefined`) from actual JS `ReferenceError`s.
- **KEY**: A single `ReferenceError` in `requestAnimationFrame` loop kills ALL subsequent frames silently. One bad line = entire game appears frozen.
- If you see `ReferenceError: XYZ is not defined` in any update function, THAT is the root cause. Fix it before touching anything else.

### Layer 2: Static Method → Global Scope Test
- HTML `onclick="ClassName.method()"` does NOT work with webpack-bundled TypeScript. The class name is module-scoped.
- **Fix**: Route all HTML callbacks through the imported singleton instance:
  ```typescript
  // WRONG - webpack breaks this:
  static selectCar() { ... }  // HTML: onclick="ClassName.selectCar()"
  
  // RIGHT - route through the default export:
  import game from './GameClass';
  window.Game = {
    selectCar: () => game.selectCar(),
  };
  ```
- Every method that an HTML button needs must be either (a) an instance method routed through `window.Game`, or (b) explicitly assigned to `window`.

### Layer 3: Update Function Liveness
- For any `requestAnimationFrame` loop, verify each called function actually executes:
  ```javascript
  // insert at loop entry:
  frameCount++;
  if (frameCount % 60 === 0) console.log('gameLoop alive, state=', this.gameState);
  ```
- If logs appear but visuals don't change, the problem is inside one of the update functions.

### Layer 4: Function-by-Function Method Call Audit
- When `initFullScene()` fails silently, check every called method:
  ```
  this.generateTrack()     → does it exist? does it throw?
  this.createPlayerCar()   → does it throw?
  this.createAICars()      → does it throw?
  this.gameLoop()          → does it throw on first frame?
  ```
- If `if (!canvas) return;` triggers, **log it**: missing canvas element.

### Layer 5: WebGL Renderer Liveness
```javascript
try {
  this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
} catch(e) {
  console.error('WebGL init failed:', e);
  // show user-visible error message
}

try {
  this.composer = new EffectComposer(this.renderer);
} catch(e) {
  console.warn('Composer failed, using fallback:', e);
  this.composer = null; // fallback to direct renderer.render()
}
```

## NEW: Audio NaN → gameLoop Silent Death (Proven Pattern)

**THE MOST COMMON HIDDEN KILLER** for Three.js racing games with Web Audio synthesis.

### Mechanism
1. Audio update function (`updateAudio`) references class constants like `ENGINE_IDLE_RPM` that **don't exist** (lost during TypeScript migration from old HTML)
2. `(currentRpm - this.ENGINE_IDLE_RPM) / (this.ENGINE_MAX_RPM - this.ENGINE_IDLE_RPM)` → `(1000 - undefined) / (undefined - undefined)` → `NaN`
3. `this.engineOsc.frequency.value += NaN` → `TypeError: The provided float value is non-finite`
4. This exception is **NOT caught** in `gameLoop()` because there's no try-catch around individual update functions
5. Entire `requestAnimationFrame` loop dies silently → **game appears black/static**
6. Clock stops advancing (`elapsedTime = 0.00`)
7. Renderer shows 0 calls
8. User reports "black screen with HUD" — because scene and HUD elements were created, but never re-rendered after frame 1

### Detection Protocol
```javascript
// Step 1: Is the game loop alive?
window.game.clock.elapsedTime  // If stuck at 0.00, loop is dead

// Step 2: Is the renderer being called?
window.game.renderer.info.render.calls  // If 0, nothing renders

// Step 3: Any JS errors?
// Check browser console OR:
// Call gameLoop() directly to catch the exception:
try {
  window.game.gameLoop();
} catch(e) {
  console.error('gameLoop crash:', e.message, e.stack);
}

// Step 4: Check audio for NaN propagation
const rpm = window.game.vdriftPhysicsFull.engine.getRPM();
'IDLE: ' + window.game.ENGINE_IDLE_RPM + ' MAX: ' + window.game.ENGINE_MAX_RPM
// If undefined → this is the root cause
```

### Root Cause: Missing Class Constants
When migrating from HTML/JS to TypeScript/webpack, **all global constants must become class members**:

```typescript
// WRONG — works in HTML/JS globals, lost in TypeScript class:
private updateAudio() {
  const rpmNorm = Math.max(0, Math.min(1, (currentRpm - ENGINE_IDLE_RPM) / (ENGINE_MAX_RPM - ENGINE_IDLE_RPM)));
  // ENGINE_IDLE_RPM is undefined in class scope!
}

// RIGHT — declared as class field:
export class PlushRacingGame {
  private readonly ENGINE_IDLE_RPM = 850;
  private readonly ENGINE_MAX_RPM = 7200;
  
  private updateAudio() {
    const rpmNorm = Math.max(0, Math.min(1, (currentRpm - this.ENGINE_IDLE_RPM) / (this.ENGINE_MAX_RPM - this.ENGINE_IDLE_RPM)));
  }
}
```

### Fix Pattern
1. **Add missing constants** as class fields with `readonly`
2. **Wrap ALL update functions in try-catch** at the gameLoop level so one bad frame doesn't kill the entire loop:
```typescript
private gameLoop = (): void => {
  try {
    this.updatePlayer(delta);
    this.updateAudio(delta);
    // ... other updates ...
    this.renderer.render(this.scene, this.camera);
  } catch(e) {
    console.warn('Game loop error (non-fatal):', e);
    // Loop continues to next frame
  }
  requestAnimationFrame(this.gameLoop);
};
```
3. **Add isFinite guards** on all AudioParam.value assignments:
```typescript
const vol = 0.02 + rpmNorm * 0.12;
if (isFinite(vol)) {
  this.engineGain.gain.value += (vol - this.engineGain.gain.value) * delta * 4;
}
```

### Verification
- [ ] `grep -rn "ENGINE_IDLE_RPM\|ENGINE_MAX_RPM" src/` returns hits in class field declarations (not just references)
- [ ] Call `window.game.gameLoop()` directly — no TypeError
- [ ] `window.game.clock.elapsedTime` increases by >2 after 2 seconds
- [ ] `window.game.renderer.info.render.calls > 0` after 2 seconds

## Common Three.js Web Game Break Patterns

### Race Condition: `{caret}` in Source Code
- If you use `patch` with caret-position markers from an editor, **you will accidentally leave `{caret}` in the file**.
- This becomes `ReferenceError: caret is not defined` at runtime in the browser.
- **Fix**: `grep -n "caret" src/*.ts` after every session of heavy patching. Delete any matches.

### Empty UI Button Stubs
- `static selectCar() { console.log('选择车辆'); }` — this is a **stub**, not a feature.
- Before declaring a feature "done", verify it produces user-visible output (DOM manipulation, scene change, alert).
- If the user clicks a menu button and nothing happens, the handler is almost certainly an empty console.log.

### Scale Mismatch — Track Length vs Speed
- Track control points for "real" F1 circuits need to be large enough. Scaling factor `s=50` with MAX_SPEED=80 gives ~35s laps — feels tiny.
- **Rule of thumb**: for a 60-90s lap time:
  - Track circumference ≈ 3000-6000 units
  - MAX_SPEED ≈ 150-250 units/s
  - ACCEL ≈ 40-60 units/s²
- Formula: `lapTime ≈ circumference / (MAX_SPEED × 0.7)` (accounting for corners)

### Three.js EffectComposer Failures
- `EffectComposer` import path: `three/examples/jsm/postprocessing/EffectComposer.js`
- If this module fails to load (version mismatch, missing peer deps), the entire init chain breaks.
- **Always wrap composer init in try-catch** and provide a `renderer.render()` fallback.

### Bloom Killing Dark Detail
- High bloom strength (`UnrealBloomPass` strength > 0.5) washes out dark areas to invisible.
- For "cyberpunk night" scenes with dark roads, keep bloom < 0.2.
- Always test with bloom OFF to see if the scene is actually rendering.

## Linked References

- `references/racing-game-code-audit-workflow.md` — Full code audit protocol: 11 bug patterns by severity, fix spiral, verification checklist
- `references/racing-game-drift-physics.md` — Drift/sideslip physics implementation: grip break model, 5-difficulty tuning table, code snippets

## ⚠️ USER QUALITY STANDARD — "禁止简单实现" (格林主人 2026-05-29 固化)

This user has an **absolute zero-tolerance policy** for the following, in priority order:

1. **禁止程序化生成冒充真实数据** — NO procedural geometry pretending to be a "real" vehicle model. NO CatmullRomCurve + planar mesh pretending to be a "real" track. If the user asks for "real赛道" and you generate it with code, they will catch it and be enraged.
2. **禁止降级实现** — NO stub/mock/placeholder/toy implementations. Every feature must be fully functional end-to-end. A `console.log('选择车辆')` instead of a working vehicle selector is NOT acceptable.
3. **禁止示例代码/占位符** — NO "// TODO: implement later". NO empty function bodies. NO "this will be expanded in future versions". Ship real code now.
4. **禁止所有车用同一套物理** — Each vehicle must have unique, realistic physics parameters (top speed, acceleration, handling, braking, weight, horsepower). NEVER share a single set of values across all vehicles.
5. **禁止"看起来像"——必须是"就是"** — The standards are binary: either it IS a real 3D model parsed from a real source, or it's fake. There is no "good enough approximation".

### What "real" means in this context

| Feature | Fake (will be rejected) | Real (accepted) |
|---------|------------------------|-----------------|
| Vehicle model | BoxGeometry + ExtrudeGeometry with hand-drawn shape | .joe/.obj/.glb model from VDrift or other real source, correctly parsed |
| Track | Procedural CatmullRom grid with Canvas texture | GPS-based control points with real elevation, or .jpk track data |
| Physics | All vehicles share Tier-based default values | Each vehicle reads independent topSpeed/accel/handling/braking/weight |
| Environment | Flat ground plane | Grass base + 3D barriers + grandstands + pit buildings + trees + curbs + billboards |

### What to do instead

- **Download real open-source game assets**: VDrift (SourceForge, 484MB), Speed Dreams, Rigs of Rods — all have real vehicle and track models
- **Write format converters**: `.joe` → JSON/OBJ is a well-defined binary format (see `references/vdrift-joe-parsing.md`)
- **Give each car unique physics**: Research real specs (top speed, 0-100 time, weight, horsepower, braking distance) and encode them directly in the model list
- **Build full track environments**: Grass base + asphalt surface + red/white curbs + 3D tube barriers + grandstands + billboards + pit buildings + trees

### Verification

Before declaring any game feature "done":
- [ ] Is it using real 3D model data from a real source? (not procedural geometry)
- [ ] Does each vehicle have unique physics parameters?
- [ ] Does every menu button produce visible user-visible output?
- [ ] Can the player actually drive and feel the difference between vehicles?
- [ ] Would the user call this "降级实现"? If yes, redo it.

## COMMANDMENT: Zero Key-Conflict Audit (ADDED 2026-05-29)

**DO NOT deploy any keyboard-driven game without running a zero key-conflict audit.**

The canonical failure mode: `D` simultaneously bound to `turn right` (via `__keys` state tracking) AND `cycle difficulty` (via `keydown` event listener). Both are in `main.ts` (global `__keys` record) and `GameClass.ts` (`keydown` handler), NOT canceling each other — both execute.

### Audit Protocol

```
1. Collect ALL driving keys from __keys reads (updatePlayer etc.)
   grep -rn "keyState\[" src/
   
2. Collect ALL function keys from keydown event listeners
   grep -rn "e.code === '" src/
   
3. Find intersection
   conflict = set(drive_keys) & set(func_keys)
   
4. Fix: Move ALL function keys OUTSIDE the WASD zone
   Left hand (WASD)  = DRIVING ONLY
   Right hand (Q/E/R/T/F/G) = FUNCTIONS
   Tab/Esc = secondary functions
```

### Golden Layout (proven to work)

```
W A S D / Arrow Keys  = DRIVE ONLY (accelerate/brake/steer)
         Q  = camera/view   (left of W, safe)
         E  = vehicle/tier  (right of W, E=Engine)
         R  = difficulty    (right side)
         F  = paint/spray   (right side, F=spray/Finish)
         T  = tune/upgrade  (right side)
       Tab  = track/circuit (deliberate keypress only)
   1-4/Digits = upgrade parts (top row)
      Esc  = pause/menu
```

**NEVER let A/S/D also control a function. NEVER let any function key sit inside the WASD cluster.**

**DO NOT deploy any keyboard-driven game without running a zero key-conflict audit.**

The canonical failure mode: `D` simultaneously bound to `turn right` (via `__keys` state tracking) AND `cycle difficulty` (via `keydown` event listener). Both are in `main.ts` (global `__keys` record) and `GameClass.ts` (`keydown` handler), NOT canceling each other — both execute.

### Audit Protocol

```
1. Collect ALL driving keys from __keys reads (updatePlayer etc.)
   grep -rn "keyState\[" src/
   
2. Collect ALL function keys from keydown event listeners
   grep -rn "e.code === '" src/
   
3. Find intersection
   conflict = set(drive_keys) & set(func_keys)
   
4. Fix: Move ALL function keys OUTSIDE the WASD zone
   Left hand (WASD)  = DRIVING ONLY
   Right hand (Q/E/R/T/F/G) = FUNCTIONS
   Tab/Esc = secondary functions
```

### Golden Layout (proven to work)

```
W A S D / Arrow Keys  = DRIVE ONLY (accelerate/brake/steer)
         Q  = camera/view   (left of W, safe)
         E  = vehicle/tier  (right of W, E=Engine)
         R  = difficulty    (right side)
         F  = paint/spray   (right side, F=spray/Finish)
         T  = tune/upgrade  (right side)
       Tab  = track/circuit (deliberate keypress only)
   1-4/Digits = upgrade parts (top row)
      Esc  = pause/menu
```

**NEVER let A/S/D also control a function. NEVER let any function key sit inside the WASD cluster.**
- **DO NOT patch `updatePlayer()` without testing it runs at least 10 frames.** One exception = frozen game.
- **DO NOT declare a menu button "done" without clicking it.** `console.log` is not a feature.
- **DO NOT adjust rendering parameters (bloom, fog, lighting) if the actual game loop isn't running.** Fix the loop first.
- **"有UI但是其他设也没有" = update loop crashed.** Always check for `ReferenceError` in RAF callback.
- **"车子倒着跑" = either headlight/taillight positions swapped (buildVehicle geometry z-coordinates) OR `playerSpeed` allows negative values when it shouldn't.**
- **DO NOT use relative/arbitrary units for track length or speed.** The user demands real meters and real km/h. 1 game unit = 1 meter. Speed displayed as km/h (m/s x 3.6).
- **DO NOT use GPS coordinate conversion for track data.** Hand-craft absolute coordinates per circuit shape. GPS conversion introduces invisible scaling errors.
- **DO NOT hardcode AI progress divisor (`/500`).** Convert AI speed using actual track length: `(speed_mps / trackLen_m) * delta`.
- **"NPC跑得快玩家跑得慢" = AI progress divisor wrong.** Fix the unit conversion before touching physics values.
- **FREE 3D DRIVING vs TRACK-BOUND:** Player position MUST use independent x/z coordinates (`carX`, `carZ`), NOT `trackCurve.getPoint(progress)`. Track-bound driving makes steering a visual-only effect. The user will notice immediately.
- **COLLISION SEARCH RESOLUTION:** With 50 samples on a 5000m circuit, error = +/-100m, causing false-positive collisions that freeze the car. Use `trackLen / 10` samples minimum.
- **COLLISION PUSH VECTOR BUG:** `new THREE.Vector3(this.carX - searchPos.x, ...)` where `searchPos = new THREE.Vector3(this.carX, ...)` produces `(0,0,0)` -- zero vector with NaN normal. Use `nearestPt = this.trackCurve.getPoint(closestProgress)` for push direction.
- **DO NOT scale track length up and down.** Every scaling change breaks ALL physics values. Decide track scale ONCE and derive ALL parameters from it.
- **REAL-WORLD PHYSICS FIRST:** Derive every value from real data before tweaking. F1: 0-100km/h ~2.5s = 11 m/s^2. Top speed ~360 km/h = 100 m/s. Scale for playability (70 m/s, 25 m/s^2) and document the derivation.
- **TRACK MESH Y FOLLOWS CONTROL POINTS:** Use `p.y` directly, NOT `p.y + 0.1`. Adding a fixed offset flattens all elevation changes.
- **TRACK TEXTURE AXIS:** `wrapS` (along track) = repeat many times (30x). `wrapT` (across width) = once. Wrong axis = texture stretched across entire track.
- **COLLISION SPEED PENALTY:** `playerSpeed *= 0.5` is a 50% cut -- too aggressive. Use `*= 0.85` (15% cut) for playable feel.
- **COLLISION PUSH VECTOR MUST USE TRACK NORMAL, NOT CENTER-TO-CAR DIRECTION:** On corners, pushing from nearest point toward car's position pushes the car OUTWARD (wrong direction). Use the track tangent → compute normal (perpendicular) → push along normal toward center. See `racing-game-code-audit-workflow.md` for the correct algorithm.
- **LAP FINISH CROSSING CAN TRIGGER MULTIPLE TIMES PER LAP:** If collision knocks player progress backward past the finish threshold, the `prevProgress < finishZone && now >= finishZone` check fires again. Add a `_lapComplete` boolean: set to `true` on crossing, reset when `progress < 0.01` (start of next lap).
- **CHECK AI ARRAY LENGTH AFTER TRACK SWITCH:** `scene.clear()` removes Three.js objects. But `this.aiProgress` and `this.aiCars` arrays must be fully replaced, not appended to. Use `this.aiProgress[i] = val` instead of `.push()`. Otherwise, every track switch doubles the AI count silently.
- **DO NOT AWARD AI PROGRESS ON PLAYER COLLISION:** `this.aiProgress[i] += 0.008` inside collision branch gives AI a bonus for being hit. Delete this line.
- **VERIFY ALL VEHICLE CONFIG FILES ARE REGISTERED:** If VehicleData uses a hardcoded file list (`registerFromDirectImport`), manually count that all batch/tier files are listed. Missing files mean missing vehicles silently (e.g. 130 written but only 70 registered).

## New: Lap Completion Gate Pattern

The standard lap crossing check `prevProgress < 0.04 && currentProgress >= 0.04` will fire **multiple times per lap** if collision knocks the player backward past 0.04. Fix:

```typescript
// Add class member:
private _lapComplete = true;

// In updatePlayer lap check:
const crossedForward = !this._lapComplete && prevProgress < finishZone && this.playerProgress >= finishZone;

// When crossing:
if (crossedForward) {
    this._lapComplete = true;
    // ... increment lap, record time ...
}

// Reset when back near start:
if (this.playerProgress < 0.01) {
    this._lapComplete = false;
}
```

## New: Track Collision Push Vector Must Use Normal Direction

On corners, pushing from nearest-point toward car position pushes the car **outward** (wrong direction). Correct algorithm:

```typescript
const nearestPt = this.trackCurve.getPoint(closestProgress);
const nearestTangent = this.trackCurve.getTangent(closestProgress);
const normalDir = new THREE.Vector3(-nearestTangent.z, 0, nearestTangent.x).normalize();
const lateralOffset = toCar.dot(normalDir);

if (Math.abs(lateralOffset) > trackHalfWidth) {
    // Push toward track center along normal
    carX -= normalDir.x * pushDist * Math.sign(lateralOffset);
    carZ -= normalDir.z * pushDist * Math.sign(lateralOffset);
}
```

## New: Track Barrier 3D Mesh (TubeGeometry)

Replace 2D `Line` track barriers with 3D `TubeGeometry` for visual clarity:

```typescript
// Collect barrier edge points
const barrierPoints: THREE.Vector3[] = [];
for each track sample:
    compute edge = center + right * (trackWidth/2 + 0.8); edge.y += 0.3
    barrierPoints.push(edge)

// Create tube
const barrierCurve = new THREE.CatmullRomCurve3(barrierPoints);
const tubeGeo = new THREE.TubeGeometry(barrierCurve, points.length * 2, 0.12, 6, true);
const barrierMesh = new THREE.Mesh(tubeGeo, barrierMat);
```

## New: Dynamic Ground Sizing

Static `PlaneGeometry(600,600)` is too small for large tracks (Le Mans ~13km). Compute dynamically:

```typescript
private getTrackBounds() {
    const pts = this.trackCurve.getPoints(50);
    // find min/max x, z
    const size = Math.max(maxX-minX, maxZ-minZ);
    const groundSize = Math.max(600, size * 1.5);
    return new THREE.PlaneGeometry(groundSize, groundSize);
}
```

## New: Camera Distance — Car Must Fill 1/3 of Viewport

**CRITICAL PATTERN**: When the original developer sets camera distance to `12m` with a car that's `1.8m wide`, the car only occupies ~15% of the viewport. The user WILL notice and complain the car is "tiny" and "far away".

### Viewport Occupancy Formula
```
viewport_width ≈ 2 × distance × tan(FOV/2)
car_occupancy = car_width / viewport_width

For FOV=60°, distance=12m:  viewport=13.9m, car (1.8m) = 12.9%  ← TOO SMALL
For FOV=60°, distance=5.5m:  viewport=6.4m,  car (1.8m) = 28.1%  ← ACCEPTABLE
For FOV=60°, distance=2.5m:  viewport=2.9m,  car (1.8m) = 62.0%  ← TOO CLOSE (parked view)
```

### Dynamic Camera Formula (Proven)
```typescript
// Speed in km/h, not m/s
const speedKmh = Math.abs(playerSpeed) * 3.6;

// Distance: 2.5m (stop) to 5.5m (250km/h)
const distance = Math.min(5.5, Math.max(2.5, 2.5 + speedKmh * 0.012));

// Height: slightly above roof level
const height = 1.8 + distance * 0.2;  // 2.3m at 2.5m distance, 2.9m at 5.5m distance

// Look target: car center (y=0.5, NOT y=1.5 — looking too high reveals more empty road)
const lookTarget = carPos.clone();
lookTarget.y += 0.5;  // or lower
```

### Verification
- Test at 0 km/h: car should fill ~35% of screen height in the lower third
- Test at 250 km/h: car should fill ~20-25% of screen height
- The car should NEVER appear "distant" at ANY speed

## New: Random Vehicle+Paint on Game Start

Every `startGame()` call should randomize:
```typescript
selectedTier = Math.floor(Math.random() * 5) + 1;  // T1-T5 random
currentPaintIndex = Math.floor(Math.random() * paintSchemes.length);
```
This gives the player fresh variety each race. Make sure `initPaintSystem()` runs BEFORE `initVehiclePerformance()` in the init chain.

## NEW PATTERN: Duplicate Class Field Causing Runtime ReferenceError

When patching a large TypeScript class repeatedly, you can accidentally create **DUPLICATE FIELD DECLARATIONS** — two `private circuitList` declarations, one in the original field section and one injected via patch into a later method section. The duplicate will compile fine under TypeScript (the second one overwrites) BUT if the second uses a different name (`CIRCUIT_DATA` vs `CIRCUITS`), you get:

```
Uncaught ReferenceError: CIRCUIT_DATA is not defined
```

The error appears at class construction time (before any method runs), so the entire game instantiation fails silently — not caught by webpack or tsc compilation.

### Root Cause Pattern
1. Original field: `private circuitList: type = CIRCUITS;` (at line ~61)
2. A patch inserted new field block near line ~1903 during class member reorganization
3. The new block includes `private readonly circuitList = CIRCUIT_DATA;` (wrong name)
4. TS compiles fine (it's just a field declaration with an undefined runtime reference)
5. At runtime, the class constructor tries to evaluate `CIRCUIT_DATA` → ReferenceError

### Prevention
- After any patch that adds class fields, verify no field is declared with a name that doesn't exist in the import scope
- Log during class construction: `console.log('Class initializing, circuitList =', this.circuitList?.length)`
- Run `npx tsc --noEmit` — this catches *most* reference issues but NOT field-initializer references to undefined variables (those are only caught at runtime)

## New: VDrift Multi-Part Model Index Offset Fix

VDrift `.joe` models export `parts` with `vertOffset`, `vertCount`, `triCount`, `indexCount` but **NOT** `indexOffset`. The code assumes `indexOffset` exists:

```typescript
const iStart = info.indexOffset;  // → undefined
const subIndices = carData.indices.slice(undefined, ...);  // → empty array
```

Result: all parts render as empty geometry → car is invisible (no triangles rendered).

### Fix
```typescript
let iStart = 0;
if (typeof info.indexOffset !== 'undefined') {
    iStart = info.indexOffset;
} else {
    // Accumulate indexCount of previous parts to find start
    for (const [prevName, prevInfo] of Object.entries(carData.parts)) {
        if (prevName === partName) break;
        iStart += (prevInfo as any).indexCount || (prevInfo as any).triCount * 3;
    }
}
```

## New: VDrift Z-up → Y-up Vertex Transform (not Group Rotation)

VDrift coordinate system: `x=right, y=forward (Y+ is front), z=up`. Three.js target: `x=right, y=up, z=backward (Z- is front)`.

**DO NOT use `bodyGroup.rotation.x = -Math.PI / 2`** — this rotates bodyGroup but leaves wheels in original coordinate system, causing wheel/body separation and reversed car direction.

### Correct vertex-level transform (proven)
```typescript
// (x, y, z) → (x, z, -y) — Y+ front → Z- front
// Car front faces Z- (toward camera in Three.js default view)
for (let i = 0; i < rawVerts.length; i += 3) {
    verts[i]   = rawVerts[i];       // x unchanged
    verts[i+1] = rawVerts[i+2];     // y ← original z (up direction)
    verts[i+2] = -rawVerts[i+1];    // z ← -original y (front direction → Z-)
}
// Apply same transform to normals
```

### Wheel positions in transformed coordinates
```
Front wheels: (±0.55, 0.15, -1.64)  ← front of car = Z-
Rear wheels:  (±0.55, 0.15, +1.64)  ← rear of car = Z+
```

### Forward direction code must match
```typescript
// MoveZ = -cos(playerAngle) because car faces Z-
let moveZ = -Math.cos(this.playerAngle) * this.playerSpeed * delta;
```


## Linked References (new)

- `references/racing-game-physics-torque-grip.md` — 3-zone torque curve, grip-break drift model, ABS/TCS integration, difficulty steering feel, AI free-driving pathfinding
- `references/racing-game-vehicle-tier-system.md` — 5-tier vehicle switch architecture, 6-dim profiles, score-to-physics mapping, V-key binding
- `references/three-js-vehicle-geometry.md` — Pure-geometry vehicle construction (Shape+ExtrudeGeometry), tier-specific dimensions, headlight/taillight/spoiler/wheel patterns, camera distance formula
- `references/vdrift-joe-parsing.md` — VDrift .joe binary format specification, complete Python parser, available car models table, Three.js multipart rendering guide (ADDED 2026-05-29)

### Verification

Before declaring a Three.js game session complete:

- [ ] `grep -rn "playCollisionSound\\|playSomeUndefinedSound" src/` — zero hits (undefined functions crash gameLoop)
- [ ] Every update function called from gameLoop is wrapped in try-catch: `try { this.updateX(dt); } catch(e) { console.warn('non-fatal:',e); }`
- [ ] Any function referenced by name in gameLoop-derived code actually exists as a class method. `grep` all method calls after adding new ones.
- [ ] `grep -n "caret" src/*.ts` -- zero results
- [ ] Every HTML `onclick` handler routes through `window.Game`, not a class name
- [ ] `updatePlayer()` runs without throwing for 100+ frames
- [ ] No `ReferenceError` in browser console during gameplay
- [ ] All menu buttons produce visible output (DOM panel, alert, or scene change)
- [ ] Track length matches intended lap time (60-90s for real circuits)
- [ ] Renderer init wrapped in try-catch with fallback
- [ ] Bloom strength < 0.2 for dark scenes
- [ ] Player position uses independent x/z coordinates, NOT track curve progress binding
- [ ] AI speed divisor uses real track length: `(speed_mps / trackLen_m) * delta`
- [ ] Track mesh Y follows control points (no fixed +0.1 offset)
- [ ] Collision push vector uses `nearestPt` not `searchPos` (no zero-vector bug)
- [ ] Collision speed penalty is <= 15% cut (not 50%)
- [ ] Physics values derived from real-world data, documented with derivation
- [ ] No duplicate class field declarations referencing undefined variables (`grep "= [A-Z_]\{3,\}" src/*.ts | grep -v "import\|readonly\|const\|export\|function\|="`)
- [ ] VDrift model parts indexOffset computed cumulatively (not assumed from field)
- [ ] Z-up to Y-up transform done at vertex level, not via group rotation
- [ ] Wheel positions match transformed coordinate system (front Z-, rear Z+)

## Linked Resources

- `references/three-js-scratchpad.md` — Runtime failure signatures, track calibration table, vehicle geometry conventions, difficulty level mapping. Read this when diagnosing a Three.js game that breaks in the browser.
- `references/racing-game-physics-spec.md` — REQUIRED physics spec: real SI units, 7 F1 track lengths, difficulty tables, NPC speed mapping. Consult BEFORE setting physics values.
- `references/racing-game-physics-realworld.md` — **NEW (2026-05-30)** Complete real-world physics reference: 7 car specs (hp/torque/weight/gear ratios), tire grip coefficients (mu), aerodynamic data (Cd/CL/frontal area), suspension spring/damping rates + full physics engine architecture (torque curve → magic formula lateral → yaw dynamics → roll/pitch → position update). Use this when implementing SIM-LEVEL racing physics.
- `references/racing-game-physics-engine-architecture.md` — **NEW (2026-05-30)** Full physics engine code architecture: Pacejka magic formula implementation, torque curve (5-zone S54 engine), yaw moment dynamics, suspension roll/pitch model, wheel velocity → slip ratio → friction circle → drive force chain. Contains the complete `updatePlayer()` logic flow for a SIM-level Three.js racing game.
  - `scripts/verify_game.py` — Automated verification script for post-build QA. Run after every webpack build:
  ```bash
  python3 scripts/verify_game.py src/
  ```

## 回滚方案
### 快速回滚
如果部署后发现问题：
1. 使用版本控制回退到上一个提交：`git revert HEAD`
2. 确认回滚后系统状态正常
3. 通知相关方变更已撤销

### 数据安全
- 所有修改前确认有备份
- 配置变更记录版本历史

---

## NEW (2026-06-01): Input Bus Disconnection

**Symptom**: Player presses W/A/S/D but car does not move/steer. No errors. Game loop runs.

**Root Cause**: `updatePlayer()` reads from `(window as any).__keys`, but no event listeners write to it.

**Fix**: Register keydown/keyup handlers for driving keys in initFullScene().

## NEW (2026-06-01): Steering Direction Inversion

**Symptom**: A turns right, D turns left; OR front wheels visually correct but body opposite.

**Fix**: Negate at key mapping, physics steerAngle, or playerAngle depending on which layer is wrong.

## NEW (2026-06-01): Constant Drift Without Input

**Symptom**: Car drifts left/right while going straight.

**Common cause**: `playerAngle = Math.atan2(vel.x, vel.z)` without negation for Z- forward cars. Fix: `playerAngle = -Math.atan2(vel.x, vel.z)`.
