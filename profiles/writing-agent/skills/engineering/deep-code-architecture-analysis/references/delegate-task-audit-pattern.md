# delegate_task 大规模代码审计模式

当需要审计一个代码库中大量文件（10+文件，数千行代码）时，标准做法是逐个 `read_file` 但太慢太卡 token。

## 替代方案：委托子Agent批量审计

```
delegate_task(
    goal="全面审计 [...] 按照功能清单逐项核实真实实现程度 [...]",
    context="项目路径: /xxx/backend/",
    toolsets=["terminal","file","web"]
)
```

### 适用场景
- 需要阅读 10+ 个文件，且每个文件不短（1000+行）
- 需要横跨多个目录的文件
- 需要比"读了文件"更深入的判断（是否真实实现？是否有mock？参数维度是否完整？）

### 子Agent的审计粒度要求

在 goal 中指定每个文件的审计项（越精确越好）：

```
对于每个功能，报告：
- 文件大小和行数
- 是否包含真实的API调用代码（非mock/placeholder）
- 支持的生成类型列表
- 支持的参数维度
- 与ComfyUI的集成方式
- 降级/模拟代码占比（百分比估算）
```

### 已知限制
- 子Agent没有对话记忆，所以所有文件路径必须交代清楚
- 子Agent的 `terminal` 是在独立沙箱中工作，路径正确性需确认
- 子Agent返回的总结是其"自称"完成的工作——需要对关键发现做交叉验证

### 交叉验证方法
子Agent返回后，对其中提到的关键发现做抽样验证：
```bash
# 如果子Agent说"file X有Y功能"
grep -n "function_signature\|class_name" /path/to/file | head -5

# 如果子Agent说"mock占比10%"
grep -c "mock\|simulate\|placeholder" /path/to/file
```
