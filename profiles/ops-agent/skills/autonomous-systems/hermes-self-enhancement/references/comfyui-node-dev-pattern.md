# ComfyUI节点开发实战模式
## 从本会话(2026-05-18/19)实战验证

### 开发流程

```
需求理解 → 逆向分析现有节点代码 → 提取核心模块 → 
增强设计 → 完整实现 → 逐行代码审核 → 
功能测试(每项功能独立验证) → 迭代优化 → 最终验收
```

### 关键原则

1. **永远不要从头写**: 逆向现有实现, 提取已验证的模块
2. **保留原有注册接口**: `NODE_CLASS_MAPPINGS` + `NODE_DISPLAY_NAME_MAPPINGS` 必须完全兼容
3. **PyTorch Module命名**: 避免Python关键字(`nonlocal`是保留字!→用 `nl_attn`)
4. **ComfyUI tensor格式**: `(B,H,W,C)` NHWC格式, 值域[0,1], float32
5. **模型推理格式**: `(B,C,H,W)` NCHW格式, 值域[0,1], float32

### PromptLibraryNode PRO 案例

- 原始: 385行 V10, 单扩展名, 无过滤, 无模板, 无标签
- 增强: 808行 PRO版, 多扩展名, 4级过滤+安全词豁免, 模板变量, 标签系统, 加权权重
- 核心: 47个类/函数, 9种注意力机制, 13种放大模式
- 测试: 45项全通过 100%

#### 关键增强点

| 功能 | V10 | PRO | 实现 |
|------|-----|-----|------|
| 扩展名 | 仅.txt | .txt,.csv,.md,.jsonl | `file_extensions`逗号分隔 |
| 过滤 | 内置7级词库 | +食物/饰品/室内/浴室(4级黑名单) | `BLOCKED_*`类变量 |
| 安全词豁免 | 无 | "orange cat"不误伤 | `SAFE_WORDS_FOR_FOOD` + 豁免逻辑 |
| 模板变量 | 无 | {prompt}/{file}/{line}/{date}/{time}等8个 | `_apply_template()` |
| 标签系统 | 无 | 文件夹名自动标签+tag_filter | `_scan_files()`返回tags |
| 权重语法 | 无 | #[weight=2.0] / #3x | 正则解析 + Weighted Random模式 |
| 输出接口 | 1路STRING | 5路(prompt+metadata+source+count+total) | `RETURN_TYPES`5个 |
| 持久化历史 | 会话级 | `.prompt_history.json`文件 | `_apply_history_dedup()` |
| 多行输出 | 1行 | 1-20行+组合模式 | `output_count` + `combine_mode` |

### FinalUltraFusion 超分节点案例

- 位置: `upscale/FinalUltraFusion/__init__.py`
- 行数: 1092行
- 算法: 9种AI + 4种基础 = 13种模式
- 注意力: 8种(CA/ECA/SA/WA/OCA/CAL/SAL/NLA)并行计算+自适应融合
- 增强: 多尺度高通滤波(3/5/7) + RRDB前端 + Transformer后端

#### 算法调度

```python
def get_algorithm(name, scale, device):
    nl = name.lower()
    if 'ultra' in nl or 'fusion' in nl:
        model = UltraSR(dim=192, num_blocks=8, scale=scale)
    elif 'dat' in nl and 'm' in nl:
        model = MDAT(dim=180, num_blocks=6, scale=scale)
    # ... 其他算法映射
    model.to(device).eval()
    _algorithm_instances[key] = model  # 全局缓存
```

#### 分块处理

```python
def tiled_process(img_tensor, process_fn, tile_size=512, overlap=32):
    # 大图分块避免OOM
    # 权重渐变融合减少接缝
    # 每块后清空CUDA缓存
```

### 测试方法论

1. **语法检查**: `ast.parse(open(file).read())`
2. **导入测试**: `importlib.util.spec_from_file_location + exec_module`
3. **功能测试**: 每个参数组合 + 边界条件
4. **种子一致性**: 相同seed→相同输出
5. **过滤测试**: 直接测试_filter方法(不依赖管道)
6. **ComfyUI兼容**: NODE_CLASS_MAPPINGS / RETURN_TYPES / CATEGORY 完整

### 常见陷阱

1. `nonlocal` 是Python保留字 → 用 `nl_attn`
2. 中文字符在YAML frontmatter中需引号包裹 → `description: "中文..."` 
3. shell heredoc内的Python代码中不能有单引号冲突 → 用独立文件
4. ComfyUI tensor是NHWC, PyTorch模型需要NCHW → 使用 `nchw_to_nhwc`/`nhwc_to_nchw` 工具函数
5. `self.lrelu()` 写法必须慎重 → 要么在`__init__`中定义`self.lrelu`, 要么直接 `F.leaky_relu()`
