---
name: threejs-game-development
category: gaming
description: Three.js browser-based 3D game development — vehicle physics, 3D model loading, coordinate systems, rendering pipelines
trigger: building a browser 3D game with Three.js, implementing vehicle physics, loading 3D models, working with WebGL rendering
---

# Three.js Browser Game Development

## Core Principles

1. **Always use `python3 -m http.server <port>` for dev server** — `npx serve` has directory-listing issues. Port 8000 is standard.
2. **Build with webpack** when using TypeScript + Three.js. Bundle size ~575KB for a full racing game is normal.
3. **Cache-bust**: Ctrl+F5 or `location.reload(true)` after each build. Console errors like `CIRCUIT_DATA is not defined` usually mean stale bundle.

### Absorbed Skills (consolidated from narrow siblings)

This skill is the umbrella for all Three.js racing game development. The following narrow skills were absorbed as labeled subsections under this SKILL.md or as reference files:

| Former Skill | Absorbed As | Reference File |
|---|---|---|
| `racing-game-threejs-build` | Subsection — Three.js Build Details | `references/racing-game-threejs-build-complete.md` |
| `racing-game-physics-migration` | Subsection — Physics Migration from VDrift | `references/racing-game-physics-migration-complete.md` |
| `open-source-racing-game-migration` | Subsection — Open Source Racing SIM Migration | `references/open-source-racing-game-migration-skill.md` |
| `threejs-game-rescue` | Subsection — Game Rescue & Compile-Fix | `references/threejs-game-rescue-complete.md` |
| `web-game-debugging` | Subsection — Web Game Debugging & QA | `references/web-game-debugging-complete.md` |

### Open-Source Racing SIM Migration (summary)

**Core Principle**: Never invent physics from scratch. Always migrate from proven open-source racing sims (VDrift, Speed Dreams, Rigs of Rods). See full content in `references/open-source-racing-game-migration-skill.md`.

Priority sources:
1. **VDrift** (GPL) — Most complete: Pacejka tire model, real transmission, suspension, aero
2. **Speed Dreams** (GPL) — Fork of TORCS, good track models
3. **Rigs of Rods** (GPL) — Soft-body physics, complex terrain

### Web Game Debugging (summary)

**5-Layer Game-Break Detection Protocol**: See full content in `references/web-game-debugging-complete.md`.

Key protocols:
- Layer 1: Console Errors — distinguish Three.js warnings from actual JS ReferenceErrors
- Layer 2: Static Method Global Scope — webpack module-scoped classes need window routing
- Layer 3: Update Function Liveness — verify gameLoop actually executes
- Layer 4: Function-by-Function Audit — check every called method exists
- Layer 5: WebGL Renderer Liveness — try-catch composer/init with fallback

### Game Rescue Workflow (summary)

**Phases**: Full Feature Audit → Zero Key-Conflict Audit → Sequential Phase Delivery. See `references/threejs-game-rescue-complete.md` for the complete workflow including the 10+ verification patterns for vehicle geometry, collision, camera, track environment, difficulty tiers, and post-deployment validation.

## VDrift Model Loading (3D Car Models)

### CRITICAL: JOE (IDP2) Binary Format — Parse Order

**The most common source of garbage/collapsed models is wrong parse order.** The actual VDrift IDP2 format (from model_joe03.cpp source) is:

```
1. Header: magic(4) + version(4) + num_faces(4) + num_frames(4) + flags(4) = 20 bytes
2. For each frame:
   a. Face data: num_faces × 18 bytes (9 uint16 LE: v0,v1,v2, n0,n1,n2, t0,t1,t2)
   b. num_verts (uint32 LE)
   c. num_texcoords (uint32 LE)
   d. num_normals (uint32 LE) — WARNING: may contain garbage (>100k), fallback to num_texcoords
   e. Vertex data: num_verts × 12 bytes (3 float LE: x,y,z)
   f. Normal data: num_normals × 12 bytes (3 float LE)
   g. TexCoord data: num_texcoords × 8 bytes (2 float LE: u,v)
```

**WRONG order** (what old parsers did — produces all coordinates near 0,0,0):
```
1. Header → read verts directly → garbage out
```

**Key pitfalls:**
- Faces come BEFORE verts in the file, not after
- Vertex indices in faces can exceed num_verts (out-of-range). **MUST filter: skip any triangle with vi ≥ num_verts**
- num_normals (3rd uint32) is often corrupted/overwritten — if > 100k, use num_texcoords as fallback
- All integers and floats are **little-endian**
- `CorrectEndian` in C++ swaps bytes — on LE host (x86), no swap needed
- One frame per file (num_frames=1 for body.joe)

```python
# Python parse_frame pseudocode:
def parse_frame(raw, pos, num_faces):
    faces = []
    for _ in range(num_faces):
        v0,v1,v2 = struct.unpack('<HHH', raw[pos:pos+6]); pos+=6
        n0,n1,n2 = struct.unpack('<HHH', raw[pos:pos+6]); pos+=6
        t0,t1,t2 = struct.unpack('<HHH', raw[pos:pos+6]); pos+=6
        faces.append((v0,v1,v2,n0,n1,n2,t0,t1,t2))
    
    nverts  = struct.unpack('<I', raw[pos:pos+4])[0]; pos+=4
    ntex    = struct.unpack('<I', raw[pos:pos+4])[0]; pos+=4
    nnorm   = struct.unpack('<I', raw[pos:pos+4])[0]; pos+=4
    if nnorm > 100000: nnorm = ntex  # fallback
    
    verts = []
    for _ in range(nverts):
        x,y,z = struct.unpack('<fff', raw[pos:pos+12]); pos+=12
        verts.append((x,y,z))
    # ... same for normals, texcoords
    
    # Face-based vertex dedup with index bounds check:
    for v0,v1,v2, n0,n1,n2, t0,t1,t2 in faces:
        if v0 >= nverts or v1 >= nverts or v2 >= nverts: continue  # SKIP OOB
        if n0 >= nnorm or n1 >= nnorm or n2 >= nnorm: continue
        for j in range(3):
            vi = [v0,v1,v2][j]
            key = (vi, [n0,n1,n2][j], [t0,t1,t2][j])
            if key not in vmap:
                vmap[key] = len(out_verts)
                out_verts.extend(verts[vi])
            out_indices.append(vmap[key])
```

### Verify With Python After Conversion
```python
import json
d = json.load(open('dist/models/XXX.json'))
nv = d['numVerts']
print(f'verts={nv}, indices_max={max(d[\"indices\"])}, in_range={max(d[\"indices\"]) < nv}')
# Expected: in_range=True. If False, model will be garbage.
# Also check coordinate ranges:
v = d['verts']
xr = min(v[::3]), max(v[::3])
yr = min(v[1::3]), max(v[1::3])
zr = min(v[2::3]), max(v[2::3])
print(f'x=[{xr[0]:.2f},{xr[1]:.2f}] y=[{yr[0]:.2f},{yr[1]:.2f}] z=[{zr[0]:.2f},{zr[1]:.2f}]')
# Expected: x ~±2, y ~±0.5, z ~±1. Huge values (>1e10) mean wrong parse.
```

### Coordinate System (Critical!)
VDrift `.joe` format uses: **x=左右, y=前后(y-是车头), z=上下** (Z-up).
Three.js uses **Y-up**: x=右, y=上, z=-前.

Forward direction in VDrift is **y-negative** (always verify with vertex data analysis).

**Recorded verification** (ATT model, confirmed correct):
```
原始VDrift坐标: x=左右, y=前后(y-车头), z=上下
前轮: (±0.72, -1.97, 0.06) → 新(±0.72, 0.06, 1.97)  z+是车头
后轮: (±0.70, 1.89, 0.05) → 新(±0.70, 0.05, -1.89)
轴距: 前轮z(+1.97) - 后轮z(-1.89) = 3.86m
```

**CRITICAL CHOICE: Vertex transform vs Group rotation — pick ONE and be consistent.**

### Approach A: Vertex Data Transform (RECOMMENDED — prevents wheel placement bugs)
Transform all vertices at the data level — no bodyGroup rotation needed:
```typescript
// VDrift raw: (x左右, y前后y-车头, z上下)
// Three.js Y-up: x=右, y=上, z=-前
// Transform: newX=原x, newY=原z, newZ=-原y
const rawVerts = new Float32Array(carData.verts);
const verts = new Float32Array(rawVerts.length);
for (let i = 0; i < rawVerts.length; i += 3) {
    verts[i] = rawVerts[i];         // x不变
    verts[i+1] = rawVerts[i+2];     // y ← 原z(上下→Y轴)
    verts[i+2] = -rawVerts[i+1];    // z ← -原y(y-车头→Z+)
}
// Also transform normals the same way
for (let i = 0; i < rawNorms.length; i += 3) {
    normals[i] = rawNorms[i];
    normals[i+1] = rawNorms[i+2];
    normals[i+2] = -rawNorms[i+1];
}
```

**CRITICAL VERIFICATION after conversion — run this every time:**
```python
import json
d = json.load(open('dist/models/XXX.json'))
nv = d['numVerts']
mi = max(d['indices'])
print(f'indices max={mi} nv={nv} OOB={mi >= nv}')
# Expected: OOB=False. If True → model will be garbage geometry.
# The most common cause: vmap[key] used len(out_verts) instead of len(out_verts)//3
```
- Group has NO rotation — just a plain container
- Wheels added directly to group (same coordinate system)
- Eliminates the entire class of wheel Y-coordinate misalignment bugs

### Approach B: Group Rotation (DO NOT USE — causes wheel position bugs)
```typescript
const bodyGroup = new THREE.Group();
bodyGroup.rotation.x = -Math.PI / 2;
group.add(bodyGroup);
```
- WARNING: bodyGroup rotation warps local Y coordinates to world Z — wheel positions become ambiguous
- Only Rx(-90°), do NOT add Ry(180°)
- Wheels must be added to the OUTER group, not bodyGroup

### Model Cleanup — Critical Post-Processing Steps

After parsing, apply these filters to the vertex/index data:

1. **Remove outliers**: Any vertex with coordinate >100 in any axis is garbage (reality: cars fit in ±3m box). Filter: `if abs(x) < 100 and abs(y) < 100 and abs(z) < 100`
2. **Rebuild index map**: After filtering, remap indices to new vertex ordering
3. **Recount**: Recalculate numVerts and numTris from filtered data

```python
cleanVerts = []
cleanNorms = []
cleanUVs = []
cleanIndices = []
vertMap = {}
for i in range(d['numVerts']):
    x, y, z = d['verts'][i*3], d['verts'][i*3+1], d['verts'][i*3+2]
    if abs(x) < 100 and abs(y) < 100 and abs(z) < 100:
        vertMap[i] = len(cleanVerts)
        cleanVerts.extend([x, y, z])
        cleanNorms.extend([d['normals'][i*3], d['normals'][i*3+1], d['normals'][i*3+2]])
        cleanUVs.extend([d['uvs'][i*2], d['uvs'][i*2+1]])
for idx in d['indices']:
    if idx in vertMap:
        cleanIndices.append(vertMap[idx])
```

### Parts Parsing
VDrift JSON has `parts` dictionary with `vertOffset`, `vertCount`, `triCount`, `indexCount`. **Critical**: `indexOffset` is often MISSING — calculate it by accumulating previous parts' `indexCount`:
```typescript
let iStart = 0;
for (const [prevName, prevInfo] of Object.entries(carData.parts)) {
    if (prevName === partName) break;
    iStart += (prevInfo as any).indexCount || (prevInfo as any).triCount * 3;
}
```

**However**: After v10 parser cleanup (index bounds check + outlier filtering), parts structure is simplified — use a single `body` part containing all data. Multi-part (body/glass/interior) extraction is deprecated due to index remapping complexity after cleanup.

### Wheel Sub-Components — Unified Rotation Protocol (CRITICAL!)

**NEVER rotate wheel sub-components (tire, hub, disc, rimGroup) individually.** Always use a `wheelGroup` with a SINGLE `rotation.z = PI/2` at the group level. All sub-components are built in default orientation (Y-axis) and the group rotation handles everything.

```typescript
const wheelGroup = new THREE.Group();
wheelGroup.rotation.z = Math.PI / 2;  // ONE rotation for ALL components

// ALL sub-components added to wheelGroup in DEFAULT orientation:
const tire = new THREE.Mesh(tireGeo, tireMat);     // LatheGeometry default Y-axis
wheelGroup.add(tire);
const hub = new THREE.Mesh(new THREE.CylinderGeometry(...), rimMat);  // Cylinder default Y-axis
wheelGroup.add(hub);
const outerRing = new THREE.Mesh(new THREE.TorusGeometry(...), rimMat);  // Torus default
wheelGroup.add(outerRing);
const disc = new THREE.Mesh(new THREE.CylinderGeometry(...), discMat);
disc.position.y = -tireWidth * 0.35;  // offset along Y (becomes Z after rotation)
wheelGroup.add(disc);
```

**DO NOT** do this (individual rotations cause perpendicular misalignment):
```typescript
// WRONG - hub and disc face wrong direction
tire.rotation.z = PI/2;
hub.rotation.z = PI/2;  // ← if these don't match exactly, parts are misaligned
disc.rotation.y = PI/2;  // ← different axis! disc faces wrong direction
```

**The offset axis flips** — Because the group rotates Z→X, Y-axis offsets become Z-axis offsets in world space. So `disc.position.y` in the group local space becomes `disc position Z` after `rotation.z = PI/2`.

### Wheel Positions — Coordinate System Verification

**CRITICAL**: `wheelPositions` data is in **(x左右, z上下, y前后)** format — NOT (x,y,z)!

This is a hybrid: `pos[0]=x(左右)`, `pos[1]=z(上下 原VDrift Z)`, `pos[2]=y(前后 原VDrift Y)`.

After extensive testing (multiple coordinate transform iterations until it worked), the correct mapping is:
```typescript
// CORRECT: wheelPositions format is (x, z, y):
//   pos[0] = VDrift x (right-left, unchanged)
//   pos[1] = VDrift z (up-down → Three.js Y)
//   pos[2] = VDrift y (forward-back, negate for Three.js Z)
wg.position.set(pos[0], pos[1], -pos[2]);
```

**WARNING**: If you use `set(pos[0], pos[2], -pos[1])` (swapping pos[1] and pos[2]), front wheels will be underground and rear wheels above ground — the car appears vertically tilted.

### Verified Data (ATT model):
```
wheelPositions['ATT']:
  [-0.84, -0.22, -1.60]  →  front-left:  (-0.84, -0.22, 1.60)  z+ = forward
  [0.84, -0.22, -1.60]   →  front-right: (0.84, -0.22, 1.60)
  [-0.88, -0.22, 1.60]   →  rear-left:   (-0.88, -0.22, -1.60) z- = rear
  [0.88, -0.22, 1.60]    →  rear-right:  (0.88, -0.22, -1.60)
```

### Front/Rear Wheel Detection — Use Index, NOT Position Values

**CRITICAL**: The `wheelPositions` array is ordered `[front-left, front-right, rear-left, rear-right]`. Use index position, NOT coordinate values, to detect front vs rear:

```typescript
for (let idx = 0; idx < positions.length; idx++) {
    const pos = positions[idx];
    const wg = new THREE.Group();
    wg.position.set(pos[0], pos[1], -pos[2]);
    ...
    wg.userData.isWheel = true;
    wg.userData.isFront = idx < 2;  // ← ALWAYS use idx < 2, NOT coordinate values
}
```

**DON'T** use `pos[2] < 0` or `pos[1] < 0` — VDrift data may have front and rear wheels at the same z-value, making coordinate-based detection unreliable. The hardcoded array ordering is the only reliable signal.

### Wheel Positioning — Group Parent Protocol (CRITICAL!)

**The most common runtime crash in VDrift model loading:**

When `addWheelsToCar(bodyGroup, ...)` is called from `buildVDriftCar`, the parameter name `bodyGroup` shadows the outer scope. If inside the function you then reference `group` (which was the old parameter name), you get `ReferenceError: group is not defined`.

**The correct calling pattern:**

```typescript
// In buildVDriftCar(group, ...):
// 'group' is the outer group (no rotation), 'bodyGroup' is the rotated child group

// Body meshes go to bodyGroup (rotated) ✓
bodyGroup.add(mesh);

// WHEELS MUST go to the OUTER group, not bodyGroup!
// Because bodyGroup has rotation, adding wheels there warps their positions
this.addWheelsToCar(group, accentColor);  // ← pass 'group', NOT 'bodyGroup'
```

```typescript
// In addWheelsToCar(parentGroup, ...):
private addWheelsToCar(parentGroup: THREE.Group, accentColor: number): void {
    // MUST use the parameter name consistently!
    const wheelParent = parentGroup;  // ← use 'parentGroup', NOT 'group'
    ...
    wheelParent.add(wg);
}
```

**Signs of this bug:**
1. JavaScript console: `Uncaught ReferenceError: group is not defined`
2. Crash at `addWheelsToCar` in `buildVDriftCar`
3. Black canvas with "game started" but no visible car

**The fix is ALWAYS the same:** ensure `addWheelsToCar` gets the right parent group AND uses its parameter consistently internally.

### Wheel Positioning — CRITICAL: y-方向是车头
After bodyGroup rotation (Rx=-90°), coordinates transform as:
```
原始(x,y,z) → 新(x, z, -y)
```

Always verify by reading actual vertex data. For ATT model:
```python
# 找出z≈0(地面附近)的顶点中y最极端的两个值
ground_verts = [v for i in range(0, len(verts), 3) 
                if 0 < verts[i+2] < 0.15]
front_y = max(v[1] for v in ground_verts)  # y最大值≠车头！
rear_y = min(v[1] for v in ground_verts)   # y最小值才是车头方向
```

ATT verified data:
```
前轮(在原始y-方向): 原始(±0.72, -1.97, 0.06) → 新(±0.72, 0.06, 1.97)  z+是车头
后轮(在原始y+方向): 原始(±0.70, 1.89, 0.05) → 新(±0.70, 0.05, -1.89)
轮距前1.44m, 后1.40m, 轴距3.86m
前轮索引0,1(positions[0],positions[1]), 后轮索引2,3
```

### Tire Visual Steering
For visible front wheel steering, mark wheel groups with userData:
```typescript
wg.userData.isWheel = true;
wg.userData.isFront = pos[2] > 0;  // Z+ direction = front (after Rx(-90°))
```
Then in the physics update loop:
```typescript
this.playerCar.children.forEach((child) => {
    if (child.userData?.isWheel && child.userData?.isFront) {
        child.rotation.y = this._steerVisualAngle;
    }
});
```

## Vehicle Physics — Production-Grade Racing Model

### Core Principle: Friction Circle / Friction Ellipse

Every tire generates its maximum grip as a **total friction force**: `F_max = mu × Fz` (mu=friction coefficient, Fz=normal load on that tire).

This total friction is SHARED between longitudinal (acceleration/braking) and lateral (cornering) forces:
```
Fx² + Fy² ≤ (mu × Fz)²
```

**Implementation in Update() loop:**
1. Calculate max friction per wheel: `maxFriction = mu * mass * g / 4` (static weight distribution)
2. Compute drive force from engine torque: `F_drive = engineTorque * gearRatio * FD * efficiency / wheelRadius`
3. Clamp drive force to `maxFriction` per driven wheel (otherwise free-spin/sliding)
4. Compute brake force: `F_brake = brakeValue * mu * mass * g` (all 4 wheels brake)
5. Net longitudinal force: `F_long = F_drive - F_brake`
6. For lateral forces: remaining friction = `sqrt((mu*Fz*4)² - F_long²)` → this is the max cornering force available
7. Calculate lateral sliding velocity, apply lateral deceleration up to remaining friction limit

**CRITICAL**: If you exceed the friction circle (too much power + too much steering at the same time), the tire loses grip completely — this is the real behavior. Do NOT separately calculate acceleration and cornering forces without considering the shared friction budget.

### Engine Model (BMW M3 E46 S54B32 base)
```typescript
ENGINE_MAX_TORQUE_NM = 365;     // @4900rpm
ENGINE_MAX_RPM = 8000;          // redline
ENGINE_IDLE_RPM = 800;
DRIVETRAIN_EFFICIENCY = 0.85;   // 15% loss
```

**Torque Curve** (5-segment — critical for realistic feel):
1. **Idle zone** (0-5%): 65% torque — clutch engagement
2. **Low-RPM climb** (5-35%): 65%→108% — turbo spool / cam engagement
3. **Torque plateau** (35-70%): 108% sustained — peak @ 4900rpm (~57% normalized)
4. **High-RPM drop** (70-90%): 108%→83% — power peak zone
5. **Redline cliff** (90-100%): 83%→50% — fuel cutoff imminent

### Gear Ratios (M3 E46 Getrag 420G 6MT)
```
[4.23, 2.53, 1.67, 1.23, 1.00, 0.83], FINAL_DRIVE = 4.10
WHEEL_RADIUS = 0.33m  // 255/40R18
```
Auto-shift: upshift at 7500rpm, downshift when rpm < 1500 and speed > 2m/s

### Acceleration Physics Chain
```
engineTorque × gearRatio × FD × efficiency
  → wheelTorque → driveForce / wheelRadius
    → F = ma → limited by tire grip (mu × Fz)
      → slipRatio control → TCS intervention
```

### Tire Model — Pacejka Magic Formula
**Longitudinal (acceleration/braking):**
```typescript
mu_x = TIRE_PEAK_MU × gripMultiplier × (1 - loadSensitivity × ln(Fz / Fz0))
mu_peak = 1.05 (UHP summer tire), loadSensitivity = 0.08
```

**Lateral (cornering) — full Magic Formula with E term:**
```typescript
B = 9; C = 1.3; D = mu_peak; E = -0.3;
Bx = B × slipAngle_deg;
Fy = D × Fz × sin(C × atan(Bx - E × (Bx - atan(Bx)))) × gripMultiplier;
```
- E = -0.3 creates the characteristic peak-and-drop shape
- B=9 gives realistic cornering stiffness (~90N/deg per kN load)

### Steering — Ackermann + Bicycle Model
```
steerAngle = sign(input) × |input| × (0.2 + input² × 0.8) × STEER_MAX_ANGLE (0.52rad≈30°)

frontSlipAngle = vehicleSlipAngle + steerAngle  // front wheel points where driver steers
rearSlipAngle = vehicleSlipAngle                // rear wheels don't steer

yawMoment = Fy_front × a × cos(sw) - Fy_rear × b
  → yawRate += (yawMoment - damping × yawRate) / inertia × dt
    → playerAngle += yawRate × dt

lateralVelocity += (lateralAccel - yawRate × speed - 6 × lateralVel) × dt
```

### Brakes — Friction-Based NOT Fixed Decel

**Brake force must be derived from tire friction, NOT a hardcoded deceleration value.** Otherwise the car stops identically at 200km/h and 20km/h, which is unrealistic.

```typescript
// CORRECT: brake force derived from tire friction
const fzPerWheel = mass * g / 4;
const maxFrictionPerWheel = mu * fzPerWheel;
brakeForceLong = brakeValue * maxFrictionPerWheel * 4;  // all 4 wheels braking
// Speed-dependent modulation (anti-lock brake simulation):
if (currentSpeed < 5) {
    brakeForceLong *= currentSpeed / 5;  // linear fade below 5m/s
}
```

```typescript
// WRONG: hardcoded deceleration
const brakeDecel = brakeValue * 15.0 * dt;  // ← wrong! ignores speed, mass, mu
```

**CRITICAL rules for brake force calculation:**
1. **Brake shares the friction circle with lateral forces** — braking hard reduces cornering ability and vice versa
2. **Low-speed fade** — at speeds < 5m/s, brakes should fade linearly to 0 to prevent sudden stop jitter at very low speeds
3. **Anti-lock**: without ABS simulation, brake force at max = wheel lock. With ABS, limit to ~90% of max friction per wheel
4. **Weight transfer** (advanced): braking shifts weight forward → front wheels get more grip, rears less. Implement as `fzFront = fzPerWheel + mass * decel * CG_height / wheelbase / 2`

### Steering — Sign Convention

**CRITICAL**: `steerAngle` sign needs to be INVERTED relative to `steeringValue`:
```typescript
const steerAngle = -this.steeringValue * this.maxSteeringAngle;
//                 ^-- NEGATIVE! Positive steeringValue = right input = positive yawRate
// But Three.js positive yaw = counter-clockwise = left turn
// So invert: positive input → negative steerAngle → negative yawRate = right turn (clockwise)
```

**Matching visual steering** — front wheels must turn in the same direction:
```typescript
this._steerVisualAngle = -this.vdriftPhysicsFull.steeringValue * this.vdriftPhysicsFull.maxSteeringAngle;
```

### Acceleration — Engine Torque Based (No Artificial Drag Factor)

```typescript
const engineTorque = this.engine.getTorque();  // already varies with RPM via torque curve
const gearRatio = this.transmission.GetCurrentGearRatio() * 
    this.differential[2].finalDrive * this.differential[1].finalDrive;
const wheelForce = engineTorque * gearRatio * 0.85 / this.wheel[0].radius;
const accel = wheelForce / this.mass * driveWheelRatio;  // ~0.5 for RWD
// NO artificial dragFactor! Speed naturally limits at equilibrium with aero drag + rolling resistance
```

**DO NOT add `dragFactor = max(0, 1 - speed/limit)`** — this makes acceleration unrealistic. Instead:
- Air resistance (`0.5 * rho * Cd * A * v²`) naturally limits top speed
- Rolling resistance (`rr * g`) adds small constant drag
- Engine torque curve naturally drops at high RPM (after torque peak)

### Forward Motion Direction — Camera-Physics Consistency

After vertex transform `(x, z, -y)` where y- = forward:
- newZ = -(-extreme_y) = +extreme_y → **car visual heading is Z+**
- Physics forward must match: `this.velocity.z -= accelLong * dt` (moving in Z- direction, which is backwards)

**Wait — verify this!** The vertex transform makes the car model visually point Z+, but the physics drives it in Z- direction. This means visual Z+ ≠ physics Z+. Fix by:
```typescript
// Physics forward: Z- (car model visually points Z+ but drives Z-)
this.velocity.z -= accel * dt;  // W key = velocity.z decreases = car moves Z-

// Visual rotation - atan2 returns angle relative to Z+, but car faces Z-
// So negate the angle: 
this.playerAngle = -Math.atan2(this.vdriftPhysicsFull.velocity.x, this.vdriftPhysicsFull.velocity.z);
```

**Camera must match:**
```typescript
// Car heading Z-, camera behind = Z+ direction (offset behind car)
const behind = new THREE.Vector3(
    -Math.sin(-carAngle) * dist,  // negate carAngle since visual angle was flipped
    camHeight,
    Math.cos(-carAngle) * dist   // +cos because car faces Z-, camera behind = more negative Z
);
```

### Mouse Look / Pivot Arm Camera (BEST)

The pivot arm camera eliminates the forward direction confusion entirely — the camera position is always relative to the car's physics body, and the camera always looks at the car center. Forward direction is simply whatever direction the car model points:
```typescript
const pivot = new THREE.Object3D();
pivot.position.copy(carPosition);
// Y-axis rotation = car's visual heading (atan2(tangent.x, tangent.z) or whatever produces correct forward)
pivot.rotation.y = carVisualAngle;
camera.position.set(0, height, -distance);  // behind the pivot
camera.lookAt(0, 0, 0);  // look at pivot center = car
```

This approach detaches the camera's local "behind" concept from the global coordinate system entirely.

### Aerodynamics
```typescript
CD = 0.32;          // M3 E46 drag coefficient
FRONTAL_AREA = 2.12; // m²
AIR_DENSITY = 1.225; // kg/m³
dragForce = 0.5 × ρ × Cd × A × v²
dragDecel = dragForce / mass  // ~700N @ 200km/h → 0.47m/s²
```

### Suspension (Equivalent Single-Wheel Model)
```typescript
SPRING_FRONT = 55000 N/m  (55 N/mm — performance street)
SPRING_REAR = 50000 N/m
DAMP_BUMP_FRONT = 1800 N-s/m
DAMP_REBOUND_FRONT = 3000 N-s/m  // ~1:1.7 bump:rebound
ANTI_ROLL = 20000 N-m/rad
```

Body roll/pitch from moments:
```
rollMoment = lateralAccel × mass × CG_height
  → rollAngle = rollMoment / rollStiffness (max ±0.3rad ≈ ±17°)
pitchMoment = driveForce × CG - brakeForce × CG
  → pitchAngle = pitchMoment / pitchStiffness (max ±0.15rad ≈ ±8.5°)
```

## Camera — Third-Person Chase

### Correct Positioning
```typescript
// 车头朝Z+, 车尾在Z-方向
const behind = new THREE.Vector3(
    -Math.sin(carAngle) * dynamicDist,  // Z+方向车头 → 车尾在Z-: 向量(-sin, h, -cos)
    camHeight,
    -Math.cos(carAngle) * dynamicDist
);
```

### Common Mistake
Using `+cos` for Z puts camera in FRONT of the car. Always use `-cos` for rear chase cam.

The `cameraMode` property must be explicitly declared (not accidentally deleted during refactoring) or `cameraMode === 0` always evaluates to false, forcing overhead drone mode.

### Critical: Camera Position Depends on Car Heading
```
If car forward direction = Z+:  behind = (-sin, h, -cos)  ✓
If car forward direction = Z-:  behind = (-sin, h, +cos)  ← must flip!
```

Always verify the actual car heading in the scene before writing camera code. Test by:
1. Place a small cube 2 units in front of the car (z+ direction)
2. Place another 2 units behind (z- direction)
3. W-press: see which cube the car moves toward

## Forward Motion Direction

### Critical: The car's visual heading vs physics forward direction
After vertex transform `(x, z, -y)`:
- VDrift y-方向=车头 → newZ = -(-1.97) = 1.97 → **visual car heading is Z+**
- BUT due to Three.js convention (Z+ points toward viewer by default in many setups), the **physics forward** might need to be Z-
- Always test: does `W` make the speedometer go up AND car visibly move forward?

```typescript
// If car moves backward on W → flip worldDz sign
const worldDz = -cosA * localVx - sinA * localVy;  // Z- forward
// vs
const worldDz = cosA * localVx + sinA * localVy;   // Z+ forward
```

### Matching rotation.y to forward direction
```typescript
// If forward is Z-:
rotation.y = Math.atan2(tangent.x, -tangent.z);

// If forward is Z+:
rotation.y = Math.atan2(tangent.x, tangent.z);
```

Mismatch causes: car visually faces track direction but physics drives it backward → speed goes up but car goes off screen.

## Forward Motion Debugging Protocol

When the user says "car moves backward when I press W" or "direction is wrong", **run the checklist in `references/still-wrong-debug-checklist.md` before making ANY edits.** This file captures every "still wrong" root cause from real sessions.

1. **Determine transformed forward direction mathematically:**
   ```
   VDrift: y-方向=车头 (always verify!)
   After (x,z,-y): newZ = -(-extreme_y) = +extreme_y → Z+ is forward
   After Rx(-90°): (x,z,-y) same mapping
   ```
   
2. **Test with a marker:**
   - Place a visible SphereGeometry at (0, 0.5, +5) and another at (0, 0.5, -5)
   - Press W — which sphere does the car move toward?
   
3. **Adjust physics forward:**
   ```
   If car moves toward Z- sphere → forward = Z-
   Set worldDz = -cosA * speed
   Set rotation.y = atan2(tangent.x, -tangent.z)
   
   If car moves toward Z+ sphere → forward = Z+
   Set worldDz = +cosA * speed
   Set rotation.y = atan2(tangent.x, tangent.z)
   ```

4. **Camera must match:**
   ```
   If forward = Z+: behind = (-sin, h, -cos) → car visible in front of camera
   If forward = Z-: behind = (-sin, h, +cos) → car visible in front of camera
   ```

### CRITICAL: cameraMode Declaration
`cameraMode = 0` (with `= 0` initialization) is absolutely required. If this field is accidentally deleted during a large class rewrite, `this.cameraMode === 0` always evaluates to `false` because `undefined !== 0`, forcing the overhead drone camera branch every time. This happened in this session — the drone cam fix was attempted 3 times, each time editing the camera offset math, when the real problem was a missing initialization.

**When refactoring large sections of a class, always grep for all references to the remaining fields AFTER the refactor is complete.** A TypeScript compiler won't catch missing fields if they're initialized via assignment (`this.foo = bar`) rather than declaration (`private foo = bar`) elsewhere.

## Forward Motion Debugging Protocol

When the user says "car moves backward when I press W" or "direction is wrong", **stop editing the physics engine** and run this checklist first:

### Step 1: Verify model forward direction
```python
# Open the JSON model file
verts = data['verts']
# Ground-level vertices where z≈0 (VDrift Z-up = ground)
ground = [(verts[i], verts[i+1], verts[i+2]) for i in range(0, len(verts), 3) 
          if 0 < verts[i+2] < 0.15]
# Find which y-extreme has higher z-values (engine hood = higher z)
y_plus_maxz = max(v[2] for v in ground if v[1] > 0)
y_minus_maxz = max(v[2] for v in ground if v[1] < 0)
# Higher z-side = front of car
```

### Step 2: Determine transformed direction
```
After (x,z,-y) transform:
  If y- = front: newZ = -(-extreme_y) = +extreme_y → car points Z+
  worldDz = +cosA * speed → W moves forward
  
  If y+ = front: newZ = -(extreme_y) = -extreme_y → car points Z-
  worldDz = -cosA * speed → W moves forward
```

### Step 3: Apply consistent sign to ALL dependent systems
When you change the forward direction, you MUST update ALL of these together:
1. `worldDz` sign in `updatePlayer`
2. `rotation.y = atan2(tangent.x, ±tangent.z)` in `createPlayerCar` and `createAICars`
3. `behind.z` sign in `updateCamera`
4. `ai.z +=` sign in `updateAI`
5. `targetAngle = atan2(dx, ±dz)` in `updateAI`

**NEVER change just one of these. All five must agree.**

### Step 4: Verify with markers
Add visible sphere markers to visually confirm direction before telling the user to reload.

## CRITICAL: Preventing GameLoop Death — The #1 Black Screen Root Cause

**The single most common cause of "black screen with HUD" is a silently crashing gameLoop.** The `requestAnimationFrame` callback throws an uncaught exception → animation loop permanently stops → WebGL stops rendering → user sees black canvas with HUD overlays.

### The Three Silent Killers

1. **Undefined constants used in updateAudio()** — `ENGINE_IDLE_RPM` and `ENGINE_MAX_RPM` not declared → `(rpm - undefined) / (undefined - undefined) = NaN` → AudioParam.value = NaN → TypeError → gameLoop dies. **Fix**: declare all audio constants as class properties with values.

2. **Missing function calls** — `this.playCollisionSound()`, `this.distanceToTrack()` called but never defined. One call in updatePlayer → gameLoop dies forever.

3. **Any throw in updatePlayer/updateAudio/updateCamera** — NaN propagation, undefined property access, or AudioParam.setValueAtTime with Infinity.

### Diagnostic Protocol

When user says "black screen, HUD only":

1. Open browser console — look for **any** error (even empty `""` exceptions)
2. Call `window.game.gameLoop()` directly — catches the actual exception with stack trace
3. Check `window.game.renderer.info.render.calls` — if 0, gameLoop isn't running
4. Check `window.game.clock.elapsedTime` — if 0, gameLoop isn't running
5. Manually call `renderer.render(scene, camera)` — if it produces 200+ calls, rendering works → problem is in gameLoop

### Prevention (MANDATORY)

**Every function called from gameLoop must be wrapped in try-catch or have ALL throwable paths protected:**

```typescript
private updateAudio(delta: number): void {
    if (!this.engineOsc || !this.engineGain || !this.engineFilter) return;
    try {
        // ... audio calculations ...
    } catch(e) {
        console.warn('🔇 Audio error:', e);
        // gameLoop continues!
    }
}
```

**DO NOT assume that a compile-time check catches all runtime issues.** TypeScript `@ts-nocheck` files, `any` typed variables, and template literals don't catch missing constants or undefined methods until runtime.

### The Complete Black Screen Diagnostic Flowchart

```
                    User says "black screen, only HUD"
                               |
                    Open browser console, check errors
                               |
                    Has JS error? ──Yes──→ Fix the error
                       |                       |
                       No                  Has "still wrong"?
                       |                   3+ times?
                    Check elapsedTime          |
                       |                   Read references/
                 elapsed > 0? ──No──→     still-wrong-debug-
                       |                   checklist.md
                       |
                       Yes
                  Check render calls
                       |
               calls > 0? ──No──→ Manual render test:
                       |             renderer.render()
                       |             calls still 0?
                       Yes              │
                       │              WebGL context lost
                  Check WebGL context   or renderer destroyed
                       |
                Check playerCar.position
                       |
            isNaN(x) or isNaN(z)? ──Yes──→
                       |             Physics position = NaN
                       |             Check: physics.position was set?
                       |             Check: initVDriftPhysics called
                       No             before createPlayerCar?
                       |
                  Check scene children
                  for visible meshes
```

### Known Crash-Inducing Patterns

1. **Missing model file** — `fetch('dist/models/XXX.json')` returns 404 → `await response.json()` throws → gameLoop never starts. **Fix**: wrap model fetch in try-catch, use fallback geometry.

2. **Physics position NaN cascade** — `vdriftPhysicsFull.position` is never set (undefined) → `physics.position.x = carX` where carX is also undefined → NaN → `carX = physics.position.x` = NaN → `playerCar.position.set(NaN, y, NaN)` → Three.js ignores NaN positions → car invisible. **Fix**: initialize carX/carZ BEFORE initVDriftPhysics(), AND set physics.position in initVDriftPhysics.
   ```typescript
   // Sequence MUST be:
   this.carX = CIRCUIT_START_X;  // init before anything
   this.carZ = CIRCUIT_START_Z;
   this.initVDriftPhysics();  // sets physics.position from this.carX/Z
   this.createPlayerCar();    // uses this.carX/Z for playerCar.position
   ```

3. **Deleted class properties during refactoring** — `cameraMode`, `playerOffset` etc. get accidentally removed when rewriting large sections. Always grep for remaining references after a big rewrite. (undefined === 0 is always false, forcing the wrong camera branch.)

2. **Wheel in wrong parent group** — If bodyGroup has rotation.x = -PI/2, wheels must be added to the OUTER group (passed as the `group` parameter), NOT bodyGroup. The `addWheelsToCar` function must use its parameter name consistently internally. `ReferenceError: group is not defined` means the function signature changed but internal references weren't updated — fix the internal reference, not the call site.

3. **THE BODYGROUP TRAP (session-killer)** — The pattern of using `bodyGroup.rotation.x = -PI/2` + wheels in bodyGroup is fundamentally broken for wheel positioning. **Solution: DO NOT use bodyGroup at all.** Use vertex data transform `(x, z, -y)` on raw vertex arrays, keep the outer group unrotated, and add wheels directly to group. This eliminates the entire class of bugs around wheel Y-coordinate misalignment.

   - bodyGroup rotation Rx(-90°) warps local y-coordinates to world z-coordinates → wheel y=0.06 becomes world z=-0.06
   - After vertex transform, world y=0.06 IS world y=0.06 — wheel position is unambiguous
   - Normals must also be transformed identically to vertices, or lighting breaks

4. **addWheelsToCar parameter protocol (CRITICAL: prevents ReferenceError crash)** — The function `addWheelsToCar` is called from both `buildVDriftCar` (passes `group`) and `buildFallbackCar` (passes `group`). The function signature and ALL internal references must use the same parameter name. If the parameter is named `parentGroup`, every internal reference to `wheelParent` must use `parentGroup`, not `group`, not `bodyGroup`.

   ```typescript
   // CORRECT pattern:
   private addWheelsToCar(parentGroup: THREE.Group, accentColor: number): void {
       const wheelParent = parentGroup;  // ← must match parameter name!
       ...
       wheelParent.add(wg);
   }
   
   // Call sites:
   // buildVDriftCar: this.addWheelsToCar(group, accentColor);  // ← group is the outer group
   // buildFallbackCar: this.addWheelsToCar(group, accentColor);
   ```

   The specific crash symptom: `ReferenceError: group is not defined` at `addWheelsToCar` — this happens when the parameter was renamed (e.g., from `group` to `bodyGroup` to `parentGroup`) but `const wheelParent = group;` was never updated.

5. **Post-rewrite validation protocol** — After any large code rewrite involving physics constants, class properties, or function signatures, ALWAYS run:
   ```
   grep -n "let torqueCurveValue\|const engineTorqueNm\|let driveForceApplied\|const frontLoadWithAero\|const rearLoadWithAero" src/PlushRacingGame.ts
   ```
   Each variable must appear EXACTLY once. Also grep for deleted constant names like `TIRE_PEAK_LONGITUDINAL_MU`, `TIRE_PEAK_LATERAL_MU` — if any remain, they cause runtime crashes that produce NO build error and NO visible error (just black canvas).

3. **Brake disc rotation — the single most common visual error**:
   - Correct: disc.rotation.z = PI/2 — disc face perpendicular to wheel axis (X-axis)
   - Wrong: disc.rotation.x = PI/2 — disc lies flat like a pancake
   - Same rule applies to hub.rotation (CylinderGeometry) and outerRing.rotation (TorusGeometry)

4. **Car moves backward on W — immediate debug protocol**:
   - Check if user says car moves backward with speed going up, or car is facing wrong way with speed going up
   - If speed goes up AND car moves backward: flip worldDz sign AND camera behind.z sign
   - If car facing wrong direction: flip atan2(tangent.x, ...) sign AND camera behind.z sign
   - NEVER just flip worldDz without also fixing camera or you fix motion but break camera

5. **Unexpected vehicle direction** — Always verify VDrift which end is front by inspecting vertex data before coding transforms. Default hypothesis should be y-方向=车头 (y-negative is forward in VDrift), but always verify with actual data analysis.
2. **Camera `+cos` vs `-cos` error** — With car heading Z+: camera behind should be `(-sin, h, -cos)`. Using `+cos` puts camera in front → overhead chase view.
3. **`cameraMode` declared but never initialized to 0** — A missing `= 0` default means `cameraMode === 0` always false, falling through to drone mode.
4. **Wheel placement outside wheel arches** — Placing wheels at the model's extreme Z values (z=1.97, z=-1.89) puts them at the front/rear bumper, not under the wheel arches. Always read vertex data to find the wheel arch position (not the body extreme). For ATT: wheel arch at y≈±1.5, not y≈±1.97. After transform: z=1.53 (front), z=-1.49 (rear), not z=1.97/z=-1.89.
5. **Forward direction mismatch** — After (x,z,-y) transform where y- is forward, always test with W-press before wiring camera. See `references/still-wrong-debug-checklist.md`.
6. **Auto-shift threshold too high** — 7500rpm redline shift feels sluggish. 1→2 shift at 5500rpm, 2+ at 6200rpm for street cars.
7. **RPM simulation decoupled from speed** — at idle+full throttle with no roll speed, RPM must climb fast (clutch slip simulation).
8. **Wheel geometry rotation chaos** — All wheel sub-geometries should use `rotation.z = PI/2` to align with the X-axis (wheel rolling axis). See `references/wheel-geometry-threejs.md`.
9. **Brake disc rotation** — Use `rotation.z = PI/2`. `rotation.x = PI/2` makes the disc lie flat like a pancake.
10. **Multiple "still wrong" rounds** — When the user says "still wrong" 3+ times, STOP editing the same code. The problem is in a DIFFERENT place. Run `references/still-wrong-debug-checklist.md`.
11. **Post-refactor audit for deleted fields** — After any large rewrite of class member declarations (especially around `private cameraMode`, `private playerOffset`, physics constants), grep for all remaining references to verify they still have declarations. `undefined !== 0` is always true and silently breaks conditional branches.
12. **Check for duplicate variable declarations after in-place rewrites** — When you patch-replace a code block (e.g., torque curve), the old block can survive. Always grep for `let torqueCurveValue`, `const engineTorqueNm`, `const wheelTorqueNm`, `let ratio`, `const driveForceN`, `let driveForceApplied` after any engine/transmission rewrite. Each must appear exactly once.
13. **Check for deleted variable references after physics simplification** — After removing `TIRE_PEAK_LONGITUDINAL_MU`, `TIRE_PEAK_LATERAL_MU`, `TIRE_LOAD_SENSITIVITY`, `AIR_DENSITY`, `CL_FRONT`, `CL_REAR`, grep for each of these names. ANY remaining reference causes runtime crash that produces NO error in the build (just a black canvas with "game started" logs).

14. **addWheelsToCar parameter chaos** — The function signature `addWheelsToCar(bodyGroup: THREE.Group, ...)` with `const wheelParent = group;` inside is a crash waiting to happen. Always match the internal variable name to the parameter name. When renaming the parameter, rename ALL references inside the function body too. This `ReferenceError: group is not defined` bug persisted through multiple builds despite the patch to fix the call site, because the internal reference was never updated.
