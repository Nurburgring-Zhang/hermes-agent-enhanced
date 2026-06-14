# VDrift ↔ Three.js Coordinate System Conversion

## The Problem

VDrift uses Z-up coordinates: x=right, y=forward(y+ nose), z=up.
Three.js uses Y-up: x=right, y=up, z=forward(z+ nose).

This mismatch causes EVERY visual bug in the game if not handled consistently.

## Two Approaches

### Approach A: Vertex Transformation (recommended for complex models)
Transform vertex data at load time:
```
newX = rawX
newY = rawZ         // VDrift z(up) → Three.js y(up)
newZ = -rawY        // VDrift y(forward) → Three.js z(forward), negate because VDrift y+ is nose
```

**Car nose direction after transform**: Z- (because VDrift y+ nose → -y = z neg)
**Forward movement**: `worldDz = -cosA * speed`
**Starting angle**: `atan2(tangent.x, -tangent.z)`
**Camera behind**: `(-sinA, height, +cosA)` (car tail is at Z+)

**Pros**: Group/node rotation stays clean, no rotation.x/z overwrite issues
**Cons**: Must also transform normals the same way; extra CPU at load time

### Approach B: Group Rotation
Set `group.rotation.x = -Math.PI / 2` on the entire car group.

**Car nose direction after rotation**: Z- (same result as Approach A)
**Same forward/camera/carrier formulas as Approach A**

**CRITICAL PITFALL**: If you also set `playerCar.rotation.x = bodyPitch` or `rotation.z = bodyRoll` in updatePlayer, these OVERWRITE the group rotation and the model flips sideways. NEVER set rotation.x/z on a group that has been rotated for coordinate conversion.

### Approach B vs A for Tires

With Approach B (group rotation), tires must be positioned in the group's **local** space:
- VDrift raw tire position: (x, y_forward, z_up)
- In group local space: (x, z_up, -y_forward) — same transform as Approach A

The group rotation handles converting local to world. **But** you MUST add tires as children of the rotated group, otherwise their local positions are in wrong space.

## Empirical Validation

Always validate with colored marker spheres before committing:
- Red sphere at Z+5 → should appear at car tail
- Blue sphere at Z-5 → should appear at car nose (facing camera if camera is at Z+)
- Green sphere at Y+3 → should appear above car

## 13 VDrift Car Nose Verification

ALL 13 VDrift models have nose at y+ (positive Y in VDrift coords).
After conversion `(x, z, -y)`, nose is at Z- direction.
