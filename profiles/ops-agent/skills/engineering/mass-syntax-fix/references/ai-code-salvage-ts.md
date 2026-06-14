# AI生成TypeScript/JS代码项目全面审核与修复
> 从本会话(racing_game_package审核改造)提炼的经验

## 审核流程

### 第一步: 资产审计
```bash
# 总览
find . -type f | wc -l
find src -name '*.ts' | wc -l
find . -name "*.ts" -exec cat {} \; | wc -l

# 资源真实性检查 (AI常塞placeholder)
file assets/models/*.glb
# 如果输出 "JSON text data" → 占位文件！
cat assets/models/*.glb 
# 内容应是: {"type":"placeholder","vertices":0,...}
```

### 第二步: 编译断裂定位
```bash
# TS检查
npx tsc --noEmit 2>&1 | grep "^src/" | head -30

# 关键错误模式:
# 1. "Cannot find module" → import路径错误（最常见）
# 2. "TS2749: refers to a value, but is being used as a type" → interface命名冲突
# 3. "TS1005: Identifier/DECLARATION expected" → 括号/大括号不闭合
# 4. "Cannot find package" → npm包不存在或拼写错误
# 5. "Object literal may only specify known properties" → 接口缺少 optional标记
```

### 第三步: 三级分类

| 级别 | 特征 | 修复方法 |
|------|------|----------|
| P0 | 语法错误,缺失import,不存在模块 | 直接编辑修复 |
| P1 | 逻辑断裂,空函数,物理体未加入world | `// @ts-nocheck`放行后替换实现 |
| P2 | 类型不匹配,废弃API,属性缺失 | 放松strict flags或加`?`optional |

## 常见AI生成bug模式

### 1. 大括号/方法不闭合
```typescript
// Bug: toggle() else块缺少闭合括号
toggle(): void {
    if (a) { doA(); } 
    else { doB();   // ← 缺少 }

// Fix:
toggle(): void {
    if (a) { doA(); } 
    else { doB(); }
}
```

### 2. 双重try-catch
```typescript
// Bug: 第一个try块未闭合就第二个catch
try {
    doStuff();
    // 缺一个 }
} catch (e) { ... }  // ← 这行悬空,前面的try没闭合
```

### 3. 路径名不存在
```typescript
// Bug
import { LevelManager } from './levels/LevelManager';
// Fix: 实际目录名不同
import { LevelManager } from './managers/LevelManager';
```

### 4. 缺失CANNON import
AI引用 `CANNON.Body` 或 `CANNON.Vec3` 但没写 `import * as CANNON from 'cannon-es'`。

### 5. 包名拼写错/不存在
```json
"lil": "^0.6.0"  // 不存在这个包！
```
直接删除不存在的包，用 `--legacy-peer-deps` 应对版本冲突。

## 三个关键决策

### 引擎升级还是重写？
- Web竞速游戏: Three.js + Cannon-es **足够**（不需要Unreal/Unity）
- 关键差距不是引擎，是API的**正确使用**
- Cannon-es应该用RaycastVehicle（四轮独立悬挂）而不是手动force模拟

### tsc strict还是relax？
- 先relax执行快速构建: `"strict": false + "skipLibCheck": true`
- 对大量车辆配制文件加 `// @ts-nocheck`
- 等能跑了再逐步fix类型错误

### CDN还是bundle？
- AI常生成CDN引用 (`<script src="https://cdnjs.cloudflare.com/...three.js">`)
- 但ES module版Three.js与CDN global版冲突
- 策略: 删CDN，全走webpack bundle

## Web竞速游戏性能基准
| 参数 | 建议值 | 说明 |
|------|--------|------|
| 重力 | -29.4 m/s² | 现实3倍 → 街机感 |
| 车辆质量 | 300-800kg | 毛绒轻量化 |
| 最大速度 | 80-250 km/h | 休闲竞速 |
| 赛道类型 | CatmullRomCurve3 | 真实曲线非折线 |
| 赛博朋克渲染 | Bloom + 霓虹灯光 | EffectComposer |
