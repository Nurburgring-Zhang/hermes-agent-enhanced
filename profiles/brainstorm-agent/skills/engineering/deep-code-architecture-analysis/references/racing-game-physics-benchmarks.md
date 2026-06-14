# 竞速游戏物理/渲染参数基准 (2026年Top Tier对照表)

## 物理参数对标

| 参数 | Forza Motorsport | Assetto Corsa Competizione | Mario Kart (对标) | 休闲Web竞速建议 |
|------|-----------------|---------------------------|-------------------|----------------|
| 重力 | -9.81 m/s² | -9.81 m/s² | -39.24 (×4) | **-29.4** (×3, 街机感强) |
| 车辆质量 | 1200-1800kg | 1250-1650kg | 200-500kg | **300-800kg** |
| 轮胎抓地力μ | 0.8-1.2 | 1.0-1.4 (热态) | 1.2-2.0 | **1.0-1.5** |
| 最大速度 | 250-380 km/h | 280-340 km/h | 80-150 km/h | **80-250 km/h** |
| 0-100加速 | 2.5-6.0s | 3.0-5.0s | 3.0-5.0s | **2.0-4.0s** (夸张) |
| 空气阻力 | CFD精度模型 | CFD+风洞数据 | 简化线性拖拽 | **kv² 基础模型** |
| 悬挂行程 | 80-120mm | 60-100mm | 50-80mm | **100-200mm** (高弹力) |
| 碰撞反弹系数 | 0.1-0.3 | 0.05-0.15 | 0.5-0.8 | **0.6-0.8** (戏剧效果) |
| 转向最大角 | 30-40° | 25-35° | 45-55° | **35-50°** |
| 悬挂刚度K | 30-60 kN/m | 40-80 kN/m | 15-30 kN/m | **20-40 kN/m** |
| 悬挂阻尼C | 2000-5000 N·s/m | 3000-6000 N·s/m | 1000-2000 | **1500-3000** |

## 物理引擎选择 (Web)

| 引擎 | 车辆物理 | 碰撞检测 | 确定性 | 适用性 |
|------|---------|---------|--------|--------|
| Cannon-es + RaycastVehicle | 四轮独立悬挂+轮胎 | 基础Box/BVH | 低 | ⭐ 首选(Web休闲竞速) |
| Rapier.rs (WASM) | 基础刚体+约束 | SAT+CCD | 高 | 高性能Web需要 |
| Ammo.js (Bullet) | RaycastVehicle+约束 | GJK+CCD | 中 | 复杂物理需要 |
| Jolt.js (WASM) | 完整车辆约束 | GJK+CCD | 高 | 移植Jolt Physics |

**建议**: Cannon-es RaycastVehicle 足够。RaycastVehicle提供:
- 四轮独立悬挂(spring length/stiffness/damping)
- 轮胎摩擦力模型(slip friction)
- 转向几何(前轮maxSteerAngle)
- 驱动力分布(engineForce + 后驱/四驱切换)

## 轮胎物理层

```
Cannon-es RaycastVehicle 轮胎模型 (简化Pacejka):
  
  纵向摩擦力 = f(slipRatio, normalForce, frictionCoeff)
  侧向摩擦力 = f(slipAngle, normalForce, frictionCoeff)
  
  其中:
    slipRatio = (wheelSpeed - vehicleSpeed) / vehicleSpeed
    slipAngle = atan2(lateralSpeed, longitudinalSpeed)
  
  关键参数:
    frictionCoefficient: 0.6(湿滑) ~ 1.5(高抓地力)
    maxSlip: 0.2(普通) ~ 0.5(漂移模式)
    rollingResistance: 0.01-0.03
```

## 赛道生成参数

| 参数 | 说明 | 建议值 |
|------|------|--------|
| CatmullRom控制点间距 | 每个控制点间距离 | 50-100m |
| 赛道宽度 | 可行驶区域 | 15-25m |
| 曲线半径 | 最小转弯半径 | 50-200m |
| 高度变化 | 上坡/下坡幅度 | ±5-30m |
| 段类型分布 | 直线:弯道:坡道 | 40%:35%:25% |
| 表面摩擦 | 沥青/砂石/草地 | 1.0/0.6/0.4 |
| 检查点数量 | 每圈 | 每隔300-500m一个 |

## 渲染对标

| 效果 | 3A竞速(UE5) | Web竞速(Three.js) | 本项目目标 |
|------|------------|------------------|-----------|
| 色调映射 | ACES | ACESFilmicToneMapping | ACESFilmicToneMapping |
| 抗锯齿 | TAA + MSAA | FXAA/SMAA | SMAA (通过后处理) |
| 阴影 | DFShadow/VSM | PCFSoft/PCSM | PCFSoftShadowMap |
| 反射 | Lumen/RT Reflection | CubeMap/SSR | SSR (ScreenSpaceReflector) |
| 运动模糊 | 相机+物体运动模糊 | VelocityPass | 简化运动模糊 |
| Bloom | 自适应 | UnrealBloomPass | UnrealBloomPass |
| SSAO | HBAO+ | SSAOPass | SSAOPass |
| 景深 | Bokeh物理DOF | BokehPass | BokehPass (菜单/过场) |

## 车辆配置→物理参数映射

```typescript
// VehicleAttributes → PhysicsBody 映射函数
function mapVehicleToPhysics(attrs: VehicleAttributes): RaycastVehicleParams {
  return {
    mass: attrs.weight,                          // kg
    engineForce: attrs.enginePower * 2,           // N
    maxSpeed: attrs.maxSpeed / 3.6,               // m/s
    brakeForce: attrs.braking * 200,              // N
    maxSteerAngle: (attrs.steering / 10) * 0.5,   // radians
    friction: attrs.tireGrip / 10 * 1.2,          // μ
    damping: attrs.dragCoefficient * 10,          // linearDamping
    suspensionStiffness: (attrs.suspensionStiffness / 10) * 40,  // kN/m
    restLength: attrs.suspensionHeight / 1000,     // m
    gearRatios: calculateGearRatios(attrs.gearCount, attrs.finalDrive)
  };
}
```

## 参考游戏控制手感参数

| 手感类型 | 漂移半径 | 转向灵敏度 | 油门响应 | 适合游戏类型 |
|---------|---------|-----------|---------|------------|
| 街机型 | 大(易漂) | 高 | 快 | Mario Kart, NFS |
| 平衡型 | 中 | 中 | 中 | GRID, Forza Horizon |
| 模拟型 | 小(精确) | 低 | 慢 | Assetto Corsa, iRacing |

**本项目建议**: 街机+平衡混合型 (毛绒玩具风格需要易上手但保留微操深度)
