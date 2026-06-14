---
name: racing-game-physics-migration
description: >-
  Migrate physics, vehicle parameters, and track data from open-source racing
  sims (VDrift, Speed Dreams, Rigs of Rods) into a custom Three.js/web racing
  game. Covers VDrift .joe model parsing, .car physics config extraction,
  Pacejka tire model porting, 6-DOF vehicle dynamics (engine/transmission/
  suspension/brake/aero), coordinate system alignment, and per-vehicle wheel
  position calibration from model vertex data.
trigger:
  - user mentions VDrift, Speed Dreams, Rigs of Rods, or any open-source racing game
  - task involves racing game physics, car handling, tire model, vehicle dynamics
  - need to extract real car dimensions (wheelbase, track, CG) from 3D model vertices
  - porting C++ racing sim physics to JavaScript/TypeScript
  - user says "参考其他游戏" or "迁移物理" or "抄作业"
  - user says review code or deep audit paired with game or racing or physics
  - user says migrate with physics or handling or powertrain
  - task involves building a complete physics engine from C++ source in TypeScript
  - user says "全量迁移" or "全部迁移" or "全部迁移过来"
  - user says "深度审核" or "深度对比其他游戏" paired with racing game
  - user says integrate all modules or integrate into render loop
  - user says context truncation or context split during racing game work
references:
  - references/vdrift-idp2-format.md — VDrift IDP2 binary model format: JOE Face structure, vertex/normal/texcoord dedup, glass/interior merge, failure modes
  - references/joe-face-global-index-fix.md — v9 fix: JOE Face uses GLOBAL vertex indices, NOT local `fi*3+j` (2026-06-01 session fix)
  - references/black-screen-root-cause.md — full diagnostic chain for Three.js racing game black screen: 6 root causes found in 2026-06-01 session (audio NaN crash, position NaN cascade, thrust-zeroed-by-integration, disconnected input bus, model cache, visibility limitation)
  - references/vdrift-physics-migration.md — detailed migration notes from this session
  - references/coordinate-system-conversion.md — VDrift Z-up to Three.js Y-up
  - references/code-audit-checklist.md — complete multi-engine code audit checklist for racing game projects
  - references/full-codebase-migration-20260531.md — full session record: all modules created, webpack tree-shaking fix, CarDynamics integration pitfalls, user signals (截断拆分), file manifest
scripts:
  - scripts/convert_v8.py — VDrift IDP2 binary → Three.js JSON model converter (JOE Face dedup + NaN protection)
  - scripts/extract-wheel-positions.py — extract per-vehicle wheel positions from .joe vertex data
  - scripts/generate-car-configs.py — generate VDrift .car format configs for all 13 models
templates:
  - templates/vdrift-physics-engine.ts — complete portable VDrift physics engine template
---

# Racing Game Physics Migration from VDrift

## Golden Rules (from user corrections)

1. **NEVER simplify or degrade the physics.** The user will detect and reject simplified models. Always port the **complete** formula chain from the source (VDrift cardynamics.cpp → full engine/transmission/clutch/differential/tire/suspension/brake/driveline). A partial port (engine + tire alone) is dead code — the user's previous session had exactly this problem where VDriftCarDynamics was instantiated but its update() never called.

2. **Per-vehicle data must be derived from the model, not hardcoded uniformly.** Every car has unique:
   - Wheelbase, track front/rear (extract from .joe vertex data)
   - Tire size (width, radius, rim radius)
   - Wheel position (front axle z, rear axle z, wheel center y)
   - Engine torque curve (from VDrift .car or real specs)
   - Gear ratios and final drive (from VDrift .car)

3. **Phase-by-phase delivery.** Break into phases the user can validate:
   - Phase 1: Model orientation + wheel position (visual)
   - Phase 2: Engine + transmission torque model
   - Phase 3: Tire (Pacejka) + steering
   - Phase 4: Suspension + aero + brake
   - Phase 5: Full track migration
   - Phase 6: Complete test + debug cycle

4. **Coordinate system is the #1 source of bugs.** VDrift: x=right, y=forward(y+ is nose), z=up. Three.js: x=right, y=up, z=forward. Conversion: `(x, z, -y)` on vertices, `group.rotation.x = -PI/2` for group-level rotation.

5. **Physics code lives in a separate file** (src/physics/VDriftPhysics.ts), not inline in the game class. Main class imports and instantiates `VDriftCarDynamics`.

6. **Camera MUST be fixed behind car.** Never bind camera to world-space coordinates or let physics perturbations affect camera stability. Fixed distance, fixed height, lerp-smooth following.

## Extended Migration Scope (2026-05-31 session outcome)

When the user says "全部迁移过来" or "包括其他赛车游戏", they mean **everything** — not just physics.
The complete racing game codebase at `/mnt/d/minimax/racing game package/` contains:

| Source | Contents | Size |
|--------|----------|------|
| `vdrift_data/vdrift/` | VDrift full C++ source (145 files) | ~24,393 LoC |
| `vdrift_data/speed-dreams-data.tar.xz` | Speed Dreams track data (9 tracks) | 768K |
| `racing_v2/index.html` | Single-file HTML game (drift system) | 69K |
| `racing_v3/index.html` | Single-file HTML game (environment) | 53K |
| `racing_v4/index.html` | Single-file HTML game (multi-camera) | 50K |
| `racing_final/index.html` | Final single-file HTML game | 48K |
| `racing_final_v2/index.html` | Latest single-file HTML (opponents + AI) | 47K |

### All Modules Created

```
src/physics/VDriftPhysicsFull/    ← Phase 1 ✅ Complete (14 files, 2264 LoC)
  CarDynamics.ts         — main update loop (727 LoC, port of cardynamics.h/.cpp)
  CarEngine.ts           — Heywood friction + torque spline + NOS
  CarClutch.ts           — clutch friction torque
  CarTransmission.ts     — fwd/rev ratios + shift logic
  CarDifferential.ts     — LSD (1way/1.5way/2way)
  CarBrake.ts            — bias + handbrake
  CarSuspension.ts       — spring + damping + anti-roll
  CarWheel.ts            — wheel physics
  CarTire.ts             — Pacejka MF: Fx/Fy/Mz full + combining
  Driveline.ts           — MotorJoint + ClutchJoint + solve2/solve4
  DriveShaft.ts          — shared by Engine + Wheels + Driveline
  Spline.ts              — Catmull-Rom torque curve interpolation
  CarConfigs.ts          — 13 real car specs (hp/torque/ratios/weight/drive)
  index.ts               — re-export

src/ai/VDiftAICar.ts              ← VDrift ai_car_standard.cpp port (212 LoC)
src/effects/DriftSystem.ts        ← from racing_v2/v3/v4 drift model (148 LoC)
src/effects/EffectsSystem.ts      ← smoke/sparks/exhaust/skidmarks (226 LoC)
src/effects/WeatherSystem.ts      ← clear/cloudy/rain/night (179 LoC)
src/effects/CameraSystem.ts       ← 5 camera modes from racing_v4 (140 LoC)
src/tracks/RealTracks.ts          ← 9 Speed Dreams track parser (191 LoC)
```

### Integration Checklist (for PlushRacingGame.ts)

1. **VDrift Physics**: In `updatePlayer()`, replace `vdriftPhysics.update(dt, t, b, s)` with `SetThrottle()/SetBrake()/SetSteering()` then `.Update(dt)`
2. **Drift**: Add `DriftSystem` update in `gameLoop()` using VDrift physics speed
3. **Effects**: Create `EffectsSystem` in `initFullScene()`, call `update()` in gameLoop
4. **Weather**: Create `WeatherSystem`, bind X key to cycle Weather enum
5. **Camera**: Replace inline camera code with `CameraSystem.cycleMode()` via C key
6. **Tracks**: Use `PRESET_TRACKS` or `generateProceduralTrack()` as circuit source
7. **AI**: Create `VDiftAICar` per opponent with own CarDynamics, pass track curve

## Multi-Engine Code Audit (when user says "审核代码" or "深度审核")

### Step 1: Full File Structure Survey
- `find /path -maxdepth 3 -type f | sort`
- Identify: git repos, model data, multiple version dirs, VDrift/Speed Dreams source
- Check dist/models/*.json for extracted VDrift 3D models

### Step 2: Dual-Physics-Engine Detection (CRITICAL)
Look for three parallel physics systems:
1. Partial VDrift TS port (`src/physics/VDriftPhysics.ts`)
2. Cannon-es wrapper (`src/engine/PhysicsEngine3D.ts` or `src/physics/PhysicsEngine.ts`)
3. Hand-rolled inline physics in the main game class

**Diagnosis:**
- Is `VDriftCarDynamics` or `CarDynamics` instantiated? Is `.Update()` called in game loop?
- Is Cannon-es `world.step()` called? What bodies does it step?
- Is `// @ts-nocheck` present? That suppresses type errors and often indicates incomplete porting.
- Use `browser_console` to check `window.game.vdriftPhysicsFull` at runtime.

### Step 3: 7 Defect Categories
1. Dead code / unintegrated modules
2. Degraded physics model (bicycle vs 4-wheel)
3. Wrong coordinate system on model loading
4. Box collision instead of raycast-vehicle
5. Binary-only input (no linear throttle/brake)
6. C++ source present but not ported
7. Monolithic game class (2500+ lines)

### Step 4: Visual Model Analysis
For each dist/models/*.json: numVerts, numTris, parts, coordinate conversion correctness.

## User Preference Signals as Pitfalls

### 截断拆分 (context truncation task splitting)
When output gets truncated during a long game dev session:
1. IMMEDIATELY stop
2. Output a short diagnostic (< 10 lines)
3. Propose the FIRST substep only (under 500 chars)
4. Wait for confirmation before proceeding

**Do NOT** dump plan + state + question in one shot. Split by substep.

### 深度审核要求 (deep audit)
When user says "深度审核" + "其他赛车游戏" or "深度对比其他游戏" + "全部迁移":
1. Scan ALL source directories first
2. List all old HTML games and identify unique features per version
3. Output migration table: old feature → new module file
4. "包括其他赛车游戏" means ALL game versions, not just VDrift

### 构建后自动验证 (build-then-verify)
After every `npx webpack`:
1. Check `grep -c 'NewModule' dist/bundle.js` — if 0, tree-shaking ate it
2. Kill + restart http.server
3. Navigate browser, click start, check console errors
4. If user says "黑屏": (a) is server running? (b) did bundle.js get served fresh?

## Architecture Reference

### CarDynamics API (used by PlushRacingGame.ts)
```
// Init
const config = buildCarConfig('M3');
const dyn = new CarDynamics();
dyn.Load(config);
dyn.transmission.Shift(1);          // Start in 1st gear

// Per frame
dyn.SetThrottle(throttle);          // 0..1
dyn.SetBrake(brake);                // 0..1
dyn.SetSteering(steer);             // -1..1
dyn.Update(dt);                     // dt in seconds

// Read state
dyn.getSpeed();                     // m/s
dyn.getSpeedKMH();                  // km/h
dyn.engine.getRPM();                // RPM
dyn.transmission.GetGear();         // gear number
dyn.velocity.x / .z;                // m/s (x=lateral, z=forward)
dyn.position.x / .z;                // world position
```

## Pitfalls

- **DO NOT** use `group.rotation.x = -PI/2` and then set `playerCar.rotation.x` in updatePlayer — the update overwrites the group rotation.

- **Wheel positions must be in the SAME space as the body.** Either both in vertex-transformed world space, or both in group-rotated local space.

- **Camera position must use `carAngle` (the yaw angle), NOT `playerAngle` from yawRate.** The latter is the internal physics state; the former is the rendered rotation.

- **Driveline clutch & motor arrays MUST be pre-allocated.** `clutch: ClutchJoint[] = []` crashes with `undefined`. Fix:
  ```
  clutch: ClutchJoint[] = [new ClutchJoint(), new ClutchJoint(), new ClutchJoint(), new ClutchJoint()]
  motor: MotorJoint[] = [new MotorJoint(), new MotorJoint(), new MotorJoint(), new MotorJoint(), new MotorJoint()]
  ```

- **Private class properties without `= null` never create a runtime property.** `private driftSystem: DriftSystem;` means `'driftSystem' in instance` is `false`. With `@ts-nocheck`, no warning. Always write `private x: X | null = null;`.

- **Always prefix new-systems init with ONE try-catch.** If any of the 12+ earlier init steps silently fails, the new-systems block never runs. The symptom: all systems show `null` at runtime, no console errors. Fix:
  ```
  try {
    this.driftSystem = new DriftSystem();
    this.effectsSystem = new EffectsSystem(this.scene);
    // ... all new system inits
  } catch(e) { console.error('new systems init failed:', e); }
  ```

- **Place ALL new-system init BEFORE any code that can fail asynchronously** (model loads, track gen, etc.). The traditional position "after initDifficulty" is too late — if Canvas acquisition or renderer creation fails, everything after the `return` statement never runs.

- **C++ `&this.xxx` syntax in TypeScript** — replace `&this.` with `this.`. TS object references are pointer-like.

- **Double `* dt` in air drag.** The C++ step `velocity *= exp(-drag * dt)` → TS `v -= drag * v * dt`. NOT `v -= drag * v * dt * dt`.

- **`if (this.drive & DriveEnum.FWD)` is correct.** VDrift uses bitwise flags (FWD=1, RWD=2, AWD=3). The `&` is bitwise AND, NOT address-of.

- **Webpack production mode silently tree-shakes whole module chains.** After build: `grep -c 'YourClassName' dist/bundle.js`. If 0, fix: `optimization: { sideEffects: false, usedExports: false }` or `mode: 'development'`.

- **Default `autoShift = false` leaves gear=0 (neutral).** Initialize: `vdriftPhysicsFull.transmission.Shift(1)`.

- **`window.game.driftSystem = null` while `weatherSystem = object` is a strong signal the init code BETWEEN those two lines threw.** Wrap everything in one try-catch.

- **Never start a multi-module migration without reading PlushRacingGame.ts fully.** The `initFullScene()` and `gameLoop()` methods have init-then-update chains that must be understood before inserting new code.

- **VDrift IDP2 binary format ≠ ASCII JOE.** Binary IDP2: 20B header + verts(32B each) + JOE Faces(18B each). Each face's vertex indices are LOCAL (0,1,2) — global = `face_num*3 + local`. Normal/tex indices are GLOBAL. Dedup key = `(global_vi, norm_ni, tex_ti)`. See `scripts/convert_v8.py`.

- **Model JSON NaN propagation.** Even when vertex data parses without NaN, JOE Face normal/tex indices can point outside bounds → reading wrong floats → NaN in output. Fix in `convert_v8.py`:
  ```python
  v = verts[global_vi] if global_vi < len(verts) else (0,0,0)
  if v[0] != v[0] or v[1] != v[1] or v[2] != v[2]: v = (0, 0, 0)
  n = norms[ni] if ni < len(norms) else (0,0,0)
  if n[0] != n[0] or n[1] != n[1] or n[2] != n[2]: n = (0, 0, 1)
  ```
  Then re-convert ALL models (not just failing ones), re-build webpack, kill+restart http.server, verify on fresh browser session.

- **Browser cache for model JSON.** If `fetch('dist/models/CO.json')` returns cached NaN-stale data despite file being clean on disk, append `?v=${Date.now()}` to the URL. The built-in `http.server` does not send `Cache-Control: no-cache` headers.

- **JOE Face indices are GLOBAL, not local.** Each JOE Face has 9 uint16 values: `v0,v1,v2,n0,n1,n2,t0,t1,t2`. The vertex indices v0/v1/v2 are GLOBAL — they point directly into the full verts array. Do NOT use `fi*3+j` (face_num*3 + local_index). That produces 4x vertex count inflation and garbled model geometry. Verified on all 13 VDrift models.

  **Correct parsing:**
  ```
  for j in range(3):
      vi = [v0, v1, v2][j]       # USE these values, they are global indices
      ni = [n0, n1, n2][j]
      ti = [t0, t1, t2][j]
      key = (vi, ni, ti)
  ```

- **Thrust impulse gets zeroed by PositionIntegration.** When adding thrust to `velocity` in `CarDynamics.Update()`, the subsequent bicycle-model position integration re-reads `speed = this.getSpeed()`. If `speed` was captured **before** the thrust was added, it's still 0 and `this.velocity = newDir * 0` zeros everything. Fix: **recalculate speed after thrust**:
  ```
  const currentSpeed = Math.sqrt(this.velocity.x**2 + this.velocity.z**2);
  // then use currentSpeed, not old speed variable
  ```

- **Three constants must be defined in PlushRacingGame class.** `ENGINE_IDLE_RPM = 850` and `ENGINE_MAX_RPM = 7200` are referenced in `updateAudio()` but were never defined after migration from old HTML. If undefined, `NaN` → `AudioParam.value = NaN` throws every frame → gameLoop stops → black screen.

- **`__keys` bus must be populated.** The input system (`updatePlayer`) reads from `(window as any).__keys`, but nothing writes to it unless `keydown`/`keyup` event handlers are registered. Add both handlers in `initFullScene()` with an array of driving keys.

- **Black screen ≠ no rendering.** `browser_snapshot` (accessibility tree) cannot show WebGL canvas content. HUD visible + 0 JS errors + mesh count > 0 = game renders correctly in real browser. The diagnostic chain is: check clock.elapsedTime growing → check renderer.info.render.calls (1+ → composer working) → check key positions for NaN → check gameLoop try-catch.

- **`updateAudio` MUST be wrapped in try-catch.** Any NaN in audio math crashes the entire gameLoop because the browser throws `TypeError` on `AudioParam.value = non-finite`. Fix:
  ```
  private updateAudio(delta: number): void {
      try {
          // ... all audio code ...
      } catch(e) {
          console.warn('🔇 音频更新错误:', e);
      }
  }

- **Position null cascade → black screen** (most common black screen cause in racing games):
  1. `createPlayerCar()` calls `initVDriftPhysics()` BEFORE setting `this.carX = startPos.x`
  2. `initVDriftPhysics()` does `physics.position.x = this.carX` → gets `undefined`
  3. Game loop reads `this.carX = physics.position.x` → `NaN`
  4. `this.playerCar.position.x = this.carX` → Three.js Vector3 gets `NaN`
  5. `CameraSystem.update()` reads `carPos.x = NaN` → camera at (NaN, y, NaN) → black screen
  **Fix:** Set carX/carZ BEFORE initVDriftPhysics:
  ```typescript
  this.carX = startPos.x;
  this.carZ = startPos.z;
  this.initVDriftPhysics();  // now uses valid carX/carZ
  this.playerCar.position.copy(startPos);  // position not overwritten by physics
  ```

- **`updateAudio` NaN crash on every frame.** Old code used `this.rpm` (stale variable never updated by new physics). When `this.rpm` is undefined, math produces NaN → `AudioParam.value = NaN` throws every frame. Fix:
  ```typescript
  const currentRpm = this.vdriftPhysicsFull?.engine.getRPM() ?? 850;
  if (!isFinite(currentRpm) || currentRpm < 0) return;
  const rpmNorm = Math.max(0, Math.min(1, (currentRpm - IDLE) / (MAX - IDLE)));
  ```

- **`browser_snapshot` cannot show WebGL content.** It only captures accessibility tree (HTML elements). HUD appears, Three.js canvas does NOT. To diagnose black screen in headless test: check `scene.background`, `scene.children` count, `camera.position` for NaN, `playerCar.position` for NaN. If all OK, the game IS rendering — user needs a real browser. The Black Screen Is The Snapshot, Not The Game.

- **AI car integration pattern.** VDiftAICar wraps its own CarDynamics. Create one per opponent with `buildCarConfig()`. Call `update(dt, trackCurve)` per frame. AI uses its own physics instance — does NOT share player's dynamics.

## VDrift IDP2 Binary Model Format (2026-06-01 — complete rewrite)

The JOE file format has been corrected 3 times across this session. The final working version is in `scripts/convert_v12.py`. See `references/idp2-format-v12-discovery.md` for full specification.

**Key corrections from the session:**
1. **2 uint32, NOT 3** — the third "uint32" is the first float of the normal data
2. **Actual vertex count = num_texcoords** (second uint32), NOT num_verts (first)
3. **GLOBAL vertex indices** in JOE Face — each face index points to any position in the verts array
4. **Coordinate conversion:** `(x, z, -y)` from file → Three.js

### Coordinate Debugging Workflow (when model is wrong)

When the user says "车身是一坨杂乱的破碎的几何体拼接" or similar:

1. **Check bounding box:** `mesh.geometry.computeBoundingBox()` — if y range > z range by 2x+, the y/z swap is wrong
2. **Check vertex range from file directly:** `python3 -c "import struct; ..."` to read raw floats without conversion
3. **Check if vertex range is [-1,1]:**
   - If yes → using wrong num_verts (use num_texcoords instead)
   - If range is small (< 0.1 in any axis) → coordinate swap is wrong
4. **Check face index range:** if max vertexIndex > actual vertex count, 90% of faces get skipped → low tri count
5. **Check normals:** if num_normals read as ~3.2B, you read one extra uint32

**Fast validation:** Run convert_v12.py, then check output:
```python
d = json.load(open('dist/models/XS.json'))
v = d['verts']
xs, ys, zs = v[::3], v[1::3], v[2::3]
print(f'x=[{min(xs):.2f},{max(xs):.2f}] y=[{min(ys):.2f},{max(ys):.2f}] z=[{min(zs):.2f},{max(zs):.2f}]')
# Expected: x=~[-2,2], y=~[-1,1], z=~[-2,2]
```

## Friction Circle Physics Model (user-enforced, 2026-06-01)

The user explicitly demanded **tire friction circle** physics. The model must be based on:

```
mu = 1.0 (tire-road friction coefficient)
Fz_per_wheel = mass * g / 4
F_max_per_wheel = mu * Fz_per_wheel

DRIVE:  driveForce = min(engineTorque * gearRatio * 0.85 / wheelRadius, F_max_per_wheel)
BRAKE:  brakeForce = brakeInput * F_max_per_wheel * 4 (all 4 wheels braking)
LATERAL: remainingFriction = max(0, F_max * 4 - |driveForce|)
         latDecel = remainingFriction / mass
```

### Pitfalls in the friction model

- **Brake is NOT part of netForceLong.** Brake was originally `netForceLong = drive - brake` which made `velocity.z -= negative_accel` = acceleration. Brake must be a SEPARATE speed reduction (proportional to current velocity):
  ```
  brakeDecel = brakeValue * maxFrictionPerWheel * 4 / mass * dt
  newSpeed = max(0, currentSpeed - brakeDecel)
  velocity *= (newSpeed / currentSpeed)
  ```

- **Lateral grip must use REMAINING friction.** The friction circle means longitudinal force (drive+brake) consumes part of the tire's total grip. The remaining grip is available for cornering:
  ```
  usedLongForce = abs(driveForceLong)
  remainingFriction = max(0, maxFrictionPerWheel * 4 - usedLongForce)
  maxLatDecel = remainingFriction / mass
  ```

- **Lateral force proportional to latSpeed**, not instant annihilation. Strong grip but not teleportation:
  ```
  reduction = min(1.0, maxLatDecel * dt / max(0.001, latSpeed))
  velocity.x -= latVx * reduction
  velocity.z -= latVz * reduction
  ```
  When `maxLatDecel * dt >= latSpeed`, `reduction = 1.0` → full lateral grip (no slide).
  When grip is insufficient, `reduction < 1.0` → controlled slide.

- **Air drag creates natural speed limit.** No hardcoded maxSpeed cap needed:
  ```
  aeroForce = 0.5 * rho * Cd * A * v²
  aeroDecel = aeroForce / mass * dt
  velocity *= (max(0, currentSpeed - aeroDecel) / currentSpeed)
  ```
  At some speed, `aeroForce * dt / mass ≈ currentSpeed`, which is the true terminal velocity.

- **Rolling resistance adds low-speed decay:**
  ```
  rrDecel = 0.015 * g * dt
  velocity *= (max(0, currentSpeed - rrDecel) / currentSpeed)
  ```

## Critical Session Discovery: wheelPositions Coordinate Format (2026-06-01)

**THE #1 BUG SOURCE** in this session was misinterpreting wheelPositions data format. Correct understanding:

```typescript
// wheelPositions data for each car (hardcoded in PlushRacingGame.ts):
const wheelPositions: Record<string, number[][]> = {
    'M3': [[-0.79,-0.28,-1.90],[0.79,-0.28,-1.90],[-0.77,-0.28,2.10],[0.77,-0.28,2.10]],
    // ...
};
```

**FORMAT**: `[x左右, z上下, y前后]` — NOT (x,y,z) and NOT (x,z,-y).

- `pos[0]` = x (左右, unchanged in Three.js)
- `pos[1]` = z (上下, becomes y in Three.js)  
- `pos[2]` = y (前后, becomes z with negation in Three.js)

**CORRECT Three.js conversion:**
```typescript
wg.position.set(pos[0], pos[1], -pos[2]);
//                  x       y(z上下)   z(-y前后取反)
```

**WRONG conversions that caused bugs in this session:**
- `set(pos[0], pos[2], -pos[1])` — puts pos[2](前后) in y(上下) → wheels underground/overground → "车身树立起来"
- `set(pos[0], pos[1], pos[2])` — no negation → car faces backward

**Wheel Group Construction (correct — unified rotation):**

```typescript
for (let idx = 0; idx < positions.length; idx++) {
    const pos = positions[idx];
    const wg = new THREE.Group();
    wg.position.set(pos[0], pos[1], -pos[2]);  // COORDINATE CONVERSION
    
    // ALL wheel parts at default Y-axis orientation, then wheelGroup rotates once
    const wheelGroup = new THREE.Group();
    wheelGroup.rotation.z = Math.PI / 2;  // Y-axis → X-axis (horizontal, car width direction)
    wg.add(wheelGroup);
    
    // Tire (LatheGeometry defaults to Y-axis)
    wheelGroup.add(tire);
    // Hub (CylinderGeometry defaults to Y-axis)
    wheelGroup.add(hub);
    // Rim (TorusGeometry defaults to Z-axis, looks same after rotation)
    wheelGroup.add(outerRing);
    // Spokes in YZ plane (wheelGroup rotation makes them XZ plane)
    wheelGroup.add(spoke);
    // Brake disc (CylinderGeometry defaults to Y-axis)
    disc.position.y = -tireWidth * 0.35;  // Offset along Y (becomes Z after rotation)
    wheelGroup.add(disc);
}
```

**Pitfall — do NOT mix per-part rotations with group rotation.** If `wheelGroup.rotation.z = PI/2` is set, do NOT also set `tire.rotation.z = PI/2` or `hub.rotation.z = PI/2` — the child objects stay in default orientation (Y-axis) and the parent group rotates them all at once. This prevents alignment mismatch between tire/hub/disc.

**`isFront` detection:** Use index, not coordinate:
```typescript
wg.userData.isFront = idx < 2;  // First two positions = front wheels
```

### Friction Circle Physics Model (2026-06-01 validated)

The user explicitly demanded physics based on **tire friction circle** — acceleration, braking, and cornering forces are all bounded by available tire grip:

```typescript
const mu = 1.0;  // tire-road friction coefficient
const g = 9.81;
const fzPerWheel = this.mass * g / 4;      // per-wheel normal force (N)
const maxFrictionPerWheel = mu * fzPerWheel; // per-wheel max friction (N)

// Drive force (limited by tire grip, not just engine torque)
driveForceLong = Math.min(engineTorque * gearRatio * 0.85 / wheelRadius, maxFrictionPerWheel);

// Brake force (proportional to brake input × available grip)
brakeForceLong = brakeValue * maxFrictionPerWheel * 4;  // all 4 wheels

// Lateral force = remaining friction after longitudinal force
usedLongForce = Math.abs(driveForceLong);
remainingFriction = Math.max(0, maxFrictionPerWheel * 4 - usedLongForce);
maxLatDecel = remainingFriction / this.mass;
```

Key rule from user: **刹车力度应当随速度、车重、轮胎摩擦力和路面情况，实时变化** — brake force must be dynamic based on current conditions, NOT a fixed constant.

### User's Physics Philosophy (from session corrections)

1. **推力应随挡位和转速变化** — NOT linear speed-based decay. Use engine torque curve × gear ratio × final drive.
2. **刹车力度应基于轮胎摩擦力** — NOT fixed deceleration. Use `brakeInput × mu × mass × g × 4`.
3. **侧向力使用摩擦圆** — longitudinal + lateral share the same friction budget.
4. **极速由推力=阻力自然平衡** — NOT hardcoded speed cap. Air drag + rolling resistance balance thrust.

## VDrift Source Code Location

All source at `/mnt/d/minimax/racing game package/vdrift_data/vdrift/src/physics/`:
- `cardynamics.cpp` — main dynamics integration (1977 lines)
- `carengine.cpp/h` — engine model
- `cartire1.cpp/h` / `cartire2.cpp/h` / `cartire3.cpp/h` — Pacejka MF (levels 1/2/3)
- `carsuspension.cpp/h` — suspension
- `cartransmission.h` — gear ratios
- `carbrake.h` — brake model
- `carclutch.h` — clutch
- `cardifferential.h` — differential (open/LSD/center)
- `driveline.h` — full driveline constraint solver (287 lines)
- `driveshaft.h` — inertia + angular velocity integration

## Vehicle Config Format (VDrift blank.car)

Key sections: [engine], [transmission], [suspension-front], [suspension-rear], [tire-front], [tire-rear], [brake], [differential]

Torque curve: `torque-curve-NN = rpm, torque_Nm`

Wheel positions derived from model JSON, grouped by car ID.
