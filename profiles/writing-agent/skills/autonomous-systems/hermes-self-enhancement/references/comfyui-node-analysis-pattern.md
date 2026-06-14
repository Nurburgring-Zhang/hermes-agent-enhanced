# ComfyUI Custom Node分析 — PromptLibraryNode V10 实战案例

## 源文件
`D:\Hermes\1000000提示词\PromptLibraryNode\__init__.py` (385行)

## 节点功能概述
读取文件夹内多份TXT文档 → 按模式选取 → 按行输出 → 智能过滤

## 现有代码质量评分: 7/10

### 优点
- 7级关键词库(200+词,中英文双语)
- 英文\b边界匹配 + 中文包含匹配双引擎
- 100次重试熔断机制(防卡死)
- 全局缓存跨调用保持(不是每次重新读文件)
- 熔断时输出最后尝试内容(而不是空字符串卡死工作流)
- 三种模式(Random/Sequential/Shuffle)
- 三种循环(Infinite/Stop at End/No Repeat 20条)

### 核心代码结构
```
get_prompt() → _get_file_list() → _get_state()(global cache) → 
    _fetch_next_prompt()(line selection) → 
    _is_prompt_valid()(7-level keyword filter, 100 retries)
```

### 严重不足(8项)
1. 只支持单扩展名 — 不能同时读.txt+.csv+.md+.jsonl
2. 无输出格式控制 — 不能加前缀/后缀/模板包装
3. 无统计信息输出 — 不知道总量/进度
4. 无文件分类/标签 — 不能按文件夹名筛选
5. No Repeat不持久化 — 重启ComfyUI后丢失
6. 无权值系统 — 所有行平等对待
7. 无关键词搜索 — 只能全量输出不能筛选
8. 单输出接口 — 只能输出STRING,无元数据

## PRO版增强方案(385行→612行)

### 新增功能

| 功能 | 实现方式 | 行数 |
|------|----------|------|
| 多扩展名 | `file_extensions`参数,逗号分隔 | +5 |
| 标签系统 | 文件夹名自动作为tags,支持`tag_filter` | +30 |
| 权重系统 | 行首`#[weight=2.0]`或`#3x`语法 | +25 |
| 关键词筛选 | `keyword_filter`参数,多关键词AND | +20 |
| 模板变量 | `{prompt}/{file}/{line}/{date}/{time}/{timestamp}/{random}/{folder}` | +30 |
| 多输出接口 | prompt + metadata_json + file_name + total_count | +10 |
| 批量输出 | `output_count=N`,一次取N行 | +35 |
| 组合模式 | Separate Lines / Combined Block / Random Choice | +15 |
| 持久化历史 | `.prompt_history.json`文件,重启不丢 | +20 |

### 关键设计决策
- **不破坏现有接口**: 原`get_prompt`保留,增强版用`get_prompt_pro`
- **向后兼容**: 旧版参数都有默认值,新参数都是optional
- **文件级增量扫描**: `os.walk`每次调用重新扫描，运行时添加的文件即时可见

## 分析方法论(可复用于任意节点分析)

### 第一步: 读取完整代码
```bash
cat __init__.py | wc -l  # 了解规模
```

### 第二步: 识别核心接口
```python
INPUT_TYPES()  # 输入参数定义
RETURN_TYPES / RETURN_NAMES  # 输出接口
FUNCTION  # 主函数名
CATEGORY  # 分类
```

### 第三步: 追踪数据流
```
输入参数 → 主函数 → 辅助函数A → 辅助函数B → ... → 输出
```

### 第四步: 评估质量
- 错误处理: try/except覆盖所有文件操作?
- 状态管理: 跨调用状态如何保持?重启后丢失吗?
- 熔断机制: 失败时输出什么?能卡死工作流吗?
- 性能: 每次调用都重新读文件吗?有缓存吗?

### 第五步: 识别6类问题

| 类别 | 典型问题 | 严重度 |
|------|----------|--------|
| 🔴 功能缺失 | 缺少核心用户需求的功能 | critical |
| 🟡 设计缺陷 | 扩展性差/耦合高/状态丢失 | medium |
| 🔵 性能问题 | 重复I/O/O(n²) | medium |
| 🟢 可用性 | 没有进度/没有错误提示 | low |
| ⚪ 代码质量 | 类型注解/注释/命名 | low |
| 🛡️ 安全 | 路径穿越/注入/硬编码 | critical |

### 第六步: 编写增强方案
- 不破坏现有功能(向后兼容)
- 新功能用optional参数
- 优先解决critical和high问题
