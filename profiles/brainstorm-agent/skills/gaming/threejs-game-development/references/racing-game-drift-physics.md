# Racing Game Drift / Sideslip Physics Implementation

## 从零到漂移：Three.js竞速游戏侧滑物理

### 问题起源

PlushRacingGame.ts 定义了这些物理变量但从未在 updatePlayer 中使用：
```typescript
private lateralVelocity = 0;
private yawRate = 0;
private slipAngle = 0;
private isDrifting = false;
private tireGrip = 1.0;
```

游戏实际只有简单的前进+转向，完全没有侧滑/漂移/抓地力突破。

### 侧滑物理模型

核心原理：转向时，车辆受到侧向力 = 速度 × 转向角速度。 
如果侧向力超过轮胎抓地力，车辆开始侧滑（漂移）。

#### 关键公式

```
lateralAccel = steerInput × playerSpeed × STEER_SPEED × 0.3
gripLimit = tireGrip × 3  // m/s²
```

- `tireGrip` 来自难度设置（娱乐=2.0，中等=1.0，大师=0.5）
- 当 `|lateralAccel| > gripLimit` → 突破抓地力 → 进入漂移状态

#### 三态逻辑

**正常转向** (lateralAccel <= gripLimit):
- 无侧滑，isDrifting = false
- slipAngle 指数衰减 (×0.95)
- 移动方向 = 车辆朝向 × speed × delta

**漂移中** (lateralAccel > gripLimit 且 speed > 5m/s):
- isDrifting = true
- slipAngle 累积: `slipAngle += (steerInput × 0.05 - slipAngle) × delta × 3`
- 前进方向减速: `moveX/Z *= slipFactor (0.85)`
- 横向滑移速度:
  ```
  slipX = cos(playerAngle) × slipAngle × playerSpeed × delta
  slipZ = -sin(playerAngle) × slipAngle × playerSpeed × delta
  ```

**恢复抓地** (无转向输入 或 速度<5m/s):
- isDrifting = false
- slipAngle 快速衰减 (×0.95)

### 实现代码

```typescript
// ====== 位置更新 + 侧滑惯性 ======
const slipFactor = this.isDrifting ? 0.85 : 1.0;
let moveX = Math.sin(this.playerAngle) * this.playerSpeed * delta * slipFactor;
let moveZ = Math.cos(this.playerAngle) * this.playerSpeed * delta * slipFactor;

if (Math.abs(steerInput) > 0 && Math.abs(this.playerSpeed) > 5) {
    const gripLimit = this.tireGrip * 3;
    const lateralAccel = steerInput * this.playerSpeed * this.STEER_SPEED * 0.3;
    if (Math.abs(lateralAccel) > gripLimit) {
        this.isDrifting = true;
        this.slipAngle += (steerInput * 0.05 - this.slipAngle) * delta * 3;
        const slipX = Math.cos(this.playerAngle) * this.slipAngle * this.playerSpeed * delta;
        const slipZ = -Math.sin(this.playerAngle) * this.slipAngle * this.playerSpeed * delta;
        moveX += slipX;
        moveZ += slipZ;
    } else {
        this.isDrifting = false;
        this.slipAngle *= 0.95;
    }
} else {
    this.isDrifting = false;
    this.slipAngle *= 0.95;
}
```

### 参数调优经验

| 参数 | 范围 | 作用 | 
|------|------|------|
| 抓地力 `gripLimit = tireGrip × 3` | 1.5-6.0 | 越大越难漂移 |
| 侧向力系数 `0.3` | 0.2-0.5 | 越大越快突破抓地力 |
| drift积累速率 `3` | 2-5 | 漂移角增长速度 |
| 最大漂移单步 `steerInput × 0.05` | 0.03-0.08 | 单帧最大漂移角变化 |
| 恢复系数 `0.95` | 0.9-0.98 | 越低恢复越快(0.95≈14帧半衰) |
| 前进减速 `slipFactor=0.85` | 0.7-0.95 | 漂移时速度损失 |

### 配合转向系统

```typescript
// 转向（带速度因子）
if (Math.abs(this.playerSpeed) > 0.1) {
    const speedFactor = Math.max(0.4, 1 - speedNorm * 0.6);
    this.playerAngle += steerInput * this.STEER_SPEED * delta * speedFactor;
} else if (Math.abs(steerInput) > 0) {
    // 极低速原地转向
    this.playerAngle += steerInput * this.STEER_SPEED * delta * 0.25;
}

// 车身侧倾视觉
this.playerCar.rotation.z += (steerInput * -0.1 * speedNorm - this.playerCar.rotation.z) * delta * 5;
```

### 5难度侧滑参数

| 难度 | tireGrip | gripLimit | 漂移特性 |
|------|----------|-----------|----------|
| 0 娱乐 | 2.0 | 6.0 | 几乎不漂移，抓地极强 |
| 1 轻松 | 1.5 | 4.5 | 偶尔漂移，易控 |
| 2 中等 | 1.0 | 3.0 | 正常漂移，需操控 |
| 3 困难 | 0.7 | 2.1 | 容易漂移，不易控 |
| 4 大师 | 0.5 | 1.5 | 极容易漂移，模拟物理 |
