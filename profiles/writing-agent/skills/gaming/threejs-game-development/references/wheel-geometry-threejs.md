# Wheel Geometry in Three.js — A Complete Reference

## Core Principle: One Rotation, All Components

**NEVER rotate individual wheel sub-components.** Build everything in the default Y-axis orientation, then group-rotate ONCE.

```typescript
const wheelGroup = new THREE.Group();
wheelGroup.rotation.z = Math.PI / 2;  // ONE rotation for ALL components
```

After `rotation.z = PI/2`, the group's local Y axis becomes the world X axis (left-right wheel axis). All sub-components that were pointing along Y now point along X.

## Verified Working Structure

```
wg (Group, positioned at wheel location with correct coord transform)
├── wheelGroup (Group, rotation.z=PI/2)
│   ├── tire (LatheGeometry, no rotation)
│   ├── hub (CylinderGeometry, no rotation)
│   ├── outerRing (TorusGeometry, no rotation)
│   ├── spokes × 5 (BoxGeometry, YZ plane positions)
│   └── disc (CylinderGeometry, offset along Y, no rotation)
```

## Brake Disc Alert

The disc uses CylinderGeometry (default Y-axis). After `wheelGroup.rotation.z = PI/2`:
- Cylinder axis: Y → X (wheel axle)
- Disc face vertical in YZ plane → **correct**
- `disc.rotation.x = PI/2` makes disc lie flat (pancake) → **wrong**

**Rule**: Never add individual .rotation to wheel sub-components.
