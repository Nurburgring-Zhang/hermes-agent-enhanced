# 黑屏根因快速诊断表 (本会话排查的完整链路)

## 黑屏 = 游戏无画面但HUD可见
Three.js游戏在browser_snapshot中仅显示HUD(HTML元素)，不显示WebGL内容。所以"有HUD无画面"是黑屏诊断起点。

## 排查链（按优先级）

### 1. 检查gameLoop是否运行
```
window.game.renderer.info.render.calls   // 0 = 没渲染
window.game.clock.elapsedTime.toFixed(1) // 不增长 = loop没跑
```

**gameLoop停跑的原因：**
遍历 `gameLoop()` 中的每个调用（`updateXxx()`），在其中找 `audioParam.value = NaN` 异常。

### 2. updateAudio NaN 崩溃（最常见）
```
this.engineOsc.frequency.value += (rpmHz - this.engineOsc.frequency.value) * delta * 10;
```
如果 `rpmHz` 或 `this.engineOsc.frequency.value` 含有 NaN/Infinity，TypeScript 抛 `TypeError` → gameLoop 整帧崩。

**根因排查：**
1. `ENGINE_IDLE_RPM` 和 `ENGINE_MAX_RPM` 是否在类中定义？从旧HTML迁移时经常丢失。
2. `const rpmNorm = (rpm - IDLE) / (MAX - IDLE)` — 如果 IDLE 或 MAX 是 `undefined`，结果为 `NaN`
3. `this.playerSpeed` 是否含有 NaN（被物理引擎NaN传播）
4. 修复：`try-catch` 包裹整个 `updateAudio()` + 每个中间变量 `isFinite()` 检查

### 3. 位置NaN级联
```
carX = physics.position.x  // 第一次读 = undefined → NaN
playerCar.position.x = carX  // Three.js Vector3 得到 NaN
cameraSystem.update(..., carPos)  // 相机位置 NaN → 黑屏
```

**排查：**
```
window.game.playerCar.position.x  // 是 NaN?
window.game.vdriftPhysicsFull.position.x  // 是 NaN?
```

**修复：** `carX`/`carZ` 必须在 `initVDriftPhysics()` 之前赋值，否则物理引擎读 `undefined`。

### 4. 推力代码被位置积分覆盖
在 `CarDynamics.Update()` 中，手动加的推力（`velocity.x += thrustX`）被后面的自行车模型位置积分覆盖：
```typescript
const speed = this.getSpeed();  // 在推力代码前读取 → 0
// ... 推力代码执行，velocity变成 -0.216 ...
const newDir = getDirection();
this.velocity.x = newDir.x * speed;  // speed=0 → velocity被清零
```

**诊断：** 手动 `SetThrottle(1); Update(0.016)` 后 `getSpeed()` 仍为接近0。

**修复：** 推力代码后位置积分前**重新计算 speed**：
```typescript
const currentSpeed = Math.sqrt(this.velocity.x**2 + this.velocity.z**2);
this.velocity.x = newDirX * currentSpeed;  // 用当前速度，非旧speed
```

### 5. 输入总线未连接
检查 `updatePlayer` 中的输入来源：
```
const keyState = (window as any).__keys || {};
```
但没有任何事件处理器写入 `__keys`。

**诊断：** 模拟按键 `window.__keys['KeyW']=true`，等1秒后查 `vdriftPhysicsFull.getSpeed()`。

**修复：** 在 `initFullScene()` 中添加：
```typescript
(window as any).__keys = {};
window.addEventListener('keydown', (e) => {
    if (['KeyW','KeyA','KeyS','KeyD',...].includes(e.code)) {
        (window as any).__keys[e.code] = true;
        e.preventDefault();
    }
});
window.addEventListener('keyup', (e) => {
    if (['KeyW','KeyA','KeyS','KeyD',...].includes(e.code)) {
        (window as any).__keys[e.code] = false;
        e.preventDefault();
    }
});
```

### 6. 模型缓存
浏览器缓存旧的模型JSON（含NaN数据），即使磁盘文件已修复。`fetch` 加时间戳：
```
const r = await fetch(`dist/models/${id}.json?v=${Date.now()}`);
```

## 黑屏诊断速查表

| 症状 | 检查点 | 最常见根因 |
|------|--------|-----------|
| HUD有，画面黑，no errors | renderer.info.render.calls | composer渲染不计数 |
| HUD有，画面黑，1个exception | AudioParam.value = NaN | ENGINE_IDLE_RPM undefined |
| HUD有，画面黑，gameLoop停 | clock.elapsedTime + 手动gameLoop() | updateAudio抛异常 |
| 车不动，物理引擎跑 | SetThrottle后speed=0 | 推力代码被位置积分覆盖 |
| 车不动，不能加速 | window.__keys状态 | keydown/keyup没设 |
| 模型一团黑 | 顶点数 vs 原车 | JOE Face解析用错索引策略 |
| 模型一团黑 | browser缓存旧JSON | ?v=Date.now()修复 |
