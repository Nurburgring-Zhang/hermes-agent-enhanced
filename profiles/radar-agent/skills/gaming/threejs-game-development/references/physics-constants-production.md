# Production-Verified Physics Constants

These constants were validated through W-test and visual inspection in the racing game project.

## Working Configuration (M3 E46 base)

### Engine
```
ENGINE_MAX_TORQUE_NM = 365    // @4900rpm
ENGINE_MAX_RPM = 8000
ENGINE_IDLE_RPM = 800
ENGINE_TORQUE_AT_IDLE = 0.75  // 75% at idle (confirmed working)
```

### Transmission
```
GEAR_RATIOS = [4.23, 2.53, 1.67, 1.23, 1.00, 0.83]
FINAL_DRIVE = 3.62
WHEEL_RADIUS = 0.33
SHIFT_TIME = 0.35
```

### Auto-shift logic (street car tuned)
```
gear 1 -> 2: shift at 5500rpm  (quick exit from first)
gear 2+ -> : shift at 6200rpm  (mid-RPM, not redline)
downshift:  when rpm < 1500 AND speed > 2m/s
```

### Forward Motion
```
worldDz = -cosA * localVx - sinA * localVy  (Z- is forward)
atan2(tangent.x, -tangent.z)                matches Z- forward
```

### Camera (Z- forward = car heads Z-)
```
behind = (-sin * dist, height, +cos * dist)  // camera in Z+ behind car
lookTarget ahead: carPos + 2m in car's forward direction (Z-)
```

## Real Car Specs (for VDrift models in project)

| ID | Car | HP | kg | Gears | FD |
|----|-----|-----|-----|-----|-----|
| ATT | Audi TT 8J | 200 | 1395 | 3.30/1.94/1.31/1.03/0.82/0.68 | 4.23 |
| 350Z | Nissan 350Z | 287 | 1450 | 3.79/2.32/1.62/1.27/1.00/0.79 | 3.36 |
| 360 | Ferrari 360 | 400 | 1390 | 3.29/2.16/1.61/1.27/1.03/0.85 | 4.44 |
| CO | Caterham 7 | 175 | 540 | 2.69/1.81/1.26/1.00/0.82/0.68 | 3.62 |
| CS | Corvette C6 | 436 | 1441 | 2.97/2.07/1.43/1.00/0.71/0.57 | 3.42 |
| M3 | BMW M3 E46 | 343 | 1495 | 4.23/2.53/1.67/1.23/1.00/0.83 | 3.62 |
