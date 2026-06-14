# Complete Track Environment Generation — Three.js Racing Games

## Overview

When the user demands a **complete racing circuit environment** (not just a road mesh), generate these 9 elements in order, each as a separate private method:

1. Grass base
2. Track surface (asphalt + markings)
3. Red/white curbs
4. 3D barriers/guardrails
5. Grandstands
6. Billboards/advertising hoardings
7. Pit buildings
8. Finish line + gantry
9. Trees/scenery

## Method Signature Pattern

All methods receive `(points: THREE.Vector3[], trackWidth: number)` except pit buildings and finish line (use trackCurve directly).

```typescript
private generateTrack(): void {
    const circuit = this.circuitList[this.currentCircuitIndex];
    this.trackCurve = createSplineFromCircuit(circuit);
    const points = this.trackCurve.getPoints(300); // 300 segments
    const trackWidth = 20; // meters
    
    this.generateGrassBase(points, trackWidth, center);
    this.generateTrackSurface(points, trackWidth);
    this.generateCurbs(points, trackWidth);
    this.generateBarriers(points, trackWidth);
    this.generateGrandstands(points, trackWidth);
    this.generateBillboards(points, trackWidth);
    this.generatePitBuildings();
    this.generateFinishLine(points, trackWidth);
    this.generateTrees(points, trackWidth);
}
```

## Element Details

### 1. Grass Base
Use a large `CircleGeometry` centered on track. Color `0x1a3a1a` (dark green). Size = `Math.max(600, trackBounds.size * 2)`. Place at y=-0.1 so track surface renders on top.

### 2. Track Surface
Generate BufferGeometry from curve points:
- For each of 300 points, compute left and right edges using cross product of tangent with up vector
- Vertices: 2 per point (left, right) = 600 verts
- UVs: u=0 for left, u=1 for right, v=i*0.03 along track
- Indices: 2 triangles per segment (quad strip)
- Close the loop with final-to-first quad

Canvas texture (2048×256):
- Base: `#2a2a3a` (dark asphalt)
- Noise: 15000 dots at random positions, brightness 35-85
- White dashed centerline: `rgba(255,255,255,0.5)` horizontal bars every 14px, height 2px
- Red/white edge lines: alternating red(`rgba(255,80,80,0.5)`) and white(`rgba(255,255,255,0.3)`) at top and bottom edges

Texture repeat: `repeat.set(40, 1)` — 40 times along the track length.

### 3. Red/White Curbs
Place at intervals of 4 points along the curve. For each curb:
- Compute tangent + right vector at that point
- Place a `BoxGeometry(0.3, 0.05, 1.5)` at `(trackWidth/2 + 0.1) * side` offset
- Alternate color: red (`0xff2200`) and white (`0xffffff`) based on `Math.floor(i/4) % 2`
- Rotate to align with tangent direction

### 4. 3D Barriers (Guardrails)
Use `TubeGeometry` along CatmullRom curve of barrier points:
- For each side (left, right), collect edge positions at every 3rd point
- Edge position = track point + side × (trackWidth/2 + 0.5) × right, y += 0.5
- Create CatmullRomCurve3 from barrier points
- TubeGeometry with radius 0.1, segments = points×2, closed=true
- Material: `0xff4400` with emissive `0xff3300` intensity 0.2

Catch TubeGeometry failures (degenerate curves) and fall back to Line.

### 5. Grandstands
Auto-detect straight sections by checking tangent dot product between points spaced 5 apart:
- If `dot > 0.995` for >10 consecutive segments, it's a straight
- Place grandstands at the midpoint of the 2 longest straights
- Each grandstand: BoxGeometry(8, 4, 5) at trackWidth/2 + 15 offset
- 4 rows of seats: BoxGeometry(7.5, 0.1, 0.8) stacked vertically
- Material: stand=`0x444466`, seats=`0x2244aa`

### 6. Billboards
Place at every 15th point along the curve, on both sides:
- BoxGeometry(3, 1.5, 0.1) at trackWidth/2 + 6 offset
- 5 alternating neon colors (red, green, blue, yellow, magenta)
- Emissive intensity 0.2 for glow effect
- Two CylinderGeometry(0.05, 0.05, 3, 6) poles per billboard

### 7. Pit Buildings
Place along the start/finish straight, perpendicular to track direction:
- Track start point + start tangent direction
- 7 buildings: BoxGeometry(5, 3, 8) spaced 6 units apart along start tangent
- Offset 16 units to the left of start (-right direction)
- Roof: BoxGeometry(5.2, 0.2, 8.2) with metal material
- Color: wall=`0x556677`, roof=`0x778899`

### 8. Finish Line + Gantry
- 15 checkered PlaneGeometry(0.8, 0.8) squares spanning the track width
- Alternating white/black colors
- Placed at y=0.2 (slightly above road surface)
- Rotated to track start tangent
- Neon gantry: 2 box pillars (0.5×8×0.5) at sides, 1 box beam (15×0.5×0.5) at top
- Cyan emissive material, cone spikes on top, PointLight(cyan, 2, 20) for illumination

### 9. Trees
Two rings of procedural trees at increasing distances:
- Ring 0: 30 trees, distance = trackWidth/2 + 12 + random(30), offset ring*40
- Ring 1: 50 trees, same formula + 40
- Each tree: CylinderGeometry trunk (height 2-5m, radius 0.08-0.15) + SphereGeometry crown (radius 0.8-1.3, squashed Y)
- Crown colors: two shades of green (`0x2a5a2a`, `0x3a7a3a`)
- Random position along the curve, randomly on left or right side

## Performance Considerations

- 300 track segments × 2 verts = 600 verts for track surface (trivial)
- 150+ trees = 150+ meshes (acceptable, each is low-poly)
- TubeGeometry barriers = most expensive geometry (use 6 radial segments, not 16)
- Canvas texture is generated once per game start (not per frame) — acceptable
- Total object count with all elements: ~600 meshes

## Pitfalls

- **Trees inside track**: Always compute offset from track curve + random distance. Without randomness, trees form uniform rings.
- **Grandstands too close**: Must be outside barrier line. barrier at trackWidth/2 + 0.5, grandstand at trackWidth/2 + 15.
- **Pit buildings oriented wrong**: Must rotate to start tangent angle, not world axes.
- **Canvas texture generation in switchCircuit**: When switching circuits, regenerate the canvas texture (don't reuse old one).
- **Memory**: Each circuit switch creates new meshes. The old ones are removed by `scene.clear()`, but BufferGeometry is not disposed. For a game with circuit switching, cache geometries or accept the mild memory leak.
