# Nanobot Factory 审计案例 — 150,000行深度逐行审核

## 项目规模
- 后端 ~100,000行 Python
- 前端 ~50,000行 React/TypeScript
- 测试 ~5,000行
- 总计 ~150,000行 / ~130个文件

## 审核方法
1. 并行启动3-4个 delegate_task leaf subagents 同时审核不同模块
2. 每个子Agent逐行读取文件，交叉引用API，检查调用链
3. 自己亲自操作浏览器验证前端页面是否真实可用
4. 汇总发现时做 **代码真实度分类**（见下方）

## 审核结果

### 问题统计
- 🔴CRITICAL: ~55个（运行时崩溃/数据丢失）
- 🟠HIGH: ~90个（功能错误/接口不匹配）
- 🟡MEDIUM: ~140个（代码质量/潜在风险）
- **总计: ~285个**

### 致命问题TOP 10
| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | 评分全部是random.uniform | server.py | 数据不可信 |
| 2 | 44个算子43个不调用AI模型 | core/operators_lib.py | AI功能全占位符 |
| 3 | seedance.generate_video不发送HTTP | llm_client.py:1274-1559 | 视频生成永远挂起 |
| 4 | 4处async with ClientSession关闭后使用 | aigc.py:342-741 | 运行时崩溃 |
| 5 | agent/~10,500行代码从未被server.py导入 | agent/ | 空中楼阁 |
| 6 | functions/6文件只有注册无执行 | functions/ | 全是壳 |
| 7 | 三套独立SQLite数据库不互通 | database_manager.py | 数据碎片化 |
| 8 | AIGC生成写入"placeholder"文本文件 | enterprise_api.py | 生成功能假 |
| 9 | 前端6个生成功能全setTimeout模拟 | src/renderer/ | AIGC前端壳 |
| 10 | OMNIGEN_AVAILABLE等7个变量未定义 | server.py | 端点永远不可用 |

### 代码真实度分类结果
| 分类 | 比例 | 说明 |
|------|------|------|
| ✅ 真实实现 | ~40% | database.py SQLite持久化, data_pipeline本地处理, tests |
| ⚠️ 骨架实现 | ~20% | agent/模块结构完整但没接入, integrations/ |
| ⬜ 静态数据 | ~10% | 前端AIGC控制台数字硬编码 |
| 💀 空中楼阁 | ~15% | agent/模块 |
| 🧱 壳 | ~5% | functions/ |
| 🔌 未接通 | ~10% | 前端startGeneration()浏览器未定义 |

## 关键审计模式

### 1. 一定要在浏览器里点按钮
读server.py代码发现startGeneration()不存在，但真正确认"按钮点了没反应"是在浏览器里 `typeof startGeneration === 'function'` 返回false的时候。

### 2. 一定要track导入链
从server.py的 import 链出发，查出：
- server.py import → llm_client.py ✅
- server.py import → agent/ ❌（完全不引用）
- server.py import → integrations/ ❌（完全不引用）

这才发现了15,000行"空中楼阁"代码。

### 3. 三把锁验证法
对每个声称是"持久化"的模块：
1. 读代码：找到 INSERT INTO / write / save 语句
2. 跑代码：启动服务后看DB文件是否被创建
3. 重启测：服务重启后数据是否还在

### 4. 类似项目中最常见的5个模式
1. "我有44个算子"→43个不调AI（声明≠实现）
2. "我有5个功能模块"→3个是壳（注册≠执行）
3. "前端按钮能点"→点了没反应（UI≠功能）
4. "评分是用AI做的"→用了random（注释≠代码）
5. "模块已集成"→从未被主入口导入（存在≠集成）
