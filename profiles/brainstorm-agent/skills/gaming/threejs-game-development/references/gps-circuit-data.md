# GPS-Based Circuit Data for Three.js Racing Games

## Conversion Formulas

```python
import math

def gps_to_local(lat, lon, center_lat, center_lon):
    """GPS coordinates to local meters"""
    meters_per_deg_lat = 111000
    meters_per_deg_lon = 111000 * math.cos(math.radians(center_lat))
    dx = (lon - center_lon) * meters_per_deg_lon
    dz = (lat - center_lat) * meters_per_deg_lat
    return (dx, dz)
```

## 7 Real Circuits with GPS Centers

### Silverstone (UK) — 52.0711°N, 1.0161°W
- 5.891km, 18 turns
- Real corner sequence: Abbey→Farm→Village→Loop→Aintree→Wellington Straight→Brooklands→Luffield→Copse→Maggots→Becketts→Chapel→Hangar Straight→Stowe→Vale→Club
- 25 control points, range x[-700,480] z[-580,380]

### Spa-Francorchamps (Belgium) — 50.4372°N, 5.9714°E
- 7.004km, 19 turns, elevation -20 to +60m
- Eau Rouge/Raidillon climb essential
- 19 control points with Y-axis elevation

### Monza (Italy) — 45.6156°N, 9.2811°E
- 5.793km, 11 turns, flat
- High-speed circuit

### Nürburgring Nordschleife (Germany) — 50.3356°N, 6.9475°E
- 20.832km, 73 turns (26 simplified), elevation -70 to +70m
- Karussell spiral corner essential

### Monaco — 43.7347°N, 7.4206°E
- 3.337km, 19 turns, elevation -10 to +18m
- Narrowest and slowest F1 circuit

### Le Mans (France) — 47.9498°N, 0.2072°E
- 13.629km, Mulsanne straight ~6km
- 18 control points

### Suzuka (Japan) — 34.8431°N, 136.5411°E
- 5.807km, 18 turns, unique figure-8 layout
- 21 control points, crosses over itself

## 1:1 Meter Scale Requirements

When user demands 1 game unit = 1 real meter:
- `gameLength` must equal real-world length
- Ground plane: `Math.max(600, trackBounds.size * 1.5)`
- Camera height: `Math.max(15, trackBounds.size * 0.15)`
- Collision sampling: `Math.min(2000, Math.max(500, trackLength/5))`
- AI speed formula: `aiSpeed / trackLength`
