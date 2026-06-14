# Vehicle Tier and Paint System Reference

## 5-Tier Vehicle Classification

Architecture in `src/vehicles/VehicleTierSystem.ts`:

```
enum VehicleTier { TIER_1_HOT_HATCH=1, TIER_2_SPORTS_CAR=2, TIER_3_SUPERCAR=3, TIER_4_RACE_CAR=4, TIER_5_PROTOTYPE=5 }
```

Each tier has `VehicleTierInfo`: name, description, UI color, speedRange [min,max], accelRange, priceRange, aiSkillRange, assistLevel.

Mapping function: `getVehicleTier(type: string)` uses a lookup table.

## Paint System

Architecture in `src/vehicles/PaintSystem.ts`:

```
enum PaintCategory { SOLID, METALLIC, MATTE, PEARL, CHROME, CUSTOM, LIVERY, CAMOUFLAGE, GRADIENT, NEON }
```

Each `PaintScheme` has: id, name, category, primaryColor, (optional secondaryColor, accentColor, wheelColor, caliperColor, interiorColor, stripeColor), liveryPattern, metallicness/roughness/clearcoat, emissiveColor, price.

Real-world racing liveries included: Gulf Oil (blue/orange), Martini (white/blue/red), Castrol (green/white/red), Monster Energy (black/green).

Registry: `PaintSchemeRegistry` (singleton). Register schemes per vehicle or per vehicle class. Auto-registers defaults for 'sports_car_default', 'race_car_default', 'hot_hatch_default'.

## Vehicle Database

`VehicleDatabase` (singleton) now auto-loads all vehicle configs via:
```typescript
const files = [
    require('./configs/vehicles_001_020'),
    // ... 5 files total
];
files.forEach(mod => {
    Object.keys(mod).forEach(key => {
        const val = mod[key];
        if (val && typeof val === 'object' && val.id) {
            vehicles.set(val.id, val);
        }
    });
});
```

## Complete Vehicle Data Structure

```typescript
interface VehicleConfig {
    id, name, type (VehicleType), category, year, manufacturer, country, price
    driveType (RWD/FWD/AWD), transmissionType (Manual/Automatic/DCT/CVT)
    engineType, engineLayout
    attributes: VehicleAttributes
    appearance: VehicleAppearance
    sound: VehicleSound
    ai: VehicleAI
    unlockConditions, stats, upgrades, customizations, specialAbilities
    hiddenStats
}
```

`VehicleAttributes` covers: maxSpeed, acceleration, braking, handling, stability, grip, steering, downforce, enginePower, engineTorque, redline, displacement, weight, powerToWeight, wheelBase, trackWidth, centerOfMass, dragCoefficient, frontalArea, liftCoefficient, gearCount, finalDrive, differentialLock, suspensionStiffness, suspensionHeight, camber, toe, tireSize, tireGrip, tireWear, fuelCapacity, fuelConsumption.

`VehicleAppearance` covers: primaryColor, secondaryColor, accentColor, bodyMaterial, metalness, roughness, clearcoat, neonLights/colors, exhaustFlames, tireSmoke, bodyKit, spoilers, diffusers, sideSkirts, frontSplitter, wheelType/Color/Size, tireProfile, windowTint, headlight/taillight types, decals, stripes, logos, customParts, animations.
