# VDrift Physics Engine Debugging Reference

## Common failure: car gets throttle but doesn't move

### Root causes (check in order):

1. **Missing ENGINE_IDLE_RPM / ENGINE_MAX_RPM constants**
   - Error: `rpmNorm = (1000 - undefined) / (7200 - undefined)` = NaN
   - Result: AudioParam.value gets NaN → TypeError → gameLoop stops → car freezes
   - Fix: Declare `ENGINE_IDLE_RPM = 850` and `ENGINE_MAX_RPM = 7200` in class

2. **No collision detection → wheelContact.depth <= 0 → no tire force**
   - VDrift physics: `UpdateWheelConstraints()` skips tire computation when `contact.depth <= 0`
   - Result: Tires produce zero force, engine torque goes nowhere
   - Quick fix: Add simplified thrust calculation in Update() using engine torque directly:
     ```
     if (throttleValue > 0.01) {
       const wheelTorque = engineTorque * gearRatio * efficiency;
       const wheelForce = wheelTorque / wheelRadius;
       const accel = wheelForce / mass * distribution;
       velocity += accel * dt * direction;
     }
     ```

3. **Position integration overwrites velocity with old speed=0**
   - Code pattern:
     ```
     const speed = this.getSpeed();  // reads OLD velocity (0)
     // thrust code adds to velocity here
     this.velocity.z = newDirZ * speed;  // multiplies by OLD speed (0) → velocity back to 0!
     ```
   - Fix: **Re-read speed after thrust code**:
     ```
     const currentSpeed = Math.sqrt(this.velocity.x * this.velocity.x + this.velocity.z * this.velocity.z);
     // then use currentSpeed for position integration
     ```

4. **WheelContactDrag kills tiny velocity**
   - `ApplyWheelContactDrag()` has `rollingDrag = 0.5 * dt`
   - At very low speed, this can cancel out thrust
   - Workaround: Remove speed < 1.0 guard on thrust code so it keeps pushing

5. **autoTransmission shifts gear incorrectly**
   - Verify `Shift(1)` is called during init
   - Check engine is actually producing torque: `engine.getTorque() > 0`
   - Gear ratio may be too high in 1st → wheelTorque huge but velocity integration eats it

### Quick diagnostic: manual stepping

```javascript
// In browser console after game starts:
var p = window.game.vdriftPhysicsFull;
p.SetThrottle(1);
p.Update(0.016);
p.getSpeed()  // should be > 0.01 after 1 step
// If 0: check getTorque(), gear ratio, and position integration overwrite
```

## Common failure: gameLoop stops (black screen)

### Diagnostic:
1. Check elapsed time: `window.game.clock.elapsedTime` — if 0, gameLoop never ran or stopped
2. Call gameLoop manually in try-catch: catches the exact undefined function
3. Common culprits:
   - `playCollisionSound is not a function`
   - `distanceToTrack is not a function`
   - Audio `AudioParam.value` NaN assignment

### Fix pattern:
Always wrap gameLoop body in try-catch:
```typescript
private gameLoop = () => {
    try {
        // ... all update logic ...
    } catch(e) {
        console.error('gameLoop crashed:', e);
        requestAnimationFrame(this.gameLoop);  // keep running despite errors
    }
};
```

But better: **never call undefined functions**. Check existence before every call:
```typescript
if (typeof this.playCollisionSound === 'function') {
    this.playCollisionSound();
}
```

## Key coordinate systems

| System | X | Y | Z | Front |
|--------|---|---|---|-------|
| VDrift (JOE file) | left-right | front-back (Y+ = front) | up | Y+ |
| Three.js standard | left-right | up | front-back | Z- |
| Converted vertex | (x) | (z = original up) | (-y = original front negated) | Z- |

## Tire force calculation (Pacejka simplified)

Tire force = D * sin(C * atan(B * slip - E * (B * slip - atan(B * slip))))

Where:
- slip = slip angle (lateral) or slip ratio (longitudinal)
- B = stiffness factor (8-9 for race tires)
- C = shape factor (1.3)
- D = peak friction coefficient (mu)
- E = curvature factor (-0.3)

The `getRollingResistance()` parameters: resistance = rr * normalForce, where rr comes from tire specification + surface rollingResist.
