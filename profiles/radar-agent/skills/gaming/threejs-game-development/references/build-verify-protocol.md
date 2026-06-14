# Build & Verify Protocol for Racing Game

## After Every `npx webpack`
1. Check output for errors
2. `grep -c 'NewModuleName' dist/bundle.js` — if 0, tree-shaking ate it. Fix: `optimization: { sideEffects: false, usedExports: false }` in webpack.config.js, or use `mode: 'development'`.
3. Kill old http.server: `kill $(pgrep -f 'http.server 8080')`
4. Restart: `python3 -m http.server 8080 --bind 0.0.0.0 &`
5. Verify: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/` should be 200
6. Open browser, click Start Race
7. Check console: 0 JS errors, all 7 systems (drift/weather/camera/effects/track/physics) show 'Y'

## Black Screen Diagnosis
When user reports black screen but HUD is visible:

1. Check server: `curl -s http://localhost:8080/dist/bundle.js | head -c 100`
2. Check window.game: does instance exist?
3. Check car position NaN:
   ```
   browser_console: window.game.playerCar.position.x
   ```
   If NaN → position null cascade (init order bug)
4. Check camera position NaN:
   ```
   browser_console: window.game.camera.position.x
   ```
   If NaN → camera.nan → black screen
5. Check scene has content:
   ```
   window.game.scene.children.filter(c => c.isMesh).length
   ```
   If < 50 → scene was cleared and not rebuilt (switchCircuit bug)
6. Check scene background:
   ```
   window.game.scene.background.getHexString()
   ```
   Should be '1a1a3e' (not '000000')

## Position Null Cascade Fix
The most common black screen root cause:
```
createPlayerCar():
  startPos = trackCurve.getPoint(0)
  initVDriftPhysics()  →  physics.position = carX (UNDEFINED at this point!)
  carX = startPos.x    ← TOO LATE
  → physics.position = NaN
  → next frame: carX = physics.position.x (NaN)
  → playerCar.position.x = NaN
  → camera.position.x = NaN
  → BLACK SCREEN
```
**Fix:** Set `this.carX = startPos.x` BEFORE calling `initVDriftPhysics()`.

## Audio NaN Fix
Old code used `this.rpm` (never updated by new physics engine).
**Fix:** Read RPM from VDrift engine:
```typescript
const currentRpm = this.vdriftPhysicsFull?.engine.getRPM() ?? 850;
if (!isFinite(currentRpm) || currentRpm < 0) return;
```
