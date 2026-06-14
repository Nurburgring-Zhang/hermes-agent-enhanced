# Real Car Physics Reference Data

Collected from manufacturer specs, automotive databases, motorsport literature. Used as reference for tuning game physics parameters.

## 7 Reference Cars — Full Specs

### 1. Audi TT 8J (2006-2010)
| Parameter | Value |
|-----------|-------|
| Engine | 2.0L TFSI EA113 I4 Turbo |
| HP | 200hp@5100rpm (2006-08), 211hp@4300rpm (2008-10) |
| Torque | 280Nm @ 1,800-5,000rpm (flat plateau) |
| 0-100km/h | 6.4s (Quattro) |
| Curb Weight | 1,395kg (Quattro) |
| Weight Dist | 57%F / 43%R |
| Gear Ratios (6MT) | 3.300/1.940/1.310/1.030/0.820/0.680, FD 4.230 |
| Tire | 225/45R17 base, 225/40R18 sport |

### 2. Nissan 350Z (2003-2008)
| Parameter | Value |
|-----------|-------|
| Engine | VQ35DE 3.5L V6 (DE) / VQ35HR 3.5L V6 (HR) |
| HP | 287hp@6200rpm (DE), 306hp@6800rpm (HR) |
| Torque | 363Nm @ 4,800rpm (both) |
| 0-100km/h | 5.5s (manual) |
| Curb Weight | 1,450kg |
| Weight Dist | 53%F / 47%R |

### 3. Ferrari 360 Modena (1999-2005)
| Parameter | Value |
|-----------|-------|
| Engine | F131 3.6L V8 |
| HP | 400hp@8500rpm |
| Torque | 373Nm @ 4,750rpm |
| 0-100km/h | 4.5s |
| Curb Weight | 1,390kg dry / 1,470kg curb |
| Weight Dist | 43%F / 57%R |
| Top Speed | 295km/h |

### 4. BMW M3 E46 (2000-2006) — PRIMARY BENCHMARK
| Parameter | Value |
|-----------|-------|
| Engine | S54B32 3.2L I6 |
| HP | 343hp@7900rpm (US), 338hp@7900rpm (EU) |
| Torque | 365Nm @ 4,900rpm |
| 0-100km/h | 5.2s |
| Curb Weight | 1,495kg (coupe manual) |
| Weight Dist | 52%F / 48%R |
| Gear Ratios (Getrag 420G) | 4.23/2.53/1.67/1.23/1.00/0.83, FD 3.62 |
| Tire | 225/45R18 F, 255/40R18 R |
| Redline | 8,000rpm (8,200 CSL) |

### 5. Corvette C6 (2005-2013)
| Parameter | Value |
|-----------|-------|
| Engine | LS2 6.0L V8 (2005-07) / LS3 6.2L V8 (2008-13) |
| HP | 400hp@6000rpm (LS2), 436hp@5900rpm (LS3) |
| Torque | 575Nm@4400rpm (LS2), 569Nm@4600rpm (LS3) |
| 0-100km/h | 4.3s (LS2), 4.1s (LS3) |
| Curb Weight | 1,441kg |
| Weight Dist | 51%F / 49%R |

### 6. Toyota Supra MKIV (1993-2002)
| Parameter | Value |
|-----------|-------|
| Engine | 2JZ-GTE 3.0L I6 Twin-Turbo |
| HP | 320hp@5600rpm (US), 276hp underrated (JDM) |
| Torque | 440Nm@3600rpm (actual) |
| 0-100km/h | 5.0s |
| Curb Weight | 1,580kg (manual) |
| Weight Dist | 53%F / 47%R |

### 7. McLaren F1 (1992-1998)
| Parameter | Value |
|-----------|-------|
| Engine | BMW S70/2 6.1L V12 |
| HP | 618hp@7400rpm |
| Torque | 651Nm @ 4,000-5,600rpm |
| 0-100km/h | 3.2s |
| Curb Weight | 1,140kg |
| Weight Dist | 42%F / 58%R |

## Tire Grip Coefficients (mu)

| Tire Type | Longitudinal mu | Lateral mu | Sliding mu |
|-----------|----------------|------------|------------|
| All-season street | 0.80-0.90 | 0.70-0.85 | 0.70 |
| UHP summer street | 0.95-1.10 | 0.90-1.05 | 0.80 |
| R-compound semi-slick | 1.10-1.20 | 1.05-1.20 | 0.90 |
| Racing slick (warm) | 1.30-1.60 | 1.30-1.70 | 1.00-1.10 |

**Load sensitivity**: mu decreases ~8% per 100% load increase.

## Aerodynamic Reference

| Vehicle | Cd | Frontal Area (m²) | Cd*A |
|---------|-----|-------------------|------|
| Family sedan | 0.28-0.32 | 2.10-2.30 | 0.59-0.64 |
| Sports coupe | 0.29-0.34 | 1.90-2.10 | 0.55-0.61 |
| GT race car | 0.35-0.42 | 1.80-2.00 | 0.63-0.70 |
| F1 open wheel | 0.70-1.10 | 1.40-1.50 | 0.98-1.05 |

**Downforce**: Street: CL=-0.05 to +0.10 / Race wing: CL=-1.0 to -2.0 / F1: CL=-2.5 to -3.0

## Suspension Reference

| Setup | Spring Rate Front | Spring Rate Rear | Damping Bump | Damping Rebound | Bump:Rebound |
|-------|-------------------|------------------|--------------|-----------------|--------------|
| Street comfort | 25-45 N/mm | 20-35 N/mm | 800-1500 N-s/m | 1500-2500 N-s/m | 1:2 |
| Sport street | 35-55 N/mm | 30-50 N/mm | 1200-2000 | 2000-3500 | 1:1.7-1.8 |
| Track/club | 80-140 N/mm | 70-120 N/mm | 1800-3500 | 3000-6000 | 1:1.5-1.7 |
| GT race car | 140-250 N/mm | 120-200 N/mm | 2500-5000 | 4000-8000 | 1:1.2-1.5 |
