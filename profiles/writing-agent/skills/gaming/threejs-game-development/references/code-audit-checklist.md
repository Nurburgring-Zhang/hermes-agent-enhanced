# Racing Game Code Audit Checklist

## Pre-Audit: Full Structure Scan
```
find /path/racing\ game\ package/ -maxdepth 3 -type f | sort
```

Checklist:
- [ ] Multiple version dirs (v2/v3/v4) — legacy HTML prototypes
- [ ] VDrift source repo at `vdrift_data/vdrift/`
- [ ] `dist/models/*.json` — extracted VDrift 3D model files
- [ ] Speed Dreams data (tar.xz)
- [ ] Main game source dir (`src/`)
- [ ] All `@ts-nocheck` annotations (count them — each is a suppressed error)
- [ ] All report/delivery documents (DEVELOPMENT_REPORT.md, etc.)

## Dual-Physics-Engine Diagnosis

### Finding the active physics engine
```bash
# Check if VDriftPhysics is actually used
grep -rn "VDriftCarDynamics\|vdriftPhysics" src/ | grep -v "import\|new\|init\|config"
# If no update() call appears → engine is dead code

# Check the main update loop
grep -n "update\|physics\|step" src/PlushRacingGame.ts | head -30
grep -n "update\|physics\|step" src/engine/GameEngine.ts | head -20

# Check what physics engine GameEngine uses
grep -n "import.*Physics\|new.*Physics" src/engine/GameEngine.ts
```

### Dead code indicators
- [ ] VDriftPhysics imported, instantiated (`new VDriftCarDynamics`) but `vdriftPhysics.update()` NOT called in game loop
- [ ] Main game class has its own `playerSpeed`, `lateralVelocity`, `yawRate` — running SIMPLIFIED physics inline
- [ ] Two Cannon-es wrappers exist (PhysicsEngine.ts AND PhysicsEngine3D.ts) — one may be unused
- [ ] `// @ts-nocheck` on every physics file — no one can maintain them

### 7 Defect Categories (check all)
| # | Defect | Present? | Evidence |
|---|--------|----------|----------|
| 1 | Dead physics code | ☐ | VDriftPhysics instantiated but update() never called |
| 2 | Degraded physics model | ☐ | Single-point bicycle, no 4-wheel/suspension/diff/clutch |
| 3 | Model coordinate wrong | ☐ | Cars face wrong direction, wheels mispositioned |
| 4 | Over-simplified collision | ☐ | Box chassis, no raycast-vehicle |
| 5 | Binary-only input | ☐ | Keyboard 0/1, no linear throttle/brake/controller |
| 6 | Unported C++ source | ☐ | cardynamics.cpp(1977 lines) but TS port <30% |
| 7 | Monolithic class | ☐ | Single file >2000 lines mixing all concerns |

## Model JSON Analysis

```bash
# Check all car models
for f in dist/models/*.json; do
    name=$(basename "$f")
    verts=$(python3 -c "import json; d=json.load(open('$f')); print(len(d.get('verts',[]))//3, d.get('numVerts'), d.get('numTris'))")
    parts=$(python3 -c "import json; d=json.load(open('$f')); print(list(d.get('parts',{}).keys()))")
    echo "$name: verts=$verts parts=$parts"
done
```

## VDrift C++ Source Inventory (to port)

From `vdrift_data/vdrift/src/physics/`:
- [ ] `cardynamics.cpp` (1977 lines) — MAIN: integrate everything
- [ ] `cardynamics.h` (521 lines) — interface
- [ ] `carengine.cpp` + `carengine.h` — torque curve + friction
- [ ] `cartire1.cpp` + `cartire1.h` — Pacejka tire (most accurate)
- [ ] `cartire2.cpp/h` / `cartire3.cpp/h` — alternative tire models
- [ ] `cartirebase.h` — base tire interface
- [ ] `carsuspension.cpp` + `carsuspension.h` — 4-wheel independent suspension
- [ ] `carclutch.h` — clutch slip model
- [ ] `cartransmission.h` — gear ratios + shift
- [ ] `cardifferential.h` — open/LSD/center differential
- [ ] `carbrake.h` — brake model
- [ ] `aerodevice.h` — aerodynamic downforce + drag
- [ ] `driveline.h` — driveline coupling
- [ ] `driveshaft.h` — driveshaft inertia
- [ ] `carwheel.h` — wheel geometry + contact
- [ ] `carwheelposition.h` — wheel position enum
- [ ] `wheelconstraint.h` — wheel constraints

## Migration Effort Estimates
| Phase | Scope | Files | LoC Estimate | Dependency |
|-------|-------|-------|-------------|------------|
| 1 | VDrift Physics Full TS Port | 8-12 | 2500-3000 | None |
| 2 | 4-wheel Cannon-es Integration | 2-3 | 500-800 | Phase 1 |
| 3 | Model Coordinate Fix | 1-2 | 200-400 | Phase 1 |
| 4 | Input System Upgrade | 2-3 | 300-600 | Phase 2 |
| 5 | Track Migration | 2-4 | 500-1000 | Phase 3 |
| 6 | Test Cycle | 1-2 | 200-400 | All above |
