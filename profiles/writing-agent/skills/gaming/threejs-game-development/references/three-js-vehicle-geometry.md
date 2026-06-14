# Three.js Vehicle Geometry Construction (No GLTF — Pure Geometry)

> Build realistic car visuals using `THREE.Shape` + `ExtrudeGeometry` + bevel.
> No GLB/GLTF models required. Real car proportions via quadratic curves.

## Core Principle: Shape Extrusion with Quadratic Curves

Replace `BoxGeometry(1.8, 0.5, 3.5)` with a custom Shape profile that traces a real car's footprint:

```typescript
const bodyShape = new THREE.Shape();
const bw = 0.9;   // half-width (total width 1.8m)
const bl = 1.75;  // half-length (total length 3.5m)

// Car footprint — real vehicle shape from above:
// nose rounded → widest at B-pillar → tapered tail
bodyShape.moveTo(0, bl);                                          // nose tip
bodyShape.quadraticCurveTo(bw * 0.3, bl, bw * 0.6, bl * 0.85);   // nose curve
bodyShape.quadraticCurveTo(bw, bl * 0.7, bw, bl * 0.3);          // front fender
bodyShape.lineTo(bw, -bl * 0.2);                                  // door line
bodyShape.quadraticCurveTo(bw, -bl * 0.6, bw * 0.7, -bl * 0.85); // rear fender
bodyShape.quadraticCurveTo(bw * 0.3, -bl, 0, -bl);               // tail
// mirror for left side (negative x control points)
```

Then extrude to 3D with bevel for smooth edges:

```typescript
const extrudeSettings = {
    steps: 1,
    depth: bodyHeight,            // 0.30-0.55m depending on car type
    bevelEnabled: true,
    bevelThickness: 0.08,         // rounds the edges
    bevelSize: 0.05,
    bevelSegments: 6,             // smooth bevel
};
const bodyGeo = new THREE.ExtrudeGeometry(bodyShape, extrudeSettings);
bodyGeo.translate(0, 0, -bodyHeight / 2);  // center vertically
const body = new THREE.Mesh(bodyGeo, bodyMat);
body.position.y = 0.25;  // sit above ground
```

## Tier-Specific Body Dimensions

| Tier | Body Height | Cabin Height | Cabin Width | Cabin Z-offset | Style |
|------|-------------|--------------|-------------|----------------|-------|
| T1 小钢炮 | 0.55m | 0.30m | 1.2m | +0.25m | Tall hatchback |
| T2 跑车 | 0.50m | 0.28m | 1.2m | +0.20m | Classic FR |
| T3 超跑 | 0.40m | 0.22m | 1.1m | +0.15m | Wedge shape |
| T4 赛车 | 0.35m | 0.18m | 1.0m | +0.10m | Flat wide |
| T5 原型车 | 0.30m | 0.15m | 0.9m | +0.05m | Extreme aero |

## Cabin (Windshield) Construction

Same Shape+Extrude pattern but with glass material:

```typescript
const cabinShape = new THREE.Shape();
const cw = cabinWidth / 2;
const cl = cabinLength / 2;
cabinShape.moveTo(0, cl);
cabinShape.quadraticCurveTo(cw * 0.4, cl, cw, cl * 0.7);
cabinShape.lineTo(cw, -cl * 0.5);
cabinShape.quadraticCurveTo(cw * 0.5, -cl, 0, -cl);
cabinShape.quadraticCurveTo(-cw * 0.5, -cl, -cw, -cl * 0.5);
cabinShape.lineTo(-cw, cl * 0.7);
cabinShape.quadraticCurveTo(-cw * 0.4, cl, 0, cl);

const cabin = new THREE.Mesh(
    new THREE.ExtrudeGeometry(cabinShape, { depth: cabinH, bevelEnabled: true, bevelThickness: 0.05, ... }),
    glassMat
);
cabin.position.set(0, 0.25 + bodyHeight, cabinZ);  // sits on top of body
```

## Headlights by Tier

```typescript
// T1-T3: Round/elliptical headlights (classic car look)
for (let side = -0.5; side <= 0.5; side += 1.0) {
    const hl = new THREE.Mesh(new THREE.SphereGeometry(0.10, 8, 8), lightMat);
    hl.scale.set(1, 0.7, 0.5);  // flatten to ellipse
    hl.position.set(side, 0.38, noseZ);
    group.add(hl);
}

// T4-T5: LED light bars (modern / race car look)
for (let side = -0.5; side <= 0.5; side += 1.0) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.03, 0.06), lightMat);
    bar.position.set(side, 0.40, noseZ);
    group.add(bar);
}
```

## Taillights by Tier

```typescript
// T1-T3: Separate tail light clusters
for (let side = -0.4; side <= 0.4; side += 0.8) {
    const tl = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.08, 0.04), redMat);
    tl.position.set(side, 0.32, tailZ);
    group.add(tl);
}

// T4-T5: Full-width light bar (BMW/Alfa Romeo style)
const lightBar = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.04, 0.05), redMat);
lightBar.position.set(0, 0.30, tailZ);
group.add(lightBar);
```

## Spoiler/Wing by Tier

| Tier | Spoiler Type | Size | Position |
|------|-------------|------|----------|
| T1-T2 | Ducktail | 1.2 x 0.04 x 0.15 | Flush on tail, height + 0.02 |
| T3 | Small wing | 1.4 x 0.04 x 0.5 | On stands, above tail |
| T4 | Race wing | 1.6 x 0.04 x 0.5 | Tall stands, tilted -0.2 rad |
| T5 | Extreme wing | 1.8 x 0.04 x 0.5 | Max height, aggressive tilt |

## Wheel Rims by Tier

```typescript
// T1-T2: Simple 6-spoke
rim = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.08, 6), accentMat);

// T3: Multi-spoke (7 spokes via individual BoxGeometry rotated around center)
for (let i = 0; i < 7; i++) {
    const a = (i / 7) * Math.PI * 2;
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.12, 0.03), accentMat);
    spoke.position.set(Math.cos(a) * 0.08, Math.sin(a) * 0.08, 0);
    spoke.rotation.z = a;
    wheelGroup.add(spoke);
}

// T4-T5: Star rim (5-point star via Shape)
const starShape = new THREE.Shape();
for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2 - Math.PI / 2;
    const a2 = a + Math.PI / 5;
    if (i === 0) starShape.moveTo(Math.cos(a) * 0.13, Math.sin(a) * 0.13);
    else starShape.lineTo(Math.cos(a) * 0.13, Math.sin(a) * 0.13);
    starShape.lineTo(Math.cos(a2) * 0.06, Math.sin(a2) * 0.06);
}
starShape.closePath();
const rim = new THREE.Mesh(new THREE.ShapeGeometry(starShape), accentMat);
```

## Additional Body Details

| Detail | Geometry | Notes |
|--------|----------|-------|
| Front grille | `BoxGeometry(0.25, 0.12, 0.05)` x2 | Positioned at nose, one on each side |
| Lower intake | `BoxGeometry(0.6, 0.08, 0.04)` | Wide flat rectangle below grille |
| Rear diffuser | `BoxGeometry(0.04, 0.10, 0.15)` x5 | Vertical fins T3+, spaced 0.2 apart |
| Side skirts | `BoxGeometry(0.05, 0.08, length*1.2)` x2 | Along body sides at 0.22 height |
| Underglow | `PlaneGeometry(1.5, 2.8)` | Transparent emissive at y=0.04 |

## Camera Distance vs Car Size Rule

**Critical**: The car must occupy ~1/3 of the screen vertically, not 15%.

**Old (broken)**: `distance = 5 + speedKmh * 0.02` → min=5m, max=10m  
With FOV=60°, at 10m the viewport width = 11.5m. Car width 1.8m = 15.6%. Too small.

**Fixed**: `distance = 2.5 + speedKmh * 0.012` → min=2.5m, max=5.5m  
With FOV=60°, at 5.5m the viewport width = 6.3m. Car width 1.8m = 28.6%. About right.

**Camera height rule**: `height = 1.8 + distance * 0.2` (at 2.5m=2.3, at 5.5m=2.9).  
Look target at car center (`carPos.y + 0.5` not `+1.5`).

**Oversight pattern**: The original developer picked "fixed 12m, 5m height" which worked in isolation but made the car microscopic. Always check: how much of the viewport does the subject occupy? At what distance?
