# Real Racing Circuit Control Points (CatmullRom3)

Generated circuit data for 7 real-world circuits usable with Three.js CatmullRomCurve3.
All coordinates scaled for game use (factor 30-60x). Each circuit is a closed loop.

## Circuit Definitions

### 1. Silverstone Circuit (UK) — F1 British GP
- Real length: 5,891m, Game scale: 50x
- 22 control points covering Copse, Maggots, Becketts, Hangar Straight, Stowe, Club, Abbey
- Key feature: High-speed esses sequence (Copse-Maggots-Becketts)
- Difficulty: HARD

### 2. Spa-Francorchamps (Belgium) — F1 Belgian GP
- Real length: 7,004m, Game scale: 50x
- 15 control points covering La Source, Eau Rouge, Raidillon, Kemmel Straight, Pouhon, Blanchimont
- Key feature: Eau Rouge elevation (y goes from 0 → 0.25s → 0), 19 corners
- Difficulty: EXPERT

### 3. Monza (Italy) — F1 Italian GP
- Real length: 5,793m, Game scale: 60x
- 14 control points covering Rettifilo, Curva Grande, Lesmo 1&2, Ascari, Parabolica
- Key feature: High-speed circuit, long straights, only 11 corners
- Difficulty: NORMAL

### 4. Nürburgring Nordschleife (Germany) — The Green Hell
- Real length: 20,832m, Game scale: 30x
- 24 control points covering Hatzenbach, Flugplatz, Fuchsröhre, Karussell, Brünnchen, Pflanzgarten
- Key feature: Extreme elevation changes (y from -0.3s to +0.3s), 73 corners, longest track
- Difficulty: EXTREME

### 5. Monaco (Monaco) — F1 Monaco GP
- Real length: 3,337m, Game scale: 20x
- 14 control points covering Sainte Devote, Casino, Fairmont Hairpin, Tabac, Piscine, Rascasse
- Key feature: Narrow street circuit, slowest F1 track, Fairmont hairpin ~180 degree turn
- Difficulty: EXPERT

### 6. Circuit de la Sarthe / Le Mans (France)
- Real length: 13,629m, Game scale: 80x
- 14 control points covering Dunlop, Tertre Rouge, Mulsanne Straight (huge gap), Mulsanne Chicane, Indianapolis, Arnage, Porsche Curves, Ford Chicane
- Key feature: 6km Mulsanne straight requires only 2-3 control points across it
- Difficulty: HARD

### 7. Suzuka (Japan) — F1 Japanese GP
- Real length: 5,807m, Game scale: 45x
- 13 control points covering First Corner, S-Curves, Dunlop, Degner, Hairpin, Spoon, 130R, Casio Triangle
- Key feature: Only figure-8 layout in F1, 130R high-speed kink, S-curves complex
- Difficulty: EXPERT

## Usage Pattern

```typescript
const circuit = CIRCUITS.find(c => c.id === 'circuit_silverstone');
const spline = new THREE.CatmullRomCurve3(circuit.controlPoints, true, 'catmullrom', 0.5);
const trackPoints = spline.getPoints(200);

// Generate track surface from edges
for (let i = 0; i < trackPoints.length; i++) {
    const tangent = spline.getTangent(i / trackPoints.length);
    const normal = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize();
    const left = trackPoints[i].clone().add(normal.clone().multiplyScalar(-7));
    const right = trackPoints[i].clone().add(normal.clone().multiplyScalar(7));
}
```

## Pitfalls

1. **Scene scale**: Game coordinates should feel natural (track ~50 units across), NOT match real-world meters (5000+). Always scale down.
2. **Closure**: The last control point should be the same as the first for a closed circuit. Set CatmullRomCurve3's `closed=true` parameter.
3. **Elevation**: Only Spa and Nürburgring have significant y variation. Flat circuits (Monza, Silverstone) use y=0 throughout.
4. **Point density**: Long straights need fewer points (2-3) to avoid creating artificial wobble in the curve.
5. **Scene cleanup**: Switching circuits requires re-adding ambient + directional light after scene.clear().
