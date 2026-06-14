# 全频谱竞速游戏代码审核方法论

## 适用场景

当要求对竞速游戏/3D游戏项目进行"全面研究+深度审核+优化方案"时，在 extreme-code-audit-triple-agent 基础流程之上增加以下步骤。

## 6层审核框架

### 层0: 项目基础统计

```
审查目标: 了解项目规模和资产构成
- 总文件数 / 总代码行数 / 最大文件TOP20
- 目录结构树
- 源文件 vs 资产文件比例
- node_modules是否安装 / 可构建性检查
```

### 层1: 资源资产审计

```
审查目标: 区分真实资产与占位符
- 纹理: 检查尺寸/位深度/是否真实
- 模型: file命令检查(glb=二进制 vs json占位)
- 音频: 检查文件头(MP3头 = 真实文件, 文本 = 占位)
- 字体: 检查字节数(小文本=TXT占位, >1KB可能真实)
- 配置文件: 检查是否是完整配置还是骨架
- 关键! file命令检测: 'JSON text data' = 假glb, 'MPEG ADTS' = 真音频
```

### 层2: 编译期断裂检查

```
审查目标: 修复阻止tsc/webpack编译的致命错误
- import路径是否存在(ls命令验证)
- import的symbol是否实际export(字符串搜索)
- class/interface缺失export
- try/catch块是否闭合(大括号平衡)
- 模块格式冲突(type:module vs require vs export default)
- 废弃API使用(Three.js r136+的outputEncoding→colorSpace等)
```

### 层3: 运行时逻辑断裂

```
审查目标: 编译通过但游戏无法运行的点
- 物理体是否加入了world(检查body.addTo vs body留在isolated)
- 渲染Pass是否使用null scene/camera
- 事件监听器绑定了但从未触发
- 空函数体(TODO/只做console.log)
- 独立创建的THREE.Scene(每个Vehicle一个自己的场景)
- 多套架构并行(Game vs GameEngine)
- 游戏主入口调用的是骨架代码而非实际引擎
```

### 层4: 跨域技术研究

```
审查目标: 建立行业基准，判断项目技术定位
- 竞品对标: 找到同类技术栈的成功产品作为参考
- 关键参数表: 物理参数/渲染参数/性能目标的对标表格
- 技术差距评估: 各子系统的能力评级(与行业标准对比)
- 引擎选择判断: 是否需要升级/更换引擎(Web游戏的关键在于联通性，不在于原始引擎能力)
```

### 层5: 领域参数映射

```
审查目标: 将设计配置映射到引擎物理参数

VehicleAttributes → PhysicsEngine参数表:
  maxSpeed, acceleration → engineForce / maxSpeed
  braking                → brakeForce  
  handling, steering     → maxSteerAngle
  grip                   → frictionCoefficient
  weight                 → chassisBody.mass
  wheelBase, trackWidth  → wheel position offsets
  centerOfMass           → centerOfMass偏移
  dragCoefficient        → linearDamping
  suspensionStiffness    → suspension stiffness/restLength
  gearCount, finalDrive  → gear ratio array(for RPM audio simulation)

赛道参数对照:
  length → CatmullRomCurve3控制点数量
  width  → track surface vertices offset
  difficulty → curve density / elevation变化幅度
  type → 地形材质(asphalt/sand/grass friction值不同)
```

### 层6: 分级修复计划

```
审查目标: 产出可执行的阶段化修复路线图

阶段命名: Phase 0 → Phase N
每个阶段:
  - 明确的修改文件清单
  - 预计耗时
  - 可验证的终点(什么算是"完成")
  
优先级编码:
  P0 = 阻止编译/启动的致命断裂
  P1 = 运行时逻辑断裂(功能无法使用)
  P2 = 质量问题(性能/安全/代码品质)
  
建议执行顺序:
  Phase 0: 编译修复(7个P0耗时15min)
  Phase 1: 构建系统修复
  Phase 2: 引擎架构统一
  Phase 3+N: 按系统深度修复(物理→赛道→车辆→渲染→音频→UI)
  Final Phase: 集成测试循环
```

## 报告格式规范

### 表格风格
- 使用`|`表格分隔符，头部加`---`分割线
- 严重度使用emoji标记: 🔴=P0 🟡=P1 🟢=P2
- 尺寸/计数在括号标注

### 分层结构
```
## 章节标题
### 子章节
#### 项目要点
- 使用列表而非段落
- 关键数据加粗
- 根因注明在括号内
```

### 跨域参考表格
```
| 维度 | 当前项目 | 行业基准 | 差距 |
|------|---------|---------|------|
| ...  | 实际值   | 对标值   | 评估 |
```

### 关于资产占位符的特别说明
- GLB模型文件如果file命令返回"JSON text data" = 肯定是占位符
- 3D游戏项目中90%的"好看不起效"问题根因是模型文件是假的
- 解决方案: 要么找真实模型(程序化生成如Three.js几何体), 要么glTF二进制替换

## Pitfalls

- ⚠️ 大项目审计不要深入每个文件的每行代码 — 先全面扫描后聚焦关键断裂点
- ⚠️ 物理引擎审计的关键问题永远是"这个body有没有加入world"
- ⚠️ 不要为了炫技而建议换引擎 — Web竞速游戏的核心问题是系统联通性不是引擎能力
- ⚠️ 赛车游戏的"车辆配置数据"可能很完整，但接入物理引擎的代码可能完全没写
- ⚠️ 格林主人极度厌恶"先回复再修" — 审计报告要一次性完整，附带解决方案
