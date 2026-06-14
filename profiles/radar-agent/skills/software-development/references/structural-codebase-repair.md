# 结构性代码库修复模式 (Structural Codebase Repair)

当接手大型AI生成的TypeScript/JavaScript代码库（10K-100K+ LOC）时，采用分层修复策略，而不是一次性解决所有问题。

## 策略概览

```
层次0: 构建系统 → npm install + webpack/tsconfig基础配置
层次1: 结构断裂 → 语法错误、缺失import、闭合块
层次2: 模块断裂 → 路径错误、导出缺失
层次3: 类型断裂 → 接口不匹配、类型断言
层次4: 逻辑断裂 → TODO空函数、运行时null引用
```

## 详细步骤

### 0. 诊断

\`\`\`bash
npx tsc --noEmit 2>&1 | tee /tmp/ts-errors.txt
grep -c "^src/" /tmp/ts-errors.txt
grep "error TS2307\|TS2305\|TS1005\|TS1434" /tmp/ts-errors.txt | sort | uniq -c | sort -rn
\`\`\`

**错误分类**：
- `TS1005`, `TS1068`, `TS1128`, `TS1434` → **结构断裂**（最高优先）
- `TS2307`, `TS2305`, `TS2724` → **模块/导出断裂**
- `TS2741`, `TS2345`, `TS2322` → **类型不匹配**（可跳过）

### 1. 层次0 — 构建系统

```bash
# 常见陷阱: 不存在包 lil@0.6.0（正确: lil-gui）
# postprocessing 6.39.1 需要 three >=0.168.0
# type:module 与 CommonJS webpack.config 冲突

# tsconfig: 先全面放松
{"strict": false, "skipLibCheck": true, "strictNullChecks": false}
```

### 2. 层次1 — 结构断裂

| 模式 | 表现 | 修复 |
|------|------|------|
| 悬空catch | try不闭合就开第二个catch | 找到正确闭合位置 |
| 缺失import | 用 `CANNON.Body` 无import | 加 `import * as CANNON from 'cannon-es'` |
| 路径错误 | `./levels/LM` 实际在 `./managers/` | 修正路径 |
| 双重大括号 | 方法闭合后多一个 `}` | 删除多余的 |
| if/else未闭合 | else块缺 `}` | 补全 |
| 坏属性 | `dragCoefficient: 0.31: 2.,` | 修正 |
| 未定义类型 | 引用 `VehicleClass` 未定义 | 添加枚举 |

### 3. 层次2 — 模块断裂

- `export { X } from './Y'` 但X不在Y中
- namespace风格: `export interface THREE.TextureAtlas` → 移除`THREE.`前缀
- 接口缺属性 → 标记optional: `customParts?: CustomPart[]`

### 4. 层次3 — 类型断裂

用 `@ts-nocheck` + `skipLibCheck` 跳过，编译通过后再逐步修复。

### 5. 层次4 — 逻辑（运行时）

空函数TODO → 删除调用或加minimal实现。

## HTML内联代码清理

巨型HTML（50K-270K）中的旧JS清理：

```python
# 找到并移除 const Game = { ... }
game_start = content.find('const Game = {')
game_end = content.find('// 启动游戏', game_start)
new_content = content[:game_start] + '// replaced by bundle\n' + content[game_end:]

# 移除CDN引用（已打包）
new_content = new_content.replace(
    '<script src="...three.js/r128...">', '<!-- bundled -->')

# 加bundle.js
new_content = new_content.replace('</body>', '    <script src="bundle.js"></script>\n</body>')
```

## webpack多版本冲突解决

| 场景 | 解决 |
|------|------|
| postprocessing 6.39.1 需 three>=0.168.0 | `--legacy-peer-deps` |
| lil 包不存在 | 删除，lil-gui已存在 |
| Three.js CDN(r128) + npm(r160) 并存 | 移除CDN，统一webpack |

## 关键原则

1. 先编译通过 → 再运行 → 最后修类型
2. AI生成代码的结构断裂100%会出现
3. 批量加 @ts-nocheck 不逐个文件纠结
4. 每次修改后清缓存: 重启serve + `?v=N` 参数
