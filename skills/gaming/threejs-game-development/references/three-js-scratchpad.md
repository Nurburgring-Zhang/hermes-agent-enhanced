# Three.js Game Scratchpad — Racing Game Session Notes

## Runtime Failure Signatures

### `ReferenceError: caret is not defined`
**Cause**: Editor cursor marker `{caret}` left in code after patch.
**Detection**: `grep -rn "caret" src/` 
**Fix**: Delete the character sequence `{caret}`.

### `THREE.Material: parameter 'emissive' has value of undefined`
**Cause**: A MeshStandardMaterial is constructed with `emissive: someVariable` where `someVariable` is undefined at call time.
**Impact**: Non-fatal warning. Material renders with default emissive (black).
**Fix**: Provide default: `emissive: color ?? 0x000000`

### `PlushRacingGame is not defined`
**Cause**: HTML onclick calls `ClassName.method()` but webpack bundles the class into module scope.
**Fix**: Route through `window.Game = { method: () => instance.method() }`

## Init Chain Debugging

When `startGame()` is called but the screen stays dark:

1. Check `initFullScene()` entry log — is it reached?
2. Check `canvas = document.getElementById('game-canvas')` — is it null?
3. Check `new THREE.WebGLRenderer({ canvas })` — does it throw?
4. Check `new EffectComposer(renderer)` — does it throw? (common with three.js version mismatches)
5. Check `this.generateTrack()` — does it run? Log entry + exit.
6. Check `requestAnimationFrame(() => this.gameLoop())` — is gameLoop firing?

## Track Scale Calibration — REAL METERS (1 unit = 1 meter)

**CRITICAL**: The user WILL reject any "relative unit" system. Always use real meters.
- Silverstone: ~5200m (control points span -200 to 1000 in x, -600 to 1000 in z)
- Spa: ~6500m (include elevation via y-coordinate, Eau Rouge climb ~80m)
- Monza: ~5200m (mostly flat, long straights)
- Nürburgring: ~18500m (huge elevation changes, simplify to 24-26 points)
- Monaco: ~3200m (narrow street circuit, tighter clusters of points)
- Le Mans: ~13000m (Mulsanne straight alone is ~6000m)
- Suzuka: ~5000m (figure-8 layout, cross-over near 130R)

**Best practice**: hand-craft control points as absolute (x,y,z) coordinates matching each circuit's real shape. Do NOT use GPS coordinate conversion — it introduces scaling errors and hard-to-debug track deformations.

## NPC Speed Must Match Player Units

When AI uses `progress` (0-1) and player uses real meters:
```typescript
// WRONG — hardcoded divisor that doesn't scale with track length:
this.aiProgress[i] += aiSpeed * delta / 500;

// RIGHT — convert AI speed (m/s) to progress using actual track length:
const trackLen = circuitList[currentIndex].gameLength;
this.aiProgress[i] += (aiSpeed / trackLen) * delta;
```

## Real Physics Units

All vehicle physics MUST use real SI units:
- Speed: m/s (HUD converts to km/h via ×3.6)
- Acceleration: m/s²
- Position: meters
- MAX_SPEED for "medium" difficulty: 70 m/s = 252 km/h
- ACCEL: 25 m/s² (0-100km/h in ~4s with street feel)
- BRAKE_FORCE: 35 m/s²
- STEER_SPEED: 2.5 rad/s

## Track Scale Calibration (OLD — DO NOT USE)

| Parameter | Small track (original) | Large track (fixed) |
|-----------|----------------------|---------------------|
| Control point scale `s` | 50-80 | 300 |
| Track circumference | ~1500-2000 | ~3500-6000 |
| MAX_SPEED | 80 | 200 (baseline) |
| ACCEL | 20 | 50 (baseline) |
| BRAKE_FORCE | 25 | 60 (baseline) |
| Lap time (avg cornering) | ~30s | ~60-90s |
| AI base speed | 30-65 | 80-180 |

## Vehicle Build Geometry

Three.js `BoxGeometry(1.8, 0.5, 3.5)` extends along Z-axis by default (3.5 is the depth).

**Headlight/Taillight convention**:
- +Z direction = forward (car "faces" +Z when rotation.y = 0)
- Headlights at z > 0, taillights at z < 0
- Driver cabin at z > 0 (front half)

**Rotation**: `Math.atan2(tangent.x, tangent.z)` converts 2D direction to angle where +Z = 0°, +X = 90°.

## Difficulty Level Mapping

| Level | autoSteer | autoBrake | TCS | ABS | Grip | Player perceived |
|-------|-----------|-----------|-----|-----|------|------------------|
| 0 娱乐 | ✅ | ✅ | ✅ | ✅ | 2.0 | Drives itself |
| 1 轻松 | ❌ | ❌ | ✅ | ✅ | 1.5 | Assisted |
| 2 中等 | ❌ | ❌ | ❌ | ❌ | 1.0 | Manual, fair |
| 3 困难 | ❌ | ❌ | ❌ | ❌ | 0.7 | Stiff, unforgiving |
| 4 大师 | ❌ | ❌ | ❌ | ❌ | 0.5 | Simulation |

## New Session (2026-06-01): gameLoop Crash Patterns

### 1. Undefined Class Function → gameLoop Death
**Calls to `this.playCollisionSound()` but function never defined.**
- Impact: `TypeError` in updatePlayer → gameLoop dies → renderer stops → "black screen with HUD"
- Detection: `grep -rn "playCollisionSound\\|play[^a-z]\\|on[^a-z]" src/ | grep -v ": //"` — find functions called but not defined
- Fix: Delete calls or stub the function. **Always grep for new method calls before building.**

### 2. Engine Constants Missing (ENGINE_IDLE_RPM, ENGINE_MAX_RPM)
- Impact: `undefined - undefined = NaN` in audio → `AudioParam.value` receives NaN → `TypeError: non-finite float` → gameLoop crash
- Root cause: HTML-to-TypeScript migration lost global constants. Nothing in tsc/webpack catches undefined class field references in initializers.
- Detection: `'IDLE: ' + window.game.ENGINE_IDLE_RPM + ' MAX: ' + window.game.ENGINE_MAX_RPM` → undefined
- Fix: Add as `private readonly ENGINE_IDLE_RPM = 850;` class fields

### 3. AudioParam.value NaN Propagation
`this.engineOsc.frequency.value += (rpmHz - this.engineOsc.frequency.value) * delta * 10`
If rpmHz or delta is NaN or Inf, the += produces NaN → TypeError.
Fix: Wrap ALL AudioParam assignments with isFinite() guards and the whole updateAudio in try-catch.

### 4. Position Integration Overwrites Velocity
In CarDynamics.UpdateToPosition, `const speed = this.getSpeed()` is captured BEFORE thrust code runs, but the position integration uses the OLD speed variable to overwrite velocity:
```typescript
const speed = this.getSpeed();  // captured BEFORE thrust
// ... thrust code adds velocity ...
this.velocity.x = newDirX * speed;  // speed=0 → RESETS velocity to 0
```
Fix: Re-read velocity after thrust: `const currentSpeed = Math.sqrt(this.velocity.x**2 + this.velocity.z**2);`
