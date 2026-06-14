# Racing Game: Vehicle Selection + Tier Switch System

> Implementation notes from PlushRacingGame session (2026-05-29)

## Tier Switch Architecture

Implement vehicle tier switching as a lightweight system within the game engine, without loading 130 separate config files at runtime.

### Core Data Structure

```
T1 (Score 10):  T1 小钢炮 — low speed, nimble handling
T2 (Score 30):  T2 跑车 — balanced performance  
T3 (Score 50):  T3 超跑 — high performance supercar
T4 (Score 70):  T4 赛车 — GT/Formula track weapon
T5 (Score 90):  T5 原型车 — ultimate hypercar/prototype
```

### 6-Dimension Performance Profiles (per tier)

Each tier has hand-tuned 6-dim scores that differ from the simple median:

```
T1: { speed:12, accel:8,  handling:15, braking:10, downforce:5,  durability:10 }
T2: { speed:28, accel:25, handling:35, braking:30, downforce:28, durability:32 }
T3: { speed:55, accel:48, handling:52, braking:53, downforce:48, durability:45 }
T4: { speed:72, accel:75, handling:68, braking:70, downforce:72, durability:62 }
T5: { speed:92, accel:90, handling:88, braking:91, downforce:92, durability:85 }
```

### Score-to-Physics Mapping

```
MAX_SPEED   = 70 + (avg - 50) * 0.4     // base 70 m/s
ACCEL       = 25 + speed * 0.08          // base 25 m/s²
STEER_SPEED = 2.5 + handling * 0.015     // base 2.5 rad/s
BRAKE_FORCE = 35 + braking * 0.08        // base 35 m/s²
```

### Key Binding

- **V key**: cycle through T1→T2→T3→T4→T5 (in-game)
- Menu "选择车辆" button: opens clickable card selector with tier information, highlighting current selection
- Visual notification on switch (2-sec fade-out overlay with tier name, color, score)

### Pitfalls

- DO NOT try to load all 130 VehicleConfig files at runtime for the selector — use the lightweight 5-tier profile instead
- DO apply the tier change to `vehicleScore` AND call `applyScoreToPhysics()` immediately
- DO NOT forget to reset `aiPhysicsState` when switching circuits (otherwise AI cars teleport to old positions)
- VehicleData.ts `registerFromDirectImport()` has a hardcoded file list — if batch files are added, update this list or they won't register
