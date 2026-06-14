# Real Vehicle Physics Reference Data (2026-05-30 Session)

Compiled from manufacturer specs and motorsport engineering sources for 7 real vehicles used as calibration targets.

## 7 Car Specs Used for Physics Calibration

All data sourced from manufacturer published specs and verified against automotive databases.

| Parameter | Audi TT 8J | Nissan 350Z | Ferrari 360 | BMW M3 E46 | Corvette C6 | Toyota Supra MK4 | McLaren F1 |
|-----------|-----------|-------------|-------------|------------|-------------|------------------|------------|
| Year | 2006-2010 | 2003-2008 | 1999-2005 | 2000-2006 | 2005-2013 | 1993-2002 | 1992-1998 |
| Engine | 2.0L TFSI I4T | VQ35DE/HR V6 | F131 V8 | S54B32 I6 | LS2/LS3 V8 | 2JZ-GTE I6TT | S70/2 V12 |
| HP | 200-211 | 287-306 | 400 | 343 | 400-436 | 320+ | 618-627 |
| Torque (Nm) | 280 | 363 | 373 | 365 | 575 | 440 (actual) | 651 |
| 0-100 km/h (s) | 6.4 | 5.5 | 4.5 | 5.2 | 4.3 | 5.0 | 3.2 |
| Top Speed (km/h) | 240 | 250 | 295 | 250 | 300 | 280 | 386 |
| Weight (kg) | 1395 | 1450 | 1470 | 1495 | 1441 | 1580 | 1140 |
| Weight Dist (F/R) | 57/43 | 53/47 | 43/57 | 52/48 | 51/49 | 53/47 | 42/58 |
| Cd | 0.33 | 0.34 | 0.34 | 0.32 | 0.31 | 0.33 | 0.32 |
| Frontal Area (m²) | 2.04 | 2.10 | 1.97 | 2.12 | 2.06 | 2.08 | 1.79 |

## Tire Grip Coefficients

| Tire Type | Peak Longitudinal mu | Peak Lateral mu | Sliding mu |
|-----------|--------------------|-----------------|------------|
| All-season street | 0.80-0.90 | 0.70-0.85 | ~0.70 |
| UHP summer | 0.95-1.10 | 0.90-1.05 | ~0.80 |
| R-compound semi-slick | 1.10-1.20 | 1.05-1.20 | ~0.90 |
| Racing slick (warm) | 1.30-1.60 | 1.30-1.70 | 1.00-1.10 |

## Suspension Rates (N/mm)

| Setup | Front (N/mm) | Rear (N/mm) | Bump:Rebound Ratio |
|-------|-------------|------------|-------------------|
| Street comfort | 25-45 | 20-35 | 1:2 |
| Sport street | 35-55 | 30-50 | 1:1.7-1.8 |
| Performance street | 50-80 | 45-75 | 1:1.7-1.8 |
| Track/Club sport | 80-140 | 70-120 | 1:1.5-1.7 |
| GT race car | 140-250 | 120-200 | 1:1.5 |
| Formula car | 250-500+ | 200-400+ | 1:1.2 |

## Damping Coefficients (N-s/m)

| Setup | Front Bump | Front Rebound | Rear Bump | Rear Rebound |
|-------|-----------|--------------|-----------|-------------|
| Street comfort | 800-1500 | 1500-2500 | 700-1300 | 1300-2200 |
| Sport street | 1200-2000 | 2000-3500 | 1000-1800 | 1800-3000 |
| Track/Club | 1800-3500 | 3000-6000 | 1500-3000 | 2500-5500 |
| Race | 2500-5000 | 4000-8000 | 2000-4500 | 3500-7000 |

## Magic Formula Tire Model Parameters

| Parameter | Value Range | Default | Notes |
|-----------|-------------|---------|-------|
| B (stiffness) | 6-12 | 9 | Higher = stiffer response, more peak force at small slip angles |
| C (shape) | 1.2-1.6 | 1.3 | Typically 1.3 for lateral, 1.65 for longitudinal |
| D (peak) | 0.8-1.7 | 1.0 | = peak mu coefficient |
| E (curvature) | -1.0 to +1.0 | -0.3 | Negative = peak-and-drop (realistic), positive = peak-and-plateau |

## Natural Frequencies vs Spring Rate Guide

| Application | Natural Freq (Hz) | Equivalent (for 350kg sprung mass) |
|-------------|------------------|--------------------------------------|
| Street comfort | 1.0-1.5 | 14-31 N/mm |
| Sport street | 1.5-2.2 | 31-67 N/mm |
| Track/Club | 2.0-3.0 | 55-124 N/mm |
| GT Race | 2.5-4.0 | 86-221 N/mm |
| Formula | 3.5-5.0 | 169-346 N/mm |

## Power-to-Weight Ratios (used for accelMultiplier baseline)

| Vehicle | HP/kg | Ratio vs M3 E46 (0.229) |
|---------|-------|------------------------|
| Audi TT 8J | 0.151 | 0.66x |
| Nissan 350Z | 0.211 | 0.92x |
| Ferrari 360 | 0.272 | 1.19x |
| BMW M3 E46 | 0.229 | **1.00x (BASELINE)** |
| Corvette C6 | 0.302 | 1.32x |
| Toyota Supra | 0.203 | 0.89x |
| McLaren F1 | 0.542 | 2.37x |
