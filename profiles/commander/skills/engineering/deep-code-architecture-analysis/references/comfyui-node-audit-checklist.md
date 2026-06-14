# ComfyUI 定制节点审计清单

针对 ComfyUI custom_nodes 的全面审计清单，适用于 reverse-engineering、代码审核、安全审计场景。

## 一、文件结构审计

| 检查项 | 说明 |
|--------|------|
| `__init__.py` 是否存在 | ComfyUI 通过 `__init__.py` 发现节点，没有这个文件节点不会被加载 |
| `NODE_CLASS_MAPPINGS` | 节点类必须在这里注册，键名作为节点ID |
| `NODE_DISPLAY_NAME_MAPPINGS` | 可选，显示友好的节点名称 |
| `WEB_DIRECTORY` | 可选，指向包含前端JS的目录（注意不带 `./` 前缀） |
| `__pycache__/` | 缓存文件不提交 |
| `requirements.txt` | 如果有第三方依赖，需要 |

## 二、节点类基础审计

```python
class MyNode:
    @classmethod
    def INPUT_TYPES(cls): ...
    RETURN_TYPES = (...)       # 必须是元组
    RETURN_NAMES = (...)       # 可选，必须是元组
    FUNCTION = "method_name"   # 入口方法名
    CATEGORY = "分类名"        # ComfyUI菜单中的分类
    OUTPUT_NODE = True/False   # 是否输出节点
```

### 检查点

- [ ] `RETURN_TYPES` 是元组不是列表（ComfyUI 会报错）
- [ ] 返回值数量与 `RETURN_TYPES` 数量一致
- [ ] 可选输出（可能返回 None）需要处理：用空 tensor `torch.zeros((0,...))` 而不是 None
- [ ] `INPUT_TYPES` 的参数类型声明是否正确（STRING/INT/FLOAT/BOOLEAN/IMAGE/etc）
- [ ] `CATEGORY` 是否有统一命名空间

## 三、IS_CHANGED 行为审计

```python
@classmethod
def IS_CHANGED(cls, **kwargs):
    return time.time()  # 每次强制重跑
```

| 返回值 | 行为 | 适用场景 |
|--------|------|----------|
| `float("NaN")` | 每次都重跑（**推荐** - 不缓存） | 随机生成、AI调用 |
| `time.time()` | 每次都重跑（可能引起额外刷新） | 同上，但会触发UI重绘 |
| 固定值 | 参数不变就不重跑 | 确定性的转换/过滤节点 |
| `hash(str(kwargs))` | 参数变化时才重跑 | 需要缓存的节点 |

**注意**: 如果节点做了大量 API 调用（LLM），不设置 IS_CHANGED 或返回 NaN 会导致参数没变也每次都重跑。对于非随机节点，应该基于参数hash做缓存。

## 四、单文件/单体巨类审计

ComfyUI 的 `__init__.py` 很容易膨胀成 1000+ 行单体文件。

### 危险信号

- [ ] 单文件超过 500 行
- [ ] 多种模式/模式间的逻辑全部写在一个类里
- [ ] 重复的 system prompt 构建代码
- [ ] 无版本号或版本号不一致（文件头 vs NODE_DISPLAY_NAME vs 注释）
- [ ] 无法被外部测试（所有逻辑在节点实例方法中）

### 推荐拆分结构

```
custom_nodes/MyNode/
├── __init__.py       # 节点注册，轻量入口
├── node.py           # 主节点类（INPUT_TYPES + get_prompt）
├── modes/            # 各模式处理逻辑
│   ├── __init__.py
│   ├── storyboard.py
│   ├── child.py
│   └── design.py
├── llm.py            # AI调用封装
├── utils.py          # 文件扫描/过滤/缓存工具
└── web/              # 前端扩展
    └── MyNode.js
```

## 五、输入参数审计

ComfyUI 参数类型：

| 参数类型 | 说明 | 常见坑 |
|----------|------|--------|
| `"STRING"` | 文本框 | `multiline: True` 不要忘了 |
| `"INT"` | 整数 | 不要用 FLOAT 当 INT 用 |
| `"FLOAT"` | 浮点数 | `step`, `min`, `max` 参数 |
| `"BOOLEAN"` | 开关 | 默认值要明确 |
| 列表 `["a","b"]` | 下拉菜单 | 默认值必须在列表中 |
| `"IMAGE"` | 图片tensor | 从可选输入接收 |
| `"*"` | 任意类型 | 慎用，影响类型推断 |

### 常见问题

- [ ] 参数数量过多（20+ 参数会影响 UI 可用性）
- [ ] optional 参数塞在 required 里（应该用 `"optional": {...}`）
- [ ] 长字符串默认值占 UI 空间过多
- [ ] 参数依赖关系未处理（参数A选"模式X"时，参数B才需要出现）

## 六、线程安全审计

ComfyUI 的执行管道可以并行处理多个队列任务。

- [ ] 实例变量（self.cache / self.state）是否线程安全
- [ ] 是否使用了 threading.Lock
- [ ] 加锁范围是否足够覆盖所有读写
- [ ] `random.seed()` 在并行执行中会互相污染
- [ ] 静态类变量/全局变量是否被多个节点实例共享

**注意**: 一个 ComfyUI 工作流中的同一个节点可能出现多次。每次执行创建独立实例，但 `IS_CHANGED` 和 `INPUT_TYPES` 是 `@classmethod`，共享类级状态。

## 七、AI/LLM 调用审计

当节点使用 HTTP API 调用 LLM 时：

- [ ] URL 硬编码还是通过 widget 传入（应该用widget传入）
- [ ] API key 安全性（是否明文存储在 workflow JSON 中——ComfyUI节点参数会写入workflow文件）
- [ ] 超时处理（必须设置 timeout，默认不设置可能无限等待）
- [ ] 重试机制（至少 3 次 + 指数退避）
- [ ] 流式/同步选择（同步 urllib.request 会阻塞 ComfyUI 执行线程）
- [ ] 错误回退（API 失败后是出空输出还是用规则引擎降级？）
- [ ] 最大 Token 限制（用户可控还是硬编码？）

**注意**: urllib.request 是同步阻塞调用。在 ComfyUI 事件循环中长时间同步调用会影响整体性能。考虑改用 `asyncio` + `aiohttp` 或在后台线程中调用。

## 八、前端JS扩展审计

ComfyUI 通过 `registerExtension` 注册前端扩展：

- [ ] 是否在 `onNodeCreated` 中使用 `requestAnimationFrame`（保证DOM就绪）
- [ ] DOM widget 的 `computeSize` 是否正确（否则节点UI会变形）
- [ ] 图片上传路径是否正确（`/upload/image`）
- [ ] widget 值是否与后端同步（序列化/反序列化）
- [ ] node.computeSize 重写是否覆盖所有widget的高度
- [ ] 大量的 DOM 操作是否导致 UI 卡顿

### 常见前端坑

- `import { api } from '../../scripts/api.js'` 路径是否正确（ComfyUI前端路径）
- 删除图片后是否同步 widget 值
- 刷新后是否能 restore 已上传的图片预览
- 多个节点实例的 DOM 状态是否隔离

## 九、性能审计

| 指标 | 警戒线 |
|------|--------|
| `__init__.py` 文件大小 | > 50KB 应拆分 |
| 单类行数 | > 500 行应拆分 |
| API调用超时 | > 30秒应考虑异步 |
| 参数数量 | > 15 个应考虑分组参数 |
| 文件扫描大小 | 应设上限（如 50MB） |

## 十、常见安全问题

- [ ] `eval()` / `exec()` —— 绝对禁止
- [ ] 文件路径注入 —— 用户可控路径是否做了白名单
- [ ] API key 写入 workflow 文件 —— workflow 是 JSON，API key 明文存储
- [ ] 服务端请求伪造（SSRF）—— 用户提供的 API URL 是否会请求内网
- [ ] XSS —— JS 端 `innerHTML` 是否引入了未转义的用户输入

## 十一、死代码/闲置资源检查

- [ ] `__init__.py` 中定义的常量/变量是否有被引用
- [ ] 数据文件（.md/.txt 等）是否被代码引用
- [ ] 方法是否被调用（grep 方法名）
- [ ] `import` 是否多余
- [ ] try-except 是否过于宽泛（裸 `except:`）

## 十二、产出物模板

审计完成后输出：

```markdown
# ComfyUI 节点审计报告

**节点**: XXX
**版本**: VX.X
**文件**: __init__.py (N行, NKB)
**核心逻辑**: 单文件/已拆分

## 功能覆盖
| 功能 | 状态 | 说明 |
|------|------|------|

## 代码质量评分
- **功能性**: N/10
- **代码质量**: N/10
- **前端交互**: N/10
- **可维护性**: N/10
- **健壮性**: N/10

## 严重问题 (🔴)
## 中等问题 (🟡)
## 小问题/建议 (🟢)

## 优先级建议
```
