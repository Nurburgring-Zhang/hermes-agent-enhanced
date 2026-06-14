# VDrift Physics Engine Structure

## Engine (`carengine.h`)
```
max-power = 343 (hp)
peak-engine-rpm = 7900
rpm-limit = 8000
inertia = 0.28 (kg-m²)
idle = 800
start-rpm = 600
stall-rpm = 400
```

## Transmission (`cartransmission.h`)
```
gears = 6
gear-ratio-r = 3.0 (reverse)
gear-ratio-1 = 4.23
gear-ratio-2 = 2.53
gear-ratio-3 = 1.67
gear-ratio-4 = 1.23
gear-ratio-5 = 1.00
gear-ratio-6 = 0.83
final-drive = 3.62 (differential)
shift-time = 0.3
```

## Suspension (`carsuspension.h`)
```
spring-constant = 55000 (N/m)
bounce = 1800 (N-s/m compression damping)
rebound = 3000 (N-s/m rebound damping)
travel = 0.13 (m)
anti-roll = 18000 (N-m/rad)
camber = -1.0 (degrees)
caster = 5.0 (degrees)
toe = 0.1 (degrees)
```

## Tire Pacejka (`cartire2.h`)
Coefficients a0-a14 (lateral), b0-b10 (longitudinal), c0-c17 (aligning):
```
# Lateral (a0=Fz0, a1=PCY1, a2=PDY1, a3=PDY2...)
a0=4000  # nominal load N
a1=1.2   # shape factor
a2=1.0   # peak factor
a3=0.0   # curvature factor
...
```

## Brake (`carbrake.h`)
```
friction = 0.4
max-pressure = 2000000 (Pa ~20bar)
radius = 0.14 (m)
area = 0.02 (m²)
bias = 0.65 (65% front)
handbrake = 0.0
```

## Tire Dimensions (`carwheel.h`)
```
tire.size = 225 45 17  (width mm, aspect ratio %, rim diameter inches)
```
Width = 225mm, Aspect ratio = 45%, Rim = 17inch
Tire radius = 17*0.5*0.0254 + 0.225*0.45 = 0.317m
