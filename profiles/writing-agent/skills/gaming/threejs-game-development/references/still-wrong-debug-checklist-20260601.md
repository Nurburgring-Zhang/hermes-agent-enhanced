# Still Wrong Debug Checklist (Session 2026-06-01)

## If User Says "Still Wrong" 3+ Times — STOP Editing The Same Code

The problem is in a **DIFFERENT** file or a **COMPLETELY DIFFERENT** root cause.

## Checklist (Run In Order, Each Before Making ANY Edit)

### 1. Model Garbage ("破碎的几何体")

```python
import json
d = json.load(open('dist/models/XXX.json'))
nv = d['numVerts']
mi = max(d['indices'])
print(f'indices max={mi}, nv={nv}, OOB={mi >= nv}')
# If OOB=True: vmap key bug (len(out_verts) vs len(out_verts)//3)
# If OOB=False: vertex transform bug

# Check coordinate ranges:
v = d['verts']
xs=[v[i] for i in range(0,len(v),3)]
ys=[v[i+1] for i in range(0,len(v),3)]
zs=[v[i+2] for i in range(0,len(v),3)]
print(f'x=[{min(xs):.2f},{max(xs):.2f}] y=[{min(ys):.2f},{max(ys):.2f}] z=[{min(zs):.2f},{max(zs):.2f}]')
# Expected: x≈±1(m宽), y≈±0.5(m高), z≈±2(m长)
# If one axis is 0 (e.g., z=[-0.01,0.01]): wrong coordinate transform
```

### 2. Physics Like Skating ("打滑")

This means **lateral grip is not being applied**. Check:

```typescript
// In Update() or updatePlayer():
// 1. Is lateral velocity being computed?
let latVx = this.velocity.x - (this.velocity.x * dx + this.velocity.z * dz) * dx;
let latVz = this.velocity.z - (this.velocity.x * dx + this.velocity.z * dz) * dz;

// 2. Is it being suppressed? Check grip factor:
const grip = 0.95;  // If < 0.8, not enough grip. 0.95+ for race cars.
this.velocity.x -= latVx * grip;
this.velocity.z -= latVz * grip;

// 3. Is the grip code actually EXECUTING?
// Add console.log('grip applied:', latSpeed) and check browser console
```

### 3. Steering Reversed ("按A向右转")

```typescript
// Check ALL THREE places that use steerAngle:
// 1. Physics direction: yawRt = speed * Math.tan(steerAngle) / wheelbase
// 2. Visual rotation: child.rotation.y = this._steerVisualAngle
// 3. Force decomposition: thrustZ = cos(steerAngle) * accel * dt

// If visual turns correctly but car goes wrong way → yawRt sign is wrong
// Fix: steerAngle = -this.steeringValue * this.maxSteeringAngle;
// AND: this._steerVisualAngle = -(same formula);

// Test: press A → car should turn left (counter-clockwise in top view)
// Press D → car should turn right (clockwise)
```

### 4. W Key Off-screen / Speed 300 With No Brakes

```typescript
// Check: is brakeValue being set?
// In CarDynamics.Update(), is brakeValue > 0.01 when S is pressed?
// Check: brakeForce = brakeValue * mu * mass * g;  // Is mu defined?

// The most common bug: brake is in the ELSE branch of if(throttleValue>0)
// Make brake independent of throttle

// Speed 300+ means no air resistance:
// const aeroForce = 0.5 * 1.225 * 0.35 * 2.0 * speed * speed;
// This MUST be applied to velocity every frame.
// Check: is aeroForce calculation using correct speed variable?
```

### 5. Game Loop Died (Black Screen)

```javascript
// In browser console:
window.game.clock.elapsedTime  // >0 means loop runs
window.game.renderer.info.render.calls  // >0 means rendering works

// If elapsed === 0:
try { window.game.gameLoop(); } catch(e) { console.log(e.stack); }
// This reveals the exact exception
```

## Root Cause Patterns After Multiple "Still Wrong"

1. **Deleted class property during refactor** — `cameraMode` missing `= 0` → drone mode always. Fix: grep for ALL class properties after any large rewrite.

2. **Deleted variable references** — After removing physics constants (`TIRE_PEAK_MU`, etc.), grep for remaining references. Any survivor crashes game loop silently.

3. **Duplicate variable declarations after patch** — `const tireShape = new THREE.Shape();` twice → build error that webpack doesn't catch with `@ts-nocheck`.

4. **Patch introduced syntax error** — removing a closing `});` or adding a stray `+` in template literal. Read the patched file, don't trust the patch tool.

5. **Browser cache stale** — Ctrl+F5 not enough. Hard reload with cache disabled (DevTools → Network → Disable cache) or append `?v=timestamp` to script tag.
