# VDrift Coordinate Verification Record

## ATT Model (Audi TT 3.2) — Verified Correct

### Raw Data (from body.joe, ground-level vertices)
```
VDrift coordinate system: x=左右, y=前后(y-车头), z=上下(Z-up)

Wheel positions from wheelPositions array (format: x, z, y):
  front-left:  pos[0]=-0.84  pos[1]=-0.22  pos[2]=-1.60
  front-right: pos[0]= 0.84  pos[1]=-0.22  pos[2]=-1.60
  rear-left:   pos[0]=-0.88  pos[1]=-0.22  pos[2]= 1.60
  rear-right:  pos[0]= 0.88  pos[1]=-0.22  pos[2]= 1.60

Transformed to Three.js (x不变, y=pos[1], z=-pos[2]):
  front-left:  (-0.84, -0.22,  1.60)  z+ = car forward
  front-right: ( 0.84, -0.22,  1.60)
  rear-left:   (-0.88, -0.22, -1.60)
  rear-right:  ( 0.88, -0.22, -1.60)

Wheelbase: 1.60 - (-1.60) = 3.20m
Front track: 0.84 - (-0.84) = 1.68m
Rear track: 0.88 - (-0.88) = 1.76m
```

### Critical Finding: wheelPositions Format

The data in the hardcoded `wheelPositions` dictionary is **NOT** (x, y, z). It's **(x, z, y)**:
- pos[0] = VDrift x (right-left) → Three.js x
- pos[1] = VDrift z (up-down) → Three.js y (the height)
- pos[2] = VDrift y (forward-back) → negated for Three.js z

**History of getting this wrong:**
1. First assumption: (x, y, z) with y=前后 → `set(pos[0], pos[2], -pos[1])` → wheels underground front, above ground rear (vertical car)
2. Second assumption: (x, z, y) but forgot negate → `set(pos[0], pos[1], pos[2])` → both front/rear at same incorrect position
3. Correct: (x, z, y) with negate → `set(pos[0], pos[1], -pos[2])` → wheels at correct height and fore-aft position

### Model Body Vertex Range (ATT body only, no glass/interior)
```
Raw JOE (before parse): x=[-0.91,0.91] y=[-1.97,1.89] z=[-0.03,0.20]
After (x,z,-y) transform: x=[-0.91,0.91] y=[-0.03,0.20] z=[-1.89,1.97]
```

Width: 1.82m, Height: 0.23m, Length: 3.86m.
Length should be ~4.2m for an Audi TT — the difference is due to missing front/rear bumpers in the body.joe file.

## Testing Protocol

To verify coordinate system at runtime:
```typescript
// Place markers at Z+ and Z- directions
const markerMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
const m1 = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), markerMat);
m1.position.set(0, 0.5, 5);  // Z+ direction
scene.add(m1);
const m2 = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), markerMat);
m2.position.set(0, 0.5, -5);  // Z- direction
scene.add(m2);
```
Press W — the car moves toward one of these markers.
