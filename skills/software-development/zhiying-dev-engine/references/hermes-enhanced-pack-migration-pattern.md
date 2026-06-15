# Hermes Agent Enhanced — 多轮商业级打磨模式

## 写文件陷阱

write_file 是全文替换不是插入。对已存在的大文件(>500行)用write_file会丢失全部未包含内容。
- 小文件/新文件: write_file
- 精确修改已存在文件: patch
- 大文件write_file = 数据丢失（实战: memory_engine.py 943行→23行，需git checkout恢复）

## 项目迁移模式

从 hermes-enhanced-pack 迁移17系统:
1. `comm -23 <(ls src/) <(ls dst/)` 逐目录diff找独有文件
2. 复制 + `grep -rn "from core\."` 修复import路径
3. 逐文件 `python3 -c "from scripts.X import *"` import验证
4. CI回归确认零退化
5. 多轮打磨: R1代码→R2框架→R3补全→R4性能→R5文档→R6门禁→R7安全→R8清理→R9测试→R10集成

## E2E真实运行验证

代码通过import≠系统可用。必须8层E2E:
L1规则引擎→L2弹性(熔断CLOSED→OPEN)→L3安全(拦截+放行+脱敏)→L4 Agent→L5引擎→L6 Loop→L7观测→L8恢复
真实调用API（非import），容忍名称差异，报告真实通过率。

## 子Agent超时处理

delegate_task超时≠没干活。Agent可能在600秒内完成了实际工作（已验证：pyproject修复+shell=True+gitignore在超时前完成）。检查文件修改时间确认。
