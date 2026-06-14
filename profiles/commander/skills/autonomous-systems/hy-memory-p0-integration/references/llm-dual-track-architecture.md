# LLM双轨架构模式（Dual-Track Architecture）

## 模式定义

所有需要"智能判断"的系统模块都应采用双轨架构：
```
LLM路径(优先) -> try: LLM调用 -> 语义理解 -> 高质量结果
                     | 失败
规则路径(降级) -> except: -> 机械执行 -> 可靠兜底
```

## 适用场景

任何需要做"判断、评估、筛选、生成、理解"的模块都应该用双轨架构。
不需要LLM的场景：纯算术、文件IO、数据搬运、状态保持。

## 实现模板

```python
def some_judgment(self, input_data):
    # LLM路径（优先）
    llm_result = None
    try:
        import urllib.request
        payload = json.dumps({...}).encode()
        req = urllib.request.Request(...)
        with urllib.request.urlopen(req, timeout=10) as resp:
            llm_result = json.loads(resp.read())["choices"][0]["message"]["content"]
        return self._parse_llm_output(llm_result)
    except Exception:
        pass
    
    # Ollama降级
    if not llm_result:
        try:
            ...  # Ollama call
            return self._parse_llm_output(llm_result)
        except Exception:
            pass
    
    # 规则路径（降级）
    return self._rule_fallback(input_data)
```

## 超时策略

- 判断类（task_boundary/recall_filter）：5-10秒超时
- 生成类（episodic_summary/l1_extraction）：15-30秒超时
- 验证类（skillopt_validation）：30秒超时
- 所有LLM调用必须有try/except + timeout保护

## 降级原则

1. LLM降级 != 系统降级。系统始终正常运行，只是从精准降级到粗略判断
2. 降级应该被记录但不应该被当作"系统坏了"
3. 当前对话LLM永远是最终兜底——这是Hermes的核心优势
