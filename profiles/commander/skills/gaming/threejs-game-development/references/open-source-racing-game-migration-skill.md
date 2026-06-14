---
name: open-source-racing-game-migration
description: Migrate physics, vehicles, tracks, and handling from open-source racing simulators (VDrift, Speed Dreams, Rigs of Rods) into a custom game engine. NOT about writing physics from scratch — always reference existing proven implementations.
---

# Open-Source Racing Game Migration

## Core Principle
**Never invent physics. Always migrate from proven open-source racing sims.** VDrift's complete physics engine (cardynamics.cpp, carengine.h, cartire2.cpp, carsuspension.cpp, cartransmission.h) is available and battle-tested. Use it directly.

## Sources (in priority order)
1. **VDrift** (GPL) — Most complete: Pacejka tire model, real transmission, suspension, aero
2. **Speed Dreams** (GPL) — Fork of TORCS, good track models (.ac/.3ds format)
3. **Rigs of Rods** (GPL) — Soft-body physics, complex terrain

## Migration Workflow

### 1. Vehicle Model Coordinate System
VDrift coordinate system: `x=left-right, y=front-back (y+=front), z=up-down`
To convert to Three.js Y-up: `newPos = (x, z, -y)` — transform vertex data directly, **DO NOT use group.rotation**

**CRITICAL: Never set `playerCar.rotation.x` or `rotation.z` in update loop** — this overwrites the vertex transform. Only set `rotation.y`.

### 2. Wheel Position Extraction
- From model vertex data: find ground-contact points (minimum z), separate into front (y>0) and rear (y<0)
- Wheel center y = ground_z + tire_radius
- Convert to world: `(x_from_model, ground_z + radius, -y_from_model)`
- Each car model MUST have its own wheel positions — do not use one-size-fits-all

### 3. Physics Migration (from VDrift source)
Files in `vdrift/src/physics/`:
- `carengine.h` — Torque curves, RPM limits
- `cartransmission.h` — Gear ratios, final drive
- `cartire*.h/cpp` — Pacejka Magic Formula (tire 2 or 3)
- `carsuspension.h/cpp` — Spring/damper/anti-roll
- `carbrake.h` — Brake torque model
- `cardynamics.cpp` — Main integration loop

### 4. Track Data
GPS-based real circuits via OpenStreetMap:
- GPS to XY: `x = (lon - centerLon) * 111320 * cos(centerLat * PI/180)`, `z = (lat - centerLat) * 111320`
- Each real track needs 15+ waypoint turns from OSM/Wikipedia
- Add CatmullRom interpolation between waypoints

### 5. Camera
Fixed distance behind car: `dist=5m, height=2.5m`. Smooth lerp, no dynamic distance scaling.
Camera look-ahead: 3m in front of car, 0.5m above.

## Pitfalls
- **DO NOT use group.rotation for Z-up→Y-up** — it breaks all child object coordinates. Transform vertex data instead.
- **DO NOT set rotation.x/z on playerCar** — this overwrites the vertex transform
- **DO NOT simplify** — user explicitly banned simplified/placeholder implementations
- **DO work locally** — all file modifications must be on local filesystem, not through browser
- **DO NOT guess physics parameters** — extract from VDrift .car config files or real vehicle specs
- **Each car has unique wheelbase and track width** — extract from model vertex data, do not share values

## User Quality Standards (from direct feedback)
- "禁止简单模拟，禁止精简实现，禁止批量实现，禁止降级实现"
- Complete migration, not partial adaptation
- Every vehicle must have real dimensions matching its model
- Real telemetry: torque curves, gear ratios, suspension rates
