# VDrift Physics Engine Full Migration (2026-05-31 session)

## Overview

Complete VDrift physics engine TypeScript port + multi-module migration.
All modules compiled, integrated into PlushRacingGame.ts, and verified working.

## Architecture: 6 Modules

```
src/
├── physics/VDriftPhysicsFull/    ← 14 files, 2264 lines (CORE PHYSICS)
│   ├── DriveShaft.ts             传动轴基础单元
│   ├── Spline.ts                 Catmull-Rom样条插值(扭矩曲线)
│   ├── CarEngine.ts              完整发动机(Heywood摩擦+NOS)
│   ├── CarTransmission.ts        变速箱(前进/倒挡)
│   ├── CarClutch.ts              离合器
│   ├── CarBrake.ts               刹车(制动力分配+手刹)
│   ├── CarDifferential.ts        差速器(LSD 1way/1.5way/2way)
│   ├── CarWheel.ts               车轮
│   ├── CarTire.ts                Pacejka完整Magic Formula轮胎
│   ├── CarSuspension.ts          悬架(弹簧+阻尼+防倾杆)
│   ├── Driveline.ts              传动系统(MotorJoint+ClutchJoint+2WD/4WD)
│   ├── CarDynamics.ts            主车辆动力学(完整集成TCS/ABS/空力)
│   ├── CarConfigs.ts             13辆VDrift车型真实工程参数
│   └── index.ts                  导出入口
├── ai/VDiftAICar.ts              ← 1 file, 212 lines (AI)
│   VDrift AI: 赛道跟随+制动点+曲率估计+速度控制
├── effects/                      ← 4 files, 693 lines (EFFECTS)
│   ├── DriftSystem.ts            飘移系统(角累积+抓地力+得分+连击)
│   ├── EffectsSystem.ts          粒子系统(烟雾/火花/排烟/轮胎痕迹)
│   ├── WeatherSystem.ts          天气系统(4种天气+昼夜+雨粒子+闪电)
│   └── CameraSystem.ts           多视角相机(5种模式:追尾/发动机盖/俯视/环绕/TV)
└── tracks/RealTracks.ts          ← 1 file, 191 lines (TRACKS)
    Speed Dreams 9赛道数据+程序化生成+普锐赛特赛道
```

## Integration into PlushRacingGame.ts

All 6 modules imported + initialized in initFullScene() + updated in gameLoop():

```typescript
// Import (line 10-16)
import { VDiftAICar, ... } from './ai/VDiftAICar';
import { DriftSystem } from './effects/DriftSystem';
import { EffectsSystem } from './effects/EffectsSystem';
import { WeatherSystem, Weather } from './effects/WeatherSystem';
import { CameraSystem, CameraMode } from './effects/CameraSystem';
import { VDRIFT_TRACKS, PRESET_TRACKS, ... } from './tracks/RealTracks';

// Init (in initFullScene, before initMinimap)
this.driftSystem = new DriftSystem();
this.effectsSystem = new EffectsSystem(this.scene);
this.weatherSystem = new WeatherSystem(this.scene, ambient, dirLight);
this.cameraSystem = new CameraSystem(this.camera);
this.currentTrack = PRESET_TRACKS[trackIdx] || generateProceduralTrack(4, 100, 14);

// Update (in gameLoop, playing state)
this.driftSystem.update(delta, speed, steer, handbrake, latAccel, grip);
this.effectsSystem.emitSmoke/emitExhaust/emitSparks(...);
this.weatherSystem.update(delta);
this.cameraSystem.update(delta, carPos, carAngle, speed);
```

## Keyboard shortcuts added
- X: cycle weather (Clear/Cloudy/Rain/Night)
- C: cycle camera modes (Chase/Hood/TopDown/Orbit/TV)

## Source games analyzed for migration

| Source | Files | Lines | What was taken |
|--------|-------|-------|----------------|
| VDrift cardynamics.cpp/h | 1977 | ~60K | Full physics engine (engine/clutch/trans/diff/tire/susp/brake/driveline/aero/TCS/ABS) |
| VDrift ai_car_standard.cpp/h | ~500 | ~15K | AI racing line follower |
| racing_v2/index.html | 1 | 69K | Drift indicator, smoke particles |
| racing_v3/index.html | 1 | 53K | Hill terrain, street lights |
| racing_v4/index.html | 1 | 50K | Multi-camera modes, race stats |
| racing_final/index.html | 1 | 48K | Checkpoints, opponents |
| racing_final_v2/index.html | 1 | 47K | Combined features |
| Speed Dreams tracks | 9 | 785K .xz | Track data |
| VDrift data/tracks | 9 .trk files | - | Track geometry |

## Critical bugs encountered

1. **Webpack tree shaking removes modules** — `optimization: { sideEffects: false, usedExports: false }` in webpack.config.js. Development mode retains all modules (72 KiB for physics alone). Production mode strips new modules completely.

2. **DriftSystem init fails silently** — `new DriftSystem()` returns undefined when module loading partly fails. Wrap in try-catch block. Root cause was webpack dev mode module caching — clean `dist/` and restart server.

3. **Camera `updateCamera()` vs `cameraSystem.update()` conflict** — Both write to `this.camera`. Disable the old `updateCamera()` when cameraSystem is active, or let cameraSystem overwrite each frame.

4. **`PRESET_TRACKS.length` called before init** — `currentCircuitIndex` must be initialized before track selection. Moved init block before initMinimap.

5. **Backup required before all edits** — `/mnt/d/Hermes/备份/PlushRacingGame.ts.pre-integration.backup`

## Engine porting completeness

| Feature | VDrift C++ | Old TS | New TS |
|---------|-----------|--------|--------|
| Engine (Heywood+NOS) | ✅ | partial | ✅ complete |
| Clutch | ✅ | ❌ | ✅ |
| Transmission (fwd/rev) | ✅ | partial | ✅ complete |
| Differential (LSD) | ✅ | ❌ | ✅ |
| Pacejka tire (full MF) | ✅ | simplified | ✅ complete |
| 4-wheel independent suspension | ✅ | ❌ | ✅ |
| Anti-roll bar | ✅ | ❌ | ✅ |
| Brake (bias+handbrake) | ✅ | ✅ | ✅ complete |
| Driveline (2WD+4WD) | ✅ | ❌ | ✅ complete |
| TCS/ABS | ✅ | ❌ | ✅ |
| Aerodynamics | ✅ | ❌ | ✅ |
| 13 real car configs | ❌ | ❌ | ✅ |
