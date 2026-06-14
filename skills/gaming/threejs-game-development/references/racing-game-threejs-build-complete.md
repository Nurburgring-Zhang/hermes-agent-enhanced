---
name: racing-game-threejs-build
description: 基于Three.js的赛车游戏开发与调试 — VDrift模型加载、坐标转换、物理引擎实现
---

# Three.js赛车游戏开发

## 核心约束
- VDrift模型原始坐标系: x=左右, y=上下, z=前后(y+车头? 有歧义)
- Three.js标准: Y-up坐标系 (x=左右, y=上下, z=前后, z-车头)
- **VDrift→Three.js转换: 只有`z = -z`取反**（VDrift z+车尾→Three.js z-车头）。**不需要Z-up→Y-up，VDrift本身就是Y-up。**
- 车头朝Z-方向

## VDrift IDP2 JOE格式解析（精确二进制格式）

### 文件结构
```
Header(20B): magic(4) + version(4) + num_faces(4) + num_frames(4) + flags(4)
  ↓
每帧:
  Face数据: num_faces个 × JoeFace(18B) = num_faces × 9×uint16
    9个uint16: v0,v1,v2, n0,n1,n2, t0,t1,t2
    → 所有索引是**全局的**（指向整个verts数组, 不是fi*3+local）
  ↓
  3个uint32(12B): num_verts | num_texcoords | ???(nnorm,不可靠)
    → **第三个uint32不可靠**(许多文件存储的是法线数据中第一个float的二进制值)
    → 实际法线数 = 从剩余字节自动推导
  ↓
  Vertex数据: num_verts个 × JoeVertex(12B) = num_verts × 3×float (x,y,z)
  ↓
  Normal数据: 从剩余字节按12B/组自动解析,直到遇到超出±1.5范围的值
    → 实际法线数 ≈ (剩余字节 - 纹理字节) / 12
    → 如果法线面索引最大值 > 解析到的法线数,扩大法线数再试
  ↓
  TexCoord数据: 剩余字节按8B/组解析 (u,v float)
    → 如果解析到0组,创建1个默认UV (0,0)
```

### 自动推导法线数（关键！）
```python
remaining = len(raw) - pos_after_verts
max_norm = remaining // 12
max_ni = max(face.n0, face.n1, face.n2 across all faces)

# 尝试候选法线数
candidates = [num_tex_input, max_norm, max_ni + 1]
for candidate in candidates:
    if 0 < candidate <= max_norm:
        # 验证：读取candidate个法线,检查值是否合理(±100以内)
        if all_ok:
            n_norm = candidate
            break
```

### 正确解析演示（v12+）

```python
# v12.py中关键逻辑:
# 1. 读num_verts和num_tex_input（前两个uint32可靠）
# 2. 第三个uint32跳过不用（值可能是垃圾）
# 3. 读顶点数据
# 4. 从剩余字节自动识别法线（12B一组）和纹理（8B一组）
# 5. 法线验证：值在±100范围内
# 6. 索引边界检查：跳过超出顶点/法线范围的三角面
```

### 完整的解析代码

```python
def parse_frame(raw, pos, num_faces):
    # 读面数据 (18B each, 9个uint16, 全部全局索引)
    faces = []
    for fi in range(num_faces):
        v0,v1,v2 = struct.unpack_from('<HHH', raw, pos); pos+=6
        n0,n1,n2 = struct.unpack_from('<HHH', raw, pos); pos+=6
        t0,t1,t2 = struct.unpack_from('<HHH', raw, pos); pos+=6
        faces.append((v0,v1,v2,n0,n1,n2,t0,t1,t2))
    
    # 读3个uint32 (第三个不可靠)
    num_verts = struct.unpack_from('<I', raw, pos)[0]; pos+=4
    num_tex_input = struct.unpack_from('<I', raw, pos)[0]; pos+=4
    _ = struct.unpack_from('<I', raw, pos)[0]; pos+=4  # 跳过
    
    # 读顶点 (12B each)
    verts = [(x,y,z) for x,y,z in ...]  # struct.unpack('<fff')
    
    # 自动推测法线数
    remaining = len(raw) - pos
    for candidate in [num_tex_input, remaining//12, max_ni+1]:
        if 0 < candidate <= remaining//12:
            # 验证法线值在合理范围
            ...
    
    # 去重: (vi,ni,ti) → unique vertex
    vmap = {}
    for face in faces:
        if v0 >= num_verts: continue  # 索引越界保护
        for j in range(3):
            key = (vi, ni, ti)
            if key not in vmap:
                vmap[key] = len(out_verts)
                out_verts.extend(verts[vi])
                out_norms.extend(norms[ni])
                out_uvs.extend([uvs[ti][0], 1-uvs[ti][1]])
            out_indices.append(vmap[key])
```

### 顶点清洗（必需步骤）

JOE解析后的顶点可能包含**异常大值**（来自越界索引保护返回的`(0,0,0)`或其他解析错误产生的畸形顶点）。必须在合并glass/interior之前做顶点清洗：

```python
cleanVerts, cleanNorms, cleanUVs, cleanIndices = [], [], [], []
vertMap = {}
for i in range(numVerts):
    x, y, z = verts[i*3], verts[i*3+1], verts[i*3+2]
    if abs(x) < 100 and abs(y) < 100 and abs(z) < 100:  # VDrift模型在±10以内
        vertMap[i] = len(cleanVerts)
        cleanVerts.extend([x, y, z])
        cleanNorms.extend([normals[i*3], normals[i*3+1], normals[i*3+2]])
        cleanUVs.extend([uvs[i*2], uvs[i*2+1]])
for idx in indices:
    if idx in vertMap:
        cleanIndices.append(vertMap[idx])
```

不清洗的后果：一个349689的顶点导致整个车身模体畸形，表现为"一团黑乎乎乱的几何体"。

### 顶点数据层转换（VDrift Y-up坐标→Three.js Y-up坐标）

VDrift坐标系和Three.js坐标系**都是Y-up**，区别仅在Z方向正负：
- VDrift: x=左右, y=上下, z=前后(z+车尾)
- Three.js: x=左右, y=上下, z=前后(z-车头)

**转换只需：`z = -z`（取反）**

```typescript
for (let i = 0; i < rawVerts.length; i += 3) {
    verts[i]   = rawVerts[i];       // x unchanged
    verts[i+1] = rawVerts[i+1];     // y unchanged (both are up!)
    verts[i+2] = -rawVerts[i+2];    // z取反: 车尾→车头方向
}
```

**⚠️ 不要用Z-up→Y-up转换 `(x, z, -y)`**：VDrift本身就是Y-up坐标系，swap y和z会让模型只有Y轴方向展开（bbox: x≈0, y=0~2.3, z≈0），变成一条竖线。

### 单mesh构建（推荐）
所有部件(glass/interior)已合并到indices数组，用单个BufferGeometry构建：

```typescript
const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.BufferAttribute(verts, 3));
geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
geo.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
geo.setIndex(new THREE.BufferAttribute(new Uint32Array(carData.indices), 1));
// 用Uint32Array而非Uint16Array，因为合并后索引可能超过65535
const mesh = new THREE.Mesh(geo, bodyMat);
group.add(mesh);
```

**不要用多部件子集提取**（vertOffset/vertCount/indexOffset），因为去重后顶点索引与原始偏移不对应，子集提取会产生空几何体或乱序几何体。

## 车轮几何体方向（标准Y-up坐标系，车头朝Z-）

车轮在Three.js Y-up坐标系中，轮胎面在XZ水平面上，轮胎轴沿X轴(左右水平)，车辆沿Z轴滚动前进。

**注意：`rotation.z = PI/2` 是正确做法！**

`LatheGeometry`默认绕Y轴旋转生成三维物体。`rotation.z = PI/2`将绕Y的旋转体绕Z轴旋转90度，使轴向变为X(左右水平)，轮胎在XZ水平面上滚动。`rotation.x = PI/2`是错误的——这会使轮胎轴变为Z方向(前后)，变成竖直轮子。

| 部件 | 几何体类型 | 默认朝向 | 修正旋转 | 结果 |
|------|-----------|---------|---------|------|
| 轮胎 | `LatheGeometry` | 绕Y轴(竖直) | `rotation.z = PI/2` | 轴向X(左右水平) |
| 轮毂 | `CylinderGeometry` | 沿Y轴 | `rotation.z = PI/2` | 沿X轴与轮胎同轴 |
| 轮辋 | `TorusGeometry` | 绕Z轴 | `rotation.z = PI/2` | 环面水平(轴向X) |
| 刹车盘 | `CylinderGeometry` | 沿Y轴 | `rotation.z = PI/2` | 盘面在XZ水平面 |

**容易犯错：** 在YZ平面(正确) vs XY平面(错误)之间混淆。关键是——车在XZ水平面上跑，轮胎在水平面上滚动，轮胎轴必须是X方向(左右)。

### 车轮位置（Three.js坐标系，无需二次转换）

wheelPositions数据已经是Three.js坐标(x左右, y上下, z前后)，`pos[2] < 0`是前轮(Z-方向=车头)：

```typescript
wg.position.set(pos[0], pos[1], pos[2]);
wg.userData.isFront = pos[2] < 0;
```

**不要做双重转换：** 如果数据已经是Three.js坐标，不能再加`(x, z, -y)`。双重转换让所有轮子位置错误。

## 轮胎位置

**注意：** wheelPositions数据已经是Three.js坐标系（x左右, y上下, z前后），**不需要再做坐标转换**。直接用 `pos[0], pos[1], pos[2]`：

```typescript
wg.position.set(pos[0], pos[1], pos[2]);
wg.userData.isFront = pos[2] < 0;  // Z-是车头
```

## 坐标转换陷阱

**不要做双重转换：** 如果wheelPositions数据已经存储为Three.js坐标，再加 `(x, z, -y)` 转换会导致所有轮子位置错误。

## 关键禁忌
- **禁止** `group.rotation.x = -PI/2` + 轮胎在group内用局部坐标 → 旋转后轮胎飞到天上
- **禁止** `playerCar.rotation.x/z = bodyRoll/bodyPitch` → 覆盖顶点转换的模型朝向
- **禁止** 用bodyGroup旋转代替顶点数据转换 → 导致坐标系混乱
- **禁止** 轮胎加在bodyGroup内 → bodyGroup旋转后轮胎位置错位
- **禁止** 调用类中不存在的函数（如`playCollisionSound`、`distanceToTrack`）→ 直接导致gameLoop崩溃
- **禁止** 赛道碰撞代码引用已删除变量（如`lateralOffset`、`trackRight`、`normalDir`）→ 编译通过但运行时未定义错误
- **禁止** `const speed = this.getSpeed()`定义后在位置积分中复用旧speed值覆盖新加的velocity → 车永远不动
- **禁止** 对wheelPositions做双重坐标转换：数据已经是Three.js坐标(x左右, z上下, y前后)，直接`set(pos[0], pos[1], -pos[2])`
- **禁止** 用`rotation.x = PI/2`转轮胎：`rotation.z = PI/2`是正确的，`rotation.x = PI/2`让轮胎竖直

## 物理引擎：摩擦圆模型（用户强制要求）

用户明确要求：**刹车力必须基于车重、轮胎摩擦系数、路面情况实时计算**，不能用固定减速度常数。加速也必须基于发动机扭矩曲线+传动比+轮胎摩擦圆。

### 摩擦圆物理模型（最终版，v12+）

**刹车/推力/转向全部基于轮胎摩擦圆：**

```typescript
const mu = 1.2;                    // 轮胎-路面摩擦系数（性能胎）
const g = 9.81;
const fzPerWheel = this.mass * g / 4;
const maxFrictionPerWheel = mu * fzPerWheel;

// 推进力（基于发动机扭矩曲线——真实转速相关）
let driveForceLong = 0;
if (this.throttleValue > 0.01) {
    const engineTorque = this.engine.getTorque();
    const gearRatio = this.transmission.GetCurrentGearRatio() * 
        this.differential[2].finalDrive * this.differential[1].finalDrive;
    const totalWheelForce = engineTorque * gearRatio * 0.85 / this.wheel[0].radius;
    driveForceLong = Math.min(totalWheelForce * 0.5, maxFrictionPerWheel);
}

// 刹车（独立于推力，直接比例减速）
if (this.brakeValue > 0.01 && currentSpeed > 0.1) {
    const brakeDecel = this.brakeValue * maxFrictionPerWheel * 4 / this.mass * dt;
    const newSpeed = Math.max(0, currentSpeed - brakeDecel);
    const ratio = newSpeed / curSpeed;
    this.velocity.x *= ratio;
    this.velocity.z *= ratio;
}

// 转向时纵向力分解
const steerAngle = -this.steeringValue * this.maxSteeringAngle;  // 取反
this.velocity.z -= driveForceLong / this.mass * cos(steerAngle) * dt;
this.velocity.x += driveForceLong / this.mass * sin(steerAngle) * dt;

// 侧向摩擦力（摩擦圆剩余容量）
const remainingFriction = max(0, maxFrictionPerWheel*4 - driveForceLong);
const maxLatDecel = remainingFriction / this.mass;
if (latSpeed > 0.01) {
    const reduction = min(1.0, maxLatDecel * dt / latSpeed);
    velocity -= latV * reduction;  // 强抓地力抑制侧滑
}

// 空气阻力 (0.5*ρ*Cd*A*v²)
// 滚动阻力 (rr_coeff*m*g)
// 自行车模型转向 (yaw = speed * tan(steer) / wheelbase)
```

### 刹车力设计原则
- **不是固定减速度常数！** 刹车力 = brakeValue * mu * m * g（基于车重和摩擦系数）
- 低速时(5m/s以下)线性降低刹车力，模拟防抱死效果
- 刹车直接做速度比例减速（不用推力公式中的netForceLong减法，那个导致S键变成了加速）

### 空气阻力（平方律，自然限制极速）
```typescript
const rho = 1.225;       // 空气密度kg/m³
const cd = 0.35;         // 风阻系数
const area = 2.0;        // 迎风面积m²
const aeroForce = 0.5 * rho * cd * area * v²;
const aeroDecel = aeroForce / mass * dt;
```

### 输入映射
```typescript
// A→左转, D→右转
if (keyState['KeyA'] || keyState['ArrowLeft']) steerInput = -1;
if (keyState['KeyD'] || keyState['ArrowRight']) steerInput = 1;

// 视觉方向取反（车头朝Z-）
this.playerAngle = -Math.atan2(velocity.x, velocity.z);
```

## EffectComposer渲染故障排查

当场景有615个mesh、gameLoop在跑、但画面黑色/空时：

1. **检查composer是否正常工作：**
   ```
   composer.width → 如果为undefined，composer未正确初始化尺寸
   ```
2. **临时绕过方案：** 在gameLoop中跳过composer，直接用renderer渲染：
   ```typescript
   // 临时绕过：gameLoop中
   if (this.renderer && this.scene && this.camera) {
       this.renderer.render(this.scene, this.camera);
   }
   ```
3. **composer的setPixelRatio/resize时机：** composer必须在renderer.setSize之后初始化，否则尺寸为undefined
4. **不要composer.render()和renderer.render()同时调用** → 输出交替覆盖

## 输入系统陷阱

- **必须同时注册keydown和keyup事件**：keydown写true，keyup写false
- **驾驶键必须在keydown事件中记录到`(window as any).__keys`**：keydown事件里已有的功能键处理不会覆盖WASD
- keydown事件初始化时必须先设置 `(window as any).__keys = {}`
- 只监听keydown事件但不写__keys → WASD永远读不到输入 → 车不动

## 物理引擎（基于VDrift cardynamics + 简化启动推力）
- 发动机扭矩: 5段曲线(怠速→低转→扭矩高原→衰减→红线)
- 传动: 真实齿比×终传比×传动效率0.85
- 轮胎: Pacejka魔术公式(B=8-9/C=1.3/D=mu/E=-0.3)
- 自行车模型: 前轮侧偏=车辆侧偏+转向角, 后轮=车辆侧偏
- 横摆力矩: Mz = a*Fy_front*cos(steer) - b*Fy_rear
- 位置更新: `velocity.z = -cosA * speed`

### VDrift纯物理引擎的局限性

纯VDrift物理依赖车轮接触碰撞检测(wheelContact.depth > 0)来产生轮胎力，在没有Cannon-es或其他碰撞检测集成时，直接移植的CarDynamics不会产生任何移动。

### 启动推力+完整物理组合模型（无碰撞检测时使用）

在`CarDynamics.Update()`末尾、位置积分之前加入综合物理模型。**必须重新读取当前velocity计算speed，禁止用旧speed变量覆盖新加的velocity。**

```typescript
// 在Update()方法的'位置积分'段：
const currentDir = this.getDirection();
const currentSpeed = Math.sqrt(this.velocity.x*this.velocity.x + this.velocity.z*this.velocity.z);

// 1) 推力（带速度衰减）
if (this.throttleValue > 0.01) {
    const wheelForce = (this.engine.getTorque() * gearRatio * 0.85) / this.wheel[0].radius;
    const dragFactor = Math.max(0, 1.0 - currentSpeed / 50.0); // 50m/s时归零
    const accel = wheelForce * 0.25 / this.mass * dragFactor;
    this.velocity.z -= Math.cos(steerEffect) * accel * dt;
}

// 2) 刹车（比例减速度）
if (this.brakeValue > 0.01 && currentSpeed > 0.1) {
    const brakeDecel = this.brakeValue * 15.0 * dt;
    const ratio = Math.max(0, currentSpeed - brakeDecel) / currentSpeed;
    this.velocity.x *= ratio;
    this.velocity.z *= ratio;
}

// 3) 空气阻力（与v²成正比）
if (currentSpeed > 0.1) {
    const aeroDrag = 0.3 * 1.225 * currentSpeed * currentSpeed * 0.5 / this.mass * dt;
    const ratio = Math.max(0, currentSpeed - aeroDrag) / currentSpeed;
    this.velocity.x *= ratio;
    this.velocity.z *= ratio;
}

// 4) 侧向摩擦（转弯防滑）
if (currentSpeed > 0.5 && Math.abs(this.steeringValue) > 0.01) {
    const nx = currentDir.x / dirLen, nz = currentDir.z / dirLen;
    const latVx = this.velocity.x - (this.velocity.x*nx + this.velocity.z*nz) * nx;
    const latVz = this.velocity.z - (this.velocity.x*nx + this.velocity.z*nz) * nz;
    this.velocity.x -= latVx * 0.3 * dt;
    this.velocity.z -= latVz * 0.3 * dt;
}

// 5) 极速硬上限
const maxSpeed = 80.0; // ~288km/h
if (spd > maxSpeed) { const ratio = maxSpeed / spd; this.velocity.x *= ratio; this.velocity.z *= ratio; }

// 6) 自行车模型转向（更新方向）
const curSpeed = Math.sqrt(this.velocity.x*this.velocity.x + this.velocity.z*this.velocity.z);
const yawRt = curSpeed * Math.tan(this.steeringValue * this.maxSteeringAngle) / 2.7;
const cosA = Math.cos(yawRt * dt), sinA = Math.sin(yawRt * dt);
const ndx = curDir2.x * cosA - curDir2.z * sinA;
const ndz = curDir2.x * sinA + curDir2.z * cosA;
this.velocity.x = ndx * curSpeed;
this.velocity.z = ndz * curSpeed;
```

**关键陷阱：** 每次调用Update()时，推力代码和刹车代码都必须位于位置积分之前，且位置积分必须用**当前**的velocity重新计算speed，不能保留Update()函数入口处的旧speed变量。否则所有修改被覆盖。

### 调试汽车不动/物理不生效的流程
1. `g.vdriftPhysicsFull.engine.getTorque()` — 引擎有扭矩吗？（启动时应有315+ Nm）
2. `g.vdriftPhysicsFull.engine.getRPM()` — 引擎转速正常吗？（启动时~1000rpm）
3. `g.vdriftPhysicsFull.transmission.GetGear()` — 挂挡了吗？（必须为1）
4. `g.vdriftPhysicsFull.throttleValue` — 油门值设进去了吗？（应为1）
5. 手动执行 `p.SetThrottle(1); p.Update(0.016); p.getSpeed()` — 直接测试物理
6. 检查推力代码是否被位置积分的旧speed变量覆盖
7. 检查wheelContact是否启用（depth<=0时跳过轮胎力计算，需要用简化推力绕开）

## 赛道数据
- 基于真实GPS坐标: 银石/斯帕/摩纳哥/纽北/勒芒/铃鹿/拉古纳塞卡
- GPS投影: 等距圆柱投影(1°≈111320m)
- 缩放因子: 0.25 (GPS坐标→游戏坐标)
- 控制点间插值: 每段4个点

## 用户偏好
- 所有修改必须在本地文件系统进行
- 分阶段交付，每步验证后再继续
- 绝对禁止占位符/模拟实现/降级实现
- 全面代码审核+历史回顾后再开始任务
- 汇报进度要简洁，直接说完成什么/缺什么

## 引用文件
- `scripts/convert_v9.py` — VDrift JOE→JSON转换器最终版（全局索引+顶点清洗）
- `references/vdrift-physics-debugging.md` — 物理引擎调试参考（车不动/gameLoop崩溃诊断）
