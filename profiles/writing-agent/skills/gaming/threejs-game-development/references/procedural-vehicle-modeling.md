# Procedural Vehicle 3D Modeling for Three.js Racing Games

## When to Use This

When the user asks for realistic vehicle 3D models in a racing game but GLB/GLTF model files are unavailable (placeholders, empty files, network limited). Use ExtrudeGeometry + ShapeGeometry + BoxGeometry combinations to build recognizable car shapes.

## Vehicle Architecture (9 layers from bottom to top)

### Layer 1: Body — ExtrudeGeometry with Bevel

Replace `BoxGeometry(1.8, 0.5, 3.5)` with a shaped car silhouette:

```typescript
const bodyShape = new THREE.Shape();
const bw = 0.9;  // half-width
const bl = 1.75; // half-length

// Top-down car silhouette: nose → windshield → cabin → rear taper → tail
bodyShape.moveTo(0, bl);
bodyShape.quadraticCurveTo(bw*0.3, bl, bw*0.6, bl*0.85);  // nose curve
bodyShape.quadraticCurveTo(bw, bl*0.7, bw, bl*0.3);       // windshield point
bodyShape.lineTo(bw, -bl*0.2);                             // cabin side
bodyShape.quadraticCurveTo(bw, -bl*0.6, bw*0.7, -bl*0.85); // rear taper
bodyShape.quadraticCurveTo(bw*0.3, -bl, 0, -bl);           // tail
// Mirror for left side:
bodyShape.quadraticCurveTo(-bw*0.3, -bl, -bw*0.7, -bl*0.85);
bodyShape.quadraticCurveTo(-bw, -bl*0.6, -bw, -bl*0.2);
bodyShape.lineTo(-bw, bl*0.3);
bodyShape.quadraticCurveTo(-bw, bl*0.7, -bw*0.6, bl*0.85);
bodyShape.quadraticCurveTo(-bw*0.3, bl, 0, bl);

// Extrude with bevel for smooth edges
const extrudeSettings = {
    steps: 1, depth: tierBodyHeight,
    bevelEnabled: true, bevelThickness: 0.08,
    bevelSize: 0.05, bevelSegments: 6,
};
const bodyGeo = new THREE.ExtrudeGeometry(bodyShape, extrudeSettings);
bodyGeo.translate(0, 0, -tierBodyHeight / 2);
const body = new THREE.Mesh(bodyGeo, bodyMat);
body.position.y = 0.25;
```

### Layer 2: Cockpit — ExtrudeGeometry with Glass Material

Elliptical shape placed on top of body:

```typescript
const cabinShape = new THREE.Shape();
const cw = cabinW / 2, cl = cabinL / 2;
cabinShape.moveTo(0, cl);
cabinShape.quadraticCurveTo(cw*0.4, cl, cw, cl*0.7);
cabinShape.lineTo(cw, -cl*0.5);
cabinShape.quadraticCurveTo(cw*0.5, -cl, 0, -cl);
cabinShape.quadraticCurveTo(-cw*0.5, -cl, -cw, -cl*0.5);
cabinShape.lineTo(-cw, cl*0.7);
cabinShape.quadraticCurveTo(-cw*0.4, cl, 0, cl);

const cabinGeo = new THREE.ExtrudeGeometry(cabinShape, { steps:1, depth:cabinH, bevelEnabled:true, bevelThickness:0.05, bevelSize:0.03, bevelSegments:3 });
cabinGeo.translate(0, 0, -cabinH / 2);
const cabin = new THREE.Mesh(cabinGeo, glassMat);
cabin.position.set(0, 0.25 + tierBodyHeight, cabinZ);
```

### Layer 3: Front Bumper + Grille

```typescript
const grilleMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.9 });
// Dual grille holes
for (let side = -0.35; side <= 0.35; side += 0.7) {
    const grille = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.12, 0.05), grilleMat);
    grille.position.set(side, 0.28, bl + 0.02);
    group.add(grille);
}
// Lower intake
const lowerGrille = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.08, 0.04), grilleMat);
lowerGrille.position.set(0, 0.18, bl + 0.02);
```

### Layer 4: Headlights (Tier-Variant)

```typescript
const hlZ = bl + 0.05;
if (tier >= 4) {  // T4/T5: LED light bar
    for (let side = -0.5; side <= 0.5; side += 1.0) {
        const bar = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.03, 0.06), lightMat);
        bar.position.set(side, 0.40, hlZ);
        group.add(bar);
    }
} else {  // T1-T3: Round/ellipsoid projectors
    for (let side = -0.5; side <= 0.5; side += 1.0) {
        const hl = new THREE.Mesh(new THREE.SphereGeometry(0.10, 8, 8), lightMat);
        hl.scale.set(1, 0.7, 0.5);
        hl.position.set(side, 0.38, hlZ);
        group.add(hl);
    }
}
```

### Layer 5: Taillights (Tier-Variant)

```typescript
const tailZ = -bl - 0.03;
if (tier >= 4) {  // wraparound LED bar
    const lightBar = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.04, 0.05), redMat);
    lightBar.position.set(0, 0.30, tailZ);
} else {  // discrete tail lights
    for (let side = -0.4; side <= 0.4; side += 0.8) {
        const tl = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.08, 0.04), redMat);
        tl.position.set(side, 0.32, tailZ);
    }
}
```

### Layer 6: Spoiler / Diffuser

```typescript
if (tier >= 3) {  // T3-T5: Big wing with stands
    const spoilerMat = new THREE.MeshStandardMaterial({ color: aColor, metalness: 0.7, roughness: 0.2 });
    const spoiler = new THREE.Mesh(new THREE.BoxGeometry(sw, 0.04, 0.5), spoilerMat);
    spoiler.position.set(0, bodyTop + cabinH + 0.15, -bl * 0.7);
    spoiler.rotation.x = -0.2;  // angle of attack
    // Wing stands
    for (let sx = -0.5; sx <= 0.5; sx += 1.0) {
        const stand = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.25, 0.04), spoilerMat);
        stand.position.set(sx, bodyTop + cabinH * 0.5, -bl * 0.7);
    }
} else {  // T1-T2: Ducktail spoiler
    const ducktail = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.04, 0.15), accentMat);
    ducktail.position.set(0, bodyTop + 0.02, -bl + 0.05);
}

// Diffuser (T3+ only)
if (tier >= 3) {
    for (let i = -0.4; i <= 0.4; i += 0.2) {
        const fin = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.10, 0.15), diffMat);
        fin.position.set(i, 0.10, -bl + 0.05);
    }
}
```

### Layer 7: Side Skirts + Wheel Arches

```typescript
// Side skirts
for (let side = -1; side <= 1; side += 2) {
    const skirt = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.08, bl * 1.2), accentMat);
    skirt.position.set(side * (bw + 0.03), 0.22, 0);
}

// Wheel arches (half-circle ShapeGeometry at each wheel)
for (let side = -1; side <= 1; side += 2) {
    for (let axle = -1; axle <= 1; axle += 2) {
        const archShape = new THREE.Shape();
        archShape.moveTo(-0.2, 0.32);
        archShape.quadraticCurveTo(0, 0.40, 0.2, 0.32);
        archShape.lineTo(0.22, 0.26);
        archShape.quadraticCurveTo(0, 0.30, -0.22, 0.26);
        archShape.closePath();
        const archGeo = new THREE.ShapeGeometry(archShape);
        const arch = new THREE.Mesh(archGeo, bodyMat);
        arch.position.set(side * (bw + 0.02), 0.28, axle * 1.0);
    }
}
```

### Layer 8: Brake System + Hood Lines

```typescript
// Brake discs (behind each wheel)
const brakeMat = new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.7, metalness: 0.6 });
const caliperMat = new THREE.MeshStandardMaterial({
    color: tier >= 4 ? 0xff2200 : 0xcc4400  // red calipers for race cars
});

for (let side = -1; side <= 1; side += 2) {
    for (let axle = -1; axle <= 1; axle += 2) {
        // Disc
        const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.02, 12), brakeMat);
        disc.position.set(side * (bw + 0.05), 0.25, axle * 1.0);
        disc.rotation.z = Math.PI / 2;
        // Caliper
        const caliper = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.06, 0.06), caliperMat);
        caliper.position.set(side * (bw + 0.08), 0.25, axle * 1.0);
    }
}

// Hood lines
for (let side = -0.3; side <= 0.3; side += 0.6) {
    const hoodLine = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.025, 0.5), bodyMat);
    hoodLine.position.set(side, bodyTop + 0.01, 0.8);
}
```

### Layer 9: Wheels (3 Styles by Tier) + Undeglow

```typescript
const rimStyle = tier >= 4 ? 'star' : tier >= 3 ? 'multi' : 'simple';
const wheelPositions = [[-bw-0.1, 0.25, 1.0], [bw+0.1, 0.25, 1.0], [-bw-0.1, 0.25, -1.0], [bw+0.1, 0.25, -1.0]];

for (const wp of wheelPositions) {
    const wheelGroup = new THREE.Group();
    // Tire
    const tire = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.12, 8, 16), wheelMat);
    tire.rotation.y = Math.PI / 2;
    wheelGroup.add(tire);
    
    // Rim by style
    if (rimStyle === 'star') {  // T4-T5: 5-spoke star
        const starShape = new THREE.Shape();
        for (let i = 0; i < 5; i++) { /* pentagram path */ }
        const rim = new THREE.Mesh(new THREE.ShapeGeometry(starShape), accentMat);
    } else if (rimStyle === 'multi') {  // T3: 7-spoke
        for (let i = 0; i < 7; i++) {
            const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.12, 0.03), accentMat);
            spoke.position.set(Math.cos(a)*0.08, Math.sin(a)*0.08, 0);
        }
    } else {  // T1-T2: Simple 6-cyl
        const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.08, 6), accentMat);
    }
    wheelGroup.position.set(wp[0], wp[1], wp[2]);
}

// Neon underglow
const underglow = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 2.8), underglowMat);
underglow.rotation.x = Math.PI / 2;
underglow.position.set(0, 0.04, 0);
```

## 5-Tier Body Parameters

```typescript
const tierParams = [
    // [bodyHeight, cabinZ, cabinH, cabinW, cabinL]
    [0.55, 0.25, 0.30, 1.2, 1.4],  // T1: Hatchback (tall, short)
    [0.50, 0.20, 0.28, 1.2, 1.3],  // T2: Sports car
    [0.40, 0.15, 0.22, 1.1, 1.2],  // T3: Supercar (low, wide)
    [0.35, 0.10, 0.18, 1.0, 1.1],  // T4: Race car
    [0.30, 0.05, 0.15, 0.9, 1.0],  // T5: Prototype (flat, narrow cabin)
];
```

## Paint System — Traverse-Based (NOT Reference-Based)

The old pattern (`carPaintMeshes = { body, spoiler, rim }`) breaks when body becomes ExtrudeGeometry. Use traverse:

```typescript
applyPaintToCar(): void {
    this.playerCar.traverse((child) => {
        if (!(child instanceof THREE.Mesh) || !child.material) return;
        const mat = child.material;
        if (Array.isArray(mat)) {
            mat.forEach(m => this.applyToMaterial(m, bodyColor, accentColor, wheelColor, scheme));
        } else {
            this.applyToMaterial(mat, bodyColor, accentColor, wheelColor, scheme);
        }
    });
}

applyToMaterial(mat, bodyColor, accentColor, wheelColor, scheme): void {
    if (mat instanceof THREE.MeshPhysicalMaterial && !mat.transparent) {
        // Body panel: full paint (color, metalness, roughness, clearcoat)
        mat.color = bodyColor; mat.metalness = scheme.metallicness; mat.roughness = scheme.roughness; mat.clearcoat = scheme.clearcoat;
    } else if (mat instanceof THREE.MeshStandardMaterial && !mat.transparent && mat.metalness > 0.5) {
        // Accent part (spoiler, skirts): accent color
        mat.color = accentColor;
    } else if (mat instanceof THREE.MeshStandardMaterial && mat.metalness > 0.7 && !mat.emissive) {
        // Wheel: wheel color
        mat.color = wheelColor;
    }
}
```

**Key insight**: The paint system uses material properties to determine what to paint, not stored mesh references. MeshPhysicalMaterial+opaque=body, StandardMaterial+metalness>0.5=accent, StandardMaterial+metalness>0.7+no emissive=wheel.

## Key Pitfalls

1. **Scaling**: Car dimensions are in meters. A real car is ~1.8m wide × 0.5m tall × 3.5m long. The ExtrudeGeometry body should match these proportions. T1 (hatchback) is taller, T5 (prototype) is flatter.

2. **Wheel position**: Front wheels at z=+1.0, rear at z=-1.0. The body half-length `bl=1.75` means wheels are visibly within the body silhouette. Adjust wheel.z if the body shape changes.

3. **Cabin z-position**: A mid-engine supercar (T3) has the cabin farther forward than a front-engine hatchback (T1). The `cabinZ` parameter controls this.

4. **Performance**: Each vehicle adds ~30 meshes. With 4 cars (1 player + 3 AI) = ~120 meshes for vehicles. This is negligible for GPU but watch for `receiveShadow` on the ExtrudeGeometry body — it adds fill-rate cost.

5. **Randomization**: When the user asks "每次游戏都是随机的车子", implement:
```typescript
this.selectedTier = Math.floor(Math.random() * 5) + 1;  // random T1-T5
this.currentPaintIndex = Math.floor(Math.random() * paintSchemes.length);  // random paint
```
