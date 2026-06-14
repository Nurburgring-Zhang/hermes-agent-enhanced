# SOTA Super-Resolution Model Research (2024-2025)

## Best PSNR Models (×4 SR on Urban100)

| Model | Set5 | Set14 | Urban100 | Manga109 | Params | Speed (V100) | Architecture |
|-------|------|-------|----------|----------|--------|-------------|-------------|
| **HAT** | 38.15 | 33.88 | 29.01 | 33.82 | 80M | ~2s | Channel+Spatial+Window attention |
| **HAT-L** | 38.35 | 34.20 | 29.55 | 33.83 | 310M | ~3-4s | Bigger HAT |
| **SRFormer** | 38.16 | 33.92 | 29.05 | 33.49 | 60M | ~1.5s | Sparse attention |
| **DAT** | 38.27 | 33.86 | 28.71 | 33.18 | 26M | ~0.8s | Dual aggregation |
| **MambaIR** | 38.20 | 33.83 | 28.81 | 33.12 | 22M | ~0.7s | State space model |
| **SwinIR** | 38.20 | 33.77 | 27.67 | 32.57 | 12M | ~0.5s | Window attention |
| **Real-ESRGAN** | — | — | — | — | 17M | ~0.3s | RRDB + GAN |

## Official Weight Download URLs

| Model | Source | Format |
|-------|--------|--------|
| **HAT** | https://github.com/XPixelGroup/HAT | .pth |
| **SwinIR** | https://github.com/JingyunLiang/SwinIR | .pth |
| **DAT** | https://github.com/zhengchen1999/DAT | .pth |
| **SRFormer** | https://github.com/HVision-NKU/SRFormer | .pth |
| **Real-ESRGAN** | https://github.com/xinntao/Real-ESRGAN | .pth |
| **ResShift** | https://github.com/zsyOAOA/ResShift | .pth |
| **MambaIR** | https://github.com/csguoh/MambaIR | .pth |

## Self-Ensemble Quality Boost

| Method | PSNR Gain | Cost |
|--------|-----------|------|
| Flip H+V (4x) | +0.1~0.3 dB | 4x |
| Multi-model avg | +0.2~0.4 dB | 3~5x |
| HAT-L 8x ensemble | +0.3~0.5 dB | 8x |

## Key Insight for Implementation

The best practice is to integrate HAT (80M) as the default premium model for PSNR priority,
Real-ESRGAN for visual quality, and DAT/SwinIR for speed. The content analyzer can detect
anime vs realistic images and auto-select.
