# 子Agent分批执行模式

## 为什么分批

当有8+个子Agent任务时，不能全量提交。原因：
1. delegate_task最多并行3个
2. 第一批的结果可能影响第二批的范围
3. 中间验证及时发现问题，避免8个全写完再排查

## 分批模式

```python
# Batch 1 (3 agents): Phase1+Phase2+Phase3 → 验证全部通过
# Batch 2 (3 agents): Phase4+Phase5+Phase6 → 验证全部通过
# Batch 3 (2 agents): Phase7+Phase8 → 验证全部通过
```

## 每批验证清单

1. 语法检查: `python3 -c "import..."` 验证
2. 功能验证: 直接调用新函数检查返回值
3. 回归检查: `grep -rn 旧模式` 确保无残留
4. 冲突检查: 确认多个子Agent没有改同一个文件
5. R14状态报告检查

## 子Agent输出核实（关键陷阱）

- 子Agent声称"已写入文件"后 → **必须在本Agent侧验证文件真实存在**
- 子Agent声称"已修改"后 → **必须用grep检查旧模式是否被移除**
- 子Agent说"文件不存在"时 → **必须亲自确认**
- 子Agent的import路径可能在子Agent环境中正确但在父Agent环境中不正确（如 `from ministry_abc import X` vs `from scripts.ministry_abc import X`）→ 必须检查实际路径

## 并行冲突模式

| 冲突类型 | 表现 | 预防 |
|---------|------|------|
| 同一文件重复定义 | 多个子Agent修改同一个文件，产生重复函数 | 每个文件只允许一个子Agent修改 |
| 旧代码残留 | 新代码插入后旧版未清理 | patch后grep检查重复定义 |
| HTML_TEMPLATE串联覆盖 | 多个注入累积花括号问题导致整个script不执行 | 所有前端变更合并为一次写入 |
| 端口占用 | 旧进程未杀干净，新进程绑定失败 | 1) pkill -f杀干净 2) 启动后curl /api/v1/health验证 |
