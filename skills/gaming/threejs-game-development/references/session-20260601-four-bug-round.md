# Session 2026-06-01: Four simultaneous bug round

## Bugs fixed

1. **Model distortion ("一团黑乎乎乱的几何体")**
   - Root cause: convert_v8.py assumed JOE Face vertex indices were local (`fi*3+{0,1,2}`). They are GLOBAL indices pointing directly into the verts array.
   - Fix: convert_v9.py — use global indices directly, add vertex cleanup (filter out coords > 100)
   - Result: XS went from 2343v to 573v (correct)

2. **gameLoop crash -> blank screen ("只有HUD没有场景")**
   - Root cause 1: `ENGINE_IDLE_RPM` (850) and `ENGINE_MAX_RPM` (7200) constants never defined → `undefined-undefined=NaN` → AudioParam got NaN → TypeError → gameLoop stops
   - Root cause 2: `playCollisionSound()` and `distanceToTrack()` called but never defined → TypeError → gameLoop stops
   - Root cause 3: `lateralOffset`/`trackRight`/`normalDir` variables deleted by previous patch but remaining code referenced them
   - Fix: add constants, wrap updateAudio in try-catch, remove all calls to undefined functions

3. **Rear-wheel steering / wrong turn direction**
   - Root cause: wheelPositions data is in (x, z_vertical, y_longitudinal) format, NOT (x,y,z) or raw VDrift. Applied wrong coordinate transform.
   - Fix: `wg.position.set(pos[0], pos[1], -pos[2])` — preserves x, uses z as height, negates y for Z- forward
   - isFront detection: use `idx < 2` (first two entries are front) instead of coordinate-based detection
   - A/D input mapping: `A→-1, D→1` (was reversed)

4. **Slow acceleration / weak brakes**
   - Root cause: ad-hoc `dragFactor` capped thrust too early, fixed brake deceleration 15m/s² was too low
   - Fix: friction circle model (mu * m * g per wheel), brake force = brakeValue * 4 * mu * m * g/4, thrust limited by tire friction, aero drag squared, rolling resistance linear
   - User explicitly demanded physics-based force model over constant deceleration multipliers

5. **Wheel assembly orientation (tire/rim/disc misaligned)**
   - Root cause: `rotation.x = PI/2` (wrong) vs `rotation.z = PI/2` (correct) fought across multiple rounds
   - Fix: wheelGroup wrapping all components with `rotation.z = PI/2`, disc.position.y instead of .z

## Correct wheelPositions coordinate transform

Data format: `[x_leftright, z_vertical, y_longitudinal]` where z=up and y=front in original VDrift
- Three.js: `wg.position.set(pos[0], pos[1], -pos[2])`
- Front/rear detection: `isFront = idx < 2` (first two entries in every car's wheelPositions array are front)

## Debugging sequence for blank screen
1. Check `g.vdriftPhysicsFull.engine.getRPM()` — engine alive?
2. Check `g.vdriftPhysicsFull.getSpeed()` — any movement?
3. Manual: `p.SetThrottle(1); p.Update(0.016); p.getSpeed().toFixed(4)`
4. If no movement: check thrust code runs (console.log throttle before/after), check position integration doesn't override velocity
5. Check gameLoop: `g.clock.elapsedTime` — if 0, gameLoop is NOT running
6. Catch gameLoop errors: `try { g.gameLoop() } catch(e) { e.message }`
7. Check rendering: `g.renderer.info.render.calls > 0` after manual `g.renderer.render(g.scene, g.camera)`
