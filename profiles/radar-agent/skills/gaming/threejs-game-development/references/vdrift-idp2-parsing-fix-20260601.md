# Session: 2026-06-01 VDrift IDP2解析修复 + 摩擦圆物理

## 背景
毛绒竞速(PlushRacingGame)的13辆VDrift模型JOE→JSON转换一直错误：
- v8: 使用错误的局部索引假设,导致顶点膨胀(2343v 2089t)→大量重复顶点
- v9: 改用全局索引,但第三个uint32(nnorm)不可靠,且法线/纹理数据错位
- v10: 加入索引边界检查和nnorm保护,但仍有大量面被跳过
- v12: 自动从剩余字节推导法线数,13辆车全部正确转换

## IDP2格式真相

| 字段 | 可靠性 | 说明 |
|------|--------|------|
| `num_faces` (header) | ✅ | 面总数 |
| `num_frames` (header) | ✅ | 帧数,通常是1 |
| `flags` (header) | ❌跳过 | 可能含压缩/存储信息 |
| `v0,v1,v2` (face) | ✅ | 全局顶点索引 |
| `n0,n1,n2` (face) | ✅ | 全局法线索引 |
| `t0,t1,t2` (face) | ✅ | 全局纹理索引 |
| `num_verts` (1st uint32) | ✅ | 顶点数 |
| `num_texcoords` (2nd uint32) | ✅ | 纹理坐标数 |
| 3rd uint32 | ❌**不可靠!** | 非法线数!实际值是法线数据中第一个float的二进制 |
| 顶点数据 | ✅ | 12B每个: 3个float(x,y,z) |
| 法线数据 | ✅ | 从剩余字节推导: 12B每个,值±100内 |
| 纹理数据 | ✅ | 8B每个: 2个float(u,v) |

## 关键发现: 第三个uint32不可靠
C++代码读作num_normals并做了ENDIAN_SWAP_32转换。但在所有13辆车中,这个值都是32亿左右(0xBExxxxxx),对应法线数据第一个float的二进制表示。`实际法线数 ≈ 纹理坐标数`。

## 法线数自动推导算法
```python
remaining = len(raw) - pos_after_verts
max_norm = remaining // 12  # 剩余字节全做12B/组能读多少

# 候选1: num_tex_input(第二个uint32)
# 候选2: max_norm(全部做法线)
# 候选3: max_face_normal_index + 1
for candidate in [num_tex_input, max_norm, max_ni + 1]:
    if 0 < candidate <= max_norm:
        读取candidate个法线,验证每个值在±100内
        if 全部通过:
            n_norm = candidate
            break
```

## 模型破碎的多种根因

| 症状 | 根因 | 修复 |
|------|------|------|
| 一条竖线(bbox: x≈0,z≈0,y=0~2.3) | Z-up→Y-up转换错把x,z,y当(x,z,-y) | 改为`z=-z`(只有z取反) |
| 巨大的模型顶点(349689) | 越界索引保护返回(0,0,0)但解析算法错了 | 清洗: abs(x)<100才保留 |
| 破碎拼接的几何体 | 顶点索引引用了不存在的顶点 | 索引越界检查+跳过无效面 |
| 大部分顶点为(0,0,0) | JOE格式面先读,但顶点读完没读到正确的法线 | 自动推导法线数,不回信第三个uint32 |
| "一团黑乎乎乱的几何体" | vmap去重把错误索引映射成大量畸形顶点 | 全局索引(vi = face[j])而非局部(fi*3+j) |

## 物理滑冰修复

| 症状 | 根因 | 修复 |
|------|------|------|
| 车身像滑冰/乱转 | 侧向摩擦力不足,mu=1.0偏低 | mu提升到1.2;侧滑抑制从比例抑制改为强抓地力 |
| 按S加速/不刹车 | `netForceLong = drive - brake`中brake为正值,`-=负数=加速` | 刹车独立做速度比例减速,不参与推力公式 |
| 按W左偏 | 视觉方向`atan2(vel.x, vel.z)`在Z-前进时返回PI,车身旋转180度 | `-Math.atan2(...)` |
| W闪到赛道外 | 第一帧位置突变(velocity从0跳到高速后被积分) | 位置更新加保护:新位置与旧位置差<50才更新 |

## 车轮旋转一致性（统一wheelGroup方案）

**所有车轮部件必须放在同一个wheelGroup中,整体旋转,不能各自单独旋转。**

```typescript
const wheelGroup = new THREE.Group();
wheelGroup.rotation.z = Math.PI / 2;  // 一次旋转,所有部件跟随

// 所有子物体以默认朝向(Y轴)生成,加到wheelGroup:
wheelGroup.add(tire);       // LatheGeometry(默认绕Y)
wheelGroup.add(hub);        // CylinderGeometry(默认沿Y)
wheelGroup.add(outerRing);  // TorusGeometry(默认绕Z)
wheelGroup.add(spoke);      // BoxGeometry(默认沿Y)
wheelGroup.add(disc);       // CylinderGeometry(默认沿Y)

// 然后wg.add(wheelGroup)
wg.add(wheelGroup);
```

**绝对不要**单独对各部件做rotation.z/hub.rotation.z/tire.rotation.z等——用户会反映"轮毂朝向错了/刹车盘朝向错了"。

**关键确认**: `rotation.z = PI/2` 是正确的。`rotation.x = PI/2` 是错误的(让轮胎竖直)。

## 可用脚本
- `scripts/convert_v12.py` — 当前可用的JOE→JSON转换器(自动推导法线数)
- `scripts/convert_v11_obj.py` — 导出OBJ格式供Blender验证

## 遗留问题
- 部分模型(TL2)只有249个三角面,明显少于其他车(1000-7000) → 可能索引越界过多导致面被跳过
- 没有纹理坐标的模型(glass.joe等少数文件)需要特殊处理
