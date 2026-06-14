# Hy-Memory 全链路审计方法论

## 问题

部署Hy-Memory集成脚本后，发现6个DB列名不匹配/查询错误/导入缺失等问题。根源：脚本假设的DB schema与现有active_memory.db的schema不一致。

## 系统性审计方法

### Step 1: 脚本完整性检查
```bash
# 检查所有预期脚本是否存在
scripts_dir=~/.hermes/scripts
for s in l1_extractor.py l2_scene_scheduler.py l3_persona_scheduler.py \
         tool_unloader.py tool_wrapper.py auto_recall.py wake_injector.py \
         hy_memory_orchestrator.py task_boundary.py episodic_injector.py \
         mermaid_builder.py emergency_compressor.py; do
  [ -f "$scripts_dir/$s" ] && echo "✅ $s" || echo "❌ $s"
done
```

### Step 2: DB schema vs 脚本SQL断言检查
```python
# 核心方法：对比PRAGMA table_info()的输出与脚本中的SQL语句
import sqlite3
conn = sqlite3.connect("~/.hermes/active_memory.db")

# 获取实际列名
cur = conn.cursor()
cur.execute("PRAGMA table_info(memory_scene)")
actual_cols = {c[1] for c in cur.fetchall()}

# 遍历脚本文件，搜索SQL中的列名引用
# 每个UPDATE/INSERT语句中引用的列名必须 ∈ actual_cols
# 常见的错误模式：
#   "keywords" vs "tags"      → memory_scene
#   "updated_at" vs "last_activated" → memory_scene  
#   "created_at" → memory_episodic可能没有此列
```

### Step 3: 逐脚本运行测试
```bash
# L2 check
python3 l2_scene_scheduler.py check
# L3 check  
python3 l3_persona_scheduler.py check
# Orchestrator check
python3 hy_memory_orchestrator.py check
# Wake injector
python3 wake_injector.py
# Tool unloader（模拟>2KB结果）
python3 -c "from tool_unloader import ToolUnloader; u=ToolUnloader(); print(u.intercept_tool_result('test',{},'X'*3000))"
```

### Step 4: 全链路语法检查
```bash
for f in *.py; do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" && echo "✅ $f"
done
```

### Step 5: 常见DB schema不匹配模式

| 脚本中使用的列名 | 实际DB列名 | 影响的表 |
|:----:|:----:|:---|
| `keywords` | `tags` | memory_scene |
| `updated_at` | `last_activated` | memory_scene |
| `created_at` (in WHERE) | 可能NULL | memory_episodic |
| `rowid` | `id` | memory_scene |

### 修复后的验证标准
- 所有13个核心脚本（含`llm_bridge.py`）语法检查通过
- L2 check 输出场景信息，无Traceback
- L3 check 输出画像信息，无Traceback
- Orchestrator check 无DB错误（特别注意`memory_episodic.created_at`）
- wake_injector 返回非"No injection"（修复：无user_input时注入persona）
- tool_unloader 拦截>2KB结果并写入refs
- `llm_bridge.py` 自身语法通过，`llm_simple("test", fallback="ok")` 返回"ok"（fallback路径）
- 自进化引擎 `self_evolution_engine.py` 语法通过，`evolve_skills()` 集成SkillOpt验证门
- **实际数据审计**（不只是语法）：查数据库表count，查wake_guide字段，查boundary_history记录数，查refs/offload文件
- **cron审计**：每2h L1 / 每6h L2+SkillOpt / 每天2am risks / 每天3am cleanup / 每天3:30am evolution / 每天5am L3
