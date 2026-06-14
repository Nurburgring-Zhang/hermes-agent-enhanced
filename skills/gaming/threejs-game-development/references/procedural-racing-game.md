# Procedural 3D Racing Game Construction

## CatmullRom Track Generation

```typescript
// 16 control points for a closed-loop track (last == first to close)
const segments = [
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(20, 0, -10),
    new THREE.Vector3(50, 0, -20),
    new THREE.Vector3(80, 2, -10),
    new THREE.Vector3(100, 4, 10),
    new THREE.Vector3(90, 3, 35),
    new THREE.Vector3(70, 2, 55),
    new THREE.Vector3(40, 1, 65),
    new THREE.Vector3(10, 0, 60),
    new THREE.Vector3(-15, 0, 50),
    new THREE.Vector3(-35, 1, 35),
    new THREE.Vector3(-45, 2, 15),
    new THREE.Vector3(-40, 1, -5),
    new THREE.Vector3(-30, 0, -15),
    new THREE.Vector3(-15, 0, -10),
    new THREE.Vector3(0, 0, 0)  // close loop
];
const curve = new THREE.CatmullRomCurve3(segments, true, 'catmullrom', 0.5);
```

### Track Mesh Generation
1. Get 200 sample points via `curve.getPoints(200)`
2. For each point, compute the right vector: `cross(up, tangent).normalize()`
3. Left edge = point - right × (trackWidth/2), Right edge = point + right × (trackWidth/2)
4. Build BufferGeometry from these edge pairs with indices for 2 triangles per segment

### Key UV Mapping
- U = 0 (left edge), 1 (right edge)
- V = i × 0.1 (repeat along track length)
- Texture set to RepeatWrapping with repeat.y proportional to track length

### Track Texture (procedural)
```typescript
const canvas = document.createElement('canvas');
canvas.width = 512; canvas.height = 512;
const ctx = canvas.getContext('2d');
ctx.fillStyle = '#2a2a3a';
ctx.fillRect(0, 0, 512, 512);
// asphalt noise
for (let i = 0; i < 20000; i++) {
    const brightness = 30 + Math.random() * 30;
    ctx.fillStyle = `rgb(${brightness},${brightness},${brightness+10})`;
    ctx.fillRect(Math.random()*512, Math.random()*512, 2, 2);
}
// lane markings
ctx.fillStyle = 'rgba(255,255,255,0.3)';
for (let y = 0; y < 512; y += 32) ctx.fillRect(250, y, 12, 16);
const tex = new THREE.CanvasTexture(canvas);
tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
tex.repeat.set(1, 30);
```

### Track Barriers and Neon Poles

**Barriers**: Loop through sample points, compute right edge, create boxes/lines.
**Poles**: Every 4th sample point, place cylinder+sphere+PointLight at ±10 units from centerline.
**Cross-track arches**: Every 20th sample point, create CatmullRomCurve3 arc from left to right side.

### Finish Line

- Checkerboard pattern: alternating black/white Planes across track width
- Arch: two pillars (BoxGeometry 0.5×8×0.5) + beam + cone spikes with PointLights
- Material: emissive cyan `0x00ffff` with `emissiveIntensity: 0.5`

## Simplified Vehicle Physics (No Cannon-es)

| Parameter | Value | Notes |
|-----------|-------|-------|
| ACCEL | 20 | Units/s² |
| BRAKE | 25 | Units/s² |
| MAX_SPEED | 80 | Units/s, capped by drag |
| FRICTION | 8 | Deceleration when no input |
| STEER_SPEED | 3.0 | Rad/s at low speed |
| STEER_FACTOR_MIN | 0.2 | High-speed steering clamp |
| TRACK_OFFSET | 500 | playerProgress = distance / 500 |
| COLLISION_DAMAGE | 0.05 | Speed retained per collision |
| COLLISION_COOLDOWN | 0.5 | Seconds between collision events |

### Input Detection
```typescript
const keyState = (window as any).__keys || {};
const throttle = keyState['KeyW'] || keyState['ArrowUp'] ? 1 : 0;
const brake = keyState['KeyS'] || keyState['ArrowDown'] ? 1 : 0;
let steer = 0;
if (keyState['KeyA'] || keyState['ArrowLeft']) steer = 1;
if (keyState['KeyD'] || keyState['ArrowRight']) steer = -1;
```

### Position Update
```typescript
const trackPos = curve.getPoint(playerProgress);
const tangent = curve.getTangent(playerProgress);
car.position.set(trackPos.x, trackPos.y + 0.5, trackPos.z);
car.rotation.y = Math.atan2(tangent.x, tangent.z);
// Body tilt with speed
const speedNorm = Math.abs(this.playerSpeed) / MAX_SPEED;
car.position.y += Math.sin(Date.now() * 0.01 * this.playerSpeed) * 0.01 * speedNorm;
car.rotation.z = steer * -0.12 * speedNorm;
```

### Drift Physics
```typescript
const driftFactor = 1 - Math.abs(steer) * 0.15 * Math.abs(this.playerSpeed) / MAX_SPEED;
if (Math.abs(steer) > 0.5 && Math.abs(this.playerSpeed) > 20) {
    this.playerSpeed *= driftFactor;
}
```

## Camera System

```typescript
// Behind and above the car
const behind = new THREE.Vector3(0, 0, 1);
behind.applyAxisAngle(new THREE.Vector3(0, 1, 0), carAngle);
behind.multiplyScalar(10);
behind.y = 6;
const desiredPos = carPos.clone().add(behind);
camera.position.lerp(desiredPos, delta * 3);
camera.lookAt(carPos);
```

## AI Opponents

- 3 cars at progress 0.25, 0.50, 0.75
- Corner braking via curvature detection
- Rank: count AI with greater progress than player

### AI Corner Braking
```typescript
const lookAhead = 0.02;
const aheadProg = Math.min(1, aiProg + lookAhead);
const curT = curve.getTangent(aiProg);
const aT = curve.getTangent(aheadProg);
const dot = curT.x * aT.x + curT.z * aT.z;
const curvature = Math.max(0, 1 - Math.abs(dot));
const speedFactor = 1 - curvature * 0.5;
const aiSpeed = (45 + i * 8) * speedFactor + Math.sin(time * 0.001 + i) * 3;
```

## Bloom Post-Processing

```typescript
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.6,  // strength
    0.3,  // radius
    0.1   // threshold
);
composer.addPass(bloom);
```

Renderer setup for game:
```typescript
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
```

## Web Audio Engine Sound

```typescript
const ctx = new (window.AudioContext || window.webkitAudioContext)();
const osc = ctx.createOscillator();
osc.type = 'sawtooth';
const filter = ctx.createBiquadFilter();
filter.type = 'lowpass';
filter.frequency.value = 400;
filter.Q.value = 2;
const gain = ctx.createGain();
gain.gain.value = 0.08;
osc.connect(filter).connect(gain).connect(ctx.destination);
osc.start();

// Update every frame:
const speedNorm = Math.abs(playerSpeed) / MAX_SPEED;
const targetFreq = 60 + speedNorm * 200;
const targetVol = 0.02 + speedNorm * 0.1;
osc.frequency.value += (targetFreq - osc.frequency.value) * delta * 5;
gain.gain.value += (targetVol - gain.gain.value) * delta * 3;
```

### Collision Sound (White Noise Burst)
```typescript
const noise = ctx.createBufferSource();
const buf = ctx.createBuffer(1, 1000, 44100);
const d = buf.getChannelData(0);
for (let i = 0; i < 1000; i++) d[i] = (Math.random() * 2 - 1) * 0.15;
noise.buffer = buf;
const ng = ctx.createGain();
ng.gain.value = 0.15;
noise.connect(ng).connect(ctx.destination);
noise.start();
noise.stop(ctx.currentTime + 0.1);
```

## Procedural City Buildings

```typescript
// 3 rings at radius 80, 140, 200 from track center
for (let ring = 0; ring < 3; ring++) {
    const count = 30 + ring * 15;
    const radius = 80 + ring * 60;
    for (let i = 0; i < count; i++) {
        const angle = (i / count) * Math.PI * 2;
        const height = 5 + Math.random() * 35;
        const width = 4 + Math.random() * 10;
        const building = new THREE.Mesh(
            new THREE.BoxGeometry(width, height, depth),
            new THREE.MeshStandardMaterial({ color: darkBluePurple })
        );
        building.position.set(cos(angle) * radius, height/2, sin(angle) * radius);
        scene.add(building);
        // Add random lit windows
        if (Math.random() > 0.3) {
            for (let w = 0; w < height/3; w+=3) {
                add window PlaneGeometry with emissive color at random position
            }
        }
    }
}
```

## Neon Light Poles

- Place every 4th track sample point
- Inner and outer offset (±10 units perpendicular to tangent)
- Cylinder (radius 0.12, height 4) + Sphere (radius 0.2) at top
- PointLight(color, intensity=1.5, distance=12)
- Colors cycle: [magenta, cyan, pink, green, yellow]

Cross-track arches every 20th sample point:
```typescript
const arcPoints: Vector3[] = [];
for (let j = 0; j <= 12; j++) {
    const t = j / 12;
    const left = center + right * (-7 + t * 14);
    left.y = 6 + Math.sin(t * Math.PI) * 3;
    arcPoints.push(left);
}
const arcCurve = new THREE.CatmullRomCurve3(arcPoints);
const arcLine = new THREE.Line(arcCurve.getPoints(20), 
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.6 }));
```

## Vehicle Model Construction (Procedural)

A complete racing car as a THREE.Group:

```typescript
buildVehicle(bodyColor, accentColor): THREE.Group {
    const group = new THREE.Group();
    
    // Body: BoxGeometry(1.8, 0.5, 3.5) with MeshPhysicalMaterial (clearcoat: 1.0)
    // Cabin: BoxGeometry(1.4, 0.35, 1.6) with glass (transparent, 0.4 opacity)
    // Headlights: SphereGeometry(0.12) emissive at front corners
    // Taillights: red emissive at rear
    // Spoiler: BoxGeometry(1.6, 0.05, 0.4) + two thin stands
    // Wheels: TorusGeometry(0.28, 0.12) + CylinderGeometry(0.15, 0.15, 0.1) rim
    // Underglow: PlaneGeometry(1.5, 3) with accentColor, transparent
    
    return group;
}
```

## Game Loop Architecture

```typescript
// Use arrow function to bind this:
private gameLoop = (): void => {
    if (this.gameState !== 'playing') return;
    const delta = Math.min(this.clock.getDelta(), 0.05);
    this.updatePlayer(delta);
    this.updateAI(delta);
    this.updateCamera(delta);
    this.updateHUD();
    this.updateAudio(delta);
    this.composer.render();
    requestAnimationFrame(this.gameLoop);
};

// Start with RAF, NOT direct call:
requestAnimationFrame(() => this.gameLoop());
// This ensures RAF chain starts even in headless browsers
```
