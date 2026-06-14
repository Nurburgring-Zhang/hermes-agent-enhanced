# write_file 截断陷阱

## 问题场景

**`write_file` 工具在接收短内容（如空字符串或几行文本）写入大型现有文件时，会直接覆盖为短内容。** 文件之前的内容被完全丢失，没有任何确认或警告。

## 触发条件

- 读取了一个大型文件（如 >1500 行 Python 文件）
- 用 `offset`/`limit` 分页读取（partial view）
- 工具提示 `"was last read with offset/limit pagination (partial view). Re-read the whole file before overwriting it."`
- 调用 `write_file` 写入短内容 → 文件被截断

## 为什么危险

- 普通人对 `write_file` 的直觉是"追加"或"只写入给我的部分，其他部分不变"
- 实际行为是完全覆盖整个文件
- 当分页读取文件后再次写入，以前的内容不在上下文窗口中，**在数据消失前没有任何工具会报错**
- 测试脚本通常验证的是截断后的空文件语法，测试通过但文件是空的

## 避免方法

1. **永远不要对已有大型文件使用 `write_file`** — 用 `patch`（修改特定行）或 `read_file`+`patch` 组合
2. **`patch` 比 `write_file` 安全** — 只修改匹配的文本块，不删除其他内容
3. **如果必须重写整个文件**，先 `cp` 备份：
   ```bash
   cp __init__.py __init__.py.bak
   ```
4. **分页读取后如果要写**，在写入前做一次全量读取确认内容完整：
   ```bash
   wc -l __init__.py   # 确认行数正确
   head -5 __init__.py # 确认头部内容
   ```
5. **写入后立即检查**：
   ```bash
   wc -l __init__.py && python3 -c "import ast; ast.parse(open('__init__.py').read()); print('OK')"
   ```

## 事故恢复路径

如果 `__init__.py` 已被清空：

```bash
# 检查备份（优先级从高到低）
# 1. 检查同目录 .bak 文件
ls -la *.bak

# 2. 检查 git stash
git stash list

# 3. 如果 .bak 存在但版本较老（如500行 vs 1650行）
cp __init__.py.bak __init__.py

# 4. 用 delegate_task 并行重建：
#    区块1 → 区块2 → 区块3
#    每个区块独立写文件，然后语法验证，最后合并

# 5. 验证
python3 -c "import ast; ast.parse(open('__init__.py').read()); print('✅ syntax OK')"
```

## 历史案例

2026-05-22: PromptLibraryNode `__init__.py` (1650行, 78KB) 被 `write_file(content="")` 清空。备份文件 `__init__.py.bak` 只有500行早期版。通过 `delegate_task` 并行重建+手动修补恢复为1314行完整版。从事故到恢复耗时约5分钟。
