# Racing Game Code Audit Workflow

## 完整代码审核工作流（从架构感知到逐Bug修复）

该工作流适用于：从零理解一个竞速游戏项目结构→发现隐藏bug→系统化修复→构建验证的全过程。

## Phase 0: 项目全景扫描

```bash
# 1. 获取完整文件树（排除 node_modules 和 dist）
find . -type f \( -name "*.ts" -o -name "*.js" -o -name "*.html" -o -name "*.css" \) \
  | grep -v node_modules | grep -v dist | sort

# 2. 识别"真活"vs"摆设"文件
#   统计每个文件的导入被谁引用，标记从未被调用的模块
grep -r "import.*from.*" src/*.ts | grep -v "@ts-nocheck"
```

## COMMANDMENT: Zero Key-Conflict Audit (2026-05-29 新增)

**DO NOT deploy any keyboard-driven game without running a zero key-conflict audit.**

The canonical failure mode: `D` simultaneously bound to `turn right` (via `__keys` state tracking) AND `cycle difficulty` (via `keydown` event listener). Both are in `main.ts` (global `__keys` record) and `GameClass.ts` (`keydown` handler), NOT canceling each other — both execute.

### Audit Protocol

```
1. Collect ALL driving keys from __keys reads (updatePlayer etc.)
   grep -rn "keyState\[" src/
   
2. Collect ALL function keys from keydown event listeners
   grep -rn "e.code === '" src/
   
3. Find intersection
   conflict = set(drive_keys) & set(func_keys)
   
4. Fix: Move ALL function keys OUTSIDE the WASD zone
   Left hand (WASD)  = DRIVING ONLY
   Right hand (Q/E/R/T/F/G) = FUNCTIONS
   Tab/Esc = secondary functions
```

### Golden Layout (proven to work)

```
W A S D / Arrow Keys  = DRIVE ONLY (accelerate/brake/steer)
         Q  = camera/view   (left of W, safe)
         E  = vehicle/tier  (right of W, E=Engine)
         R  = difficulty    (right side)
         F  = paint/spray   (right side, F=spray/Finish)
         T  = tune/upgrade  (right side)
       Tab  = track/circuit (deliberate keypress only)
   1-4/Digits = upgrade parts (top row)
      Esc  = pause/menu
```

**NEVER let A/S/D also control a function. NEVER let any function key sit inside the WASD cluster.**

## Phase 1: 架构理解（全局通读）

**预期耗时**: 20-30分钟
**目标**: 理解完整的游戏循环链路、模块依赖图、数据流方向

### 必须回答的问题
1. **入口在哪？** (main.ts → import game → initialize → startGame → gameLoop)
2. **核心类是单体还是模块化的？** 检查PlushRacingGame.ts是否包含了渲染/物理/AI/UI/音频一切
3. **哪些模块写了但没用？** 检查engine/*, audio/*, ui/*, camera/*, input/* 是否真正被导入
4. **游戏状态机是什么？** menu → playing → paused → results
5. **更新循环顺序？** updatePlayer → updateAI → updateCamera → updateHUD → updateAudio → render

### 关键阅读顺序
1. main.ts (5分钟) — 入口、全局Game对象、事件绑定
2. PlushRacingGame.ts 前200行 (10分钟) — 类字段、构造函数、初始化
3. 赛道生成 (generateTrack, ~200行) — 赛道数据+网格生成+纹理
4. 物理引擎 (updatePlayer, ~120行) — **最核心，逐行理解**
5. AI逻辑 (updateAI, ~50行) — progress追踪
6. UI/HUD (~100行) — DOM操作、HUD更新
7. CircuitData.ts (~200行) — 赛道控制点坐标
8. VehicleTierSystem.ts (~350行) — 性能分级系统

## Phase 2: Bug挖掘清单

### [CRITICAL] 必须检查的12个高危区域（含按键冲突）

#### 1. AI数组长度污染
```
检查: createAICars() 中是否用 push 而非索引赋值
问题: 赛道切换 → this.aiCars = [] → createAICars → push
        第二次切换 → push 追加 → AI数量翻倍
修复: this.aiCars[i] = car 替代 push
        this.aiProgress[i] = 0 替代 push
```

#### 2. 终点线反复触发
```
检查: finishZone 检测逻辑
问题: 碰撞导致progress在0.04附近摆动 → 一圈多次完赛
修复: 添加 _lapComplete 布尔标记
        private _lapComplete = true;
        // 终点线检测:
        const crossedForward = !this._lapComplete && prev < zone && now >= zone;
        // 完成一圈后:
        this._lapComplete = true;
        // progress回落到0.01以下时:
        if (this.playerProgress < 0.01) this._lapComplete = false;
```

#### 3. 赛道碰撞采样点不足
```
检查: 采样循环中 totalSegs 的计算
问题: 固定500点 → 弯道间距过大 → 碰撞漏检
修复: totalSegs = Math.min(2000, Math.max(500, Math.floor(trackLen / 5)))
        // 100m采样一次，确保弯道不漏
```

#### 4. 赛道碰撞推回方向错误
```
检查: 推回向量计算方式
问题: 用圆心方向推回 → 弯道上推出赛道更远
修复: 用赛道最近点的法线方向（垂直于切线）
        const nearestTangent = trackCurve.getTangent(closestProgress);
        const normalDir = new THREE.Vector3(-nearestTangent.z, 0, nearestTangent.x).normalize();
        const lateralOffset = toCar.dot(normalDir);
        if (Math.abs(lateralOffset) > trackHalfWidth) {
            carX -= normalDir.x * pushDist * Math.sign(lateralOffset);
            carZ -= normalDir.z * pushDist * Math.sign(lateralOffset);
        }
```

#### 5. 极低速不能转向
```
检查: 转向条件 if (speed > threshold)
问题: threshold=0.5m/s → 静止车不能原地转向
修复: if (speed > 0.1) → 正常转向因子
        else if (steerInput) → 原地25%转向
```

#### 6. AI碰撞奖励对手
```
检查: this.aiProgress[i] += ... 在碰撞分支中
问题: 玩家撞AI → AI获得意外progress奖励
修复: 删除该行
```

#### 7. 重复方法定义
```
检查: 搜索相同签名的方法两次定义
问题: formatTime 定义了两次(行1631和1690)
修复: 删除其中一个
```

#### 8. 车辆注册系统遗漏
```
检查: VehicleData.registerFromDirectImport 中的 files 数组
问题: batch1-5 + t1共6个文件未被导入 → 130辆车中只有70辆可访问
修复: 添加缺少的 require('./configs/vehicles_101_130_batch1') 等
```

#### 9. 侧滑变量定义了但闲置
```
检查: lateralVelocity, yawRate, slipAngle, isDrifting, tireGrip 是否被使用
问题: 定义了但updatePlayer中未使用
修复: 集成到驾驶模型中（见侧滑模型）
```

#### 10. 地面固定尺寸
```
检查: new THREE.PlaneGeometry(600, 600) 在赛道生成中
问题: 勒芒赛道范围7500m → 地面600x600不够
修复: 动态计算赛道边界取1.5倍
```

#### 11. 赛道切换时进度残留
```
检查: aiProgress = [0.25, 0.50, 0.75] + push导致的数组污染
问题: 多次切换后数组长度3→6→9
修复: 见#1
```

#### 12. 按键冲突 — WASD区域内有功能键
```
检查: 驾驶键集合(function of __keys) ∩ 功能键集合(function of keydown listener)
问题: D键同时做右转(__keys['KeyD'])和切换难度(keydown监听KeyD)
        C键/ V键 / N键 / P键 / M键都在WASD区域内
修复: 所有功能键移到WASD区域之外:
        C(视角) → Q     V(车辆) → E
        N(赛道) → Tab   P(喷涂) → F
        M(改装) → T     D(难度) → R
        按键布局验证脚本:
        python3 -c "
import re
drive = set(re.findall(r\"keyState\['(\\w+)'\]\", open('src/PlushRacingGame.ts').read()))
func = set(re.findall(r\"e\\.code\\s*===\\s*'(\\w+)'\", open('src/PlushRacingGame.ts').read()))
conflict = drive & func
print('冲突键:', conflict if conflict else '零冲突')
"
```

### [MEDIUM] 性能与美术检查点
- 纹理尺寸 2048x256 (沿赛道方向长，横向窄) + repeat.set(30,1)
- Bloom强度 ≤ 0.15 (否则暗部消失)
- 赛道边线用红白路肩风格（cf. FIA标准）
- 车道线密度：每12px（非每16px）
- 建筑的城市半径 = trackSize * 0.8 + 100 + ring * 150

## Phase 3: 修复优先级

```
P0 (blocking runtime crashes):
  #2 终点线反复触发 → 圈数无限增加
  #3 赛道碰撞漏检 → 冲出赛道无反馈
  #6 AI碰撞奖励对手 → 不公平
  #11 AI数量翻倍 → 赛道切换后卡死

P1 (gameplay correctness):
  #4 推回方向错误 → 弯道手感诡异
  #5 低速转向不能 → 发夹弯转不了
  #8 车辆注册遗漏 → 130辆只有70辆可用
  #10 地面不够大 → 大赛道背景缺失
  #12 按键冲突 → WASD功能键冲突

P2 (physics depth):
  #9 侧滑系统 → 无漂移手感
  #1 物理参数映射 → T1-T5差异不明显

P3 (visual polish):
纹理优化、灯光强度、霓虹灯密度
```

## Phase 4: 螺旋修复模式

对每个bug:
1. **patch修复** — 最小改动量
2. **构建验证** — webpack --mode production
3. **grep检查** — 确保每步后没有`{caret}`残留
4. **临近代码检查** — 检查附近5行是否有别的隐式bug
5. **按键冲突审计** — 每次改动后运行交集检查

## Phase 5: 验证清单

- [ ] build成功 (0 errors)
- [ ] grep -rn "caret" src/ — 0 results
- [ ] 每条关键路径：startGame → generateTrack → gameLoop → updatePlayer → render
- [ ] 物理参数：1单位=1米，速度m/s，HUD显示km/h(×3.6)
- [ ] 碰撞推回使用法线方向
- [ ] AI progress不为负也不溢出
- [ ] 赛道切换后AI数量不翻倍
- [ ] 终点线穿越一圈只触发一次
- [ ] 极低速能转向
- [ ] 侧滑变量被实际使用
- [ ] 按键冲突审计: drive_keys ∩ func_keys = ∅
