# 赛车游戏黑屏+物理不工作 调试记录 (2026-06-01)

## 问题链（按出现顺序）

### 1. 黑屏（渲染循环未运行）
**根因：** `updateAudio()` 中 `ENGINE_IDLE_RPM` 和 `ENGINE_MAX_RPM` 未定义。
`(currentRpm - undefined) / (undefined - undefined) = NaN`
`engineOsc.frequency.value` 被赋NaN → TypeError → gameLoop崩溃 → 不再请求下一帧 → 黑屏

**修复：** 添加类常量 `ENGINE_IDLE_RPM = 850` 和 `ENGINE_MAX_RPM = 7200`
**加固：** `updateAudio()` 整体用 `try-catch` 包裹

### 2. 模型乱码
**根因：** JOE Face解析错误。VDrift `.joe` 文件中每个Face的vertex索引是**全局**索引（指向整个verts数组），错误地当作`fi*3+local`解析。
**后果：** 索引膨胀出15712→3875的错误映射，vmap去重把相同(0,0,0)顶点重复映射为不同顶点，顶点数膨胀到2343（实际应该573）

**修复：** `convert_v9.py` 重写parse函数，JOE Face的v0/v1/v2直接当全局索引用

### 3. 模型畸形（一个大顶点349689）
**根因：** 越界索引(`vi > numVerts`)被`(0,0,0)`保护，但顶点JSON中有个异常大值来自其他解析错误。
**后果：** 车身显示为"一团黑乎乎乱的几何体"

**修复：** 在`convert_v9.py`的`convert()`函数中增加顶点清洗：
```python
if abs(x) < 100 and abs(y) < 100 and abs(z) < 100:
    # 保留正常顶点，其余剔除
```

### 4. 操作不管用（WASD无响应）
**根因：** `window.addEventListener('keydown', ...)` 只处理了功能键(Esc/Q/Tab/F/T/R/E/G)，没有处理WASD。`updatePlayer()` 从 `(window as any).__keys` 读取输入，但keydown/keyup从未写入。
**后果：** throttle/brake/steer始终为0

**修复：** 在keydown中记录驱动键到 `__keys`，添加keyup事件清空

### 5. 汽车不动（物理引擎不产生速度）
**根因1：** 位置积分复用入口处的旧 `speed = this.getSpeed()`（值为0）来设置 `this.velocity.z = newDirZ * speed = 0`，覆盖了推力代码加的0.216m/s

**根因2：** 推力代码在 `speed < 1.0` 条件下才执行，但旧speed=0导致条件为真，可加了也没用因为被位置积分覆盖

**修复：** 
- 位置积分前 `const currentSpeed = Math.sqrt(this.velocity.x*this.velocity.x + this.velocity.z*this.velocity.z)`
- 移除 `speed < 1.0` 限制

### 6. 汽车跑得飞快刹不住 + 转弯乱跑
**根因：** 只有推力没有刹车/阻力/极速限制。自行车模型转弯没有侧向摩擦力。

**修复：** 在CarDynamics.Update()的位置积分段加入综合模型：
- 推力带速度衰减（50m/s时归零）
- 刹车力（brakeValue × 15m/s²）
- 空气阻力（0.3 × 1.225 × v² × 0.5 / mass）
- 侧向摩擦力（抑制垂直行驶方向的速度分量）
- 极速硬上限80m/s(~288km/h)

### 7. GameLoop崩溃（不存在的函数调用）
**根因：** `this.playCollisionSound()` 和 `this.distanceToTrack()` 从未定义，但updatePlayer中调用了它们

**后果：** 任何碰撞或赛道边界检测都抛TypeError → gameLoop崩溃

**修复：** 删除了所有对这两个函数的调用，简化了赛道碰撞逻辑

### 8. EffectComposer不渲染
**根因：** `composer.width` 和 `composer.height` 为undefined（未正确初始化尺寸）

**临时修复：** 跳过composer渲染，直接用renderer.render()

## 经验教训
1. **类常量/变量初始化检查** — undefined变量参与的数学运算产生NaN → 传播到AudioParam → gameLoop崩溃。每次集成新功能（如音频）必须加try-catch
2. **函数存在性检查** — 调用的函数必须已定义或至少声明为空函数
3. **变量引用完整性** — 删除变量后检查所有引用是否更新
4. **VDrift索引类型确认** — JOE Face的vertex索引是全局的（可直接索引verts数组），不是local的
5. **顶点清洗** — 模型转换后必须做范围检查（VDrift模型在±10内），排除异常顶点（如349689）
6. **车轮方向** — `rotation.z = PI/2` 使LatheGeometry从绕Y变成绕X（水平）。`rotation.x = PI/2` 是错误的（会做成竖直轮）
7. **位置积分顺序** — 推力/刹车/阻力必须在位置积分之前应用，且位置积分必须用修改后的velocity重新计算speed
8. **坐标系统一** — wheelPositions数据格式可能已经是Three.js坐标，不需要再做VDrift→Three.js转换
