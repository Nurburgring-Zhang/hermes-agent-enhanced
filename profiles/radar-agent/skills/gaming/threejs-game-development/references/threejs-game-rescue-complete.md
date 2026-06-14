---
name: threejs-game-rescue
description: "Rescue, compile-fix, and build AI-generated Three.js game codebases. End-to-end process: fixing structural TypeScript errors, porting from inline HTML to webpacked modules, creating procedurally-generated 3D racing/WebGL games, and deploying as playable browser app."
trigger: "user asks to review/fix/upgrade a Three.js game project, or codebase has AI-generated game code with structural issues"
---

# Three.js Game Rescue and Architecture

## Goal

## 触发条件
- 用户提及此功能相关关键词时
- 遇到此领域的标准问题时
- 需要执行该领域的标准操作时

Take a broken or skeleton AI-generated Three.js game codebase and turn it into a compilable, runnable, playable browser game.

## Workflow

### Phase 0: Full Feature Audit (DO NOT SKIP — prevents cascade-fix spiral)

**Critical**: Before touching any code, produce a **complete feature inventory** mapping every UI element, button, game method, and callback to its implementation status. This prevents the cascade-fix trap where each fix breaks something else because you never had a full picture.

1. Run `find` on project structure to map source files, assets, configs
2. Count files: `find src -name '*.ts' | wc -l`, sum lines per file
3. Check `package.json` for dependency version conflicts and nonexistent packages (e.g. `lil@0.6.0` typo)
4. **Backup first**: `cp -r project /backup/path/`
5. Run `npx tsc --noEmit` to get baseline error count
6. Check for dual architecture (inline HTML game code + separate TypeScript src/)

#### Feature Inventory (mandatory table)

Before changing code, produce a table mapping every externally-visible feature to its implementation status:

| Feature | Expected Behavior | Actual Implementation | Status |
|---------|-----------------|----------------------|--------|
| Menu: Start Race | Hides menu, starts game loop | Calls game.startGame() | OK |
| Menu: Select Vehicle | Shows vehicle picker | `console.log('选择车辆')` — **STUB** | BROKEN |
| Menu: Select Character | Shows character picker | `console.log('选择角色')` — **STUB** | BROKEN |
| Menu: Settings | Shows settings panel | `console.log('游戏设置')` — **STUB** | BROKEN |
| Menu: Credits | Shows credits | `console.log('游戏制作信息')` — **STUB** | BROKEN |
| ... | ... | ... | ... |
| Pause: Resume | Hides pause menu, resumes physics | `() => {}` — **EMPTY** | BROKEN |
| Pause: Restart | Resets game to initial state | Calls nonexistent `PlushRacingGame.start()` | BROKEN |
| Pause: Return to Menu | Hides pause, shows main menu | Complex expression with optional chaining | BROKEN |

**Key audit signals**:
- `static XYZ(): void { console.log(...); }` = placeholder/stub — **always broken**
- `() => {}` in `window.Game` callbacks = empty handler — **always broken**
- `?.` optional chaining in `returnToMenu` = likely buggy
- Methods referencing nonexistent static methods = runtime crash

**Why this matters**: Fixing visual bugs (track too dark, car facing wrong way) while menu buttons are stubs means the user will see "nothing works" even after visual fixes. Always fix structural stubs first, then visual bugs.

### Phase 1: Structural Fix
When the codebase has AI-generation errors (block brace mismatches, wrong import paths, undefined types, missing CANNON imports):

1. Fix entry file first (the main game class usually has the worst brace errors — look for unmatched try/catch blocks)
2. Fix import paths referencing non-existent directories (e.g. `./levels/LevelManager` → `./managers/LevelManager`)
3. Add missing `import * as CANNON from 'cannon-es'` to files using CANNON types
4. Add missing interfaces/enums that are referenced but never defined (VehicleClass, VehicleTemplate, DecalConfig optional fields, etc.)
5. Fix webpack.config.js: use CommonJS `module.exports`, replace `contentBase` with `static`, add file loaders for glb/gltf/mp3/ttf
6. Handle dependency conflicts with `--legacy-peer-deps` if needed
7. Add `// @ts-nocheck` to AI-generated config/data files when strict typing is impossible
8. For large repetitive vehicle config files, add @ts-nocheck rather than fixing every type mismatch

### Phase 2: Engine Unification
When there are TWO game engine implementations (inline HTML + TypeScript src/):

1. Identify which is the NEW target (TypeScript src/)
2. Keep the inline HTML's CSS/UI framework (buttons, HUD, menus)
3. Remove CDN script tags for three.js and cannon.js (bundle them via webpack)
4. Remove the inline `const Game = { ... }` object entirely (can be 60KB+)
5. Remove the inline `window.addEventListener('load', initGame)` event — it fires before bundle.js loads
6. Also remove any inline cannon-check scripts that warn about loading
7. Add `<script src="bundle.js"></script>` before `</body>`
8. Wire HTML onclick handlers to bundle via `window.Game` object — note that `PlushRacingGame` is a webpack module, NOT global

### Phase 3: Build a Playable Game

1. Use `THREE.CatmullRomCurve3` with 16+ control points forming a closed loop for the track
2. Generate track mesh by computing left/right edges along the curve normals using cross product
3. Simplified vehicle physics (acceleration, braking, friction, max speed, steering that scales with speed)
4. Add air drag: `playerSpeed -= playerSpeed² × 0.0005` for realistic top-speed limit
5. Add drift effect: when steering hard at high speed, speed is reduced by a drift factor
6. Camera that lerps to behind-car position using the car's forward angle
7. AI opponents at different initial progress values — use curvature-based corner braking via tangent dot-product
8. Game loop via requestAnimationFrame with delta time clamping
9. Bloom post-processing via EffectComposer + UnrealBloomPass
10. Procedural city buildings with lit windows arranged in rings
11. Neon light poles at regular intervals along track edges + cross-track arch lights
12. Web Audio API oscillator (sawtooth + lowpass filter) frequency-coupled to speed

### Phase 3b: Lap Detection and Collision System

1. Finish line: detect crossing of progress=0 zone (finishZone = 0.05 of track length)
2. Track progress-based: track when the car passes from `progress < finishZone` to `progress >= finishZone` going forward
3. Lap timing: record lapStartTime, compute lapTime on crossing, push to lapTimings array
4. Keep bestLapTime, total lap count, compare with TOTAL_LAPS to trigger finishRace()
5. Boundary collision: compute car's offset from track centerline using right-vector dot product. If offset > trackWidth/2 - ε, apply speed penalty, push car back toward center, trigger collision sound. Use collision cooldown timer.
6. **Player-AI collision** (often missing!): After boundary checks, iterate AI cars, compute 2D distance to player. If < 1.8 (car width), push both apart on their progress values, reduce speeds, trigger collision sound. This prevents AI vehicles from phasing through the player.

```typescript
// Player-AI collision snippet
const playerPos = playerCar.position;
for (let i = 0; i < aiCars.length; i++) {
    const dx = playerPos.x - aiCars[i].position.x;
    const dz = playerPos.z - aiCars[i].position.z;
    const dist = Math.sqrt(dx * dx + dz * dz);
    if (dist < 1.8) {
        const pushStrength = (1.8 - dist) * 0.5;
        playerProgress -= pushStrength * 0.005;
        playerSpeed *= 0.6;
        aiProgress[i] += pushStrength * 0.005;
        collisionCooldown = 0.3;
        playCollisionSound();
        break;
    }
}
```

### Phase 3c: HUD System — Specific ID Pattern (preferred over SVG)

After this session's refactoring, the recommended HUD pattern uses specific DOM IDs, not SVG query selectors:

```typescript
// GOOD — use specific element IDs:
const speedEl = document.getElementById('speed-value');
if (speedEl) speedEl.textContent = String(displaySpeed);

const lapEl = document.getElementById('hud-lap-value');
if (lapEl) lapEl.textContent = `${currentLap} / ${totalLaps}`;

const lapTimeEl = document.getElementById('lap-time-value');
if (lapTimeEl) lapTimeEl.textContent = `${currentTime.toFixed(1)}s`;

const posEl = document.getElementById('race-position');
if (posEl) posEl.textContent = `第 ${rank} 名`;
```

**HTML structure for HUD**: Use specific `id` attributes on `<span>` elements, not SVG `<text>`:
```html
<div id="speed-gauge">
    <span class="speed-value" id="speed-value">0</span><span class="speed-unit">km/h</span>
</div>
<div id="race-info">
    <div class="lap">圈数: <span id="hud-lap-value">1 / 3</span></div>
    <div class="time">⏱ <span id="hud-time-value">0:00</span></div>
    <div class="position" id="race-position">第 1 名</div>
</div>
```

**Legacy SVG pattern** (avoid — fragile, slow, hard to debug):
The inline HTML from original AI output often creates speed gauges as SVG elements inside `#speed-gauge`. This requires `querySelector('#speed-gauge svg').querySelectorAll('text')` — which fails silently if the SVG structure is slightly different.

### Phase 3d: Skill Upgrades — AI Corner Braking, Drift Physics, Minimap

### 5-Level AI Difficulty System

When implementing AI difficulty aligned with the player's difficulty setting:

```typescript
// AI speed by difficulty: [30, 38, 45, 55, 65]
// AI skill (corner): 0.3 + difficulty * 0.12  → 0.30, 0.42, 0.54, 0.66, 0.78
// AI consistency: 1 - difficulty * 0.05 → harder AI is more stable/less noisy
// AI variance noise: (1 - consistency) * 8 → random fluctuations

// Corner braking by AI skill level (not hardcoded 0.5 factor):
const aiSkill = 0.3 + difficulty * 0.12;
const cornerFactor = 1 - curvature * aiSkill;  // low-skill AI slows down MORE in corners
```
```typescript
const dot = currentTangent.x * aheadTangent.x + currentTangent.z * aheadTangent.z;
const curvature = Math.max(0, 1 - Math.abs(dot)); // 0=straight, 1=sharp turn
const speedFactor = 1 - curvature * 0.5;
```

**Minimap**: Render on a 2D Canvas:
1. Get 100 sample points from the CatmullRom curve
2. Compute world-space bounding box of track points
3. Scale and translate to canvas coordinates
4. Draw track path (stroke), player position (cyan), AI positions (colored dots)
5. Update every frame via updateMinimap()

### Phase 4: Build Pipeline and Deploy
1. Build: `npx webpack --mode production`
2. Clean dist before each build: `rm -rf dist`
3. Copy assets (textures, audio) to `dist/assets/`
4. Regenerate dist/index.html from source (remove CDN, inline Game, add bundle.js reference)
5. Serve (preferred): `cd /project/root && python3 -m http.server 8000`
   - **Python http.server is more reliable than `serve`** — it correctly serves root index.html without directory-listing mode, has no zombie process issue, and needs no npm install
   - Fallback: `npx serve -s dist -l 8000` (single-page mode, avoids directory listing)
   - Kill old servers: `pkill -f "python3.*http.server"` or `pkill -f "serve"`

### Phase 5: Browser Testing Loop
1. Navigate to localhost via browser tool (handle `ERR_CONNECTION_REFUSED` by retrying after 2s)
2. Click start button, verify HUD elements via snapshot
3. Check for JS errors via browser_console
4. Simulate keyboard with `window.__keys`
5. Verify speed display updates in SVG text elements
6. Test collision by driving to track edge
7. Test lap crossing by driving one full lap
8. Test ESC pause menu visibility

## Phase 6: Vehicle System Upgrade (for racing games)

When the user asks to upgrade a racing game's vehicle system to real-world standards:

1. **Classify vehicles into tiers**: 5 tiers matching real-world vehicle classes — Tier 1 Hot Hatch, Tier 2 Sports Car, Tier 3 Supercar, Tier 4 Race Car (GT3/Formula/Rally), Tier 5 Prototype (Le Mans Hypercar). Each tier defines speed/accel/price/AI-skill ranges.

2. **Create tier mapping**: Map existing VehicleType enum values to tiers via a `getVehicleTier(type)` function.

3. **Paint/Livery system**: Create a PaintSchemeRegistry with categories (Solid, Metallic, Matte, Pearl, Chrome, Livery, Camouflage, Gradient, Neon). Add real-world livery patterns (Gulf Oil, Martini, Castrol, Monster Energy). Each scheme has: primaryColor, secondaryColor, accentColor, wheelColor, caliperColor, emissiveColor, metallicness/roughness/clearcoat.

4. **Vehicle database registration**: The VehicleDatabase must actually load vehicle configs — don't rely on a skeleton `console.log('initializing')`. Use `require('./configs/vehicles_XXX_YYY')` to import all exported configs. Handle fallback when `require.context` is unavailable.

5. **Vehicle count**: Track how many vehicles have complete data (attributes + appearance) vs incomplete stubs. Report this to the user.

### Phase 6b: Batch Vehicle Data Generation (Python -> TypeScript Pipeline)

When the user asks to create many vehicle configs for a racing game, DO NOT hand-write each TypeScript object. Use a Python tuple-to-file pipeline.

**Data structure**: Use flat tuples (40+ fields) — one per vehicle. Unpack with position indexing to avoid long variable lists in the tuple assignment.

**Pitfall — Python f-string backslashes**: `{\"true\" if cond else \"false\"}` in an f-string causes `SyntaxError: f-string expression part cannot include a backslash`. Compute conditional variables BEFORE the f-string, then reference by name:
```python
# BAD:
f'neon: {{\"true\" if is_t5 else \"false\"}}'
# GOOD:
neon_str = "true" if is_t5 else "false"
f'neon: {neon_str}'
```

**Pitfall — Data variable naming**: `u$` is an invalid Python name. Use `umoney` or `unlockCost` instead.

**Real vehicle data per tier**: T1 200-330hp, T2 380-660hp, T3 600-1015hp, T4 480-1050hp, T5 627-2014hp. Use real manufacturer specs, not made-up numbers.

## Phase 6c: Real Circuit Track Data (CatmullRom Circuits)

When the user wants real-world racing circuits in a 3D game:

1. Create `CircuitData.ts` with `CircuitDefinition` interface and per-circuit constructor functions returning Vector3[] control points
2. Helper functions: `createSplineFromCircuit(circuit)` -> CatmullRomCurve3, `generateTrackPoints()` -> Vector3[], `generateTrackEdges()` -> boundary arrays
3. Export `CIRCUITS` array for dropdown/keyboard cycling

**Pitfall — Coordinate scaling**: Apply a scaling factor (30-60) to all control points. A 5.8km real track should be 15-50 game units, not 5800.

**Pitfall — Scene.clear() cleanup**: When rebuilding circuits (keyboard switch), re-add lights, ground, and sky after scene.clear() removes everything.

**7 real circuits**: Silverstone, Spa, Monza, Nurburgring, Monaco, Le Mans, Suzuka.

**Circuit switching UX**: Add N key to cycle circuits. On switch: clear scene, rebuild track, reset vehicles, re-init minimap.

### GPS-Based Circuit Data (Advanced)

For more accurate circuits, use real-world GPS coordinates mapped to game positions. See `references/gps-circuit-data.md` for:
- GPS-to-game-unit conversion formula
- 7 circuits with 14-23 waypoint coordinates each
- Height simulation (Eau Rouge at Spa!) via sine waves
- Per-circuit scaling guidance

**IMPORTANT — 1:1 meter scale preference**: The user in this session explicitly rejected scaled-down tracks (e.g., scaling factor 50/120/300) and demanded **1 game unit = 1 real meter**. When using this approach:
- Set `gameLength` to the circuit's real-world length in meters (e.g., Silverstone=5891)
- Control points are expressed in raw meters, not scaled
- The CatmullRom curve will produce a track that spans hundreds to thousands of units (Silverstone spans ~700x600 units)
- This requires dynamic ground size (`trackBounds.size * 1.5` instead of fixed `600x600`)
- Camera mode 1 (bird's-eye) height must be dynamic: `Math.max(15, trackBounds.size * 0.15)`
- The `totalSegs` formula for collision sampling must scale with track length: `Math.min(2000, Math.max(500, Math.floor(trackLen / 5)))` — not a fixed 500 samples
- **AI speed → progress formula** must use actual track length: `this.aiProgress[i] += (aiSpeed / trackLen) * delta` — not a fixed divisor like `/500`

**Pitfall — gameLength mismatch**: If `gameLength` in the circuit definition doesn't match the actual perimeter of the control points after CatmullRom interpolation, the AI speed calculations will be wrong (AI goes too fast or too slow). Verify the interpolated length (developer console trace of getPoint at 0-1 range) and set gameLength to that value, not the real-world length.

## Phase 6e: Vehicle Performance Calibration (100-point scale, constrained)

When the user demands rigorous performance calibration with specific numeric constraints, DO NOT hand-tune vehicle scores. Use an algorithmic approach:

1. **Define tier medians**: T1=10, T2=30, T3=50, T4=70, T5=90 (100-point scale)
2. **Algorithm**: raw scores from physical attributes → scale to tier median → clamp intra-tier spread (±5) → clamp intra-vehicle spread (±8) → clamp per-dimension spread (±15) → inject personality from power-to-weight ratio
3. **Verification**: After calibration, run a batch validation across all vehicles to confirm all constraints pass
4. **Upgrade cap**: Max 3 upgrade levels, cannot cross more than 2 tiers (T1→T3 cap). Each upgrade level ≈+8pts average.
5. **Physics mapping**: Map 100-point scores to game parameters using baseline + delta formula. See reference file for exact coefficients.

**Key constraint order**: scale → avg clamp → intra-vehicle clamp → per-dimension clamp → personality. Re-clamp after personality injection.

**Pitfall — Raw downforce floor**: Real vehicle downforce is tiny for non-racing cars. Add +10 baseline offset so T1-T2 cars don't get unfairly low scores dragging their average down.

**Pitfall — Verification first**: Always validate the constraint model in Python (or a quick script) BEFORE writing the TypeScript implementation. The algorithm has multiple interacting clamps that can produce degenerate states.

See `references/vehicle-performance-calibration.md` for the full algorithm, upgrade model, physics mapping formulas, and verification checklist.

## Critical Architecture Decision: Track-Progressive vs Free-3D Driving

Racing games in Three.js can use TWO fundamentally different driving models:

| Aspect | Track-Progressive (Progress-based) | Free 3D Driving |
|--------|-----------------------------------|-----------------|
| Car position | `trackCurve.getPoint(playerProgress)` | `carX += sin(angle)*speed*delta` |
| Car rotation | `atan2(trackTangent.x, trackTangent.z)` | `playerAngle += steerInput*STEER_SPEED*delta` |
| Steering effect | Changes progress offset, not actual direction | Changes actual heading angle |
| Track constraint | Car CANNOT leave the track line | Car CAN leave; collision pushes back |
| Lap detection | PlayerProgress crossing 0→1 boundary | Project car position onto track curve nearest point |
| Physics feel | Rail-like, no real inertia | Actual momentum, oversteer possible |
| AI following | Same curve-based system | Same (AI is simpler, stays on curve) |

**When to use which**:
- **Progress-based**: Arcade games where the car should always stay on track, simpler to implement lap detection and AI
- **Free 3D**: Games where the player can crash off-track, need realistic oversteer/drift, or the track is wide enough that staying centered is a skill

**Migration path (Progress→Free 3D)**:
1. Replace `trackCurve.getPoint(progress)` with `carX/carZ` + physics update
2. Instead of `playerProgress += speed * delta / trackLength`, compute `moveX = sin(angle)*speed*delta` and `moveZ = cos(angle)*speed*delta`
3. Find nearest track point every frame (brute-force 50-sample loop) for lap detection + boundary collision
4. All AI cars stay on progress-based model (simpler)

**Pitfall — Partial migration**: You CANNOT have the car position set by `trackCurve.getPoint()` AND have `playerAngle` independently computed. The result is: car visually slides sideways while being dragged along the rail. Either commit to free 3D (independent x/z) or commit to progress-based (angle follows track).

```typescript
// WRONG — hybrid that causes slides:
this.playerProgress += this.playerSpeed * delta / 500;
const trackPos = this.trackCurve.getPoint(this.playerProgress);
this.playerCar.position.copy(trackPos);  // <-- rail
this.playerAngle += steerInput * delta;  // <-- independent angle — CONFLICT!

// RIGHT — free 3D:
this.carX += Math.sin(this.playerAngle) * this.playerSpeed * delta;
this.carZ += Math.cos(this.playerAngle) * this.playerSpeed * delta;
this.playerCar.position.set(this.carX, 0.5, this.carZ);
this.playerCar.rotation.y = this.playerAngle;
// progress is derived from nearest point on curve (for lap detection only)
```

## Circuit Scaling — Choosing the Right Factor

The track scaling factor (S) determines gameplay feel. Getting it wrong causes multiple cascading failures:

| S Value | Track Size | Lap Time (80 speed) | Problems |
|---------|-----------|---------------------|----------|
| 50 | 800-1200 | 10-15s | Reasonable, buildings need radius > 1000 |
| 120 | 2000-3000 | 25-37s | Camera distance starts to matter |
| 300 | 5000-6000 | 60-90s | Camera can't keep up, vision cone too narrow |

**Rules**:
- S=50 is the sweet spot for a browser game — the camera at height 15 can see the whole track
- Always update `gameLength` in circuit definitions when changing S
- When S changes, ALL dependent values must update: building radius, camera height, max speed, AI speed
- Building radius must be `> trackSize * 0.8 + 100` — compute this from the actual curve points, not from S directly

**Pitfall — Buildings inside the track**: If buildings are generated at a fixed radius (e.g., `80 + ring * 60`) but the track is scaled to S=300 (track spans 5000 units), buildings ALL appear INSIDE the track loop. Always compute track bounds first:
```typescript
const pts = trackCurve.getPoints(50);
let maxSpan = 0;
for (const p of pts) { maxSpan = Math.max(maxSpan, Math.abs(p.x), Math.abs(p.z)); }
const cityRadius = maxSpan + 100;  // buildings OUTSIDE the track
```

## Pitfall — `process.env` Polyfill Required for Browser

## Pitfall — `process.env` Polyfill Required for Browser

Webpack-bundled TypeScript code often references `process.env.NODE_ENV`. This crashes in the browser with `ReferenceError: process is not defined`.

**Fix**: Add at the TOP of the entry file (`main.ts`), BEFORE any import statements:

```typescript
if (typeof process === 'undefined') { 
    (window as any).process = { env: { NODE_ENV: 'production' } }; 
}
```

**Why line 1 matters**: JavaScript module imports execute before any module-level code. If `process.env.NODE_ENV` is referenced inside an imported module (e.g., in a `development` vs `production` check), the ReferenceError throws during import resolution — before your polyfill has a chance to run. Placing it at line 1, before all imports, ensures the global `process` object exists before any module code executes.

**Alternative**: The webpack.config.js `DefinePlugin` approach (`new webpack.DefinePlugin({ 'process.env.NODE_ENV': JSON.stringify('production') })`) is more robust, but requires modifying webpack config. The polyfill approach works without config changes.

## REAL-WORLD VEHICLE PHYSICS ENGINEERING (from this session's data)

When building realistic racing physics beyond the simplified `ACCEL/BRAKE/MAX_SPEED` model, use **real vehicle engineering parameters** sourced from manufacturer specs and motorsport literature.

### Coordinate System: Three.js vs VDrift (Z-up vs Y-up)

This is the #1 source of "car faces backwards / drives backwards / wheels at wrong position" bugs.

**TO DETERMINE WHICH WAY THE MODEL FACES:**
1. Find the model's extreme vertices: `min_y_verts` vs `max_y_verts` (for Z-up models)
2. Check which end has higher Z-values (engine hood = higher, trunk = lower)
3. The end with higher Z is usually the **car front** (engine bay has upward bulge)
4. **Do NOT assume y+ is the front** — VDrift .joe models use y- as front direction

**VDrift coordinate system** (confirmed via vertex analysis of 13 car models):
```
x = left/right (±0.91 for ATT)
y = forward/backward (y- = FRONT, y+ = REAR) — IMORTANT: y- is front!
z = up/down (z+ = up, max ~0.66 for ATT)
```

**WRONG coordinate transforms that look correct in math but produce backward cars:**
- `(x, y, z) → (x, z, -y)` — places car front at Z- when game expects Z+
- `rotation.x = -PI/2` alone — puts car on its side in Y-up
- `rotation.x = -PI/2; rotation.y = PI` — correct: flips Z→Y then rotates 180° so front faces Z+

**CORRECT Z-up→Y-up for VDrift models (validated):**
```
bodyGroup.rotation.x = -Math.PI / 2;
bodyGroup.rotation.y = Math.PI;  // front goes from Z- to Z+
```
This transforms: original VDrift (x, y-, z) → game (x, z, -y) → after y-rot: (-x, z, y) = front at Z+

**Tire positions in bodyGroup-rotated space:**
```
Original VDrift front tire: (x=±0.72, y=-1.97, z=0.06)  [y- = front]
→ After rotation: (∓0.72, 0.06, -(-1.97)) = (∓0.72, 0.06, 1.97)
→ Front wheel at z=+1.97 (Z+ direction = front)
→ Rear wheel at z=-1.89 (Z- direction = rear)
```

**TO VERIFY FRONT/BACK empirically (without guesswork):**
```python
verts = model_data['verts']
# y+端(y>1.9)和y-端(y<-1.9)的z范围
front_high_z = max(v[2] for v in verts if v[1] < -1.9)  # y-端的最高点
rear_high_z = max(v[2] for v in verts if v[1] > 1.9)   # y+端的最高点
# 有更高z凸起的一端是车头(引擎盖)
# y-端有凸起 → y-是车头
```

### Engine Torque Curve (Real S54B32-based)

**REAL engine characteristics** (not 4-segment linear):
```
RPM range:    800 → 3300 → 4900 → 5800 → 7200 → 8000
Torque %:     65% → 100% → 108% → 108% → 83% → 50%
               ↓       ↓       ↓       ↓      ↓      ↓
Characteristics: idle → climb → peak → plateau → drop → redline collapse
```

**Implementation pattern** (5-segment with smooth transitions):
```typescript
const engRpmNorm = (rpm - IDLE) / (MAX_RPM - IDLE);  // 0.0 to 1.0
let torqueFactor: number;
if (engRpmNorm < 0.05) torqueFactor = AT_IDLE + (1-AT_IDLE)*(norm/0.05);
else if (engRpmNorm < 0.35) torqueFactor = min(1.08, max(0.7, 1.0 + ramp));
else if (engRpmNorm < 0.70) torqueFactor = 1.0 + sin(t * PI) * 0.08;
else if (engRpmNorm < 0.90) torqueFactor = 1.08 - t * 0.25;
else torqueFactor = 0.83 - t * 0.33;  // 0.83 → 0.50
```

**Key parameters per engine:**
```
ENGINE_MAX_TORQUE_NM     = peak torque (e.g., 365 for M3 E46)
ENGINE_POWER_HP          = peak power (e.g., 343 for M3 E46)
ENGINE_MAX_RPM           = redline (e.g., 8000)
ENGINE_IDLE_RPM          = idle (e.g., 800)
ENGINE_TORQUE_PEAK_RPM   = rpm at peak torque (e.g., 4900)
ENGINE_TORQUE_AT_IDLE    = torque fraction at idle (e.g., 0.65)
ENGINE_TORQUE_AT_MAX     = torque fraction at redline (e.g., 0.55)
```

### Transmission / Gearbox Design

**REAL gear ratios** (not simplified): Use Getrag 420G (BMW M3 E46) as reference:
```typescript
GEAR_RATIOS = [4.23, 2.53, 1.67, 1.23, 1.00, 0.83];
FINAL_DRIVE = 4.10;
DRIVETRAIN_EFFICIENCY = 0.85;  // 15% drivetrain loss
WHEEL_RADIUS = 0.33;  // meters (255/40R18)
```

**RPM → Speed → Torque chain:**
```
wheelRpm = (speed * 60) / (2 * PI * WHEEL_RADIUS)
engineRpm = wheelRpm * GEAR_RATIO * FINAL_DRIVE
engineTorque = ENGINE_MAX_TORQUE_NM * torqueCurve(rpm)
wheelTorque = engineTorque * GEAR_RATIO * FINAL_DRIVE * EFFICIENCY
driveForce = wheelTorque / WHEEL_RADIUS
```

**Auto shift strategy** (street car, not race car):
- Upshift: `rpm > 6500` (not redline 8000 — street driving)
- Downshift: `rpm < 1800 && speed > 2m/s`
- Shift cooldown: `SHIFT_TIME = 0.25s`
- Post-shift rpm: multiply by `0.72` for upshift, `1.35` for downshift

**Pitfall — RPM simulation decoupled from speed**: In a simplified model where `rpm` and `speed` are independently updated, at standstill with throttle, rpm can rise to 6500 while speed stays 0, triggering an upshift at zero speed. Fix: add `speedMs > 2` condition to upshift check.

**Pitfall — clutch slip at standstill**: At very low speed (< 1m/s), rpm should rise faster (clutch not fully engaged) to simulate revving. Multiply rpm delta by `2.0` when `speed < 1`.

### Tire Model: Pacejka Magic Formula (MF)

**REQUIRED** for realistic handling. Without it, steering is linear/arcade.

**Parameters** (UHP summer tire — Michelin Pilot Sport 4S class):
```
TIRE_PEAK_LONGITUDINAL_MU = 1.05  (peak braking/acceleration friction)
TIRE_PEAK_LATERAL_MU      = 1.00  (peak cornering friction)
TIRE_SLIDING_MU           = 0.80  (fully sliding friction)
TIRE_LOAD_SENSITIVITY     = 0.08  (mu drops 8% per load doubling)
```

**Magic Formula** (lateral force):
```
Fy = D * sin(C * atan(B*x - E*(B*x - atan(B*x)))) * gripMultiplier
where:
  x = slipAngle in degrees
  B = 9  (stiffness factor — 8-12 for street tires)
  C = 1.3 (shape factor — typically 1.3 for lateral)
  D = TIRE_PEAK_LATERAL_MU (peak value)
  E = -0.3 (curvature factor — negative = peak-and-drop shape)
```

**Longitudinal slip-based drive force:**
```typescript
// Dynamic load on each axle (weight transfer from acceleration):
weightTransfer = (driveForce * throttle * CG_HEIGHT) / WHEELBASE;
frontLoad = FRONT_STATIC_WEIGHT - weightTransfer;  // unloads front
rearLoad = REAR_STATIC_WEIGHT + weightTransfer;     // loads rear

// Load-sensitive mu:
muPerWheel = TIRE_MU * (1 - LOAD_SENSITIVITY * ln(load / staticLoad));

// Max drive force (RWD: rear wheels only):
maxDriveForce = muRear * rearLoad;

// Slip ratio control:
slipRatio = (wheelRpm * WHEEL_RADIUS / ratio - speed) / max(1, speed);
if (slipRatio > 0.15) driveForce *= (0.7 - (slipRatio - 0.15) * 0.5);
else driveForce = min(driveForce, maxDriveForce);
```

**Pitfall — using tireGrip as a single multiplier without load transfer**: Without `frontLoad`/`rearLoad` calculation, acceleration always has the same grip regardless of weight transfer. This means the car accelerates identically from standstill and at 200km/h — unrealistic.

**Pitfall — TCS/ABS as boolean toggles without physics integration**: TCS should limit `driveForce` when `slipRatio` exceeds threshold. ABS should pulse brake pressure near lockup threshold. Both MUST interact with the tire model, not just be separate boolean multipliers.

### Ackermann Steering Geometry + Bicycle Model

**REQUIRED** for realistic steering feel. Without it, turning feels like rotating a rigid body around its center.

**Steering angle:**
```typescript
steerInput = 1 (A) or -1 (D)
// Non-linear mapping for precision feel:
ackermannFactor = |steerInput| * (0.2 + |steerInput|² * 0.8);
steerAngle = sign(steerInput) * ackermannFactor * MAX_STEER_ANGLE;
// MAX_STEER_ANGLE = 0.52 rad (≈30° steering rack angle)
// This produces: input 0.1→2°, 0.5→10°, 1.0→30°
```

**Slip angle calculation (bicycle model):**
```typescript
// Vehicle body slip = direction of travel vs heading
vehicleSlipAngle = atan2(lateralVelocity, speed);

// Front wheels: steer direction adds to slip
frontSlipAngle = vehicleSlipAngle + steerAngle;
// Rear wheels: no steering angle
rearSlipAngle = vehicleSlipAngle;

// Lateral forces from Magic Formula:
Fy_front = MagicFormula(frontSlipAngle_degrees, frontLoad);
Fy_rear = MagicFormula(rearSlipAngle_degrees, rearLoad);
```

**Yaw moment that actually turns the car:**
```typescript
// Distance from CG to each axle:
a = WHEELBASE * WEIGHT_REAR;   // front axle to CG
b = WHEELBASE * WEIGHT_FRONT;  // rear axle to CG

// Yaw moment: front pulls one way, rear pulls the other
yawMoment = Fy_front * a * cos(steerAngle) - Fy_rear * b;

// Yaw inertia (simplified — treat as point mass at each axle):
yawInertia = MASS * a * b;
yawDamping = 25000;  // N-m-s/rad

// Angular acceleration → yaw rate → heading:
yawRate += (yawMoment - yawDamping * yawRate) / yawInertia * dt;
yawRate = clamp(yawRate, -3.5, 3.5);
playerAngle += yawRate * dt;
```

**Lateral velocity (side-slip):**
```typescript
// Lateral acceleration from tire forces:
lateralAccel = (Fy_front * cos(steerAngle) + Fy_rear) / MASS;

// Side-slip velocity integral (bicycle model):
lateralVelocity += (lateralAccel - yawRate * speed - 6 * lateralVelocity) * dt;
lateralVelocity = clamp(lateralVelocity, -8, 8);
```

**Pitfall — steering changes heading directly without yaw dynamics**: `playerAngle += steerInput * STEER_SPEED * delta` rotates the car like a turret, ignoring tire slip, inertia, and speed-dependent understeer. The correct approach always routes through `yawRate`.

**Pitfall — frontSlipAngle = vehicleSlip + steerAngle * 0.8**: The `* 0.8` factor is WRONG. Front wheel slip angle is EXACTLY `vehicleSlip + steerAngle` — the front wheels point where the steering says. The 0.8 factor comes from not accounting for slip angle correctly and trying to fudge the response.

### Suspension + Body Dynamics (Roll/Pitch)

**REQUIRED** for realistic visual feedback. Without it, the car appears rigidly glued to the ground even during hard cornering/braking.

**Parameters** (street sport setup):
```typescript
// Spring rates in N/m (N/mm * 1000):
SUSPENSION_SPRING_FRONT = 55000;  // 55 N/mm
SUSPENSION_SPRING_REAR  = 50000;

// Damping in N-s/m: bump(compression) vs rebound(extension):
SUSPENSION_DAMP_BUMP_FRONT    = 1800;
SUSPENSION_DAMP_REBOUND_FRONT = 3000;  // ~1:1.7 bump:rebound ratio
SUSPENSION_DAMP_BUMP_REAR     = 1500;
SUSPENSION_DAMP_REBOUND_REAR  = 2600;

ANTI_ROLL_STIFFNESS = 20000;  // N-m/rad
CG_HEIGHT = 0.50;  // meters
```

**Roll from lateral acceleration:**
```
rollMoment = lateralAccel * MASS * CG_HEIGHT;
rollStiffness = (spring_front + spring_rear) * 0.5 * (0.5 * WHEELBASE)² + ANTI_ROLL
targetRoll = rollMoment / rollStiffness;  // in radians
bodyRoll += (targetRoll - bodyRoll) * dt * 8;
bodyRoll = clamp(bodyRoll, -0.3, 0.3);  // max ±17°
```

**Pitch from longitudinal acceleration:**
```
pitchMoment = driveForce * CG_HEIGHT - brakeForce * CG_HEIGHT;
pitchStiffness = similar formula with anti-roll * 0.3
targetPitch = pitchMoment / pitchStiffness;
bodyPitch = lerp with dt*6, clamp to ±0.15 (±8.5°)
```

### Aerodynamics (Drag + Downforce)

**REQUIRED** for realistic top-speed limiting and high-speed stability.

**Drag force** (correct physics — NOT `v² * 0.000015`):
```typescript
// F_drag = 0.5 * ρ * Cd * A * v²
AIR_DENSITY = 1.225;  // kg/m³ at sea level
CD = 0.32;            // e.g., M3 E46
FRONTAL_AREA = 2.12;  // m²
dragForce = 0.5 * AIR_DENSITY * CD * FRONTAL_AREA * speed²;
dragDecel = dragForce / MASS;  // in m/s²
```

**Downforce contribution** (important for high-speed grip):
```typescript
CL_FRONT = -0.02;  // slight front downforce
CL_REAR = 0.05;    // slight rear lift (typical for unmodified street car)

downforce = 0.5 * AIR_DENSITY * CL * FRONTAL_AREA * speed²;
// Adds to tire normal load at high speed:
frontLoad += downforce_front * g;
rearLoad += downforce_rear * g;
```

### Braking System

**REQUIRED** for realistic stopping distances.

**Physical brake model** (NOT `BRAKE_FORCE = 35`):
```typescript
BRAKE_MAX_DECEL = 11.3;  // m/s² ≈ 1.15g (100-0km/h in ~34m)
BRAKE_BALANCE_FRONT = 0.65;  // 65% front bias

// Brake force limited by tire grip:
brakeDecel = BRAKE_MAX_DECEL * brakeMultiplier;
brakeForce = min(MASS * brakeDecel, 
                 (muFront * frontLoad + muRear * rearLoad * 0.7) * 0.8);

// ABS:
if (hasABS) speed -= (brakeForce / MASS) * dt * 0.9;
else speed -= (brakeForce / MASS) * dt * 1.2;  // non-ABS can briefly exceed tire limit
```

### Coordinate Transform Decision Matrix

When placing a VDrift model in Three.js Y-up space, use this table:

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| `bodyGroup.rotation.x = -PI/2; y = PI` | Simple, no vertex preprocessing | Need to compute all child positions in rotated space | Multi-part models (body+glass+interior) with indexOffset |
| Vertex transform `(x, z, -y)` | Children can use native coords | Requires loop over all vertices + normals | Fallback geometry or single-mesh models |
| `mesh.rotation.x = -PI/2` | Minimal code change | Wheels must be in separate unrotated group | Simple single-body models |

### Per-Vehicle Physics Multiplier System

When supporting **multiple vehicles with different performance**, use multiplier system (NOT per-vehicle constant overrides):

```typescript
// Baseline = M3 E46 (343hp, 1495kg, 5.2s 0-100)
// Each vehicle computes multipliers against this baseline:
_accelMultiplier = (vehicle_hp / vehicle_weight) / (343 / 1495);
_handlingMultiplier = vehicle_handling_rating / 5;
_brakeMultiplier = 33 / vehicle_100_0_distance;  // 33m reference

// Physics then uses:
driveForce *= _accelMultiplier;  // actually applied in wheelTorque calculation
mu *= _gripMultiplier;           // from difficulty system
brakeDecel *= _brakeMultiplier;
```

**Pitfall — overwriting physics constants per car**: Setting `this.ACCEL = 25 + diff * 0.08` during `applyScoreToPhysics()` then having `updatePlayer()` use `this.ACCEL` directly is fragile — any code path that modifies `ACCEL` (difficulty, upgrades) breaks the per-vehicle tuning. Use multipliers that stack, not overwrites.

### Difficulty System as Multipliers

Difficulty should NOT overwrite physics constants. Use layered multipliers:

```typescript
_gripMultiplier = [1.3, 1.15, 1.0, 0.85, 0.65][difficulty];
_powerMultiplier = [1.2, 1.1, 1.0, 0.9, 0.8][difficulty];
_brakeHelperMultiplier = [1.3, 1.15, 1.0, 0.85, 0.7][difficulty];

// In physics:
mu *= _gripMultiplier * _accelMultiplier;  // stacks
driveForce *= _powerMultiplier * _accelMultiplier;
brakeDecel *= _brakeMultiplier * _brakeHelperMultiplier;
```

### Reference Vehicle Dataset

Use these real-world specs for physics calibration (7 cars from this session):

| Car | HP | Torque(Nm) | Wt(kg) | 0-100(s) | Top(km/h) | Gear Ratios | FinalD | 
|-----|-----|-----------|--------|----------|-----------|-------------|--------|
| Audi TT 8J | 200-211 | 280 | 1395 | 6.4 | 240 | 3.30/1.94/1.31/1.03/0.82/0.68 | 4.23 |
| Nissan 350Z | 287-306 | 363 | 1450 | 5.5 | 250 | 3.79/2.32/1.62/1.27/1.00/0.79 | 3.36 |
| Ferrari 360 | 400 | 373 | 1470 | 4.5 | 295 | 3.29/2.16/1.61/1.27/1.03/0.85 | 4.44 |
| BMW M3 E46 | 343 | 365 | 1495 | 5.2 | 250 | 4.23/2.53/1.67/1.23/1.00/0.83 | 3.62 |
| Corvette C6 | 400-436 | 575 | 1441 | 4.3 | 300 | 2.97/2.07/1.43/1.00/0.71/0.57 | 3.42 |
| Toyota Supra | 320+ | 440 | 1580 | 5.0 | 280 | 3.83/2.19/1.38/1.00/0.81/0.65 | 3.27 |
| McLaren F1 | 618 | 651 | 1140 | 3.2 | 386 | (6MT ~similar ratios) | — |

### Common Bug Patterns in CatmullRom Racing Games

### Bug: ApplyPaint — `!mat.emissive` Always False

**Symptom**: Wheel color or accent materials don't change when cycling paint schemes. The body color changes but wheels stay the same.

**Root cause**: `mat.emissive` is a `THREE.Color` object — it's ALWAYS truthy (even at default black `Color(0,0,0)`). `!mat.emissive` is `false` for EVERY material, so the wheel-color branch never executes.

**Fix**: Check the emissive color hex value explicitly:
```typescript
// WRONG — never matches:
else if (mat.metalness > 0.7 && !mat.emissive)

// RIGHT:
else if (mat.metalness > 0.7 && mat.emissive && mat.emissive.getHex() === 0)
```

### Pattern: Menu Callbacks Are Console.log Stubs / Empty Functions

**Symptom**: Clicking menu buttons (Select Vehicle, Select Character, Settings, Credits) logs a message to console but does nothing visible. User reports "buttons don't work."

**Root cause**: AI-generated game code often creates static methods on the main game class that only `console.log` their action:

```typescript
// AI-generated stub pattern:
static selectCar(): void { console.log('选择车辆'); }
static selectCharacter(): void { console.log('选择角色'); }
```

These are called from HTML via `window.Game = { showVehicleSelect: () => PlushRacingGame.selectCar(), ... }`.

**Fix options** (choose based on ambition level):
1. **Quick fix**: Replace stubs with `alert()` calls that explain the feature is coming:
   ```typescript
   static selectCar(): void { 
       alert('🚗 车辆选择\n\n即将推出: 从130辆车中选择您的座驾！');
   }
   ```
2. **Full implementation**: Build actual selection UI (takes hours — get user buy-in first).
3. **Redirect to existing keyboards**: For settings, redirect to existing keyboard controls:
   ```typescript
   static openSettings(): void {
       alert('⚙️ 设置\n\n难度: D键\n视角: C键\n喷涂: P键\n改装: M键');
   }
   ```

**Pitfall — `restartRace()` references nonexistent static**: The pattern `PlushRacingGame.start()` expects a static method that doesn't exist. `startGame()` is an instance method. The restartRace handler must manipulate the singleton's state directly:
```typescript
restartRace: () => {
    const g = game; // imported singleton
    g.gameState = 'menu';
    g.startGame(); // instance method, not static
}
```

**Pitfall — `resumeRace()` is empty**: `() => {}` — the common fix pattern:
```typescript
resumeRace: () => {
    document.getElementById('pause-menu')!.style.display = 'none';
    const g = game as any;
    if (g && g.gameState === 'paused') g.gameState = 'playing';
}
```

### Pattern: Overlay Management — Hide All Before Showing One

**Problem**: Multiple UI overlays (menu, pause, results, upgrade) stack on top of each other because `finishRace()` shows `results-screen` without hiding `pause-menu` or `menu-overlay`.

**Fix**: Always call `hideAllOverlays()` before showing any menu. This prevents the CSS `display: flex` stacking that happens when multiple overlays are visible simultaneously.

```typescript
private hideAllOverlays(): void {
    ['menu-overlay', 'pause-menu', 'results-screen', 'upgrade-menu']
        .forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
}
```

### Bug: VDrift model invisible — body/glass/interior parts render with no faces

**Symptom**: VDrift multi-part model loads without error (console shows "✅ 3D模型已加载") but the car is invisible. All three parts (body/glass/interior) are children of the car group with zero triangles.

**Root cause**: The parts JSON does NOT include `indexOffset` field. When the Three.js loader calls `info.indexOffset`, it gets `undefined`. Then `carData.indices.slice(undefined, iStart + iCount)` returns an empty array. The `BufferGeometry.setIndex()` with an empty index array produces a geometry with zero faces — it exists in the scene tree but with nothing to render.

**Fix in Three.js loader** — compute indexOffset from cumulative previous parts:
```typescript
let iStart = 0;
if (typeof info.indexOffset !== 'undefined') {
    iStart = info.indexOffset;
} else {
    let accumulated = 0;
    for (const [prevName, prevInfo] of Object.entries(carData.parts)) {
        if (prevName === partName) break;
        const pi = prevInfo as any;
        accumulated += pi.indexCount || pi.triCount * 3;
    }
    iStart = accumulated;
}
const iCount = info.indexCount || info.triCount * 3;
```

**Fix in Python export** (better — fix the source):
```python
index_offset = 0
for part_name in ['body', 'glass', 'interior']:
    merged['parts'][part_name] = {
        'vertOffset': vert_offset,
        'vertCount': result['numVerts'],
        'triCount': result['numTris'],
        'indexCount': result['numTris'] * 3,
        'indexOffset': index_offset,  # ← ADD THIS
    }
    vert_offset += result['numVerts']
    index_offset += result['numTris'] * 3
```

### Bug: Car faces backwards / drives backwards
**Symptom**: Car appears to drive backwards — the spoiler is at the front, headlights at the rear. Steering feels inverted.

**Root cause**: `buildVehicle()` has headlights/spoiler at wrong z-coordinates. In Three.js, a `BoxGeometry(1.8, 0.5, 3.5)` defaults its front face toward +Z. All car parts must respect this:
- **Headlights** go at z = **+1.8** (front)
- **Spoiler** goes at z = **-1.6** (rear)
- **Cabin/driver** goes at z ≈ **+0.2** (front half)
- **Taillights** go at z = **-1.8** (rear)

Do NOT put headlights at z=-1.8 and spoiler at z=+1.6 — that's backwards.

### Bug: Car slides sideways / becomes perpendicular to track
**Symptom**: The car body rotates independently from its movement direction, causing the vehicle to drift sideways off the track or face sideways while moving forward.

**Root causes and fixes**:
1. **Slip angle too wide**: `slipAngle = clamp(value, -0.5, 0.5)` allows 28 degrees of side rotation — visible as the car body pointing off-line. Fix: clamp to `±0.2` (~11 degrees).
2. **Lateral offset too large**: `lateralOffset = slipAngle * 2` multiplies the already-large angle. The car physically moves sideways relative to the track centerline by up to 1.0 game units. Fix: `lateralOffset = slipAngle * 0.5`.
3. **Rotation accumulated via lerp, not set directly**: `playerAngle += ((targetAngle + driftAngle) - playerAngle) * delta * 4` lets the angle lag behind the track direction by a significant amount, especially at high delta times. Fix: Set `car.rotation.y` directly to `targetAngle + driftAngle` each frame — no smoothing.

**Correct pattern**:
```typescript
const targetAngle = Math.atan2(trackTangent.x, trackTangent.z);
const driftAngle = slipAngle * 0.15;  // max ~3 degrees visual drift
car.rotation.y = targetAngle + driftAngle;  // direct set, NOT accumulated
```

### Bug: gear/rpm not reset on circuit switch

**Symptom**: After switching circuits (N key), the car starts in a weird gear (e.g., gear 5 at 0 speed) or RPM stays at redline.

**Root cause**: `switchCircuit()` rebuilds the scene and vehicles but doesn't reset gearbox state.

**Fix**: Add to `switchCircuit()`:
```typescript
this.gear = 1;
this.rpm = 850;  // IDLE_RPM
this.shiftCooldown = 0;
```
**Symptom**: Opponent cars drive directly through the player's car with no visual/mechanical interaction.

**Root cause**: No collision detection between player and AI vehicles — the game only checks track boundary collisions.

**Fix**: Add collision detection after boundary checks:
```typescript
const playerPos = playerCar.position;
for (let i = 0; i < aiCars.length; i++) {
    const aiPos = aiCars[i].position;
    const dist = Math.hypot(playerPos.x - aiPos.x, playerPos.z - aiPos.z);
    if (dist < 1.8) {  // car width
        playerProgress -= pushStrength * 0.005;
        playerSpeed *= 0.6;
        aiProgress[i] += pushStrength * 0.005;
        // trigger collision sound
        break;
    }
}
```

### Bug: Menus overlap / results screen hidden behind pause
**Symptom**: At race finish, the results screen appears on top of (or behind) the pause menu. ESC toggles both, creating a stack of overlapping flex overlays.

**Root cause**: `finishRace()` doesn't close other overlays. Only the `results-screen display: flex` is set.

**Fix**: Add a `hideAllOverlays()` that runs before showing any new overlay (covered in detail above in the Overlay Management section).

### Bug: Scene is too dark / only wireframe geometry visible
**Symptom**: The 3D scene renders as mostly black with only glowing/emissive objects visible (neon poles, track glow). Track surface and buildings appear as dark silhouettes or barely visible wireframe-like lines.

**Root causes (check in this order)**:

1. **Bloom over-intensity** — `UnrealBloomPass` with strength > 0.5 eats all non-emissive detail. The bloom threshold (default 0.3) treats the entire scene as a light source, washing out diffuse surfaces. **Fix**: Reduce bloom strength to 0.2 and threshold to 0.1:
   ```typescript
   const bloomPass = new UnrealBloomPass(
       new THREE.Vector2(width, height),
       0.2,    // strength (was 0.6)
       0.1,    // radius (was 0.3)  
       0.05    // threshold (was 0.1)
   );
   ```

2. **Canvas texture too dark** — Procedural racing games often generate track textures on a Canvas. A fill color of `#2a2a3a` (brightness ~42) + noise in range `30-60` produces a surface that's far too dark to be visible under moderate lighting. **Fix**: Use `#3a3a4a` base with noise range `50-110`. Final material color should be `0x9999aa` not `0x444466`.

3. **Texture.repeat too high** — `trackTexture.repeat.set(2, 40)` stretches the small canvas texture across the entire track. Each texel covers multiple track segments, making the surface look like a solid dark color. **Fix**: Use `repeat.set(1, 15)` so each canvas pixel maps to ~15 track-length repeats — visible as a discernible tiled pattern.

4. **DirectionalLight too dim** — A single `DirectionalLight(0xffaaff, 0.8)` at moderate height doesn't provide enough illumination for the dark scene. **Fix**: Use `(0xffddcc, 1.5)` for warm white, add a fill light `(0x8888ff, 0.5)` and a hemisphere light `(0x4488ff, 0x224466, 0.4)`:
   ```typescript
   const ambient = new THREE.AmbientLight(0x445566, 0.6);
   const dirLight = new THREE.DirectionalLight(0xffddcc, 1.5);
   dirLight.position.set(30, 60, 30);
   const fillLight = new THREE.DirectionalLight(0x8888ff, 0.5);
   fillLight.position.set(-30, 20, -30);
   const hemiLight = new THREE.HemisphereLight(0x4488ff, 0x224466, 0.4);
   ```
   Apply this to ALL places where lights are created (both initFullScene and switchCircuit).

5. **MeshStandardMaterial roughness/metalness too high** — `roughness: 0.8, metalness: 0.3` absorbs too much light. **Fix**: `roughness: 0.6, metalness: 0.1` for better diffuse response.

6. **Procedural canvas texture base color too dark**: A `ctx.fillStyle = '#2a2a3a'` (RGB ~42/42/58) produces an almost-black surface even with good lighting. The noise values `30 + Math.random() * 30` (range 30-60) add no visible texture. **Fix**: Use `'#3a3a4a'` base (RGB 58/58/74) with noise range `50 + Math.random() * 60` (range 50-110). Final material color should be `0x9999aa` not `0x444466`.

**Cascade risk**: Fixing only the texture or only the lighting leaves the scene still dark, leading to "I fixed X but it's still dark" — fix ALL six simultaneously.

### Bug: `playCollisionSound is not a function` — gameLoop Crash Loop

**Symptom**: Game starts, scene loads, but after a moment the game freezes. Console shows a stack trace of `gameLoop` repeated hundreds of times (recursive RAF calls that all crash at the same line). The crash loop generates enormous stack traces that fill the console.

**Root cause**: `updatePlayer()` calls `this.playCollisionSound()` which was never defined in the class. It was referenced in code (probably migrated from an older version that had it) but the function was left out. Since it's called inside the gameLoop's try-catch-less section (or outside), it crashes the entire frame loop.

**Fix**: Either define a stub:
```typescript
private playCollisionSound(): void {
    // no-op — collision sound feature not implemented
}
```
Or remove all references to it. Search: `grep -rn 'playCollisionSound' src/`

**Prevention**: When refactoring game classes, audit ALL private method calls to ensure the target function exists. Easy to miss when deleting dead code.

### Bug: `distanceToTrack is not a function` — gameLoop Crash

**Symptom**: Same as above — gameLoop crashes, frame loop stops, screen freezes on HUD.

**Root cause**: Refactored collision code calls `this.distanceToTrack(x, z)` which was never defined. The function name was assumed/guessed during a hasty refactor.

**Fix**: Replace with a simple distance-from-origin check:
```typescript
const maxDistFromOrigin = 200;
if (Math.abs(this.carX) > maxDistFromOrigin || Math.abs(this.carZ) > maxDistFromOrigin) {
    this.carX *= 0.98;
    this.carZ *= 0.98;
}
```

### Bug: `updateAudio` NaN Crash Stops Rendering

**Symptom**: Game renders first frame then black screen. Console shows `TypeError: The provided float value is non-finite` at updateAudio.

**Root cause (compound)**:
1. `ENGINE_IDLE_RPM` and `ENGINE_MAX_RPM` referenced but **never defined** in the class (migration loss from old HTML)
2. `(currentRpm - undefined) / (undefined - undefined) = NaN`
3. `rpmHz = 60 + NaN * 340 = NaN` → `engineOsc.frequency.value += NaN` → throws TypeError
4. gameLoop has no try-catch → entire loop dies → RAF stops → black screen

**Fix**: 
1. Define constants: `private readonly ENGINE_IDLE_RPM = 850; private readonly ENGINE_MAX_RPM = 7200;`
2. Wrap entire `updateAudio` in try-catch so it NEVER crashes the gameLoop

**Rule for racing game audio**: ALWAYS wrap `updateAudio` in try-catch. Audio is the #1 source of NaN crashes in Web Audio API physics games.

### Bug: Composer renders blank frames despite renderer.render() working

**Symptom**: Manual `renderer.render(scene, camera)` produces visible output, but the gameLoop's `composer.render()` shows blank/black.

**Root cause**: `EffectComposer` constructor doesn't set width/height explicitly when called before `renderer.setSize()`. Composer has `width=undefined, height=undefined`, causing passes to render at 0x0 internally.

**Fix**: Either initialize composer AFTER renderer.setSize(), or skip composer and use direct renderer:
```typescript
// In gameLoop — use renderer directly, bypass composer
this.renderer.render(this.scene, this.camera);
```

**Better pattern — conditional**: Check if composer has valid size before using it:
```typescript
if (this.composer && isFinite(this.composer.renderWidth)) {
    this.composer.render();
} else if (this.renderer) {
    this.renderer.render(this.scene, this.camera);
}
```

**Symptom**: When the user presses ESC to pause, the game appears to freeze but the pause menu doesn't appear for several seconds. Or: the pause menu appears but the game's position resets when resumed.

**Root cause**: The game loop does `if (gameState !== 'playing') return;` — this means when paused, RAF stops being called. The renderer never draws the pause menu overlay because the render pass is inside the game loop:

```typescript
// BROKEN: RAF stops on pause
private gameLoop = (): void => {
    if (this.gameState !== 'playing') return;  // <-- kills RAF chain
    // ... update physics ...
    this.composer.render();
    requestAnimationFrame(this.gameLoop);
};
```

**Fix**: RAF must **always** continue. Only skip physics updates when paused:

```typescript
private gameLoop = (): void => {
    if (this.gameState === 'menu') return;  // only stop on menu
    
    const delta = Math.min(this.clock.getDelta(), 0.05);
    
    if (this.gameState === 'playing') {
        this.updatePlayer(delta);
        this.updateAI(delta);
        this.updateCamera(delta);
        this.updateHUD();
        this.updateAudio(delta);
    }
    
    if (this.gameState === 'paused') {
        this.updateCamera(delta);  // still let camera orbit/spin
    }
    
    this.composer.render();  // always render
    requestAnimationFrame(this.gameLoop);  // always schedule next frame
};
```

This pattern ensures the pause menu renders immediately, and the camera can still animate during pause.

### Bug: Game shows directory listing instead of playable game

**Root causes and fixes**:
1. **No index.html in dist/**: Webpack's `clean: true` nukes it on every rebuild. Disable `clean: true` or add `HtmlWebpackPlugin`.
2. **`serve` lists dist/ as a directory**: Even with index.html present, serve's directory-listing mode is enabled by default and shows the contents of dist/ as a file list instead of serving the HTML. Fix: switch to `python3 -m http.server 8000` from the project root — it correctly serves root `index.html`. Or use `serve -s dist` (single-page mode) which serves index.html for any path.
3. **`process.env` undefined**: If `process.env.NODE_ENV` is referenced anywhere (TypeScript/webpack code), it throws in the browser. Add polyfill: `if (typeof process === 'undefined') { (window as any).process = { env: { NODE_ENV: 'production' } }; }`
4. **`npx serve` launched without `-s` flag and no index.html**: When the served directory has no index.html, `serve` falls back to directory listing. Even WITH index.html, `serve` can show the parent directory listing instead if launched from the wrong directory. **Most reliable**: Use Python's built-in HTTP server from the project root — it always serves root index.html correctly and has no lingering-process issue.

### Bug: HUD elements not updating
**Symptom**: Speed gauge shows "0", lap count stays at "1/3", elapsed time doesn't tick.

**Root cause**: HUD code uses `querySelector('#speed-gauge svg').querySelectorAll('text')` to find speed text, but the HTML uses `<span class="speed-value">` instead of SVG elements. The query finds nothing.

**Fix**: Match HUD code to actual HTML structure. Use `document.getElementById('speed-value')` for speed, `document.getElementById('hud-lap-value')` for lap count, etc. Prefer specific IDs over generic SVG selectors.

### Pattern: Camera Mode Switching (Third-Person vs Bird's-Eye)

**Symptom**: C key does nothing, or camera mode enum is defined but empty.

**Fix**: Implement two camera modes with independent positioning logic:

```typescript
if (this.cameraMode === 0) {
    // Third-person: behind car using rotation.y
    const behind = new THREE.Vector3(
        -Math.sin(carAngle) * 10,  // behind X
        5,                         // height
        -Math.cos(carAngle) * 10   // behind Z
    );
    camera.position.lerp(carPos.clone().add(behind), delta * 3);
} else {
    // Bird's-eye: top-down, follows car x/z
    camera.position.lerp(new THREE.Vector3(carPos.x, 30, carPos.z + 5), delta * 2);
}
camera.lookAt(carPos.clone().add(new THREE.Vector3(0, 1, 0)));
```

**Key point**: Both modes `lookAt` the car's position + 1 unit up. The difference is the camera's offset from the car — behind and above vs directly above.

### Pattern: Camera Distance Tuning — Preventing "Car Too Small" UX Bug

**Symptom**: The car looks large at parking speed but shrinks to a speck at high speed. User reports "车子跑起来镜头就变得特别远，车子变得特别小".

**Root cause**: Camera distance formula was linear: `5 + speedKmh * 0.02` → at 250km/h the camera is 10m away. With FOV=60°, a 1.8m-wide car at 10m distance occupies only ~10° of the 60° FOV (about 15% of screen width).

**Fix — speed-clamped dynamic distance**:

```typescript
if (this.cameraMode === 0) {
    // Dynamic: car occupies ~1/3 of screen at all speeds
    const speedKmh = Math.abs(this.playerSpeed) * 3.6;
    const dynamicDist = 2.5 + speedKmh * 0.012;  // 0km/h=2.5m, 250km/h=5.5m
    const clampedDist = Math.min(5.5, Math.max(2.5, dynamicDist));
    // Camera height relative to distance (closer = lower)
    const heightRatio = 1.8 + clampedDist * 0.2;  // 2.5m=2.3, 5.5m=2.9
    const behind = new THREE.Vector3(
        -Math.sin(carAngle) * clampedDist,
        heightRatio,
        -Math.cos(carAngle) * clampedDist
    );
    // ... lerp and lookAt
}
```

**Key parameters**:
- Distance range: **2.5-5.5m** (NOT 5-10m or 12m fixed)
- Height range: **2.3-2.9** (NOT 3.5-5.0 or 5m fixed)
- lookAt y-offset: **0.5** (NOT 1.5 — look at vehicle center, not roof)
- lerp rate: **4** (faster follow, NOT 3)

### Pattern: Key Binding Conflict — D Key Does Double Duty (Steering + Difficulty)

**Symptom**: The car steers right when pressing D, but difficulty also changes. User may complain "按键不会冲突吗" or "D键是转向还是切换难度".

**Root cause — two independent keyboard systems sharing the same key**:
1. `main.ts` has a global `keydown/keyup` listener recording ALL keys into `__keys` (used by `updatePlayer` for driving — W/A/S/D/Arrows)
2. The game class has its own `keydown` listener for function shortcuts (difficulty cycle, camera switch, paint, upgrade)
3. These are **separate event listeners**, NOT overrides — BOTH fire on every keypress

So pressing D causes BOTH:
- `__keys['KeyD'] = true` → `updatePlayer` reads this for **right steering**
- `cycleDifficulty()` triggers in the keydown handler → **difficulty changes**

**Architecture fix — physical separation principle**:
| System | Listener Source | Keys | Purpose |
|--------|----------------|------|---------|
| Driving (per-frame state) | `main.ts` `keydown/keyup` | W/A/S/D + Arrows | Continuous physics input |
| Functions (one-shot) | Game class `keydown` | All other keys | Toggle/cycle features |

The two key sets MUST be disjoint. **Any overlap is a hard bug** that produces unpredictable behavior.

**Safe key mapping (validated in this session — ZERO conflict):**
```
W A S D / ↑ ← ↓ →   = Driving only (accelerate/brake/steer)
         Q = Camera view (isolated left of W)
         E = Vehicle tier (safe, near W thumb)
         R = Difficulty (right zone, safe)
         F = Paint (right zone, safe)
         T = Upgrade menu (right zone, safe)
       Tab = Circuit switch (deliberate, physically isolated)
  Esc     = Pause (isolated)
  1-4     = Upgrade parts (number row, safe)
  G       = Transmission mode (auto/manual toggle)
```

**Pitfall — C key is adjacent to D**: C sits between S (brake) and D (right steer). Pressing D brushes C, causing accidental camera switch. NEVER use C, V, N, or M as function keys — they sit in the WASD danger zone.

**Verification script** (run after every key remapping):
```python
import re
drive = set(re.findall(r"keyState\['(\w+)'\]", prg))
func = set(re.findall(r"e\.code\s*===\s*'(\w+)'", prg))
conflict = drive & func
assert not conflict, f"🔴 Key conflict: {conflict}"
print(f"✅ Zero conflict: {sorted(drive)} vs {sorted(func)}")
# Also verify all on-screen text labels match new keymap
```

### Pattern: `PlushRacingGame is not defined` — Static Methods Not Global in Webpack Module

**Symptom**: Menu buttons (Select Vehicle, Character, Settings, Credits) that call `PlushRacingGame.selectCar()` via `window.Game` throw `ReferenceError: PlushRacingGame is not defined` in the console.

**Root cause**: `PlushRacingGame` is a TypeScript class in a webpack module. Its static methods are **not** accessible from the global scope. The `import game from './PlushRacingGame'` only imports the default export (singleton instance), not the class itself. HTML `onclick` handlers call `window.Game.showVehicleSelect()` which references `PlushRacingGame.selectCar()` — but `PlushRacingGame` is never assigned to `window`.

```typescript
// BROKEN in main.ts — PlushRacingGame is a module class, not global
window.Game = {
    showVehicleSelect: () => PlushRacingGame.selectCar(),  // ReferenceError
};
```

**Fix options**:
1. **Convert static methods to instance methods** and reference via the imported `game` instance:
   ```typescript
   // In PlushRacingGame.ts — remove 'static' keyword:
   selectCar(): void { alert('车辆选择'); }
   
   // In main.ts — use the imported 'game' instance:
   window.Game = {
       showVehicleSelect: () => (game as any).selectCar(),
   };
   ```

2. **Don't reference the class at all** — use inline fallbacks for stubs:
   ```typescript
   window.Game = {
       showVehicleSelect: () => alert('🚗 Coming soon!'),
   };
   ```

3. **Assign the class to window** (least clean — pollutes global):
   ```typescript
   (window as any).PlushRacingGame = PlushRacingGame;
   ```

Note that `startRace: () => game.startGame()` works fine because `game` is the already-imported singleton instance — it never references the class name.

### Pattern: `caret is not defined` — Editor Artifact in Code

**Symptom**: JavaScript runtime error `Uncaught ReferenceError: caret is not defined` at `updatePlayer`. The game's physics engine stops working entirely, but scene rendering and other features that don't depend on updatePlayer continue.

**Root cause**: An editor cursor-position marker `{caret}` was accidentally left in the code during a patch operation. It's syntactically valid TypeScript (object destructuring of a variable called `caret` that doesn't exist), so webpack builds without error. But at runtime, the JavaScript engine tries to evaluate `caret` as a variable reference and throws.

```typescript
// BROKEN — {caret} is not a comment, it's a JS object destructuring attempt
let steerInput = steerRaw;{caret}
//                        ^^^^^^ ReferenceError: caret is not defined
```

**Prevention**: After every `patch()` operation on TypeScript/JavaScript files, verify no editor artifacts leaked in:
```bash
grep -n "caret\|cursor\|CURSOR\|TODO\|FIXME" src/PlushRacingGame.ts
```

If found, remove them with a targeted patch — the `{caret}` pattern specifically must be deleted entirely (including braces), not just replaced.

## Browser Deployment Pitfalls

1. **Webpack `clean: true` nukes index.html**: If you manually create `dist/index.html` after building, the NEXT build will delete it. Either:
   - Disable `clean: true` in `webpack.config.js`
   - Add `HtmlWebpackPlugin` to generate `dist/index.html` from a template
   - Place `index.html` in the project ROOT (not dist/) and serve the root directory

2. **`process.env` not defined in browser**: If the game code uses `process.env.NODE_ENV`, add a polyfill at the top of the entry file:
   ```typescript
   if (typeof process === 'undefined') { 
       (window as any).process = { env: { NODE_ENV: 'production' } }; 
   }
   ```
   This is needed because TypeScript/webpack code sometimes references `process.env` for dev-mode checks. Without it, the game crashes on load with `ReferenceError: process is not defined`.

The polyfill MUST be at line 1 of the entry file (before any `import` statements), because imports execute before any module-level code. If placed after imports, the throw happens before the polyfill runs.

3. **`serve` shows directory listing instead of game**: The `serve` npm package shows a file directory when there's no `index.html` at the served path. Even when `index.html` exists, `serve` may still list the dist/ subdirectory as the root. **More reliable**: use Python's built-in HTTP server:
   ```bash
   cd /path/to/project/root
   python3 -m http.server 8000
   ```
   This correctly serves root `index.html` and resolves `/dist/bundle.js` via relative URL.

4. **Serve process lingering**: Old `serve` processes survive pkill and keep serving stale files. Kill with `pkill -f "serve"` and wait 2s before restarting. Use `python3 -m http.server` instead — no zombie processes.

### Phase 5: Real Open-Source 3D Asset Integration — VDrift Model Import

When the user demands **real 3D car models** (not procedurally-generated geometry), the fastest source is open-source racing simulators. **VDrift** is the best option — GPL-licensed, 12+ real vehicle models, 9+ real circuits.

**Download source**: SourceForge (`vdrift` project, source tarball ~484MB). The game data (`.joe` binary mesh files + `.png` textures) is bundled in `vdrift-YYYY-MM-DD.tar.bz2` under `data/`.

## CRITICAL RULE: REAL DATA OVER PROCEDURAL GENERATION

This is a hard preference from the user. When building 3D game content:
1. **Source open existing assets FIRST** (VDrift, Speed Dreams, OpenGameArt, Sketchfab free downloads)
2. **Download and convert** existing formats to target engine formats
3. **Use real-world data** (GPS coordinates, actual vehicle specs, real corner sequences)
4. **Only procedurally generate as fallback** when absolutely no real data exists

**THIS IS NOT OPTIONAL.** The user will reject programmatic geometry (BoxGeometry, ExtrudeGeometry, CatmullRom curves from imagination) when the task specifies "真实赛道" or "真实车辆". Do NOT start with procedural generation and offer to "fix it later" — start with real data acquisition.

### VDrift Asset Download

SourceForge URL: `https://sourceforge.net/projects/vdrift/files/`
Download: `curl -L "https://sourceforge.net/projects/vdrift/files/vdrift-2014-10-20.tar.bz2/download" -o vdrift.tar.bz2 --connect-timeout 30`
The game data (`.joe` binary mesh files + `.png` textures) is in `data/` after extraction.

### JOE03 Binary Format — CORRECT PARSING (verified against VDrift C++ source)

**The JOE03 format uses VERTEX INDICES, NOT world-space positions.** The approach of "match world-space vertex positions" is fundamentally wrong and produces only ~5% of expected triangles. Use index-based parsing:

**Header (16 bytes):**
```
uint32 magic = 'IDP2'
uint32 version = 3
uint32 num_faces     ← NOT num_verts! This is the number of triangle faces
uint32 num_frames    ← Almost always 1
```

**Per-frame data (in this exact order):**
1. `faces[num_faces]`: Each face = **9 × uint16 (18 bytes total)**:
   - `vertexIndex[3]` — indices into verts array
   - `normalIndex[3]` — indices into normals array
   - `textureIndex[3]` — indices into texcoords array
2. `num_verts: uint32` — count of vertices in this frame
3. `num_texcoords: uint32` — count of UV coordinates
4. `num_normals: uint32` — count of normals
5. `verts[num_verts]`: Each = `3 × float32` (x, y, z) = 12 bytes
6. `normals[num_normals]`: Each = `3 × float32` (nx, ny, nz) = 12 bytes
7. `texcoords[num_texcoords]`: Each = `2 × float32` (u, v) = 8 bytes

**Unique vertex deduplication** (critical — without this, you get duplicate vertex explosion):
```python
vert_map = {}
unique_verts = []
unique_normals = []
unique_uvs = []
indices = []

for face in faces:
    for j in range(3):
        key = (face['verts'][j], face['texcoords'][j], face['normals'][j])
        if key not in vert_map:
            vert_map[key] = len(unique_verts)
            unique_verts.append(verts[face['verts'][j]])
            unique_normals.append(normals[face['normals'][j]])
            unique_uvs.append(uvs[face['texcoords'][j]] if face['texcoords'][j] < len(uvs) else (0,0))
        indices.append(vert_map[key])
```

**Z-up → Y-up conversion**: Apply `mesh.rotation.x = -Math.PI / 2` on the THREE.Group or Mesh.

**Python parser template** (validated on 13 VDrift car models, 2,000-22,000 tris each):
```python
import struct, json

def parse_joe_v3(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    if data[0:4] != b'IDP2':
        return None
    num_faces = struct.unpack_from('<I', data, 8)[0]
    num_frames = struct.unpack_from('<I', data, 12)[0]
    offset = 16
    
    for frame in range(num_frames):
        faces_data = data[offset:offset + num_faces * 18]
        offset += num_faces * 18
        
        faces = []
        for i in range(num_faces):
            v = struct.unpack_from('<9H', faces_data, i * 18)
            faces.append({'verts': [v[0],v[1],v[2]], 'normals': [v[3],v[4],v[5]], 'texcoords': [v[6],v[7],v[8]]})
        
        nv = struct.unpack_from('<I', data, offset)[0]; offset += 4
        nt = struct.unpack_from('<I', data, offset)[0]; offset += 4
        nn = struct.unpack_from('<I', data, offset)[0]; offset += 4
        
        verts = [struct.unpack_from('<3f', data, offset+i*12) for i in range(nv)]; offset += nv*12
        normals = [struct.unpack_from('<3f', data, offset+i*12) for i in range(nn)]; offset += nn*12
        uvs = [struct.unpack_from('<2f', data, offset+i*8) for i in range(nt)]; offset += nt*8
        
        # Deduplicate (see above)
        # ... build unique_verts, unique_normals, unique_uvs, indices ...
    
    return {'verts': [...], 'normals': [...], 'uvs': [...], 'indices': [...], 'numVerts': ..., 'numTris': ...}
```

### VDrift Model Multi-Part Export

Export body+glass+interior as a single JSON with a `parts` map for per-part material assignment:

```python
merged = {
    'name': car,
    'verts': [], 'normals': [], 'uvs': [], 'indices': [],
    'parts': {},  # { 'body': {vertOffset, vertCount, triCount, indexCount}, 'glass': {...}, 'interior': {...} }
    'numVerts': 0, 'numTris': 0,
}
vert_offset = 0
for part_name in ['body', 'glass', 'interior']:
    # parse and deduplicate
    merged['verts'].extend(part_data['verts'])
    merged['indices'].extend([i + vert_offset for i in part_data['indices']])
    merged['parts'][part_name] = {'vertOffset': vert_offset, 'vertCount': ..., 'triCount': ..., 'indexCount': ...}
    vert_offset += part_data['numVerts']
```

### Per-Car Independent Physics

DO NOT use shared tier values (all T2 = same speed). Every VDrift model MUST have its own `topSpeed`, `accel`, `handling`, `braking`, `weight`, `hp`:

```typescript
const VDRIFT_CAR_MODELS = [
    { id: '350Z', name: '日产 350Z', tier: 2, topSpeed: 250, accel: 5.7, handling: 7, braking: 34, weight: 1400, hp: 287 },
    { id: 'F1-02', name: 'F1 2002', tier: 5, topSpeed: 350, accel: 2.5, handling: 9, braking: 25, weight: 600, hp: 900 },
    // ... each with REAL manufacturer specs
];

private applyRealCarPhysics(): void {
    this.MAX_SPEED = p.topSpeed / 3.6;         // km/h → m/s
    this.ACCEL = 27.78 / Math.max(0.1, p.accel); // 0-100 time → m/s²
    this.STEER_SPEED = 1.5 + (p.handling / 10) * 2.0;
    this.BRAKE_FORCE = (27.78 * 27.78) / (2 * Math.max(1, p.braking));
}
```

### Model Loading — Async with Await

Car models (1-5MB each) must be loaded via fetch BEFORE scene creation. Use `await waitForModel(id)` to block startGame until loaded:

```typescript
startGame = async () => {
    this.selectRandomVDriftCar();
    const loaded = await this.waitForModel(this.currentVdriftModelId);
    this.initFullScene();  // only called after model is ready
}
```

**VDrift 13-model inventory (all validated):**

| File | Tris | Parts |
|------|------|-------|
| 350Z.json | 8452 | body+glass+interior |
| 360.json | 10011 | body+glass+interior |
| ATT.json | 2344 | body+glass+interior |
| CO.json | 9803 | body+glass+interior |
| CS.json | 4574 | body+glass |
| F1-02.json | 13394 | body |
| LE.json | 12154 | body+glass+interior |
| M3.json | 8070 | body+glass+interior |
| M7.json | 4948 | body+glass+interior |
| SV.json | 5035 | body+glass+interior |
| TC6.json | 22154 | body+glass+interior |
| TL2.json | 5618 | body+glass+interior |
| XS.json | 4457 | body+glass+interior |

### Gearbox + Torque Curve (Prevents 4s-to-250km/h Problem)

Without a gearbox, acceleration is constant and unrealistically fast. Implement:

```typescript
private gear = 1;
private readonly GEAR_RATIOS = [3.5, 2.2, 1.5, 1.1, 0.85, 0.65];  // 6-speed
private readonly FINAL_DRIVE = 3.5;
private readonly MAX_RPM = 7200;
private readonly IDLE_RPM = 850;
private shiftCooldown = 0;
private rpm = 0;

// In updatePlayer():
const currentRatio = this.GEAR_RATIOS[this.gear - 1] * this.FINAL_DRIVE;
const wheelRpm = (this.playerSpeed * 60) / (2 * Math.PI * wheelRadius);
this.rpm = Math.max(IDLE_RPM, Math.min(MAX_RPM, wheelRpm * currentRatio));

// Torque curve: low→peak→drop
const rpmNorm = (this.rpm - IDLE_RPM) / (MAX_RPM - IDLE_RPM);
let torqueFactor = rpmNorm < 0.3 ? rpmNorm/0.3*0.85       // rise
                 : rpmNorm < 0.65 ? 0.85+(rpmNorm-0.3)/0.35*0.2  // peak
                 : rpmNorm < 0.85 ? 1.05-(rpmNorm-0.65)/0.2*0.15 // fall
                 : 0.9-(rpmNorm-0.85)/0.15*0.3;             // redline drop

// Auto shift at 95% redline
if (shiftCooldown <= 0 && gear < 6 && targetRpm > MAX_RPM * 0.95) {
    gear++;
    shiftCooldown = SHIFT_TIME;  // 0.35s no power during shift
    rpm = MAX_RPM * 0.7;        // post-shift rpm drop
}
```

**Bug — speedRatio reference in steering after gearbox refactor**: When you replace the simplified speed control with the gearbox system, the `speedRatio` variable (computed as `this.playerSpeed / this.MAX_SPEED`) gets deleted from the speed section. But the steering section (below, unchanged) still references it. Fix by re-adding `const speedRatio = this.playerSpeed / (this.MAX_SPEED || 1);` at the top of the steering section.

### Gearbox Audio — Shift Sound

Replace the simple oscillator with:
1. RPM-to-frequency: `60 + (rpm - IDLE_RPM) / (MAX_RPM - IDLE_RPM) * 340` (idle=60Hz, redline=400Hz)
2. Lowpass filter that opens with RPM (200 + rpmNorm*1200)
3. Shift sound: pre-buffered white noise burst (`AudioBuffer.createBuffer`) played on gear change

### Transmission Mode Switch

Add both Auto and Manual:
- `transmissionMode: 'auto' | 'manual'` (toggle: G key)
- Auto: auto upshift at 95% redline, auto downshift at very low RPM+banking
- Manual: ShiftRight=upshift, Z=downshift
- Both modes share the same `shiftCooldown` timer and torque calculation

**Bug — manual shift fires every frame via keyState**: If you put manual shift detection in `updatePlayer()` using `keyState['ShiftRight']`, holding Shift will cause continuous upshifts (every frame). **Fix**: Move manual shift to the `keydown` event listener (edge-triggered, not level-triggered):

```typescript
// In keydown handler — fires ONCE per keypress:
if (this.transmissionMode === 'manual' && this.shiftCooldown <= 0) {
    if ((e.code === 'ShiftRight' || e.code === 'ShiftLeft') && this.gear < 6) {
        this.gear++;
        this.shiftCooldown = this.SHIFT_TIME;
        this.rpm = this.MAX_RPM * 0.7;
        e.preventDefault();
    }
    if (e.code === 'KeyZ' && this.gear > 1) {
        this.gear--;
        this.shiftCooldown = this.SHIFT_TIME * 0.5;
        this.rpm = this.MAX_RPM * 0.85;
        e.preventDefault();
    }
}
```

**VDrift model list (12 real cars extracted in this session):**

| ID | Real Car | Tier | Vertices | Tris |
|----|----------|------|----------|------|
| 350Z | Nissan 350Z | 2 | 5524 | 642 |
| 360 | Ferrari 360 Modena | 3 | 7726 | 652 |
| ATT | Audi TT | 2 | 1366 | 256 |
| CO | Caterham 7 | 2 | 8042 | 653 |
| CS | Corvette Stingray | 3 | 4470 | 799 |
| F1-02 | Formula 1 2002 | 5 | 13394 | 1798 |
| LE | Le Mans Prototype | 5 | 8008 | 1341 |
| M3 | BMW M3 E46 | 2 | 5752 | 1009 |
| M7 | McLaren F1 | 4 | 4200 | 298 |
| SV | Saleen S7 | 4 | 4607 | 295 |
| TC6 | Toyota Celica GT4 | 2 | 14795 | 121 |
| TL2 | Toyota Supra | 2 | 4916 | 828 |
| XS | BMW M3 GTR | 3 | 3875 | 17 |

**Caveats**: 
- `.joe` files use **Z-up** coordinate system. In Three.js (Y-up), rotate the root group: `mesh.rotation.x = -Math.PI / 2`
- `.png` textures are stored alongside `.joe` files (e.g., `body00.png`, `glass.png`). Webpack's `asset/resource` rule for `.png` handles them
- Original 350Z body is 200KB (5524 verts, 642 tris) — acceptable for browser game
- **VDrift uses triangle vertex WORLD POSITIONS** not vertex indices. The parser must match world-space positions to the vertex list (round to 3 decimal places) — this is the hardest part. Expect ~70-90% match rate; unmatched vertices use nearest-neighbor fallback
- Model files MUST be placed under `assets/models/` (served as static files, NOT bundled into JS). Access via `fetch('assets/models/obj/MODEL_ID.json')`

**Loading pattern in game class:**
```typescript
private vdriftModelCache: Map<string, THREE.BufferGeometry> = new Map();
private currentVdriftModelId = '350Z';

private async loadVdriftModel(modelId: string): Promise<void> {
    if (this.vdriftModelCache.has(modelId)) return;
    const response = await fetch(`assets/models/obj/${modelId}.json`);
    const data = await response.json();
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(data.verts), 3));
    geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(data.uvs), 2));
    geo.setIndex(new THREE.BufferAttribute(new Uint16Array(data.indices), 1));
    geo.computeVertexNormals();
    this.vdriftModelCache.set(modelId, geo);
}

private buildVehicle(pColor, aColor, paintScheme): THREE.Group {
    const group = new THREE.Group();
    const cachedGeo = this.vdriftModelCache.get(this.currentVdriftModelId);
    if (cachedGeo) {
        const mesh = new THREE.Mesh(cachedGeo.clone(), bodyMat);
        mesh.rotation.x = -Math.PI / 2;  // Z-up → Y-up
        group.add(mesh);
        this.addSimpleWheels(group, aColor);  // add wheel placeholders
    } else {
        this.buildFallbackCar(group, pColor, aColor);  // box fallback
    }
    return group;
}
```

**Random car at each start:**
```typescript
const VDRIFT_CAR_MODELS = [
    { id: '350Z', name: '日产 350Z', tier: 2 },
    // ... all 13 models
];
private selectRandomVDriftCar(): void {
    const car = VDRIFT_CAR_MODELS[Math.floor(Math.random() * VDRIFT_CAR_MODELS.length)];
    this.currentVdriftModelId = car.id;
    this.selectedTier = car.tier;  // sync with physics tier
    this.loadVdriftModel(car.id);  // async load
}
```

**Pitfall — textures not loading**: The `.joe` files reference texture names (e.g., `body00.png`) but the export JSON only contains geometry. You must apply materials separately in Three.js. Use separate MeshPhysicalMaterial with desired color/metalness/roughness, ignoring the original VDrift texture references.

**Pitfall — model orientation**: VDrift models are designed for Z-up coordinate system; Three.js uses Y-up. Without `rotation.x = -Math.PI / 2`, the car will lie on its side. **But** applying this rotation to individual meshes causes the wheels (added separately) to be in the wrong coordinate space.

**Fix**: Put body meshes in a child Group that gets the rotation; add wheels to the parent (unrotated) Group:
```typescript
const bodyGroup = new THREE.Group();
bodyGroup.rotation.x = -Math.PI / 2;  // Z-up → Y-up for models only
group.add(bodyGroup);
// body/glass/interior meshes → bodyGroup
// wheels → group (not rotated)
```

**Pitfall — model scale**: VDrift models are in real-world meter scale. A 4.4m car body (350Z) will correctly measure ~4.4 units in Three.js. The track's `gameLength` should match.

### Phase 5b: Real GPS-Based Circuit Data

When the user demands **real-world racing circuits** (not procedurally-generated curves), use GPS coordinates from Wikipedia/OpenStreetMap. **This session's method:**

1. Get GPS center coordinates for each circuit from Wikipedia
2. Convert each circuit's known corner sequence to XY coordinates relative to center
3. Use real corner names and approximate curvature radii

**GPS-to-game conversion:**
- 1 degree latitude ≈ 111,000 meters
- 1 degree longitude ≈ 111,000 × cos(latitude) meters
- Center the circuit at origin, express control points in meters

**Pitfall — 1:1 meter scale preference**: The user EXPLICITLY rejected scaled-down tracks (scale factors 50/120/300). They demanded 1 game unit = 1 real meter. This means:
- `gameLength` must equal real-world track length (Silverstone=5891, not 5200)
- Control points span 700+ units (Silverstone goes from x=-700 to x=480)
- Ground plane must be dynamic: `Math.max(600, trackBounds.size * 1.5)`
- Camera mode 1 (overhead) height must be dynamic
- Collision sampling segments count must scale: `Math.min(2000, Math.max(500, trackLength/5))`
- AI speed formula must use real track length as divisor: `aiSpeed / trackLength`

**This session's circuits (with real GPS centers):**

| Circuit | GPS Center | Real Length | Corners | Control Points |
|---------|-----------|-------------|---------|----------------|
| Silverstone | 52.0711°N, 1.0161°W | 5891m | 18 | 25 (Abbey→Farm→...→Club) |
| Spa | 50.4372°N, 5.9714°E | 7004m | 19 | 19 (La Source→Eau Rouge→...) |
| Monza | 45.6156°N, 9.2811°E | 5793m | 11 | 16 (Rettifilo→Grande→...) |
| Nürburgring | 50.3356°N, 6.9475°E | 20832m | 73 | 26 (simplified key corners) |
| Monaco | 43.7347°N, 7.4206°E | 3337m | 19 | 17 (Ste Devote→Casino→Fairmont→...) |
| Le Mans | 47.9498°N, 0.2072°E | 13629m | 38 | 18 (Dunlop→Mulsanne→...) |
| Suzuka | 34.8431°N, 136.5411°E | 5807m | 18 | 21 (S-curves→130R→Casio Triangle) |

**Elevation**: Include Y-axis height variation for circuits with real elevation change (Spa: -20 to +60m, Nürburgring: -70 to +70m, Monaco: -10 to +18m). Flat tracks (Silverstone, Monza, Le Mans, Suzuka) use Y=0.

**Key disciplines when user says '这不是真实赛道'**:
1. Source real GPS coordinates from Wikipedia/OSM — do NOT invent coordinates
2. Use real corner NAMES and SEQUENCE — each control point must correspond to a named corner
3. Use real track LENGTH — CatmullRom interpolation should produce a track close to real length
4. Include elevation where the real circuit has it (Spa's Eau Rouge climb is essential)
5. If you can't download GPS waypoints (Overpass API blocked, network restricted), derive control points from the circuit shape using:
   - Published corner-by-corner distance tables
   - Circuit map images (estimate relative positions)
   - Known corner radii from racing data sites

## CRITICAL RULE: REAL DATA OVER PROCEDURAL GENERATION + VDRIFT COORDINATE SYSTEM

This session produced a strong user preference that must be encoded as a workflow rule:

**When building 3D game content with real-world references, the CORRECT approach is:**
1. **Source open existing assets first** (VDrift, Speed Dreams, OpenGameArt)
2. **Download and convert** existing formats to target engine formats
3. **Use real-world data** (GPS coordinates, actual vehicle dimensions, real corner sequences)
4. **Only procedurally generate as fallback** when real data is unavailable

**The WRONG approach (what triggered user frustration):**
1. Procedurally generating track control points from imagination
2. Using `BoxGeometry` + `ExtrudeGeometry` with guessed proportions instead of real 3D models
3. Making up vehicle performance numbers instead of using real manufacturer data

**Trigger phrases that indicate this preference is active:**
- "根据真实车辆建模" (model based on real vehicles)
- "真实赛道" (real track)
- "不是真实赛道" (not a real track)
- Any mention of specific real car models, circuits, or manufacturers

**Execution order when this trigger fires:**
1. Search for open-source game data (VDrift, Speed Dreams, Rigs of Rods)
2. Download via SourceForge/GitHub (`curl -L` with long timeout, typically 300s+)
3. Parse and convert to target format (joe→JSON, write Python parser)
4. Integrate into game engine (async fetch + BufferGeometry)
5. Only fall back to procedural geometry when no real model exists for that specific vehicle

### Phase 6e: Progressive Feature Integration (Paint/Upgrade/Difficulty/Season)

When the user asks to add new systems (paint, upgrades, difficulty levels, season scoring) to an existing monolithic game class, use this injection pattern:

### Integration Pattern — Adding a Feature to a Monolith

1. **Add properties** at the class-level property block (near the top)
2. **Add initialization call** in the main init method (e.g., `this.initDifficulty()` after other inits)
3. **Add hotkey handler** in the keydown listener (e.g., `KeyD` for difficulty cycle)
4. **Add UI elements** dynamically (create DOM elements in methods like `createDifficultyHUD()`)
5. **Modify existing update methods** to consume new parameters (e.g., `updatePlayer()` reads `this.diffAutoSteer`)
6. **Build-validate cycle** after each major change

Example pattern for adding a UI element:
```typescript
private createPaintHUD(): void {
    if (document.getElementById('paint-hud')) return; // guard against double-init
    const hud = document.createElement('div');
    hud.id = 'paint-hud';
    hud.style.cssText = 'position:fixed;bottom:240px;right:15px;z-index:100;...';
    hud.innerHTML = '<div id="paint-name">-</div>';
    document.body.appendChild(hud);
}
```

### Paint System Integration

1. Import PaintSchemeRegistry from vehicles/PaintSystem
2. Add `carPaintMeshes` property (stores `{ body, spoiler, rim }` mesh references from buildVehicle)
3. Save mesh references by checking `if (this.playerCar === group)` inside buildVehicle
4. applyPaintToCar: iterate meshes, update material.color / metalness / roughness
5. switchPaint: cycle schemes, call applyPaintToCar, update HUD

**Pitfall — Player car detection**: buildVehicle is called for both player and AI cars. Only store references when building the player car. Use a flag or check against `this.playerCar`.

### Upgrade System (8-level, 4 parts)

Add properties: `upgradeParts = { engine:0, suspension:0, brake:0, aero:0 }`, `upgradeMultipliers = ...`, `MAX_UPGRADE_LEVEL = 8`

Each level = +6.25% to that part's multiplier. Apply to physics:
- Engine → ACCEL = 20 × engineMult
- Suspension → STEER_SPEED = 3.0 × suspMult
- Brake → BRAKE_FORCE = 25 × brakeMult
- Aero → MAX_SPEED = 80 + (aeroMult-1)×20

Show a modal upgrade menu (M key) with per-part level bars, percentages, and hotkeys 1-4.

### 5-Difficulty Physics Engine

When implementing difficulty levels directly in a monolith game class:

| Level | Name | Steering | Brakes | Accel | MaxSpd | Grip | AutoSteer | AutoBrake | TCS | ABS |
|-------|------|----------|--------|-------|--------|------|-----------|-----------|-----|-----|
| 0 | 娱乐 | 4.5 | 28 | 22 | 85 | 2.0 | 90% | Yes | Yes | Yes |
| 1 | 轻松 | 3.8 | 27 | 21 | 82 | 1.5 | 50% | No | Yes | Yes |
| 2 | 中等 | 3.0 | 25 | 20 | 80 | 1.0 | No | No | Yes | No |
| 3 | 困难 | 2.2 | 23 | 18 | 78 | 0.7 | No | No | No | No |
| 4 | 大师 | 1.8 | 20 | 16 | 75 | 0.5 | No | No | No | No |

**Physics model**: Torque curve (speedNorm → 1−0.5×speedNorm damping), slip angle (steer × speedNorm × delta), understeer (speedNorm − grip×0.8), drift detection (|slipAngle| > 0.15 ∧ speed > 20 → speed ×= 1−delta×0.5), roll animation (rotation.z lerps to -steer×0.15×speedNorm).

### Season/Points System

Use F1-style points table: `[25, 18, 15, 12, 10, 8, 6, 4, 2, 1]`

Calculate position by comparing player progress vs AI progress (accounting for lap count). Display in results screen with recent-race history.

## Pitfalls

### Common Failures

- **RAF never starts**: The first call to `gameLoop()` should use `requestAnimationFrame(() => this.gameLoop())` instead of `this.gameLoop()` directly. In some browser contexts (headless, fresh page load), direct call doesn't initiate the RAF chain.
- **`initMinimap` crashes on existing non-canvas element**: `document.getElementById('minimap')` may return a `<div>`, not a `<canvas>`. Casting as HTMLCanvasElement and calling `.getContext()` will throw. Check `instanceof HTMLCanvasElement` before using.
- **`browser_console` error accumulation**: Console messages persist across navigations. Use `?v=N` or clear before each test run.
- **PlushRacingGame not global**: webpack modules scope their exports. Static methods won't be accessible as `PlushRacingGame.start()`. Use the exported `const game` instance: `window.Game = { startRace: () => game.startGame() }`.
- **SVG text elements in speed gauge**: The `text` element content is inside an SVG. Updating `textContent` works but the SVG may re-render only after the next RAF frame. The first few frames will show "0" even as speed accumulates.

### Pattern Matches: what to look for

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| webpack builds but game shows blank page | old inline Game.init() still running in load event | Remove the entire inline Game object + load listener |
| "THREE is not defined" in console | inline HTML code references THREE before bundle loads | Remove all inline `<script>` blocks referencing THREE |
| Speed stays at 0 even with W held | RAF chain not started; or gameState not 'playing' | Call `requestAnimationFrame(() => this.gameLoop())` in startGame() |
| Minimap crashes on second game start | Already-initialized canvas replaced by div | Guard with `instanceof HTMLCanvasElement` |
| AI speed doubles each frame | Duplicate progress update line (patch artifact) | Remove the extra `this.aiProgress[i] += ...` |
| HUD elements not found | HTML IDs don't match what code expects | Snapshot HTML to find actual IDs/SVG structure |

### Complete Track Environment Generation

When adding environment elements (grass, curbs, barriers, grandstands, billboards, pit buildings, finish line, trees) to a racing circuit, use the pattern in `references/complete-track-environment.md`. Each element is a separate private method called in sequence from `generateTrack()`.

Covers: grass base generation, track surface with CanvasTexture markings, red/white curbs, TubeGeometry guardrails, grandstand placement with straight-section detection, neon billboards, pit building rows, checkered finish line with gantry, and procedural tree placement.

## Reference Files
- `references/ai-code-fix-patterns.md` — Concrete error patterns and fixes for AI-generated TypeScript game code
- `references/procedural-racing-game.md` — Code snippets for CatmullRom track gen, vehicle physics, camera, AI, Bloom, audio, city and neon lighting
- `references/racing-game-v2-enhancements.md` — Lap/collision/drift/AI/minimap system additions from v2
- `references/raf-headless-debug.md` — Debugging RAF in headless browser and frame loop startup
- `references/vehicle-tier-paint-system.md` — 5-tier vehicle classification and paint/livery system
- `references/batch-vehicle-generation.md` — Python-to-TypeScript batch pipeline for 70+ vehicle configs
- `references/racing-game-circuits.md` — Real F1/GT circuit control points (Silverstone, Spa, Monza, Nürburgring, Monaco, Le Mans, Suzuka)
- `references/racing-game-physics-difficulty.md` — 5-difficulty physics engine: torque curve, TCS, ABS, auto-steer, slip angle, drift, AI sync
- `references/vehicle-performance-calibration.md` — 100-point scale calibration algorithm: tier medians, spread constraints, upgrade caps, physics mapping, verification checklist
- `references/gps-circuit-data.md` — GPS-based circuit generation using real-world track coordinates, conversion formulas, per-circuit waypoint details, and scaling guidance
- `references/procedural-vehicle-modeling.md` — Complete vehicle 3D construction using ExtrudeGeometry + ShapeGeometry plus traverse-based paint system
- `references/vdrift-model-import.md` — VDrift open-source racing game model import pipeline: JOE binary format parser, Z-up→Y-up conversion, async fetch loading pattern
- `references/vdrift-coordinate-system-and-bug-patterns.md` — This session's hard lessons: VDrift y-=front coordinate system, wheel position math, LatheGeometry alignment, race-start bugs, AI spin fix, GPS circuit control point density, and the critical one-carY-setting bug

## Verification
- [ ] webpack production build succeeds (0 errors)
- [ ] dist/ has bundle.js + index.html + assets/
- [ ] Browser shows main menu with buttons
- [ ] Clicking start hides menu, shows HUD + 3D canvas (use RAF not direct call)
- [ ] Console shows no JS errors
- [ ] Keyboard input moves the car (speed > 0 after W held 2s)
- [ ] AI cars visible and moving with corner braking
- [ ] Rank, lap count, and speed update
- [ ] Collision: car hitting track edge causes speed drop + sound
- [ ] Lap crossing detected, timing recorded
- [ ] 3 laps triggers finish screen
- [ ] ESC pauses, C switches camera
- [ ] Vehicle database registers 50+ vehicles (verify in console log)
- [ ] PaintSchemeRegistry instantiates without error
- [ ] Difficulty cycle (D key) updates parameters and HUD
- [ ] Upgrade menu (M key) shows per-part levels and 1-4 hotkeys work
- [ ] Circuit switch (N key) rebuilds track correctly
- [ ] Race finish shows points/season display
- [ ] **Key bindings**: D drives right only (no difficulty change). All function keys (Q/E/R/F/T/G/Tab) produce correct one-shot actions without affecting WASD driving. **ZERO keys overlap between driving and function sets.**
- [ ] **Gearbox**: Speed increases realistically through gears (not 0-250km/h in 4 seconds). RPM follows speed × gear ratio. Shifting produces a brief power cut.
- [ ] **Transmission mode**: G toggles auto/manual. In manual, Shift=upshift, Z=downshift work as one-shot actions (not continuous). shiftCooldown prevents double-shifts.
- [ ] **Shift sound**: An audible click/grind occurs on each gear change (white noise burst).
- [ ] **Paint** (F): Changes body color AND accent (wheels/spoiler) color. The emissive check uses `getHex() === 0` not `!mat.emissive`.

## 回滚方案
### 代码回退
1. `git revert HEAD` 撤销最后一次提交
2. `git stash` 恢复工作区状态
3. 重新运行测试套件确认无回归

### 紧急回滚
1. `git reset --hard HEAD~1` 硬回退
2. `git push --force-with-lease` 推送
3. 通知团队变更已回退
